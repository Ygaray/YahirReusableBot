# Phase 3: Reusable public-surface footguns - Context

**Gathered:** 2026-07-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden the hub's public surface against nine footguns that are **unreachable in WeatherBot today
but guaranteed to bite the next consumer** — each with a RED-first regression test against a
hub-assertable observable, GATE-01 (full suite + import-hygiene / litmus / grimp) staying green.
This is the hub's entire reason to exist (ROADMAP §"Phase 3").

The nine findings, at their **verified** locations (the `HUB-HARDENING-REPORT` line numbers have
drifted — Phase 2 confirmed this; use these):

| Finding | Verified location | Defect |
|---|---|---|
| **MATCH-01 (H06)** | `registry/match.py:59-61` | `rest = stripped[len(spec.name):]` slices the **un-folded** original with the **folded** keyword length → mis-slice when input casefold changes length (`ß`→`ss`, `ﬁ`→`fi`). |
| **MATCH-02 (H13)** | `registry/match.py:59` (validate at `registry.py:39-48`) | `spec.name` compared raw against folded input, no registration-time validation → empty name claims blank input; uppercase name is permanently unmatchable. |
| **RELY-02 (H09)** | `reliability/retry.py:165` | `step = burst_spread_s / (burst_size - 1)` raises `ZeroDivisionError` when `burst_size == 1`; the `== burst_size` early-return (`:161`) only shields the first attempt. |
| **RELY-03 (H10)** | `reliability/retry.py:161` | `two_burst_wait` fires its mid-pause at `attempt_number == burst_size`, **blind to the stop bound** → a standalone caller pairing it with its own `stop_after_attempt(N)` desyncs the mid-pause. |
| **DISC-05 (H11)** | `discord/panelkit.py:309` | `interaction.user.bot`/`.id` dereferenced with no None guard → `AttributeError` raised **outside** `View.on_error`'s reach. |
| **DISC-06 (H12)** | `discord/panelkit.py:157-192` (`PanelKit.__init__`) | `marker` required but unvalidated; `cid.startswith("")` is always True → `is_owned_panel` claims every bot-authored pin, so `summon_panel` could delete unrelated pins. |
| **LIFE-02 (H14)** | `lifecycle/identity.py:76,83` | `os.close(fd)` at `:76`, then the except-path re-closes at `:83`; a reused fd integer means the guarded close hits an **unrelated** descriptor (`except OSError: pass` hides it). |
| **LIFE-03 (H15)** | `lifecycle/identity.py:191-192,218` | The non-Linux `/proc`-absent degrade returns raw `proc_marker` as the sentinel; the matcher basenames `argv[0]` (`:191`) but compares to the **un-basenamed** `proc_marker` (`:192`) → a path-shaped marker breaks the documented "degrade to True". |
| **SCHED-01 (H16)** | `scheduler/engine.py:72-74` | `remove()` forwards straight to `remove_job`, raising `JobLookupError` for an already-gone id — asymmetric with `register`, throws on a reconcile double-remove race. |

**Pairing constraints (ROADMAP-mandated — land together, not independently):**
- **MATCH-01 + MATCH-02** — both are `registry/match.py` casefold symmetry; fixing one without the
  other leaves the matcher half-consistent.
- **RELY-02 + RELY-03** — both are the `retry.py` `burst_size` coupling.

**Not in this phase:** SURF-01 (H17 docstring/`__all__` drift) and LIFE-04 (H18 `ReadyGate` fatal
outcome) are Phase 4. Every H01–H08 finding is already closed (Phases 1–2).

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues the milestone-wide sequence. Phase 1 reached **D-20**, Phase 2
> reached **D-33**, so Phase 3 starts at **D-34**. Distinct namespace from the module docstrings'
> own extraction decisions (`D-02..D-09` inside the source files).
>
> **The user reviewed all four gray areas and accepted the recommended default for each** ("we can
> go with ur defaults") — so every decision below is a locked default, not an open question. They
> are recorded with their rejected alternatives so the planner sees the reasoning, not just the
> verdict.

### Matcher casefold symmetry (MATCH-01 + MATCH-02 — paired)

- **D-34 (MATCH-02, name-validation policy):** **Reject loudly at registration.**
  `CommandRegistry.__init__` (`registry.py:39-48`, the seam where `commands` is frozen and
  `by_name` / `by_keyword_len_desc` are derived) validates every `spec.name`: **non-empty AND
  already-casefolded** (`name == name.casefold()`), raising `ValueError` otherwise. This is the
  registration point `match_command` consumes, and it matches the module's existing
  "fails LOUD here at construction" idiom (`panelkit.py:207` asserts a curated command exists).
  - **Rejected — casefold `spec.name` at match time** (`folded.startswith(spec.name.casefold())`):
    tolerant, needs no registration change, but it **silently hides** an uppercase-name bug (the
    consumer's `def` name never matches what they typed and they get no signal) and pays a
    per-match casefold cost on the hot path. Deny-by-default / loud-failure posture wins:
    a malformed spec is a consumer wiring bug that must surface at build, not vanish at runtime.
- **D-35 (MATCH-01, arg-slice alignment):** **Preserve the raw-case arg (locked contract); map the
  keyword boundary back to an index in the ORIGINAL stripped string — never slice from the folded
  string.** `ParsedCommand.arg` is documented RAW/case-preserved (`match.py:36-39`, `:51`), so
  slicing from `folded` is off the table — it would lowercase the arg. Because D-34 guarantees
  `spec.name` is already casefolded, the keyword test stays `folded.startswith(spec.name)`; the fix
  is to compute how many characters of the **original** `stripped` produce the matched folded
  prefix (incrementally casefold a growing prefix until its folded length reaches `len(spec.name)`,
  then that original index is the boundary), and slice the arg from there. The length change is an
  **input-side** effect (`ßtatus` folds longer), so it bites regardless of D-34 — both fixes are
  genuinely independent and must land together.

### Retry `burst_size` coupling (RELY-02 + RELY-03 — paired)

- **D-36 (RELY-02, `burst_size <= 1` degrade):** **Guard, degrade — do not raise.** In
  `_within_burst_wait` (`retry.py:157-167`), guard `burst_size <= 1` before the
  `burst_spread_s / (burst_size - 1)` division and return the spread base (no division by zero).
  With `burst_size == 1` each burst is a single attempt and `stop_after_attempt(2)` bounds the whole
  schedule, so the degenerate spread value is never actually consumed before exhaustion — the guard
  only has to **not crash**. REQ RELY-02 says "degraded wait rather than a `ZeroDivisionError`",
  so degrade is the specified behavior; a loud raise is the wrong posture for a wait callable
  running inside tenacity.
- **D-37 (RELY-03, standalone desync):** **Document the precondition loudly in `two_burst_wait`'s
  docstring; do not add coupling machinery.** `two_burst_wait` structurally **cannot see the stop
  bound** — it only receives `retry_state.attempt_number` — so it physically cannot self-check the
  desync. `build_retrying` already couples correctly (`burst_size=attempts_per_burst`,
  `stop=stop_after_attempt(2 * attempts_per_burst)`, `retry.py:258-260`), which is the wired path
  every real consumer uses. The residual risk is only a direct caller wiring `two_burst_wait` into
  their own `Retrying`. The minimal, honest fix is a **loud docstring precondition**: state that a
  standalone caller MUST pair it with `stop_after_attempt(2 * burst_size)` and that a mismatched stop
  fires the mid-pause at the wrong attempt (or never). This matches the module's heavy
  contract-in-docstring idiom.
  - **Rejected — a matched-pair factory** (`build_two_burst_wait(...) -> (wait, stop)` so a
    standalone caller can't desync): new public surface for a low-severity, unreachable footgun; no
    consumer needs it (`build_retrying` is the wired path). Revisit only if a second consumer
    actually calls `two_burst_wait` standalone (build-in-consumer-then-promote).
  - **Rejected — a hard assert inside `two_burst_wait`:** it has no access to the stop bound, so
    there is nothing to assert against.

### Scheduler `remove()` contract (SCHED-01)

- **D-38:** **Idempotent swallow.** `SchedulerEngine.remove` (`engine.py:72-74`) catches
  `JobLookupError` → debug-log + return, so removing an already-gone id is a **no-op success**
  (the desired end-state — that id absent — is achieved), directly analogous to
  `Path.unlink(missing_ok=True)`. This is safe for the reconcile double-remove race and the
  misfire-coalesce race the report names, and is symmetric with `register`'s tolerant posture. The
  swallow is **not** hiding a real error (unlike LIFE-02's masked close), so it does not violate the
  loud-failure preference — it is stated in the docstring as the contract.
  - **Rejected — keep raising, document the raise as contract:** pushes a `try/except JobLookupError`
    into every reconcile call site (including the hub's own future reconcile paths), re-deriving the
    idempotency the report asks the hub to own.

### Identity non-Linux degrade (LIFE-03)

- **D-39:** **Basename both sides in `_argv_matches_marker`.** At `identity.py:192`, compare
  `prog == Path(proc_marker.decode("utf-8", "replace")).name` instead of the raw `proc_marker`
  decode — symmetric with the `argv[0]` basenaming already one line above (`:191`). One line, and it
  fixes **both** the non-Linux `/proc`-absent degrade sentinel AND real Linux matching for a
  path-shaped marker (which currently returns False even on Linux). It is a no-op for a normal
  basename marker (`Path("examplebot").name == "examplebot"`) and does not touch the `-m` module
  branch (`:200-205`, module targets are never path-shaped), so program-identity-by-basename — the
  D-03 design where `console_name` IS the argv0 basename — is applied consistently.
  - **Rejected — validate/normalize `proc_marker` to a basename at `LifecycleIdentity`
    construction:** `proc_marker` is deliberately independent bytes (D-03, may be an `-m` module
    name), and normalizing it at the struct boundary is a heavier, more surprising change than the
    one-line matcher fix; the matcher is the single place identity is actually compared.

### Folded (clear-cut — surfaced, folded without discussion; the user's "defaults" covers these)

- **D-40 (DISC-05):** None-guard `interaction.user` at the top of `interaction_check`
  (`panelkit.py:299-309`): when `interaction.user` is absent, emit the existing reject log (every
  other reject path logs — this one must too, `:314`/`:321`) and `return False`. No ephemeral ack
  (there is no user to ack). Keeps the gate's "a clean `return False` is the sole audit record"
  contract intact.
- **D-41 (DISC-06):** Reject an empty / whitespace-only `marker` at `PanelKit.__init__`
  (`panelkit.py:157-192`, alongside the existing positive-injection assertions) — raise a clear
  error at construction, matching the "no module default; fails LOUD at construction" idiom. Closes
  the `cid.startswith("")`-owns-everything hole at the source.
- **D-42 (LIFE-02):** In `write_pid_atomic` (`identity.py:62-87`), set `fd = -1` immediately after
  the first `os.close(fd)` (`:76`); the except-path close (`:82-85`) becomes a guarded
  `if fd != -1: os.close(fd)` (or equivalent closed-flag) so the reused-integer descriptor is never
  double-closed. The re-raise posture and temp-file unlink are otherwise byte-identical.

### RED-first regression coverage (per finding, D-13 two-commit idiom)

- **D-43:** Each fix ships its RED-first test against a **hub-assertable observable** (the D-17
  lesson — never a consumer symptom):
  - **MATCH-01:** a spec named `sstatus`, input `"ßtatus hello"` → assert `arg == "hello"` (raw case
    preserved); a `ﬁnd` variant confirming the length-changing fold slices correctly.
  - **MATCH-02:** `CommandRegistry`/`build_registry` with an empty-name spec → `pytest.raises(ValueError)`;
    an uppercase-name spec (`"Status"`) → also rejected at build (proving it can't become permanently
    unmatchable).
  - **RELY-02:** `_within_burst_wait(attempt_number=2, burst_size=1, ...)` → returns a float, does not
    raise `ZeroDivisionError` (drive via `build_retrying(attempts_per_burst=1)` and force two attempts
    if a black-box assertion reads cleaner).
  - **RELY-03:** an assertion that pins `two_burst_wait`'s mid-pause to `attempt_number == burst_size`
    (the documented precondition made executable), so a future refactor that silently decouples them
    fails.
  - **DISC-05:** a synthetic `interaction` whose `.user` is None → `interaction_check` returns False
    and does not raise.
  - **DISC-06:** `PanelKit(..., marker="")` → raises at construction; a whitespace-only marker variant.
  - **LIFE-02:** an injected `os.replace` that raises → assert the temp fd is closed exactly once (a
    fake fd/close-counter double, per the no-mocking-library house style) and the original error
    re-raises.
  - **LIFE-03:** `_argv_matches_marker` with a path-shaped `proc_marker` (`b"/usr/bin/thebot"`) against
    the degrade sentinel → returns True; and a real argv0 `b"/opt/thebot"` → matches by basename.
  - **SCHED-01:** a fake scheduler whose `remove_job` raises `JobLookupError` → `SchedulerEngine.remove`
    returns without raising; a present-id variant still forwards the removal.

### Claude's Discretion

- Exact `ValueError` messages for D-34/D-41, provided they name the offending value (empty vs
  uppercase spec.name; empty marker) for consumer clarity.
- The precise algorithm for D-35's original-string boundary computation (incremental-casefold scan
  vs. any equivalent that preserves the raw arg and survives length-changing folds) — a "how" for the
  planner/researcher; the DECISION is "map to the original index, don't slice from folded".
- The exact degrade return value for D-36 within "does not raise" (spread base vs. a fixed sentinel),
  since it is never consumed before exhaustion at `burst_size == 1`.
- Whether the nine fixes ship as one plan or split — they touch **five disjoint files**
  (`registry/`, `reliability/retry.py`, `discord/panelkit.py`, `lifecycle/identity.py`,
  `scheduler/engine.py`), so grouping by file is natural and the two ROADMAP pairings
  (MATCH-01+02, RELY-02+03) MUST stay within one plan each. Sequence so a deliberately-RED test never
  overlaps a sibling's full-suite gate (the Phase-1 "Plan 03 waits on 02" lesson, re-applied in Phase 2).
- Exact test-function names and whether `pytest.raises()` is used (Phases 1–2 established it as
  acceptable); grow `tests/conftest.py` only when ≥2 test files actually share a double (D-10).
- Exact docstring wording for the fixed functions, provided the D-34/D-37/D-38/D-39 contracts are stated.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of record for the findings
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` — fix direction per finding. **H06 at :132-137,
  H09 at :151-156, H10 at :158-163, H11 at :165-169, H12 at :171-174, H13 at :176-179, H14 at :181-185,
  H15 at :187-191, H16 at :193-198.** Note: its fix-site line numbers are stale — use the verified
  locations table in `<domain>` above. Its consumer-impact triage (`:44`) is the "why unreachable
  today" argument.
- `.planning/backlog/HUB-FINDINGS-HANDOFF.md` — full failure scenario and evidence per finding.
- `.planning/REQUIREMENTS.md` — RELY-02 `:29-30`, RELY-03 `:32-34`, LIFE-02 `:44-45`, LIFE-03 `:47-48`,
  DISC-05 `:83-84`, DISC-06 `:86-87`, MATCH-01 `:100-102`, MATCH-02 `:104-106`, SCHED-01 `:110-112`,
  GATE-01 `:118-121`.
- `.planning/ROADMAP.md` §"Phase 3: Reusable public-surface footguns" — the five success criteria and
  the two **pairing constraints** (MATCH-01+02, RELY-02+03) that MUST land together.

### Files being modified (verified locations)
- `yahir_reusable_bot/registry/match.py` — `match_command` `:45-68`; folded-prefix test `:59`;
  the mis-aligned slice `:61`; `ParsedCommand`'s RAW-arg contract `:36-39`.
- `yahir_reusable_bot/registry/registry.py` — `CommandRegistry.__init__` `:39-48` (the D-34
  validation seam); `build_registry` `:83-89`.
- `yahir_reusable_bot/registry/spec.py` — `CommandSpec.name` `:66`.
- `yahir_reusable_bot/reliability/retry.py` — `_within_burst_wait` `:157-167` (D-36 guard);
  `two_burst_wait` `:170-205` (D-37 docstring precondition); `build_retrying` `:208-272` (the
  correctly-coupled wired path).
- `yahir_reusable_bot/discord/panelkit.py` — `PanelKit.__init__` `:157-192` (D-41 marker guard);
  `interaction_check` `:299-330` (D-40 None guard); `is_owned_panel` free fn `:461-479`.
- `yahir_reusable_bot/lifecycle/identity.py` — `write_pid_atomic` `:62-87` (D-42 double-close);
  `_argv_matches_marker` `:130-205` (D-39 basename both, `:191-192`); `_read_proc_cmdline` degrade
  `:208-219`.
- `yahir_reusable_bot/scheduler/engine.py` — `SchedulerEngine.register` `:44-70`, `remove` `:72-74`
  (D-38 idempotent swallow), `list_live_ids` `:76-78`.

### Prior-phase context (carried forward — conventions this phase inherits)
- `.planning/phases/01-reachable-reliability/01-CONTEXT.md` — D-11 no-mocking house style, D-13
  two-commit RED-first proof, D-14 phase branch, D-16 both-levels, D-17 hub-assertable-observable
  discipline.
- `.planning/phases/02-latent-runtime-robustness/02-CONTEXT.md` — the verified-locations-table
  convention (report lines drift), the "surface clear-cut fixes but fold without a discussion round"
  pattern, and the RED-test-never-overlaps-a-sibling-gate sequencing.

### Test conventions and standing gates
- `.planning/codebase/TESTING.md` — house style: flat `tests/`, module-level `test_*()` functions,
  docstring-first, no mocking library, synthetic inline doubles, `test_selfproof_*` naming, no CI.
  (Stale re: conftest — Phases 1–2 added/used one; grow it only on a real second caller, D-10.)
- `tests/conftest.py` — exists (Phase 1, D-09/D-10): `fake_stop_event`, `cmdline_bytes`
  (`cmdline_bytes` is directly reusable for LIFE-03's argv doubles).
- `tests/test_match.py` / `tests/test_retry.py` / `tests/test_identity.py` / `tests/test_selection.py`
  — existing per-module test precedents; match their shape (add adversarial cases, not just happy paths).
- `tests/test_import_hygiene.py` — the standing GATE-01 gate + `test_selfproof_*` idiom source.

### Project constitution
- `ECOSYSTEM.md` §3 — human-gated close-out (the `pyproject.toml` bump, `v0.1.2` tag, WeatherBot
  repin are NOT autonomous).
- `CLAUDE.md` (repo root) — one-way dependency, `discord.py==2.7.1` exact pin, no-domain-nouns litmus
  (D-13 litmus gate — every new `def`/`class`/param name must stay generic).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (seams already present — fixes need no new test hooks)
- **MATCH-02:** `CommandRegistry.__init__` (`registry.py:39-48`) already iterates every spec to build
  `by_name` / `by_keyword_len_desc` — the D-34 validation drops into that same single pass, no new
  traversal.
- **RELY-02/03:** `build_retrying` injects `attempts_per_burst` (`retry.py:211`) — a test builds a
  `burst_size == 1` retrying in-memory; `_within_burst_wait` is a pure function driven directly.
- **DISC-05/06:** `interaction_check` reads only `interaction.user` / `interaction.data`, and
  `PanelKit.__init__` already has a positive-injection assertion block — a synthetic interaction /
  a bad-marker construction exercise both in-memory, no gateway.
- **LIFE-02/03:** `write_pid_atomic` and `_argv_matches_marker` are pure/stdlib; a fake fd
  close-counter (LIFE-02) and the existing `cmdline_bytes` fixture (LIFE-03) drive them with no `/proc`.
- **SCHED-01:** `SchedulerEngine` wraps an injected scheduler (`engine.py:41-42`) — a fake whose
  `remove_job` raises `JobLookupError` drives the idempotency branch directly.

### Established Patterns (constrain the fixes)
- **Fail-LOUD-at-construction** (`panelkit.py:207` curated-command assert; `identity.py` WRITER
  re-raises) — D-34 and D-41 extend this idiom to spec-name and marker validation.
- **Degrade-vs-raise split** — the module raises on startup/wiring errors (writer, marker) but
  degrades on runtime/portability conditions (the `/proc`-absent guard, the interruptible sleep).
  D-36 (degrade the wait), D-38 (swallow already-gone), D-40 (return False on absent user) sit on the
  degrade side; D-34/D-41 sit on the raise side — the split is deliberate, not inconsistent.
- **Raw-case preservation in the matcher** — `ParsedCommand.arg` is documented RAW; D-35 must not
  break it (this is why "slice from folded" is rejected).
- **Contract-in-docstring** — this codebase carries decision rationale inline in function docstrings
  (`identity._argv_matches_marker` is a full essay); the D-37/D-38/D-39 contracts belong there, not
  only in commit messages.
- **Deny-by-default posture** (`retry.is_transient` docstring) — D-34's reject-loud mirrors it: an
  unrecognized/malformed input fails closed and visible rather than being silently normalized.

### Integration Points
- `CommandRegistry` / `match_command` are public surface any consumer parameterizes — D-34's new
  `ValueError` at registration is a **new failure mode a consumer can hit at build**; name it in the
  phase summary handed to the human-gated close-out (a consumer with an uppercase command name will
  now fail fast where it previously silent-failed at match).
- `PanelKit.__init__`'s new empty-marker raise is likewise a build-time behavior change (previously it
  constructed and mis-owned pins) — note in the phase summary.
- `SchedulerEngine.remove` becoming idempotent is a silent→tolerant behavior change consumers may rely
  on during reconcile — note it.
- The other fixes (MATCH-01, RELY-02/03, DISC-05, LIFE-02/03, SCHED-01 degrade) are behavior-preserving
  on the happy path — they only change the previously-crashing/mis-sliced edge.

</code_context>

<specifics>
## Specific Ideas

- **The MATCH-01+02 pairing is load-bearing, not bureaucratic:** MATCH-02 normalizes `spec.name`
  (registration side), MATCH-01 fixes the input-side length change (`ßtatus`). The length mis-slice
  bites from the **input** even with perfectly-normalized names, so shipping one without the other
  leaves a matcher that is correct for one class of Unicode input and wrong for the other. Carry this
  "two independent axes, one contract" framing into the plan.
- **The RELY-03 linchpin:** the function cannot self-check because it never receives the stop bound —
  so a "loud assert" is physically impossible and a factory is over-built for an unreachable footgun.
  The docstring precondition + an executable test pinning mid-pause to `attempt_number == burst_size`
  is the honest ceiling of what the hub can enforce here. Don't let a reviewer push for machinery the
  function structurally can't support.
- **LIFE-03's fix is strictly more correct than the report frames it:** the report says "fix the
  non-Linux degrade", but basenaming both sides ALSO fixes real Linux matching for a path-shaped
  marker (currently False even on Linux). One line closes both.

</specifics>

<deferred>
## Deferred Ideas

- **Matched-pair `two_burst_wait` factory** (RELY-03 Option 2) — a `build_two_burst_wait() -> (wait,
  stop)` helper so a standalone caller cannot desync. Deferred under build-in-consumer-then-promote:
  no consumer calls `two_burst_wait` standalone (`build_retrying` is the wired path). Promote if a
  second consumer actually wires the wait callable by hand.
- **Validate/normalize `proc_marker` at `LifecycleIdentity` construction** (LIFE-03 Option 3) —
  rejected now (D-39) as heavier than the one-line matcher fix; revisit only if marker shape becomes a
  recurring consumer-confusion source.
- **Refresh `.planning/codebase/TESTING.md`** — still stale re: the conftest Phases 1–2 use.
  Housekeeping, not phase scope.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 3 scope.

</deferred>

---

*Phase: 3-public-surface-footguns*
*Context gathered: 2026-07-27*
