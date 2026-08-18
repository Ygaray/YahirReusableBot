# Phase 7: v0.1.2 debt paydown - Context

**Gathered:** 2026-08-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Close every open item from the v0.1.2 retrospective audit
(`.planning/v0.1.2-MILESTONE-AUDIT.md`, 9 items) so the hub carries forward no known footgun and
no stale planning doc. Nine requirements: **MATCH-03, LIFE-05, SURF-02, DISC-07, DISC-08, HYG-02,
HYG-03, DOCS-02, DOCS-03**.

Independent of Phases 5–6 (Track A / PC-01 redaction promotion). Sequenced last so the headline
promotion lands first and this debt absorbs any slip.

**Not in this phase:** any new capability. Every item is a known defect or a deliberately-deferred
decision from v0.1.2. Adopting a static type checker is explicitly deferred (see `<deferred>`).

</domain>

<premise_corrections>
## ⚠ Premise corrections — read these BEFORE the requirement text

Four requirement/audit statements were verified against live source and the filesystem during
discussion and found **stale or imprecise**. A downstream agent reading only `REQUIREMENTS.md` or
the audit will re-derive the wrong premise. This section supersedes them.

### PC-A — LIFE-05's requirement text names an already-fixed form

`REQUIREMENTS.md:186` and the audit's item 9 describe "the attached `-mmodule` form false
negative." **That form is already fixed.** `yahir_reusable_bot/lifecycle/identity.py:226-227`
decodes `-mexamplebot` → `examplebot`:

```python
if token.startswith(b"-m"):
    return token[2:] == proc_marker
```

Landed in v0.1.2 (commit `60698b1`) with three passing tests in `tests/test_identity.py`
(lines 130, 143, 152). The **actual** remaining false negative is the *bundled short-option
group* — `python -Omexamplebot`, `python -Imjson.tool` — pinned as a deliberate limitation by
`tests/test_identity.py:165` (`test_bundled_short_option_group_not_matched`) and reasoned out in
the `_argv_matches_marker` docstring at lines 179–192.

D-61 decides the *bundled* form. It does not decide the attached form, which needs no decision.

### PC-B — HYG-03 is a production defect, not only a test-double artifact

The audit classifies HYG-03 as a "test-double artifact." **The root cause is in production code.**
`yahir_reusable_bot/discord/gateway.py:353`:

```python
future = asyncio.run_coroutine_threadsafe(self._client.close(), loop)
```

`self._client.close()` constructs the coroutine object **before** `run_coroutine_threadsafe` is
called. On the TOCTOU race the surrounding docstring itself describes (the loop closes between
`loop.is_running()` and this line), `run_coroutine_threadsafe` raises, the coroutine is never
scheduled, and it is garbage-collected unawaited. The test reproduces this race; it does not
create it. Fixing only the fake client masks the live leak and deletes the only signal.

**Fix constraint (why the `try` must be split):** `coro.close()` cannot go in the existing shared
`except`. If scheduling *succeeded* and only `future.result()` timed out, the coroutine is live on
the loop and closing it raises `RuntimeError: cannot close a running coroutine`. The
scheduling-failure and await-failure paths must be separated.

### PC-C — DISC-07's root cause is the exception hierarchy

Verified at runtime: `discord.Forbidden` **is** a subclass of `discord.HTTPException` (as is
`discord.NotFound`). The *first* `msg.pin()` already separates them (`gateway.py:196-200`, where
`Forbidden` re-raises to the outer TOCTOU backstop). The **retry** pin at `gateway.py:218` catches
bare `HTTPException`, so a revoked permission on retry is logged as
`"panel pin failed at cap even after evicting a stray"`. It is not a missing branch — it is a
subclass being swallowed by a broader `except` that runs first.

### PC-D — the drift count is 14 lines / 9 files, and the audit's own "11 artifacts" is stale

The audit (`v0.1.2-MILESTONE-AUDIT.md:142`) and `REQUIREMENTS.md:217` both say "11 planning
artifacts." That count included `STATE.md:101`, which has since been rewritten for v0.2.0. The
live count is **9 files / 14 lines** of genuine drift (full map in `<code_context>`).

**Critical for the DOCS-02 gate:** three of the 14 sites write the **bare** `ops/daemon.py` form
without the `weatherbot/` prefix (`04-CONTEXT.md:48`, `04-RESEARCH.md:15`, `04-VALIDATION.md:77`).
A gate greping the fully-qualified `weatherbot/ops/daemon.py` misses them. This is the audit's own
headline lesson recurring — *a check derived from a narrower string than the error cannot catch
the error.* **The gate pattern is `ops/daemon`, not `weatherbot/ops/daemon`.**

</premise_corrections>

<decisions>
## Implementation Decisions

> Decision numbering continues the project-wide sequence. Phase 6 reached **D-60**, so Phase 7
> starts at **D-61**.
>
> **Framing note for downstream agents (carried from Phases 5–6, still binding):** the user is
> highly technical in this project's domain (Python services, systemd, deployment). Surface
> decisions in plain language with a concrete recommendation; do not present bare trade-off menus.
> `USER-PROFILE.md` matched `learning_style: guided`, which nominally activates advisor mode's
> product-outcome reframe — it was **deliberately not applied** here, and the reasoning was
> surfaced to the user at discuss time for audit.
>
> **Advisor-mode deviation, recorded:** the four gray areas were **not** researched by parallel
> advisor subagents. The session was configured not to spawn agents unasked, and the orchestrator
> had already read every relevant code site, verified the `discord` exception hierarchy at runtime,
> traced the identity-guard fix through git history, and checked the WeatherBot paths on disk — so
> comparison tables were synthesized inline from that evidence. Every option below is grounded in a
> verified fact, not a generic pattern. The deviation was disclosed to the user before the tables
> were presented.

### Identity guard `-m` boundary (LIFE-05)

- **D-61 (ratify the boundary, and make the limitation consumer-visible):** the bundled
  short-option group (`python -Om<module>` / `-Im<module>`) stays **undecoded**. No behavioral
  change to `_argv_matches_marker`. Three deliverables instead:
  1. Correct the stale requirement/audit text so it names the **bundled** form, not the
     already-fixed attached form (see PC-A).
  2. Flip LIFE-05 to resolved-as-documented-limitation, with the reasoning recorded.
  3. **State the constraint in `EXTENSION-GUIDE.md`** — a consumer-facing contract line
     ("do not launch your daemon as `python -Om<module>`"), not only a private docstring.

  **Why:** the guard's failure directions are asymmetric. A false negative reports a live daemon
  as dead (annoying, recoverable). A false positive delivers SIGHUP — default disposition
  *terminate* — to an unrelated recycled PID. The code's own docstring
  (`identity.py:184-192`) already argued this out: `-Om` is `-O`+`-m`, but `-Xmfoo` is `-X`
  *consuming* `mfoo`, so partial decoding of CPython's bundling grammar risks matching the wrong
  token. The phase goal is "no known footgun" — decoding would arguably **add** one.

  - **Rejected — decode the bundled group with a whitelist** (walk short-option letters against
    CPython's argument-less flag set `-B -b -d -E -i -I -O -P -q -s -S -u -v -x`, bail to `False`
    on any unknown letter so `-Xmfoo` never decodes): closes the last known false negative and is
    genuinely implementable safely. Rejected because it encodes a slice of CPython's CLI grammar
    into the hub — which drifts when CPython changes — and any whitelist gap converts a benign
    false negative into a dangerous false positive. It buys closure on a gap **no consumer in the
    ecosystem currently hits**.
  - **Rejected — ratify with an internal record only** (correct the requirement text, no
    consumer-facing doc): identical behavior, but this is a **hub**. A limitation that exists only
    in a private docstring is invisible to the consumer who trips it.

- **D-61a (scope note for the planner):** LIFE-05 ships **no source change** to `identity.py`
  beyond an optional comment marker. Its RED-first obligation under GATE-02 is satisfied by the
  already-passing pinned test `test_bundled_short_option_group_not_matched` — a boundary guard,
  explicitly GREEN both pre- and post-fix. **Do not manufacture an artificial RED test for a
  decision whose outcome is "no behavioral change."** Record this exemption explicitly in the plan
  so the GATE-02 RED-first ancestry audit does not flag it as a gap.

### Public surface annotations (SURF-02)

- **D-62 (narrow `on_online`, and sweep the other two loose `Callable[...]` to a decided state):**
  three annotation sites, each with a distinct verdict:

  | Site | Verdict |
  |---|---|
  | `lifecycle/ready_gate.py:91` `on_online: Callable[..., None] \| None` | **Narrow** → `Callable[[HealthResult], None] \| None` |
  | `discord/panelkit.py:166` `render: Callable[..., discord.Embed]` | **Narrow arity** → `Callable[[Any, Any], discord.Embed]` |
  | `scheduler/engine.py:52` `callback: Callable[..., Any]` | **Leave variadic** — record why |

  **Grounding facts, all verified:**
  - `on_fail` at `ready_gate.py:92` is **already** `Callable[[HealthResult], None] | None`. Only
    `on_online` is loose — this is drift, not a design stance.
  - The hub always invokes it with exactly one argument
    (`_best_effort_hook(self._on_online, result, label="on_online")`, `ready_gate.py:135`). There
    is no variadic case; `Callable[..., None]` is strictly *less* accurate than reality.
  - **The only live consumer already conforms:** `WeatherBot/weatherbot/scheduler/wiring.py:442`
    is `def _on_online(_result) -> None:` — single positional param. Narrowing breaks nothing
    today. (Tests at `WeatherBot/tests/test_lifecycle_module.py:59,104` likewise pass
    `lambda _arg: ...`.)
  - `panelkit` calls `render(reply, render_arg)` — always exactly two positional args. Narrowing
    to `[Any, Any]` is type-vacuous but **arity-accurate**, which is the real contract.
  - `scheduler.register(callback)` passes opaque `args`/`kwargs` straight through to
    `add_job` — `Callable[..., Any]` is **correct**, not drift. Recording that verdict converts it
    from an unexamined site into a decided non-issue.

  - **Rejected — narrow `on_online` only:** the literal requirement, smallest diff. Rejected
    because it leaves the same class of finding live against two other sites, ready to resurface
    in the next retrospective.
  - **Rejected — leave loose and document why:** there is nothing to document except "we didn't
    get to it." That would make the phase goal's "explicitly decided" a decided-by-accident.

- **D-63 (enforcement is a signature-assertion test, not a type checker):** the hub runs **no**
  static type checker — dev deps are `pytest`, `ruff`, `syrupy`, `time-machine`, `grimp` only. So
  SURF-02's RED-first regression test asserts the annotation directly:

  ```python
  hints = typing.get_type_hints(ReadyGate.__init__)
  assert hints["on_online"] == Callable[[HealthResult], None] | None
  ```

  This fails against pre-fix source (RED-first satisfied) and keeps failing if anyone widens it
  back. It guards *these signatures*, not all call sites — a deliberate, narrower scope than a
  type checker would give. **Adopting pyright was raised by the user and explicitly deferred** —
  see `<deferred>` for the sizing and reasoning.

### Unawaited-coroutine warning (HYG-03)

- **D-64 (fix production, and split the log by cause):** restructure `BotThread.stop()`
  (`gateway.py:350-357`) so the coroutine is bound to a name, the schedule and the await are
  separate `try` blocks, and the orphan is reclaimed **only** on the scheduling-failure branch:

  ```python
  coro = self._client.close()
  try:
      future = asyncio.run_coroutine_threadsafe(coro, loop)
  except Exception:
      coro.close()   # never scheduled -> reclaim; safe here and ONLY here
      _log.warning("bot client.close() could not be scheduled (loop closed)")
  else:
      try:
          future.result(timeout=timeout)
      except Exception:
          _log.warning("bot client.close() did not complete cleanly")
  ```

  *(Illustrative shape, not a literal patch — the planner owns the final form. The invariants it
  must preserve: `stop()` NEVER raises, and `self._thread.join(timeout=timeout)` below is ALWAYS
  reached.)*

  **Why split the messages:** the `try` has to be split regardless, to satisfy the
  `RuntimeError: cannot close a running coroutine` constraint in PC-B — so two distinct messages
  are free. And they buy real diagnosability: you learn whether the loop died early or the client
  hung. This is **the same posture DISC-07 takes** — stop conflating two causes behind one
  message. Landing both with one posture makes the phase coherent rather than a bag of patches.

  - **Rejected — fix the test double** (make `_FakeCloseableClient.close` synchronous): one line,
    suite instantly clean. Rejected outright — it **masks** the defect. The production orphan
    survives on the live closed-loop race and the only signal is deleted. Directly contradicts the
    phase goal.
  - **Rejected — fix production, keep one log message:** the same real fix, but the "one message"
    saving is cosmetic once the `try` is split anyway, and it discards free diagnosability.

- **D-65 (zero-warnings becomes structural, not incidental):** add
  `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` in `pyproject.toml`. HYG-03's
  wording is *"the full suite emits zero warnings"* — today that is true by accident, with nothing
  enforcing it. This makes any future warning **fail** the suite, matching the posture GATE-02
  takes everywhere else.

  **Planner obligation:** verify the full suite stays green under the filter before committing it
  (baseline at discuss time was `158 passed, 1 warning` — the 1 being HYG-03 itself). If a
  dependency deprecation ever forces an exception, the remedy is a **targeted `ignore::` entry
  with a comment naming the dependency and the reason** — never removing the filter.

### Doc drift (DOCS-02 / DOCS-03)

- **D-66 (correct the active artifacts, annotate the archive):**
  - **Correct in place** the 2 active genuine-drift sites: `REQUIREMENTS.md:119` and
    `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:213` (the origin).
  - **Annotate, do not rewrite,** the 7 archived files under
    `.planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/`: add a one-line drift banner
    at the top of each, pointing at the audit finding. Bodies stay as the historical record of
    what was actually believed at the time.
  - **Do NOT touch** the 3 intentional mentions (`REQUIREMENTS.md:217`,
    `v0.1.2-MILESTONE-AUDIT.md:21` and `:142`) — they name the wrong path *as the error being
    described*. Rewriting them would destroy the record of the finding.

  **Why annotate rather than rewrite the archive:** `04-01-PLAN.md:257` contains the
  `<automated>` grep check that *passed by grepping the wrong string*. That artifact is the
  primary evidence for the audit's headline lesson. Rewriting it erases the evidence; a banner
  preserves it while warning anyone who lands there directly.

  - **Rejected — correct everything including the archive:** cleanest greppable end state, but
    rewrites history and destroys the `<automated>`-check evidence above.
  - **Rejected — correct active only, leave archive untouched:** keeps history honest, but a
    reader landing in `04-01-PLAN.md` directly gets no warning at all.

- **D-67 (verification = an always-runs in-suite gate + one-time recorded filesystem evidence):**
  two mechanisms, deliberately separate:

  1. **In-suite gate (standing, no cross-repo dependency).** A test asserting the string
     **`ops/daemon`** (bare — see PC-D) appears in **no active planning artifact**, with an
     explicit exempt-list for the files that legitimately discuss the drift. **Every exemption
     carries an inline comment stating why it is exempt.** The exempt set at authoring time:
     `.planning/v0.1.2-MILESTONE-AUDIT.md`, `.planning/REQUIREMENTS.md` (the DOCS-02 requirement
     block at line 217), and the annotated archive under
     `.planning/milestones/v0.1.2-phases/`.
  2. **One-time filesystem evidence (recorded in the phase SUMMARY, not a test).** Verify all
     three de-hack paths resolve on disk in WeatherBot, and record the result as evidence.
     Verified at discuss time (2026-08-03): `weatherbot/ops/daemon.py` **does not exist**;
     `weatherbot/scheduler/daemon.py` **exists**; `weatherbot/ops/selfcheck.py` **exists**.

  **Why not a `skipif(weatherbot_missing)` test.** The roadmap asks the check to assert the path
  resolves on disk in WeatherBot, but the hub's suite cannot hard-depend on a WeatherBot checkout
  (fresh clone, CI, another machine). A skip-guarded check is the **same failure class the audit
  warned about**: a check that silently does not run is false assurance, exactly like a check that
  greps the string that produced the error. Splitting into a gate that always runs and evidence
  that is recorded once avoids both.

  - **Rejected — marker convention instead of an exempt-list** (require intentional mentions to
    carry an inline marker like `(NONEXISTENT — drift example)`, gate asserts every occurrence is
    marked): more robust to new files, but depends on a convention being remembered by every
    future author. The exempt-list is explicit and self-documenting at the cost of needing an
    update when a new file legitimately discusses the drift.
  - **Rejected — recorded evidence only, no standing gate:** the correction is a fact, but nothing
    would stop it re-drifting.

- **D-68 (DOCS-03 rides on the same correction, and fixes the stale count):** wherever a corrected
  enumeration lands, it names **three** de-hack sites, not two:
  1. `weatherbot/scheduler/wiring.py` `_on_fail` — the fatal-branch `threading.Event` de-hack
  2. `weatherbot/scheduler/daemon.py` — the gate-return exit-code check (**the corrected path**)
  3. `weatherbot/ops/selfcheck.py` `to_health_result` — **the PRODUCING site.** Without it
     classifying `CONFIG_INVALID` as fatal, `HealthResult.fatal` is never set and the
     `ReadyOutcome.FATAL` branch is unreachable in the consumer.

  The generalizable rule to record: **a hub-side deliverable enumerating consumer de-hack sites
  must name the site that PRODUCES the input, not only the sites that CONSUME the outcome.**

  Also correct the stale **"11 artifacts"** figure in `REQUIREMENTS.md:217` (and note it in the
  audit) to the live count — see PC-D. DOCS-02 is *about* stale path claims; leaving its own count
  stale would be self-refuting.

### Claude's Discretion

The user reviewed these four and left the stated directions to the planner. Root causes are pinned
to exact lines; the fix directions below are not open questions.

- **MATCH-03** — add a `seen: set[str]` to the existing D-34 validation loop at
  `registry/registry.py:53` and raise `ValueError` naming the duplicate. The loop already checks
  non-empty + already-casefolded but not uniqueness, so a duplicate silently overwrites in
  `by_name` while `by_keyword_len_desc` / `render_help` carry both. Error type is locked to
  `ValueError` by the ROADMAP. **Consumer-breaking** — the repin needs a WeatherBot sweep for
  duplicate `spec.name` values.
- **DISC-07** — insert an `except discord.Forbidden` **before** the `except discord.HTTPException`
  on the *retry* pin at `gateway.py:218`. Per PC-C, `Forbidden` is a subclass currently swallowed
  by the broader handler. Mirror the distinct treatment the first `msg.pin()` already applies at
  `gateway.py:196-200`.
- **DISC-08** — stop calling `matches.pop(0)` before the eviction delete (`gateway.py:208`).
  Remove the stray from the cleanup list only on a **successful** delete, so a failed eviction is
  still retried by the loop at `gateway.py:237` instead of being dropped from that call's cleanup.
- **HYG-02** — `_log.warning("hook failed; engine result unaffected", label=label)` replacing the
  f-string at `lifecycle/ready_gate.py:188`, **and** the verbatim clone at `config/reload.py:326`.
  One fix, two sites — do not leave the clone drifted.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §"Phase 7: v0.1.2 debt paydown" (lines 355–415) — goal, success criteria,
  the pairing constraint (DISC-07+DISC-08), the shared-site note (HYG-02), the two mandated human
  decisions, and the doc-fix verification note
- `.planning/REQUIREMENTS.md` lines 176–236 — the 9 requirement statements + GATE-02.
  ⚠ **Read `<premise_corrections>` above first** — LIFE-05's text (line 186) is stale and the
  "11 artifacts" figure (line 217) is out of date
- `.planning/v0.1.2-MILESTONE-AUDIT.md` §"Doc Drift" (139–159) and §"Tech Debt — 9 open items"
  (161–177) — the origin of every item in this phase

### Governing constitution
- `ECOSYSTEM.md` §3 — the human-gated close-out rule (tag cut / version bump / consumer repin are
  never performed autonomously). MATCH-03's consumer-breaking sweep lands here
- `CLAUDE.md` — the no-domain-nouns rule and the one-way dependency, enforced by
  `tests/test_import_hygiene.py`
- `EXTENSION-GUIDE.md` — **written to by D-61**: the consumer-facing `-Om<module>` launch-form
  constraint

### Source sites touched by this phase
- `yahir_reusable_bot/registry/registry.py:43-59` — the D-34 validation loop (MATCH-03)
- `yahir_reusable_bot/lifecycle/identity.py:141-228` — `_argv_matches_marker`, its reasoning
  docstring, and the `-m` scan (LIFE-05)
- `yahir_reusable_bot/lifecycle/ready_gate.py:91-92, 135, 174-188` — the `on_online`/`on_fail`
  annotations and `_best_effort_hook` (SURF-02, HYG-02)
- `yahir_reusable_bot/config/reload.py:326` — the verbatim `_best_effort_hook` clone (HYG-02)
- `yahir_reusable_bot/discord/gateway.py:184-260` — `summon_panel`'s pin/evict/cleanup path
  (DISC-07, DISC-08)
- `yahir_reusable_bot/discord/gateway.py:350-360` — `BotThread.stop()` (HYG-03)
- `yahir_reusable_bot/discord/panelkit.py:166` — the `render` annotation (SURF-02)
- `yahir_reusable_bot/scheduler/engine.py:49-75` — `register`'s variadic `callback` (SURF-02,
  leave-as-is verdict)

### Test sites
- `tests/test_identity.py:130-180` — the attached-form tests (already GREEN) and the pinned
  bundled-form limitation test at line 165
- `tests/test_gateway.py:272-293` — `_FakeCloseableClient` /
  `test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call` (HYG-03's reproducer)
- `tests/test_ready_gate.py:105, 137` — existing `on_online=` call sites (SURF-02 blast radius)
- `tests/test_import_hygiene.py` — the standing grimp + isolated-import + AST-litmus gate
- `pyproject.toml` `[tool.pytest.ini_options]` — **written to by D-65**

### Doc-drift target files (DOCS-02 / DOCS-03)
**Correct in place (active):**
- `.planning/REQUIREMENTS.md:119` · `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:213`

**Annotate with a drift banner, do NOT rewrite (archive,
`.planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/`):**
- `04-01-PLAN.md` (lines 29, 249, 256, 257, 261) · `04-CONTEXT.md` (48, 181) ·
  `04-RESEARCH.md` (15) · `04-01-SUMMARY.md` (194) · `04-02-SUMMARY.md` (120) ·
  `04-VALIDATION.md` (77) · `04-VERIFICATION.md` (74)

**Exempt — intentional mentions, do NOT touch:**
- `.planning/REQUIREMENTS.md:217` · `.planning/v0.1.2-MILESTONE-AUDIT.md:21` and `:142`

### Cross-repo (read-only reference; never imported, never modified by this phase)
- `/home/yahir/Projects/WeatherBot/weatherbot/scheduler/wiring.py:435-465` — the live `on_online`
  wiring, `def _on_online(_result) -> None:` (SURF-02 blast-radius evidence)
- `/home/yahir/Projects/WeatherBot/weatherbot/scheduler/daemon.py` — the **correct** gate-return
  de-hack path (DOCS-02)
- `/home/yahir/Projects/WeatherBot/weatherbot/ops/selfcheck.py` — the **producing** de-hack site
  (DOCS-03)

</canonical_refs>

<code_context>
## Existing Code Insights

### Baseline at discuss time
`uv run pytest -q` → **158 passed, 1 warning**. The single warning **is** HYG-03:

```
tests/test_gateway.py::test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call
  gateway.py:357: RuntimeWarning: coroutine '..._FakeCloseableClient.close' was never awaited
```

### Reusable assets
- **The D-34 validation loop** (`registry/registry.py:43-59`) — MATCH-03's `seen: set[str]` drops
  straight into the existing loop; no new structure needed.
- **The distinct-`Forbidden` pattern already in `summon_panel`** (`gateway.py:196-200`) — DISC-07
  copies an idiom the same function already uses, rather than inventing one.
- **`on_fail`'s already-narrow annotation** (`ready_gate.py:92`) — SURF-02's target shape exists
  three lines from the site it is fixing.
- **The pinned-limitation test idiom** (`tests/test_identity.py:165`) — a GREEN-both-ways boundary
  guard with the reasoning in its docstring. LIFE-05's outcome reuses this exact form; Phase 6 also
  used it for the processor-only-leaks test.

### Established patterns (constraining)
- **Strictly serial plans, RED → GREEN → gates green, before the next plan's RED commit.**
  Hard-won in Phases 1–3, re-proven in 5 and 6. A deliberately-RED test must never overlap a
  sibling plan's full-suite gate.
- **Every requirement ships a RED-first regression test** (GATE-02) — with the D-61a exemption
  recorded above for the one requirement whose decided outcome is "no behavioral change."
- **Structured logging throughout** — `_log.warning("message", key=value)`, never f-strings. HYG-02
  is a violation of the house style, and D-64's new messages must follow it.
- **Injection-by-`Any` at the seams is deliberate architecture**, not sloppiness. This is exactly
  why D-62 leaves `scheduler/engine.py:52` variadic and why adopting a strict type checker is a
  separate, sized piece of work rather than a drive-by.

### Integration points
- **`summon_panel` is a single-function collision zone** — DISC-07 and DISC-08 both edit
  `gateway.py:184-260`. The ROADMAP already mandates they land in **one plan**.
- **`_best_effort_hook` is duplicated verbatim** across `lifecycle/ready_gate.py:174` and
  `config/reload.py:326` (cloned by D-09). HYG-02 must patch **both**; the clone is intentional
  and stays a clone.
- **`pyproject.toml` is touched by D-65** (`filterwarnings`) and by the human-gated close-out
  (version bump) — the bump is **not** this phase's to make.
- **Doc-drift correction spans `.planning/` only** — no source file carries the wrong path.

### The drift map (verified 2026-08-03) — 14 lines, 9 files

| File | Lines | Class |
|---|---|---|
| `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` | 213 | active drift — **origin** |
| `.planning/REQUIREMENTS.md` | 119 | active drift |
| `…/04-cleanup-readygate-fatal/04-01-PLAN.md` | 29, 249, 256, 257, 261 | archive drift |
| `…/04-CONTEXT.md` | 48, 181 | archive drift |
| `…/04-RESEARCH.md` | 15 | archive drift (**bare form**) |
| `…/04-01-SUMMARY.md` | 194 | archive drift |
| `…/04-02-SUMMARY.md` | 120 | archive drift |
| `…/04-VALIDATION.md` | 77 | archive drift (**bare form**) |
| `…/04-VERIFICATION.md` | 74 | archive drift |
| `.planning/REQUIREMENTS.md` | 217 | **intentional — exempt** |
| `.planning/v0.1.2-MILESTONE-AUDIT.md` | 21, 142 | **intentional — exempt** |

`04-CONTEXT.md:48` also uses the bare form. Reproduce with `grep -rnE "ops[/.]daemon" --include="*.md" .`

</code_context>

<specifics>
## Specific Ideas

- **"Don't conflate two causes behind one message"** emerged as the phase's connecting thread. It
  is literally DISC-07's requirement, and the user chose the same posture for HYG-03 (D-64) on that
  basis. The planner should treat it as the phase's stylistic through-line, not two coincidental
  fixes.
- **The user raised adopting pyright unprompted** when told the hub runs no type checker, then
  accepted deferring it once the first-run triage cost was laid out. That instinct is on record —
  the backlog entry should be written so it is easy to pick up, not buried.
- **"Make it structural"** was the explicit rationale for D-65 (`filterwarnings = ["error"]`): the
  user preferred an enforced invariant over a satisfied assertion. Applies to D-67's standing gate
  too — both chose the always-runs mechanism over the one-time check.
- **The archive is evidence, not clutter.** D-66 annotates rather than rewrites specifically to
  preserve `04-01-PLAN.md:257`, the `<automated>` check that passed by grepping the wrong string.

</specifics>

<deferred>
## Deferred Ideas

- **Adopt a static type checker (pyright) as a standing gate.** Raised by the user during SURF-02
  — correctly observing that an annotation nothing checks is a comment with extra syntax. Deferred
  out of Phase 7, not rejected.

  **Why deferred:** it is a toolchain change every future phase then pays, and the first run over
  this codebase will surface its own backlog — the injection architecture is deliberately
  `Any`-heavy at every seam (`scheduler: Any`, `trigger: Any`, `render_arg: Any`, the opaque
  `dispatch`/`render` closures). Probably near-clean in `basic` mode; a flood in `strict`, and
  triaging that flood is its own scoped work. Folding it in would turn "close 9 audit items" into
  "close 9 audit items **and** adopt static typing," and the debt phase — sequenced last precisely
  to absorb slip — would absorb that instead.

  **Sizing for whoever picks this up:** decide `basic` vs `strict`; decide baseline-and-burn-down
  vs fix-all-before-green; check `discord.py==2.7.1`'s stub quality (it is an exact pin, so its
  types are fixed); confirm the `Any`-at-seams sites are annotated as *intentional* rather than
  flagged. → **file to `.planning/backlog/`, target a future milestone.**

- **Decode CPython's bundled short-option group in the identity guard** (`python -Om<module>`).
  Considered and rejected for Phase 7 as D-61's rejected alternative — the whitelist approach is
  implementable, but the false-positive risk (SIGHUP to an unrelated PID) is the strictly worse
  direction and no consumer launches this way. Revisit only if a consumer actually needs that
  launch form.

</deferred>

---

*Phase: 7-v0.1.2 debt paydown*
*Context gathered: 2026-08-03*
