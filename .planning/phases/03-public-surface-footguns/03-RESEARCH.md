# Phase 3: Reusable public-surface footguns - Research

**Researched:** 2026-07-27
**Domain:** Unicode-aware text matching, tenacity retry-callable contracts, discord.py 2.7.1 View/Interaction semantics, POSIX fd lifecycle, host-scheduler exception contracts
**Confidence:** HIGH (every claim below was verified against the installed dependency versions or the working tree; two claims **correct** the CONTEXT.md rationale on evidence — see Common Pitfalls #1 and #2)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Decision numbering continues the milestone-wide sequence. Phase 1 reached **D-20**, Phase 2
> reached **D-33**, so Phase 3 starts at **D-34**. Distinct namespace from the module docstrings'
> own extraction decisions (`D-02..D-09` inside the source files).
>
> **The user reviewed all four gray areas and accepted the recommended default for each** ("we can
> go with ur defaults") — so every decision below is a locked default, not an open question. They
> are recorded with their rejected alternatives so the planner sees the reasoning, not just the
> verdict.

**Matcher casefold symmetry (MATCH-01 + MATCH-02 — paired)**
- **D-34 (MATCH-02, name-validation policy):** Reject loudly at registration. `CommandRegistry.__init__` (`registry.py:39-48`) validates every `spec.name`: non-empty AND already-casefolded (`name == name.casefold()`), raising `ValueError` otherwise. Rejected: casefold `spec.name` at match time (tolerant but silently hides an uppercase-name bug).
- **D-35 (MATCH-01, arg-slice alignment):** Preserve the raw-case arg (locked contract); map the keyword boundary back to an index in the ORIGINAL stripped string — never slice from the folded string. Because D-34 guarantees `spec.name` is already casefolded, the keyword test stays `folded.startswith(spec.name)`; the fix computes how many characters of the original `stripped` produce the matched folded prefix.

**Retry `burst_size` coupling (RELY-02 + RELY-03 — paired)**
- **D-36 (RELY-02):** Guard, degrade — do not raise. In `_within_burst_wait` (`retry.py:157-167`), guard `burst_size <= 1` before the `burst_spread_s / (burst_size - 1)` division and return the spread base (no division by zero).
- **D-37 (RELY-03):** Document the precondition loudly in `two_burst_wait`'s docstring; do not add coupling machinery. `two_burst_wait` structurally cannot see the stop bound. Rejected: a matched-pair factory; a hard assert (nothing to assert against).

**Scheduler `remove()` contract (SCHED-01)**
- **D-38:** Idempotent swallow. `SchedulerEngine.remove` (`engine.py:72-74`) catches the job-store's lookup-miss error → debug-log + return, so removing an already-gone id is a no-op success, analogous to `Path.unlink(missing_ok=True)`. Rejected: keep raising, document as contract.

**Identity non-Linux degrade (LIFE-03)**
- **D-39:** Basename both sides in `_argv_matches_marker`. At `identity.py:192`, compare `prog == Path(proc_marker.decode("utf-8", "replace")).name` instead of the raw `proc_marker` decode — symmetric with the `argv[0]` basenaming already one line above (`:191`). Rejected: validate/normalize `proc_marker` at `LifecycleIdentity` construction.

**Folded (clear-cut — surfaced, folded without discussion)**
- **D-40 (DISC-05):** None-guard `interaction.user` at the top of `interaction_check` (`panelkit.py:299-309`): when `interaction.user` is absent, emit the existing reject log and `return False`. No ephemeral ack.
- **D-41 (DISC-06):** Reject an empty / whitespace-only `marker` at `PanelKit.__init__` (`panelkit.py:157-192`) — raise a clear error at construction.
- **D-42 (LIFE-02):** In `write_pid_atomic` (`identity.py:62-87`), set `fd = -1` immediately after the first `os.close(fd)` (`:76`); the except-path close (`:82-85`) becomes a guarded `if fd != -1: os.close(fd)`.

**RED-first regression coverage (D-43)** — see the `<domain>` table in CONTEXT.md for the per-finding test shape; restated with verified assertion shapes under Validation Architecture below.

### Claude's Discretion

- Exact `ValueError` messages for D-34/D-41.
- **The precise algorithm for D-35's original-string boundary computation** — resolved below (Common Pitfalls #4 / Code Examples).
- The exact degrade return value for D-36 within "does not raise."
- Whether the nine fixes ship as one plan or split (five disjoint files; the two pairings MUST stay within one plan each; sequence so a deliberately-RED test never overlaps a sibling's full-suite gate) — recommendation below (Architecture Patterns → Sequencing).
- Exact test-function names and whether `pytest.raises()` is used; grow `tests/conftest.py` only when ≥2 test files actually share a double.
- Exact docstring wording for the fixed functions.

### Deferred Ideas (OUT OF SCOPE)

- Matched-pair `two_burst_wait` factory (RELY-03 Option 2) — no consumer calls it standalone.
- Validate/normalize `proc_marker` at `LifecycleIdentity` construction (LIFE-03 Option 3).
- Refresh `.planning/codebase/TESTING.md` (stale re: conftest) — housekeeping, not phase scope.
- SURF-01 (H17) and LIFE-04 (H18) — Phase 4.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MATCH-01 | Arg extraction correct when the keyword's casefold changes length | Code Examples §1 gives the verified `_keyword_boundary` algorithm; Common Pitfalls #4 documents the adversarial overshoot case and why `>=`/exact-with-reject is required, not naive prefix-casefold |
| MATCH-02 | `spec.name` validated at registration (non-empty, already-casefolded) | `registry.py:39-48` confirmed as the single derivation pass; validation drops into the existing loop, no new traversal |
| RELY-02 | `burst_size == 1` degrades instead of raising `ZeroDivisionError` | Empirically reproduced the exact crash (Common Pitfalls #3); tenacity call-order trace proves the wait callable runs BEFORE `stop_after_attempt` can halt the schedule, so the guard is load-bearing, not defensive-only |
| RELY-03 | Standalone `two_burst_wait` desync is a documented precondition, not machinery | tenacity source trace confirms `RetryCallState` never carries a stop bound; `attempt_number` is 1-indexed, incremented only after a continue decision |
| DISC-05 | `interaction_check` returns False, never raises, when `.user` is absent | Common Pitfalls #1 (verified discord.py 2.7.1 correction) + the `MISSING` sentinel finding (guard shape must be falsy-check, not `is None`) |
| DISC-06 | Empty `marker` rejected at `PanelKit.__init__` | Confirmed construction seam at `panelkit.py:157-192`; no new research needed beyond the guard shape |
| LIFE-02 | `write_pid_atomic` never double-closes the temp fd | Code Examples §3 gives the `monkeypatch`-based close-counting double (first use of `monkeypatch` in this repo — flagged as a house-style extension) |
| LIFE-03 | Non-Linux degrade holds for a path-shaped `proc_marker` | Verified against source; test drives `_argv_matches_marker` directly with the degrade sentinel shape |
| SCHED-01 | `SchedulerEngine.remove` has a stated idempotent contract | Common Pitfalls #2 (apscheduler is NOT a hub dependency — verified `JobLookupError(KeyError)` inheritance means `except KeyError:` is correct and dependency-free) |
| GATE-01 | Full suite + import-hygiene/litmus/grimp stay green | Environment Availability confirms pytest 9.1.1 / ruff 0.15.20 / grimp 3.14 installed; baseline `uv run pytest` is 35 passed, 0 failed pre-phase |
</phase_requirements>

## Summary

Phase 3 is nine independent, mostly one-line-to-ten-line fixes across five disjoint files, and the
design is already locked (D-34..D-42). The research value here is in the "how," and this pass
surfaced two **verified corrections to the CONTEXT.md/finding-report rationale** that do not change
any locked decision but materially change what the planner should tell the executor:

1. **DISC-05's stated mechanism is wrong for the installed discord.py 2.7.1.** Empirically calling
   the real, unmodified `discord.ui.View._scheduled_task` proves an `AttributeError` raised inside
   `interaction_check` **is** caught and routed to `on_error` — it does not "escape View.on_error's
   reach" as H11/CONTEXT.md states. The D-40 fix (None-guard, return False, log) is still exactly
   right — it restores the clean, silent, INFO-level reject-log contract instead of a noisy
   ERROR-level `on_error` backstop crash-path — but the RED test must not be written to "prove an
   exception escapes on_error," because it doesn't. Also: `interaction.user`'s absence sentinel is
   `discord.utils.MISSING`, not `None` — the guard must be a falsy check (`if not interaction.user:`),
   not an identity check.
2. **`apscheduler` is not a dependency of this hub, anywhere, ever** (not in `pyproject.toml`, not
   importable in this venv, not referenced in `yahir_reusable_bot/` outside one docstring comment).
   D-38 says "catch `JobLookupError`" — but the hub cannot import that class without adding a new
   dependency, which would contradict `SchedulerEngine`'s own documented host-scheduler-agnostic
   design. Verified against APScheduler 3.x's actual source: `class JobLookupError(KeyError)`. The
   fix is `except KeyError:` — dependency-free, and the precedent (`reload.py:152`) already avoids
   naming apscheduler's exception directly.

A third finding refines D-35's "how": the CONTEXT-suggested "incrementally casefold a growing
prefix until its folded length reaches `len(spec.name)`" is *almost* right but has one silent bug
(a naive `==`-only scan with no overshoot handling can leave a spec's match undetected, and a
naive re-casefold-per-prefix loop is O(n²)); the exact, verified, O(n) algorithm is in Code
Examples §1, empirically checked against every one of the 104 Unicode codepoints whose
`str.casefold()` changes length.

**Primary recommendation:** implement the nine fixes as five plans (one per file), landed strictly
serially (RED commit → GREEN commit → GATE-01 reverified green, before the next plan's RED commit),
using the algorithm/guard shapes below — MATCH-01+02 and RELY-02+03 each stay inside one plan.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Command-text matching (MATCH-01/02) | API / Backend (library, pure function) | — | `match_command`/`CommandRegistry` are pure, side-effect-free text processing invoked by a host's dispatch layer; no I/O, no framework coupling |
| Retry/backoff scheduling (RELY-02/03) | API / Backend (library) | — | `tenacity`-composed wait/stop policy; runs inside whatever async/thread context the host's retry call sits in, but the hub owns only the policy function, not the loop |
| Discord panel operator gate (DISC-05/06) | Frontend Server (SSR-analog: gateway event handling) | API / Backend (ownership predicate is pure) | `interaction_check`/`on_command` run inside discord.py's gateway event loop (the "frontend" for a bot — it renders/receives from Discord's edge); `is_owned_panel` is a pure predicate usable anywhere |
| Process identity / PID lifecycle (LIFE-02/03) | API / Backend (host process control) | — | `write_pid_atomic`/`_argv_matches_marker` are OS-process-lifecycle primitives, not request-serving code; they run at daemon startup/reload, not per-request |
| Job scheduling registrar (SCHED-01) | API / Backend (host process control) | Database/Storage (job persistence is the HOST's scheduler's concern, not this facade's) | `SchedulerEngine` is a thin non-owning facade; the actual scheduler (host-injected, e.g. APScheduler) owns persistence/trigger semantics |

This phase touches zero browser/client-tier code and zero CDN/static-asset code — it is entirely
library-tier hardening, which is why every RED test in D-43 is a hub-assertable, in-memory,
no-gateway/no-filesystem-mocking-needed unit test (LIFE-02 is the one exception requiring a real
temp directory + `monkeypatch`, discussed below).

## Standard Stack

No new stack. Every dependency this phase touches is already pinned and installed:

### Core (already pinned — verified against the working `.venv`)
| Library | Installed version | Purpose | Verification |
|---------|---------|---------|--------------|
| `tenacity` | 9.1.4 | retry/wait/stop composition (RELY-02/03) | `uv.lock:736-741`; confirmed `Retrying.__init__` signature and `RetryCallState` source read directly from the installed package |
| `discord.py` | 2.7.1 (exact pin) | `View`/`Interaction`/`ui.Item` semantics (DISC-05/06) | `uv.lock:228-237`; confirmed via reading `discord/ui/view.py` and `discord/interactions.py` directly, plus an executed empirical test against the real `View._scheduled_task` |
| `httpx` | 0.28.1 | unaffected by this phase (RELY-01 already fixed Phase 1) | no change |
| `structlog` | ≥26.1.0 | logging idiom for the new reject/debug log lines (D-34/38/40) | unchanged usage pattern (`_log.info(...)` / `_log.debug(...)`) |
| stdlib `os` / `pathlib` / `tempfile` | Python 3.13 (repo requires ≥3.12) | LIFE-02/03 | no new import |

### Supporting (test-only — one new technique)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` (built-in `monkeypatch` fixture) | 9.1.1 installed (pin `>=9.0.3`) | LIFE-02's fd close-counting double | `monkeypatch` is part of pytest core, not a mocking library (no `unittest.mock`/`pytest-mock` object patching) — it substitutes a real, hand-written double for a real attribute. This is the **first use of `monkeypatch` in this repo**; flag it in the plan the same way Phase 1 flagged `conftest.py` (D-09) and `pytest.raises()` as deliberate first uses |
| `grimp` | 3.14 | GATE-01 import-hygiene, unchanged | verified installed |
| `ruff` | 0.15.20 | lint, unchanged | verified installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `monkeypatch`-substituted `os` shim (LIFE-02) | Refactor `write_pid_atomic` to accept injectable `close`/`replace` callables | Rejected: D-42's locked fix is a one-line/flag change to existing code, not a new-parameter API change; adding injection params here is a bigger surface change than the phase calls for |
| `except KeyError:` for SCHED-01 | Add `apscheduler` as a dependency and `except apscheduler.jobstores.base.JobLookupError:` | Rejected: contradicts `SchedulerEngine`'s own documented host-agnostic design (module docstring: "the native trigger object passes through untouched... any host binds its own callable through the identical hole") and adds a dependency this repo has never needed; `KeyError` is `JobLookupError`'s actual, verified base class |
| Per-character `>=`-accumulation boundary scan (MATCH-01) | CONTEXT's literal "casefold a growing prefix, check exact length" | Both are correct if the exact-match variant treats "no exact hit found" as "no match" (proven below); the accumulation form is O(n) instead of O(n²) and doesn't need to re-casefold substrings repeatedly |

**Installation:** none — no `pyproject.toml` change, no `uv add`, no new dependency of any kind.
This is itself a phase-shape fact worth stating in the plan: **Phase 3 ships zero new dependencies.**

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** No `pyproject.toml` change is
in scope. The one candidate dependency a naive reading of the findings might suggest —
`apscheduler`, to import `JobLookupError` for SCHED-01 — is explicitly **rejected** by this
research (see Common Pitfalls #2): the correct, dependency-free fix is `except KeyError:`, verified
against APScheduler 3.x's actual source (`class JobLookupError(KeyError)`). If a future reviewer
suggests adding `apscheduler` as a dependency to make the `except` clause "more explicit," that
is a **regression** against this module's host-agnostic design — flag it, don't take it.

**Packages removed due to [SLOP] verdict:** none (none proposed).
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────────┐
                     │              Host consumer process           │
                     │  (WeatherBot or a future bot's composition    │
                     │   root — outside this repo)                   │
                     └───────┬──────────────┬──────────────┬────────┘
                             │              │              │
                text command │      Discord │       APScheduler-shaped
                     input    │  gateway     │       scheduler instance
                             ▼              ▼              ▼
              ┌───────────────────┐ ┌──────────────┐ ┌────────────────┐
              │ CommandRegistry /  │ │  PanelKit     │ │ SchedulerEngine │
              │ match_command      │ │  (View)       │ │ (facade)        │
              │ (registry/)        │ │ (discord/)    │ │ (scheduler/)    │
              │                    │ │               │ │                 │
              │ D-34 validate name │ │ D-40 None-    │ │ D-38 swallow    │
              │  at __init__       │ │  guard user   │ │  KeyError on    │
              │ D-35 map boundary  │ │ D-41 reject   │ │  remove()       │
              │  to original index │ │  empty marker │ │                 │
              └────────┬───────────┘ └──────┬────────┘ └────────┬────────┘
                       │                    │                    │
                       ▼                    ▼                    ▼
              ParsedCommand(spec,   interaction_check()   idempotent no-op
              arg=RAW-case slice)   → False, never raises  on already-gone id
                       │
                       │  (independent of the above — a
                       │   parallel pure-function fix)
                       ▼
              ┌────────────────────┐         ┌─────────────────────────┐
              │ reliability/retry.py│        │ lifecycle/identity.py    │
              │                     │        │                          │
              │ D-36 guard          │        │ D-42 fd=-1 after first   │
              │  burst_size<=1      │        │  close (no double-close) │
              │ D-37 loud docstring │        │ D-39 basename both sides │
              │  precondition       │        │  in _argv_matches_marker │
              └─────────────────────┘        └──────────────────────────┘
                (wait callable fed          (write_pid_atomic / is_running_process
                 into tenacity.Retrying      called at daemon startup / reload —
                 by the host's call site)    no gateway, no scheduler involved)
```

A reader can trace any single finding start-to-finish: host calls into one of the five hub
modules → the hub module's fixed function returns a value or raises per its documented contract →
control returns to the host. No finding in this phase crosses a file boundary except the two
mandated pairings (MATCH-01+02 both live under `registry/`; RELY-02+03 both live in `retry.py`).

### Recommended Project Structure

No new modules. Four **new test files** are required — CONTEXT.md's canonical_refs claims
`tests/test_match.py` is an "existing per-module test precedent," but **the working tree has no
such file** (verified: `tests/` currently contains only `conftest.py`, `test_gateway.py`,
`test_identity.py`, `test_import_hygiene.py`, `test_reload.py`, `test_retry.py`,
`test_selection.py`). This mirrors Phase 1's discovery that `retry.py`/`identity.py` had zero
tests before Phase 1 created the first ones — the same is true here for `match.py`, `registry.py`,
`panelkit.py`, and `scheduler/engine.py`.

```
tests/
├── test_match.py       # NEW — MATCH-01 (registry/match.py); mirrors module-name convention
├── test_registry.py    # NEW — MATCH-02 (registry/registry.py); mirrors module-name convention
├── test_retry.py        # EXTEND — RELY-02/03 (already exists, Phase 1)
├── test_panelkit.py     # NEW — DISC-05/06 (discord/panelkit.py)
├── test_identity.py     # EXTEND — LIFE-02/03 (already exists, Phase 1)
└── test_engine.py       # NEW — SCHED-01 (scheduler/engine.py; mirrors the module basename
                          #        the same way test_reload.py mirrors config/reload.py)
```

The `test_<module_basename>.py` convention is unbroken across every existing file
(`test_retry.py`↔`retry.py`, `test_identity.py`↔`identity.py`, `test_reload.py`↔`reload.py`,
`test_selection.py`↔`selection.py`, `test_gateway.py`↔`gateway.py`) — the four new files should
follow it exactly. `registry/` has two source modules (`match.py`, `registry.py`) that both need
tests; keep them in separate files matching each module, rather than merging into one
`test_registry_all.py`, so the mirror convention doesn't get an exception.

### Sequencing (Claude's Discretion — plan/wave grouping)

**Recommendation: five plans, one per disjoint file, executed strictly serially** (not
parallel waves), preserving the D-13 two-commit-per-fix (RED parent, GREEN child) idiom and the
Phase 1/2 "a deliberately-RED test never overlaps a sibling's full-suite gate" lesson:

1. `scheduler/engine.py` (SCHED-01) — smallest surface, single finding, proves the `except KeyError:`
   dependency-free pattern first while the codebase is still fully green.
2. `lifecycle/identity.py` (LIFE-02 + LIFE-03) — extends the existing `test_identity.py`; two
   independent findings in one file (not a ROADMAP-mandated pairing, but naturally grouped since
   both touch the same module, matching Phase 1/2 precedent of grouping same-file findings into
   one plan).
3. `registry/` (MATCH-01 + MATCH-02, **mandated pairing**) — new `test_match.py` + `test_registry.py`;
   the most algorithmically novel fix (the boundary-scan), do it once the simpler patterns are proven.
4. `reliability/retry.py` (RELY-02 + RELY-03, **mandated pairing**) — extends `test_retry.py`;
   requires care with tenacity's wait-before-stop call order (Common Pitfalls #3).
5. `discord/panelkit.py` (DISC-05 + DISC-06) — new `test_panelkit.py`; heaviest new-double surface
   (a synthetic `View`/`Interaction`), do it last.

The **file order itself is not load-bearing** (all five are truly disjoint — no import edges
between `registry/`, `reliability/`, `discord/`, `lifecycle/`, `scheduler/`). What IS load-bearing:
**each plan's RED commit and GREEN commit must land back-to-back with GATE-01 re-verified green
before the next plan's RED commit is committed.** If wave-based parallel execution is used, do NOT
run two of these five plans in the same wave — a second plan's RED-first test committed while a
sibling plan is still between its RED and GREEN commits makes the full-suite state ambiguous about
which fix is actually broken, and (per Phase 1/2 practice) breaks the clean parent-child commit
adjacency D-13 requires as "the proof."

**Process note for the planner:** Phase 1 worked on a dedicated phase branch merged at the end
(D-14; branch `phase-01-reachable-reliability`, merge commit `81df616`). **Phase 2 committed
directly to `main`** (git history: `ec5195f`..`c27876b` on `main`, no phase branch, no merge
commit) — `.planning/config.json` sets `"branching_strategy": "none"`. CONTEXT.md does not
re-state D-14 for Phase 3. This is a genuine open question the planner should resolve explicitly
(see Open Questions) rather than silently assuming either convention.

### Pattern 1: Registration-time deny-by-default validation (D-34)
**What:** Validate every `spec.name` inside `CommandRegistry.__init__`'s existing single derivation
pass — no new traversal.
**When to use:** Any invariant the matcher's runtime code depends on but cannot cheaply re-check
per call (already established for `is_transient`'s deny-by-default posture, Phase 1 D-02).
**Example:**
```python
# yahir_reusable_bot/registry/registry.py — inside CommandRegistry.__init__,
# in the same pass that already builds self.commands / self.by_name
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    for spec in self.commands:
        if not spec.name or spec.name != spec.name.casefold():
            raise ValueError(
                f"CommandSpec.name must be non-empty and already casefolded "
                f"(match_command folds input, never spec.name); got {spec.name!r}"
            )
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    self.by_keyword_len_desc: tuple[CommandSpec, ...] = tuple(
        sorted(self.commands, key=lambda c: len(c.name), reverse=True)
    )
```

### Anti-Patterns to Avoid
- **Casefolding `spec.name` at match time instead of validating at registration (rejected D-34
  alternative):** silently hides a consumer wiring bug and pays a per-match cost on the hot path.
- **Slicing the arg from the folded string (rejected D-35 alternative):** breaks the locked
  RAW-case `ParsedCommand.arg` contract — a consumer's argument would silently lowercase.
- **Importing `apscheduler` to catch `JobLookupError` by name (see Common Pitfalls #2):** adds an
  unnecessary hard dependency and contradicts the module's host-agnostic design.
- **Asserting discord.py's `on_error` does NOT catch an `interaction_check` exception (see Common
  Pitfalls #1):** this is empirically false for the pinned 2.7.1 and would make the RED test
  assert something untrue about the library.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting "job not found" from a host-injected scheduler without depending on its package | A custom `JobLookupError`-lookalike class hierarchy, or an `apscheduler` import | `except KeyError:` | APScheduler's real `JobLookupError` IS a `KeyError` (verified against the 3.x source); Python's own `KeyError` is already available with zero new imports |
| Casefold-length-changing Unicode boundary detection | A full Unicode `NFKC`/`unicodedata` normalization pass, or a third-party grapheme-cluster library | Per-character `len(ch.casefold())` accumulation (Code Examples §1) | The matcher already promises "only `str.strip`/`str.casefold`/slicing" as a load-bearing security contract (module docstring); a purpose-built O(n) scan over `str.casefold()` itself needs no new library and was verified against every codepoint in the standard library's Unicode tables |
| Faking a closed/reused file descriptor for LIFE-02's regression test | A custom syscall-level fd-reuse simulator | A `monkeypatch`-installed `os.close` counter that delegates to the real `os.close` | Proves the STRUCTURAL invariant ("closed at most once") the fix guarantees, without needing to force an actual OS-level fd collision (which is non-deterministic and not something a single-threaded test can reliably arrange) |

**Key insight:** every one of these nine fixes is small specifically because the module already
does the hard design work (opaque-callable injection, structural typing, pure functions); the
temptation this phase specifically must resist is over-engineering the FIX to compensate for a
library detail that turns out, on verification, not to be a problem at all (DISC-05's on_error
routing) or to already have a clean stdlib answer (SCHED-01's `KeyError`).

## Common Pitfalls

### Pitfall 1 (VERIFIED CORRECTION): DISC-05's "escapes View.on_error" claim does not hold for discord.py 2.7.1
**What goes wrong:** H11/CONTEXT.md states the `AttributeError` from `interaction.user.bot`
"raised outside View.on_error's reach." If a test or docstring is written asserting this, it
asserts something false about the pinned library version.
**Why it happens:** The claim may be true for other discord.py versions, or may have been a
sweep-tool inference rather than a live-source read. Reading `discord/ui/view.py:587-600` in the
INSTALLED 2.7.1 package shows `_scheduled_task`'s `try` block wraps
`await self.interaction_check(interaction)` in the SAME try as `item.callback(interaction)`, both
routed to `except Exception as e: return await self.on_error(interaction, e, item)`.
**How to avoid:** Verified empirically — constructed a real `discord.ui.View` subclass overriding
`interaction_check` to reproduce the exact H11 defect (`interaction.user.bot` with `.user = None`)
and called the REAL, unmodified `view._scheduled_task(item, interaction)`:
```
on_error_called_with: (<class 'AttributeError'>, "'NoneType' object has no attribute 'bot'", <CmdButton ...>)
```
`on_error` WAS invoked with the `AttributeError`. **The D-40 fix (None-guard, log, return False) is
still exactly correct** — the actual defect this reveals is that a None/absent `.user` currently
crashes into `PanelKit.on_error`'s noisy `_log.exception("panel view on_error backstop", ...)` +
attempted (likely-failing, since the interaction can't be meaningfully acked) `_safe_error_edit`,
INSTEAD of the clean, silent, INFO-level `_log.info("panel reject...")` + `return False` every
other reject path uses. State the mechanism this way in the fix's docstring/commit, not "escapes
on_error."
**Warning signs:** A RED test that drives the fix through `view._scheduled_task`/`_dispatch_item`
and asserts `on_error` was NOT called would be RED for the wrong reason (it WAS called, pre-fix, via
the library's own exception handling) — the correct RED test calls `panel.interaction_check(interaction)`
**directly** (which is what D-43 already specifies) and asserts it returns `False` without raising,
sidestepping the `on_error` question entirely.

**Bonus finding — the absence sentinel is `MISSING`, not `None`:** `discord.Interaction.__init__`
(`discord/interactions.py:274`) initializes `self.user: Union[User, Member] = MISSING` (not
`None`) and only overwrites it if the interaction payload carries a `member` or `user` key.
`discord.utils.MISSING` is a distinct sentinel object (`_MissingSentinel`, `__bool__` returns
`False`, `__eq__` always `False`) — `interaction.user is None` would NOT catch this case; only a
falsy check does. **The D-40 guard must be `if not interaction.user:`, not
`if interaction.user is None:`.** Verified: neither `User` nor `Member` override `__bool__`, so a
real user object is always truthy — the falsy check cannot false-positive on a legitimate user.

### Pitfall 2 (VERIFIED CORRECTION): `apscheduler` is not, and must not become, a hub dependency
**What goes wrong:** D-38/CONTEXT.md/the finding report all say "catch `JobLookupError`." A
literal reading suggests `from apscheduler.jobstores.base import JobLookupError` — but this
package is NOT installed (`ModuleNotFoundError: No module named 'apscheduler'` in this venv) and
is NOT in `pyproject.toml` (dependencies are exactly `discord.py`, `httpx`, `structlog`, `tenacity`
— verified by reading `pyproject.toml:6-14`). The only mention of "APScheduler" anywhere in
`yahir_reusable_bot/` is a code COMMENT in `scheduler/engine.py:15` (a docstring, not an import).
**Why it happens:** `SchedulerEngine` is deliberately host-scheduler-agnostic — its own docstring
states the trigger and callback "pass through untouched... so any host binds its own callable
through the identical hole (D-05)." Adding an `apscheduler` import for one `except` clause breaks
that abstraction and adds a real dependency this repo has never needed.
**How to avoid:** `except KeyError:` — verified against APScheduler 3.x's actual published source
(`apscheduler/jobstores/base.py`): `class JobLookupError(KeyError): ...`. `KeyError` is a Python
builtin, requires no import, and is precise (not so broad it swallows unrelated bugs — `remove_job`
on a real APScheduler scheduler raises exactly this and nothing else for the "not found" case).
Precedent already exists in this codebase: `config/reload.py:152`'s PHASE-2 reconcile-failure
handler catches a broad `except Exception as exc:` rather than naming any apscheduler exception
type — this repo has never imported apscheduler and this phase should not be the first to do so.
**Warning signs:** if a reviewer or a future edit adds `import apscheduler` anywhere under
`yahir_reusable_bot/`, that is a regression against the module's design and should be caught by
code review (there is no automated gate for "don't add this specific dependency," so call it out
explicitly in the plan's `must_haves`).

### Pitfall 3 (VERIFIED, load-bearing for the RELY-02 test design): tenacity calls `wait` BEFORE `stop`
**What goes wrong:** It's tempting to assume `_within_burst_wait`'s degenerate `burst_size == 1`
division is only theoretically reachable because `stop_after_attempt(2)` "would have already
stopped" the retry by the time the division would fire.
**Why it happens:** Reading tenacity's `BaseRetrying._post_retry_check_actions`
(`.venv/.../tenacity/__init__.py:391-401`) shows the actual per-iteration order is:
`_run_wait` (calls the `wait` callable) → `_run_stop` (evaluates `stop_after_attempt`) →
`_post_stop_check_actions` (only NOW decides whether to sleep-and-continue or raise/return). The
wait callable's return value is silently DISCARDED if stop fires, but **the wait callable still
executes and can still raise** even on the attempt where `stop_after_attempt` is about to end the
schedule.
**How to avoid:** Empirically reproduced the exact pre-fix crash with the RECOMMENDED test
configuration:
```
build_retrying(fake_stop_event, attempts_per_burst=1, burst_spread_s=0, mid_pause_s=0)
→ ZeroDivisionError: division by zero (raised on attempt_number=2, attempts=2 total)
```
`_within_burst_wait(attempt_number=2, burst_size=1, ...)` hits `attempt_number == burst_size` → `1
== 1`? No — `2 != 1` — falls through to `step = burst_spread_s / (burst_size - 1)` →
`ZeroDivisionError`, raised from INSIDE the wait callable, one call before `stop_after_attempt(2)`
would have ended the loop anyway. This confirms D-36's framing precisely ("the degenerate spread
value is never actually consumed before exhaustion — the guard only has to not crash") while also
proving the guard is genuinely load-bearing, not a defensive no-op.
**Warning signs:** A test that only checks the RETURNED value of `_within_burst_wait` at
`attempt_number == burst_size` (the branch that already worked pre-fix) would stay GREEN before AND
after the fix — the RED assertion must exercise `attempt_number != burst_size` with `burst_size <= 1`
(either directly, or via `build_retrying(attempts_per_burst=1, ...)` driven to its second attempt,
exactly as reproduced above).

### Pitfall 4 (VERIFIED, refines D-35's "how"): a naive length-equality boundary scan has one silent bug
**What goes wrong:** CONTEXT.md's suggested algorithm — "incrementally casefold a growing prefix of
the original `stripped` until its folded length reaches `len(spec.name)`" — is correct for the two
named examples (`ßtatus`/`sstatus`, `ﬁnd`/`find`) but has an unhandled edge: **a single original
character's casefold expansion can straddle the target length entirely**, so the growing-prefix
length never equals the target exactly — it jumps from below to above in one step.
**Why it happens:** `casefold()` is not a 1:1 character map; 104 codepoints in Unicode's case-folding
table (verified by scanning all 0x110000 codepoints against the installed CPython 3.13) expand to
more than one character (`ß→ss`, `ﬁ→fi`, `ﬆ→st`, `İ→i̇`, `ǰ→j`+combining-caron, etc). Adversarial
case constructed and verified: spec name `"s"` (length 1, already-casefolded per D-34), input
`"ß foo"` → `folded = "ss foo"`, which DOES pass `folded.startswith("s")` — but the very first
original character (`ß`) alone folds to 2 characters, so a scan requiring an EXACT length match at
some prefix never finds one; it jumps from accumulated-length 0 straight past 1 to 2.
**How to avoid:** This is provably **not a real match** and should be rejected the same way
`"sunny"` doesn't match `"sun"` — verified via a full-Unicode-codepoint scan that **zero** of the
104 multi-character casefold expansions contain a whitespace character, so whenever the boundary
scan overshoots without hitting the target length exactly, the folded content immediately following
the notional keyword boundary is guaranteed non-whitespace — i.e., a genuine word-boundary
violation. The correct algorithm (Code Examples §1) therefore treats "scan completes without
finding the exact target length" as "this spec does not match, continue" — which is exactly the
existing `continue` control flow already in `match_command`'s loop, no new branch semantics needed.
**Warning signs:** the test suite should include the adversarial single-character-overshoot case
(`"s"`/`"ß foo"` → no match) alongside the two CONTEXT-named examples, as the sharpest discriminator
that the algorithm handles overshoot correctly and doesn't silently mis-slice or crash.

### Pitfall 5: `tests/test_match.py` is not an existing file — CONTEXT.md's canonical_refs is stale on this point
**What goes wrong:** Planning against "match its shape" (an existing precedent) when no such file
exists risks the plan under-scoping the new-file creation work (import boilerplate, docstring
conventions, `MARKER`-style module constants) that Phase 1 had to do from scratch for
`test_retry.py`/`test_identity.py`.
**Why it happens:** CONTEXT.md's canonical_refs section lists `tests/test_match.py` /
`tests/test_selection.py` together as "existing per-module test precedents." `test_selection.py`
DOES exist (Phase 2, D-29). `test_match.py` does NOT — verified via `ls tests/` and a recursive
grep for `match_command`/`CommandRegistry`/`PanelKit`/`SchedulerEngine` across `tests/`, which
found zero references anywhere except one incidental `SchedulerEngine`-adjacent double in
`test_reload.py` (a fake of `SchedulerEngine` ITSELF, for `ReloadEngine`'s benefit — not a test of
`SchedulerEngine`'s own contract).
**How to avoid:** Budget the plan for four brand-new test files (`test_match.py`,
`test_registry.py`, `test_panelkit.py`, `test_engine.py`), matching Phase 1's "founding the test
substrate for this module" framing, not "adding one case to an existing suite."
**Warning signs:** none specific — this is a scoping/estimation risk, not a runtime risk.

## Code Examples

### 1. MATCH-01's verified original-index boundary algorithm
```python
# yahir_reusable_bot/registry/match.py — new private helper + its call site.
# Verified: O(n), single pass, no re-casefolding of growing substrings, and correct
# for every codepoint whose str.casefold() changes length (checked against all
# 104 such codepoints in the installed CPython 3.13 Unicode tables — see
# Pitfall 4 for the adversarial overshoot case this handles).

def _keyword_boundary(stripped: str, name: str) -> int | None:
    """Return the index into `stripped` just past the folded match of `name`.

    `name` is already casefolded (guaranteed by D-34's registration-time
    validation). Accumulates each original character's casefolded length; the
    boundary is the first original index where the running total reaches
    `len(name)` EXACTLY. If the running total jumps PAST `len(name)` without
    ever hitting it exactly, the keyword boundary falls strictly inside a
    single character's multi-char casefold expansion (e.g. `ß`->`ss`) — this
    can never be a real word-boundary match, because no Unicode casefold
    expansion contains whitespace (verified across all 0x110000 codepoints),
    so the folded character immediately after the notional boundary is
    guaranteed non-whitespace. Returning None in that case is equivalent to
    the existing word-boundary rejection (`continue`), not a new failure mode.
    """
    target = len(name)
    acc = 0
    for i, ch in enumerate(stripped, start=1):
        acc += len(ch.casefold())
        if acc == target:
            return i
        if acc > target:
            return None
    return None  # defensive; unreachable given the caller's startswith guard


def match_command(text: str, specs: Iterable[CommandSpec]) -> ParsedCommand:
    stripped = text.strip()
    folded = stripped.casefold()
    for spec in specs:
        if not folded.startswith(spec.name):
            continue
        boundary = _keyword_boundary(stripped, spec.name)
        if boundary is None:
            continue
        rest = stripped[boundary:]
        if rest and not rest[0].isspace():
            continue
        arg = rest.strip() or None
        return ParsedCommand(spec=spec, arg=arg)
    return ParsedCommand(spec=None, arg=None)
```
Verified end-to-end against the D-43-named cases plus the adversarial one:
```
match_command("ßtatus hello", [spec("sstatus")]) -> spec=sstatus, arg="hello"
match_command("ﬁnd hello",    [spec("find")])     -> spec=find,    arg="hello"
match_command("ß foo",        [spec("s")])         -> spec=None,    arg=None   (adversarial overshoot — correctly rejected)
match_command("ﬆatus hi",     [spec("status")])    -> spec=status,  arg="hi"   (extra adversarial ligature beyond the two D-43-named cases)
```

### 2. SCHED-01's dependency-free idempotent swallow
```python
# yahir_reusable_bot/scheduler/engine.py
def remove(self, job_id: str) -> None:
    """Drop the job with this id; a no-op success if it is already gone.

    Idempotent by design (D-38, SCHED-01): a host scheduler's "job not found"
    signal (e.g. APScheduler's JobLookupError, which IS a KeyError —
    verified against apscheduler 3.x source) is caught and swallowed with a
    debug log, mirroring Path.unlink(missing_ok=True). This module never
    imports a specific scheduler package (host-agnostic by design, D-05); a
    bare `except KeyError:` catches the real signal without adding a
    dependency this facade has never needed.
    """
    try:
        self._scheduler.remove_job(job_id)
    except KeyError:
        _log.debug("scheduler remove: id already absent", job_id=job_id)
```
Test double — no apscheduler import needed:
```python
class _FakeRawScheduler:
    """A minimal double for the host-injected scheduler `SchedulerEngine` wraps."""
    def __init__(self, raise_on_remove: bool = False) -> None:
        self.raise_on_remove = raise_on_remove
        self.removed: list[str] = []

    def remove_job(self, job_id: str) -> None:
        if self.raise_on_remove:
            raise KeyError(f"No job by the id of {job_id} was found")  # apscheduler's JobLookupError IS a KeyError
        self.removed.append(job_id)
```

### 3. LIFE-02's monkeypatch-based close-counting double (first `monkeypatch` use in this repo)
```python
# tests/test_identity.py addition
def test_write_pid_atomic_closes_temp_fd_exactly_once_on_replace_failure(tmp_path, monkeypatch):
    """A failing os.replace must not double-close the temp fd (D-42/LIFE-02).

    Real os.close is used (delegated through), so a genuine pre-fix double
    close raises OSError (EBADF) on the SECOND call in-process — which the
    pre-fix `except OSError: pass` swallows. This proves the STRUCTURAL
    invariant the fix guarantees ("closed at most once"), rather than trying
    to force an actual fd-integer-reuse race (non-deterministic, unprovable
    in a single-threaded test).
    """
    import os as real_os
    from yahir_reusable_bot.lifecycle import identity

    close_calls: list[int] = []
    real_close = real_os.close

    def _counting_close(fd: int) -> None:
        close_calls.append(fd)
        real_close(fd)

    fake_os = types.SimpleNamespace(**vars(real_os))
    fake_os.close = _counting_close
    fake_os.replace = lambda *a, **kw: (_ for _ in ()).throw(OSError("simulated replace failure"))
    monkeypatch.setattr(identity, "os", fake_os)

    pid_file = tmp_path / "bot.pid"
    with pytest.raises(OSError, match="simulated replace failure"):
        identity.write_pid_atomic(pid_file)

    assert len(close_calls) == 1, (
        "the temp fd must be closed exactly once; a second close on the same "
        "fd integer risks silently closing an unrelated descriptor if the OS "
        "reused it between the two close() calls"
    )
```
(`types.SimpleNamespace(**vars(real_os))` is one reasonable way to build a delegating fake module
object without a mocking library; the planner/executor may pick any equivalent shape — the
load-bearing part is that `close` counts real invocations and `replace` raises.)

### 4. DISC-05's direct, on_error-independent test (unaffected by Pitfall 1)
```python
# tests/test_panelkit.py — calls interaction_check DIRECTLY, sidestepping
# discord.py's View/_scheduled_task dispatch machinery entirely (matches D-43's
# literal spec and is unaffected by the Pitfall 1 correction).
class _FakeInteraction:
    def __init__(self, user=None):
        self.user = user
        self.data = {"custom_id": "mk:cmd:status"}

def test_interaction_check_returns_false_without_raising_when_user_absent():
    panel = _build_test_panel()  # constructed with the usual required-injection args
    interaction = _FakeInteraction(user=None)
    result = asyncio.run(panel.interaction_check(interaction))
    assert result is False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `str.lower()` for case-insensitive command matching | `str.casefold()` | Already the case in this codebase (Phase-0 extraction) | `casefold()` is the Unicode-correct choice for caseless matching (handles `ß`, ligatures, Turkish dotting) but is precisely why length-preservation cannot be assumed — this phase is closing the gap that choice opened |
| N/A (no prior `monkeypatch` use in this repo) | `pytest`'s built-in `monkeypatch` fixture for LIFE-02 | This phase | First introduction; the planner should call this out in the plan the same way Phase 1 called out `conftest.py` and `pytest.raises()` as deliberate house-style extensions |

**Deprecated/outdated:** none — no library version changes in this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The absence of `interaction.user` in production discord.py 2.7.1 (via the `MISSING` sentinel path) is reachable only in edge interaction-payload shapes not currently exercised by WeatherBot (guild member data missing from the payload) | Pitfall 1 / Phase Requirements DISC-05 | Low — even if the exact production trigger differs from this description, the guard (`if not interaction.user:`) and the RED test (direct `interaction_check` call with a synthetic `.user = None`) are correct regardless of which real-world payload shape produces the absent-user condition |
| A2 | No future discord.py patch release within the `==2.7.1` exact pin changes `_scheduled_task`'s try/except wrapping | Pitfall 1 | None — the pin is exact (`discord.py==2.7.1`), so this is not a moving target for this phase |

**All other claims in this research were verified via direct source reads of the installed
dependencies, or via executed reproductions in this environment** — no additional unconfirmed
assumptions remain.

## Open Questions

1. **Phase branch vs. direct-to-main (process, not correctness)**
   - What we know: Phase 1 used a dedicated phase branch (`phase-01-reachable-reliability`)
     merged at the end (D-14). Phase 2's git history shows commits landing directly on `main`
     with no phase branch and no merge commit. `.planning/config.json` sets
     `"branching_strategy": "none"`.
   - What's unclear: whether Phase 3 should resurrect D-14's phase-branch convention or follow
     Phase 2's direct-to-main precedent. CONTEXT.md does not restate D-14 for this phase.
   - Recommendation: the planner should decide explicitly and state the choice in the plan's
     process notes, rather than leaving it implicit — either choice is compatible with GATE-01
     and the D-13 two-commit idiom; it only affects whether `main` sees interim RED commits.

2. **Whether `registry/`'s two new test files should be split or combined**
   - What we know: `match.py` and `registry.py` are separate modules with separate existing
     naming precedent (`test_<module>.py` per file).
   - What's unclear: nothing technical — this is pure discretion, already delegated by CONTEXT.md.
   - Recommendation: keep them split (`test_match.py`, `test_registry.py`) to preserve the
     unbroken 1:1 module-name convention; a combined file would be the first exception to it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` / Python 3.13 venv | all fixes | ✓ | Python 3.13 (repo requires ≥3.12) | — |
| `pytest` | all RED/GREEN tests, GATE-01 | ✓ | 9.1.1 (pin `>=9.0.3`) | — |
| `ruff` | lint | ✓ | 0.15.20 (pin `>=0.15.16`) | — |
| `grimp` | import-hygiene gate (GATE-01) | ✓ | 3.14 | — |
| `tenacity` | RELY-02/03 | ✓ | 9.1.4 (pin `>=9.1.4`) | — |
| `discord.py` | DISC-05/06 | ✓ | 2.7.1 exact pin | — |
| `apscheduler` | **deliberately NOT used** (see Pitfall 2) | ✗ (not installed, not a dependency) | — | `except KeyError:` — no fallback needed, this is the correct design, not a gap |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `apscheduler` is absent by design; no fallback needed
because the fix does not require it (see Common Pitfalls #2).

Baseline (pre-phase) full-suite run: `uv run pytest tests/ -q` → **35 passed, 0 failed** (one
pre-existing, unrelated `RuntimeWarning` about an un-awaited coroutine in `test_gateway.py`, not
introduced by this research and out of this phase's scope).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (pin `>=9.0.3` in `pyproject.toml`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths=["tests"]`, `pythonpath=["."]`, `addopts="-ra"` |
| Quick run command | `uv run pytest tests/test_<file>.py -v` (per new/modified file) |
| Full suite command | `uv run pytest -q` (matches `.planning/config.json`'s `workflow.test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MATCH-01 | `ßtatus hello`/`ﬁnd hello`/adversarial `ß foo` (overshoot) extract correctly (or correctly non-match) | unit | `uv run pytest tests/test_match.py -x` | ❌ Wave 0 (new file) |
| MATCH-02 | Empty-name spec and uppercase-name spec both raise `ValueError` at `CommandRegistry`/`build_registry` construction | unit | `uv run pytest tests/test_registry.py -x` | ❌ Wave 0 (new file) |
| RELY-02 | `build_retrying(attempts_per_burst=1, ...)` driven to exhaustion does not raise `ZeroDivisionError` | unit | `uv run pytest tests/test_retry.py -k rely_02 -x` | ✅ (extend existing) |
| RELY-03 | `_within_burst_wait`/`two_burst_wait` mid-pause fires exactly at `attempt_number == burst_size`, pinned by assertion | unit | `uv run pytest tests/test_retry.py -k rely_03 -x` | ✅ (extend existing) |
| DISC-05 | `interaction_check` with `.user = None` (or the `MISSING`-shaped absence) returns `False`, never raises | unit | `uv run pytest tests/test_panelkit.py -k disc_05 -x` | ❌ Wave 0 (new file) |
| DISC-06 | `PanelKit(..., marker="")` and `marker="   "` both raise at construction | unit | `uv run pytest tests/test_panelkit.py -k disc_06 -x` | ❌ Wave 0 (new file) |
| LIFE-02 | A failing `os.replace` results in exactly one `os.close` call on the temp fd; original error re-raises | unit | `uv run pytest tests/test_identity.py -k life_02 -x` | ✅ (extend existing) |
| LIFE-03 | `_argv_matches_marker` with a path-shaped `proc_marker` matches the non-Linux degrade sentinel AND real basenamed argv0 | unit | `uv run pytest tests/test_identity.py -k life_03 -x` | ✅ (extend existing) |
| SCHED-01 | A fake scheduler whose `remove_job` raises `KeyError` (the `JobLookupError` shape) → `SchedulerEngine.remove` returns without raising; a present-id variant still forwards the removal | unit | `uv run pytest tests/test_engine.py -x` | ❌ Wave 0 (new file) |
| GATE-01 | Full suite + import-hygiene/litmus/grimp stay green after every commit | integration/gate | `uv run pytest -q && uv run pytest tests/test_import_hygiene.py -q` | ✅ (standing gate) |

### Sampling Rate
- **Per task commit:** the specific new/modified test file (`uv run pytest tests/test_<file>.py -v`)
- **Per plan (RED→GREEN pair) merge:** full suite (`uv run pytest -q`)
- **Phase gate:** `uv run pytest -q` (35+ passing, 0 failing) AND
  `uv run pytest tests/test_import_hygiene.py -q` green, before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_match.py` — covers MATCH-01 (new file, no existing precedent despite CONTEXT.md's claim)
- [ ] `tests/test_registry.py` — covers MATCH-02 (new file)
- [ ] `tests/test_panelkit.py` — covers DISC-05/06 (new file)
- [ ] `tests/test_engine.py` — covers SCHED-01 (new file)
- Framework install: none — pytest/ruff/grimp all already installed and verified
- No new shared fixtures anticipated in `tests/conftest.py` under D-10's "grows on a real second
  caller" rule — each new double (fake raw scheduler, fake interaction, monkeypatched os) is used
  by exactly one test file in this phase; revisit only if a later phase needs the same double

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | This phase touches no auth flow |
| V3 Session Management | no | N/A |
| V4 Access Control | yes (DISC-05/06) | `interaction_check`'s operator-gate + `is_owned_panel`'s ownership predicate are the access-control surface here; the fixes CLOSE gaps (a None-user bypass path and an empty-marker "matches everything" hole), they do not introduce new access-control logic |
| V5 Input Validation | yes (MATCH-01/02, DISC-06) | `CommandSpec.name` and `PanelKit`'s `marker` become validated-at-construction inputs (D-34/D-41) — deny-by-default, matching the existing `is_transient` deny-by-default idiom (Phase 1 D-02) |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Empty/blank ownership marker matching every bot-authored message (H12/DISC-06) | Elevation of Privilege (an unauthenticated actor's message could be treated as an owned, deletable panel) | Reject empty/whitespace marker at construction (D-41) — already the locked fix |
| Operator-gate bypass via an unhandled exception path (H11/DISC-05) | Denial of Service (a crash-prone gate is a worse failure mode than a clean reject) / minor Elevation-of-Privilege risk (an unhandled exception's fallback behavior is less auditable than an explicit `return False`) | None-guard + explicit `return False` + audit log (D-40) |
| Div-by-zero inside a retry wait callable crashing the whole retry schedule (H09/RELY-02) | Denial of Service (an unhandled crash inside `Retrying.__call__` propagates as a `ZeroDivisionError`, not the expected exhaustion outcome, potentially confusing upstream error handling) | Guard + degrade (D-36) |
| Uppercase/empty command spec silently unmatchable or over-matching (H13/MATCH-02) | Tampering-adjacent (an operator-facing command silently never firing, or an empty command silently matching blank input, is a correctness/availability issue more than a classic injection) | Deny-by-default validation at registration (D-34) |

No new external input surface is introduced by this phase (no new network calls, no new
deserialization, no new file I/O beyond the pre-existing `write_pid_atomic`/`is_running_process`
paths already covered by LIFE-01/02/03). This phase is entirely about making already-injected,
already-trusted (per the module's existing threat model) inputs fail closed/clean instead of
failing open or crashing.

## Sources

### Primary (HIGH confidence — verified by direct execution/source read in this session)
- Installed `tenacity` 9.1.4 source (`.venv/lib/python3.13/site-packages/tenacity/__init__.py`) —
  `Retrying.__init__` signature, `RetryCallState.attempt_number` (1-indexed, incremented at
  `iter.py`-equivalent `_post_stop_check_actions.next_action`), and the `_run_wait`-before-`_run_stop`
  call order.
- Installed `discord.py` 2.7.1 source (`.venv/lib/python3.13/site-packages/discord/ui/view.py`,
  `discord/interactions.py`, `discord/ui/item.py`, `discord/utils.py`) — `View._scheduled_task`'s
  try/except scope, `Interaction.user`'s `MISSING` initialization, `_MissingSentinel.__bool__`.
- An executed, in-session reproduction calling the REAL `discord.ui.View._scheduled_task` with a
  synthetic `.user = None` interaction — confirms `on_error` IS invoked (contradicts H11's stated
  mechanism; does not change the D-40 fix).
- An executed, in-session reproduction of `build_retrying(attempts_per_burst=1, ...)` against the
  pre-fix `yahir_reusable_bot.reliability.retry` — confirms `ZeroDivisionError` on the second
  attempt (RELY-02).
- A full-Unicode-codepoint scan (`for cp in range(0x110000)`) against CPython 3.13's
  `str.casefold()` — confirms exactly 104 codepoints expand to multiple characters, none of which
  contain whitespace, and confirms the per-character concatenation property
  `(a+b).casefold() == a.casefold()+b.casefold()` holds for every tested case (MATCH-01).
- `pyproject.toml` / `uv.lock` — confirms the exact dependency set and pinned versions; confirms
  `apscheduler` is absent.
- Web fetch of the actual APScheduler 3.x GitHub source
  (`apscheduler/jobstores/base.py`) — confirms `class JobLookupError(KeyError)`.
- Direct reads of `yahir_reusable_bot/registry/match.py`, `registry.py`, `spec.py`,
  `reliability/retry.py`, `discord/panelkit.py`, `lifecycle/identity.py`, `scheduler/engine.py` —
  confirms every line-number claim in CONTEXT.md's canonical_refs (all accurate, one trivial
  one-line drift: `interaction_check`'s actual span is `299-331`, not `299-330` as stated — the
  specific referenced defect line `:309` is exact).
- `git log` / `git branch` — confirms Phase 1 used a phase branch + merge commit; Phase 2 committed
  directly to `main` with no branch.
- `uv run pytest tests/ -q` — confirms pre-phase baseline: 35 passed, 0 failed.

### Secondary (MEDIUM confidence)
- APScheduler `JobLookupError` base-class confirmation via WebSearch (cross-checked against the
  GitHub source fetch above, which is the authoritative confirmation).

### Tertiary (LOW confidence)
- None — every claim in this research was either verified by direct execution/source read in this
  session, or is a locked decision copied verbatim from CONTEXT.md (not a research claim).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every version verified against the installed `.venv`.
- Architecture: HIGH — every fix's location and surrounding function verified against the current
  working tree; the two corrections (Pitfalls 1 and 2) are backed by executed reproductions, not
  inference.
- Pitfalls: HIGH — all five pitfalls are either verified by direct execution in this session
  (1, 2, 3, 4) or by direct filesystem inspection (5).

**Research date:** 2026-07-27
**Valid until:** 30 days, EXCEPT the `discord.py==2.7.1` and `tenacity>=9.1.4` exact-pin-dependent
findings (Pitfalls 1 and 3), which are valid as long as those pins are unchanged (exact pin for
discord.py; the tenacity call-order trace is unlikely to change across minor versions but was only
verified against 9.1.4 specifically).
