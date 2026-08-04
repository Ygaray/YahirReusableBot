# Phase 7: v0.1.2 debt paydown - Research

**Researched:** 2026-08-03
**Domain:** Internal Python library debt paydown (registry validation, Discord adapter exception
handling, structured logging, public-surface annotations, planning-doc drift correction) —
`yahir_reusable_bot`, the hub of a two-repo bot ecosystem
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Decision numbering continues the project-wide sequence. Phase 6 reached D-60, Phase 7 starts at
> D-61.

**Identity guard `-m` boundary (LIFE-05):**
- **D-61 (ratify the boundary, and make the limitation consumer-visible):** the bundled
  short-option group (`python -Om<module>` / `-Im<module>`) stays undecoded. No behavioral change
  to `_argv_matches_marker`. Three deliverables: (1) correct the stale requirement/audit text to
  name the bundled form, not the already-fixed attached form; (2) flip LIFE-05 to
  resolved-as-documented-limitation with reasoning recorded; (3) state the constraint in
  `EXTENSION-GUIDE.md` as a consumer-facing contract line.
- **D-61a (scope note):** LIFE-05 ships no source change to `identity.py`. Its RED-first
  obligation is satisfied by the already-passing pinned test
  `test_bundled_short_option_group_not_matched` (GREEN both pre- and post-fix). Do NOT manufacture
  an artificial RED test for a decision whose outcome is "no behavioral change." Record this
  exemption explicitly so the GATE-02 RED-first ancestry audit does not flag it as a gap.

**Public surface annotations (SURF-02):**
- **D-62 (narrow `on_online`, sweep the other two loose `Callable[...]`):**
  - `lifecycle/ready_gate.py:91` `on_online: Callable[..., None] | None` → narrow to
    `Callable[[HealthResult], None] | None`
  - `discord/panelkit.py:166` `render: Callable[..., discord.Embed]` → narrow arity to
    `Callable[[Any, Any], discord.Embed]`
  - `scheduler/engine.py:52` `callback: Callable[..., Any]` → leave variadic, record why
- **D-63 (enforcement is a signature-assertion test, not a type checker):** the hub runs no
  static type checker. SURF-02's RED-first regression test asserts the annotation directly via
  `typing.get_type_hints(...)`. Adopting pyright was raised by the user and explicitly deferred.

**Unawaited-coroutine warning (HYG-03):**
- **D-64 (fix production, split the log by cause):** restructure `BotThread.stop()`
  (`gateway.py:350-357`) so the coroutine is bound to a name, the schedule and the await are
  separate `try` blocks, and the orphan is reclaimed only on the scheduling-failure branch.
  Illustrative shape (not a literal patch — the planner owns the final form; invariants: `stop()`
  NEVER raises, and `self._thread.join(timeout=timeout)` is ALWAYS reached):
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
- **D-65 (zero-warnings becomes structural, not incidental):** add
  `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` in `pyproject.toml`. Planner
  obligation: verify the full suite stays green under the filter before committing it. Baseline at
  discuss time: `158 passed, 1 warning` (the 1 being HYG-03 itself). Future dependency
  deprecations get a targeted `ignore::` entry with a comment, never a filter removal.

**Doc drift (DOCS-02 / DOCS-03):**
- **D-66 (correct active artifacts, annotate archive):** correct in place
  `REQUIREMENTS.md:119` and `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:213`. Annotate
  (drift banner, do not rewrite) the 7 archived files under
  `.planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/`. Do NOT touch the 3 intentional
  mentions (`REQUIREMENTS.md:217`, `v0.1.2-MILESTONE-AUDIT.md:21` and `:142`).
- **D-67 (verification = always-runs in-suite gate + one-time recorded filesystem evidence):**
  (1) a standing test asserting the bare string `ops/daemon` appears in no active planning
  artifact, with an explicit commented exempt-list; (2) one-time filesystem verification (recorded
  in the phase SUMMARY, not a test) that all three de-hack paths resolve on disk in WeatherBot.
  No `skipif(weatherbot_missing)` — a check that silently doesn't run is the same failure class
  the audit warned about.
- **D-68 (DOCS-03 rides on the same correction, fixes the stale count):** the corrected
  enumeration names three de-hack sites: `weatherbot/scheduler/wiring.py` `_on_fail`,
  `weatherbot/scheduler/daemon.py` (the corrected path), and
  `weatherbot/ops/selfcheck.py` `to_health_result` (the PRODUCING site — without it classifying
  `CONFIG_INVALID` as fatal, the FATAL branch is unreachable downstream). Also correct the stale
  "11 artifacts" figure in `REQUIREMENTS.md:217` to the live count (9 files / 14 lines).

### Claude's Discretion

Fix directions are stated, not open — root causes are pinned to exact lines:

- **MATCH-03** — add `seen: set[str]` to the existing D-34 validation loop at
  `registry/registry.py:53`, raise `ValueError` naming the duplicate. Error type locked to
  `ValueError` by the ROADMAP. Consumer-breaking — the repin needs a WeatherBot sweep for
  duplicate `spec.name` values.
- **DISC-07** — insert `except discord.Forbidden` BEFORE `except discord.HTTPException` on the
  retry pin at `gateway.py:218`, mirroring the idiom the first `msg.pin()` already uses at
  `gateway.py:196-200`.
- **DISC-08** — stop calling `matches.pop(0)` before the eviction delete
  (`gateway.py:208`). Remove the stray from the cleanup list only on a successful delete, so a
  failed eviction is still retried by the loop at `gateway.py:237`.
- **HYG-02** — `_log.warning("hook failed; engine result unaffected", label=label)` replacing the
  f-string at `lifecycle/ready_gate.py:188` AND the verbatim clone at `config/reload.py:326` (D-09
  clone). One fix, two sites.

### Deferred Ideas (OUT OF SCOPE)

- **Adopt a static type checker (pyright) as a standing gate.** Raised by the user unprompted
  during SURF-02; deferred, not rejected. File to `.planning/backlog/` for a future milestone.
  Sizing: mode choice (`basic` vs `strict`), baseline-and-burn-down vs fix-all,
  `discord.py==2.7.1` stub quality (exact pin, so its types are fixed), and confirming the
  `Any`-at-seams sites are annotated as intentional.
- **Decode CPython's bundled short-option group** (`python -Om<module>`) in the identity guard.
  D-61's rejected alternative — the whitelist approach is implementable, but the false-positive
  risk (SIGHUP to an unrelated PID) is strictly worse. Revisit only if a consumer actually needs
  that launch form.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MATCH-03 | Duplicate `spec.name` rejected at registration with `ValueError` | Live source verified (`registry/registry.py:39-64`); existing D-34 loop + `tests/test_registry.py` convention documented below with exact insertion point |
| LIFE-05 | Identity guard `-m` boundary resolved as documented limitation | Live source + docstring verified (`identity.py:141-228`); D-61a's no-RED-test exemption grounded in the already-GREEN `tests/test_identity.py:165` |
| SURF-02 | `on_online` narrowed; `panelkit.render` narrowed; `engine.callback` left variadic, recorded | Live source verified at all three sites; `typing.get_type_hints` RED/GREEN behavior independently verified this session, including a load-bearing `localns` gotcha for `panelkit.py` |
| DISC-07 | Retry-pin log distinguishes `discord.Forbidden` from `discord.HTTPException` | Live source verified (`gateway.py:184-260`); `Forbidden`/`HTTPException` subclass relationship independently confirmed at runtime; existing fake-message test convention documented |
| DISC-08 | Failed eviction-delete does not drop the stray from cleanup | Live source verified (same site); exact pop/cleanup-loop interaction traced line-by-line |
| HYG-02 | `_best_effort_hook` logs via `label=` kwarg, both sites | Both call sites verified byte-identical (`ready_gate.py:188`, `config/reload.py:339`); `structlog.testing.capture_logs()` shape independently verified this session |
| HYG-03 | Zero warnings; unawaited-coroutine `RuntimeWarning` eliminated | Root cause verified in production code (`gateway.py:353`); baseline warning count reproduced (`158 passed, 1 warning`); a SECOND, distinct pytest warning pathway (`PytestUnraisableExceptionWarning`) discovered under `-W error` and documented as a Common Pitfall |
| DOCS-02 | Every active planning artifact naming a consumer de-hack site names a path that exists | Full 14-line/9-file drift map independently re-derived via `grep -rnE "ops[/.]daemon"`, matches CONTEXT.md's PC-D exactly; WeatherBot filesystem paths independently re-verified this session |
| DOCS-03 | Documented de-hack site set includes the producing site | `weatherbot/ops/selfcheck.py:149` `to_health_result` independently read and confirmed as the producing site (`fatal=result.reason == CONFIG_INVALID`) |
</phase_requirements>

## Summary

This is a debt-paydown phase against nine already-decided requirements (D-61 through D-68 locked
in `07-CONTEXT.md`). There is no new capability to design — the job is to ground every locked
decision in the exact current shape of the source so the planner can write concrete, line-numbered
tasks instead of hand-wavy ones. All nine sites were re-read directly from disk during this
research session (not inferred from any planning artifact), and every one matches the CONTEXT.md
description exactly — no fifth premise correction was found. Three genuinely new, independently
verified findings not already in CONTEXT.md are worth flagging to the planner up front:

1. **`typing.get_type_hints(PanelKit.__init__)` raises `NameError` unless called with
   `localns={"SelectedContext": SelectedContext}`** — `SelectedContext` is imported only under
   `TYPE_CHECKING` in `panelkit.py`, so the D-63 signature-assertion pattern that works cleanly
   for `ReadyGate.__init__` (`on_online`) needs this extra argument for `panelkit.render`'s
   RED-first test, or it fails for a reason unrelated to the annotation being tested.

2. **D-65's `filterwarnings = ["error"]` interacts with a second, distinct pytest warning
   pathway.** Running the suite today with the equivalent of the pytest.ini filter
   (`pytest -o filterwarnings=error`) does NOT surface the familiar `RuntimeWarning` from the
   default warnings summary — it fails via `PytestUnraisableExceptionWarning`, a separate pytest
   plugin (`unraisableexception`) that intercepts the interpreter's GC-time "Exception ignored in"
   report for the orphaned coroutine. Both pathways share the exact same root cause (the
   never-scheduled `coro` object), so D-64's production fix should eliminate both together — but
   the planner's GREEN verification for HYG-03/D-65 must confirm the suite is clean under the
   *actual* `-o filterwarnings=error` invocation, not just under the plain `pytest -q` default
   summary, because they are different capture mechanisms.

3. **No conftest.py fixture, and no existing test in this repo, exercises `structlog` output.**
   HYG-02 and DISC-07's RED-first tests are the first in this repo to assert on log content. This
   session independently confirmed `structlog.testing.capture_logs()` is available (structlog is
   already pinned ≥26.1.0, no new dependency) and returns
   `[{"label": ..., "event": ..., "log_level": ...}]` — the exact shape needed to assert the
   `label=` kwarg landed instead of an f-string.

**Primary recommendation:** ground every plan directly in the line numbers and code shown below
(all re-verified live during this session); use the D-34 validation-loop pattern in
`registry/registry.py` and the `tests/test_registry.py` self-proof-note convention as the template
for MATCH-03; use `structlog.testing.capture_logs()` for every new log-content assertion; and treat
D-65's filter-verification step as needing the `-o filterwarnings=error` (or real ini) invocation,
not the default `pytest -q` summary.

## Architectural Responsibility Map

This is a single-tier Python library (no browser/SSR/CDN split) — the "tiers" below are the hub's
own internal layer boundaries, which is the correct unit for sanity-checking task assignment in
this phase.

| Capability | Primary Layer | Secondary Layer | Rationale |
|------------|-------------|----------------|-----------|
| Duplicate command-name rejection (MATCH-03) | `registry/registry.py` (construction-time validation) | — | Registration-time invariant; must never leak into `match_command`'s hot path |
| `-m` argv identity matching (LIFE-05) | `lifecycle/identity.py` (`_argv_matches_marker`) | `EXTENSION-GUIDE.md` (consumer-facing doc) | Behavior stays in the lifecycle layer; the NEW deliverable is a documentation surface, not code |
| Callback annotation accuracy (SURF-02) | `lifecycle/ready_gate.py`, `discord/panelkit.py`, `scheduler/engine.py` (type signatures) | `tests/` (signature-assertion regression) | Pure signature-level change; zero runtime behavior change at any of the three sites |
| Discord exception discrimination (DISC-07) | `discord/gateway.py` (`summon_panel`, retry-pin `except` chain) | — | Exception-hierarchy correctness is entirely local to the adapter layer; no cross-layer effect |
| Cleanup-list integrity on failed delete (DISC-08) | `discord/gateway.py` (`summon_panel`, `matches` list bookkeeping) | — | Same function as DISC-07; ROADMAP mandates one plan |
| Structured-log kwarg discipline (HYG-02) | `lifecycle/ready_gate.py`, `config/reload.py` (`_best_effort_hook`, both clones) | — | A house-style violation duplicated at two sites by the D-09 clone; both must move together |
| Coroutine lifecycle correctness (HYG-03) | `discord/gateway.py` (`BotThread.stop`) | `pyproject.toml` (`[tool.pytest.ini_options]`, D-65) | Production fix in the adapter layer; the pytest-config change is a project-wide enforcement mechanism, not adapter-specific |
| Planning-doc path accuracy (DOCS-02/03) | `.planning/` (non-runtime; REQUIREMENTS.md, backlog, archive) | `tests/` (new standing doc-drift gate) | Entirely outside the runtime `yahir_reusable_bot/` package — no source file carries the wrong path (already confirmed in CONTEXT.md's Integration Points) |

## Package Legitimacy Audit

**No new packages.** This phase touches zero entries in `[project.dependencies]` or
`[dependency-groups].dev` in `pyproject.toml`. The only `pyproject.toml` edit is D-65's addition of
`filterwarnings = ["error"]` under the existing `[tool.pytest.ini_options]` table — a config key,
not a package. `structlog.testing.capture_logs()` (used for the new log-assertion tests) ships
inside the already-pinned `structlog>=26.1.0` dependency; `typing.get_type_hints` is stdlib. No
`package-legitimacy check` invocation is needed for this phase.

## Standard Stack

No new stack. Confirmed current pins (`pyproject.toml`, re-read live):

| Library | Pinned version | Role in this phase |
|---------|---------|---------------------|
| `discord.py` | `==2.7.1` (exact) | DISC-07/DISC-08 sites; `discord.Forbidden`/`discord.HTTPException` subclass relationship independently confirmed at runtime this session |
| `structlog` | `>=26.1.0` | HYG-02/HYG-03/DISC-07 log-content assertions via `structlog.testing.capture_logs()` (verified working, see Code Examples) |
| `pytest` | `>=9.0.3` | All new RED-first tests; `[tool.pytest.ini_options]` is the D-65 edit site |
| `grimp` | `>=3.14` | Unaffected by this phase's fixes; DOCS-02's new doc-drift gate is a plain `pytest` test, not a grimp graph gate |

Dev-only tooling (`ruff`, `syrupy`, `time-machine`) is untouched by this phase's scope.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────┐
                     │        Host composition root             │
                     │        (WeatherBot, out of scope)         │
                     └───────────────┬─────────────────────────┘
                                     │ injects callables
                                     ▼
   ┌──────────────┐   ┌────────────────────┐   ┌───────────────────────┐
   │ registry/     │   │ lifecycle/          │   │ discord/               │
   │ registry.py   │   │ ready_gate.py        │   │ gateway.py             │
   │               │   │ identity.py          │   │ panelkit.py            │
   │ MATCH-03:     │   │ SURF-02 (on_online): │   │ DISC-07/DISC-08:       │
   │ construction- │   │ signature narrows    │   │ summon_panel retry-pin │
   │ time ValueError│  │ HYG-02: label= kwarg │   │ + eviction cleanup     │
   │ guard          │   │ LIFE-05: doc-only    │   │ HYG-03: BotThread.stop │
   └──────┬────────┘   └──────────┬──────────┘   │ coroutine lifecycle    │
          │                        │              │ SURF-02 (render):      │
          │  by_name / by_keyword  │  on_online/  │ signature narrows      │
          │  _len_desc views       │  on_fail     └───────────┬────────────┘
          ▼                        ▼                          ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │              config/reload.py — HYG-02's second clone site         │
   │              (_best_effort_hook, verbatim D-09 duplicate)          │
   └──────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │  scheduler/engine.py — SURF-02 (callback): recorded leave-as-is    │
   └──────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │  .planning/ (non-runtime) — DOCS-02/DOCS-03                        │
   │  REQUIREMENTS.md, HUB-HARDENING-REPORT-v0.1.2.md (active, corrected)│
   │  milestones/v0.1.2-phases/04-*/  (archive, annotated not rewritten) │
   │  NEW: tests/test_doc_drift.py — standing grep gate over .planning/  │
   └──────────────────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────────────────┐
   │  WeatherBot (sibling repo, read-only reference for DOCS-02/03)     │
   │  scheduler/wiring.py:442 _on_online  |  scheduler/daemon.py        │
   │  ops/selfcheck.py:149 to_health_result (the PRODUCING site)        │
   └──────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

No new files/directories in `yahir_reusable_bot/`. One new test file is warranted:

```
tests/
├── test_registry.py        # MATCH-03: extend with a duplicate-name test class
├── test_gateway.py          # DISC-07/DISC-08/HYG-03: extend existing summon_panel /
│                             #   BotThread.stop test groups
├── test_ready_gate.py        # SURF-02 (on_online): extend with a get_type_hints assertion
├── test_panelkit.py          # SURF-02 (render): extend with a get_type_hints assertion
│                             #   (needs the localns={"SelectedContext": ...} workaround)
├── test_reload.py            # HYG-02: extend with a capture_logs assertion for the
│                             #   config/reload.py clone site
└── test_doc_drift.py         # NEW — DOCS-02's standing gate over .planning/*.md
```

### Pattern 1: Construction-time uniqueness guard (MATCH-03's template)

**What:** `registry/registry.py:39-64`'s existing D-34 loop already validates `spec.name` for
non-empty + already-casefolded, raising `ValueError` naming the offending value, INSIDE the same
pass that builds `self.commands`, BEFORE any derived view (`by_name`, `by_keyword_len_desc`) is
computed.

**When to use:** MATCH-03 drops a `seen: set[str]` into this exact loop.

**Example (current live source, `registry/registry.py:39-64`):**
```python
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    for spec in self.commands:
        if not spec.name or spec.name != spec.name.casefold():
            raise ValueError(
                f"CommandSpec.name must be non-empty and already casefolded "
                f"(match_command folds input, never spec.name); got {spec.name!r}"
            )
    # MATCH-03 lands here: a `seen: set[str]` check inside this same loop, raising
    # ValueError naming the duplicate, BEFORE `by_name` is derived below.
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    self.by_keyword_len_desc: tuple[CommandSpec, ...] = tuple(
        sorted(self.commands, key=lambda c: len(c.name), reverse=True)
    )
```

The existing `tests/test_registry.py` establishes the exact test convention to extend: a
`_spec(name)` factory helper, a "self-proof note" docstring explaining why a naive
"still constructs" assertion is NOT RED-proving, `pytest.raises(ValueError, match=...)` asserting
the message names the offending value, and a `test_valid_*_still_construct_without_regression`
guard. MATCH-03's new tests belong in this same file, following this same shape (two specs sharing
a `name`, asserting `pytest.raises(ValueError, match="duplicate-name-value")`).

### Pattern 2: Exception-hierarchy discrimination (DISC-07's template)

**What:** The FIRST `msg.pin()` in `summon_panel` (`gateway.py:194-200`) already distinguishes
`discord.Forbidden` (re-raise to the outer TOCTOU backstop) from a broader `discord.HTTPException`
handler that runs after it. The RETRY pin at `gateway.py:216-222` does NOT yet apply this same
split — its `except discord.HTTPException` at line 218 is reached BEFORE any `Forbidden`-specific
branch, and since `discord.Forbidden` IS a subclass of `discord.HTTPException` (independently
confirmed at runtime this session: `issubclass(discord.Forbidden, discord.HTTPException) == True`),
a revoked permission on retry is caught by the generic branch and logged as
`"panel pin failed at cap even after evicting a stray"` — indistinguishable from a genuine
pin-cap failure.

**When to use:** DISC-07 inserts `except discord.Forbidden:` immediately before the existing
`except discord.HTTPException:` at line 218, mirroring lines 196-200's idiom.

**Example (current live source, `gateway.py:194-222`, annotated):**
```python
try:
    await msg.pin()
except discord.Forbidden:
    # Already correct — re-raises to the outer TOCTOU backstop.
    raise
except discord.HTTPException:
    # Pin-cap headroom-reserve (D-26) ...
    if len(matches) >= 1:
        stray = matches.pop(0)          # <- DISC-08 site: pop happens BEFORE delete succeeds
        try:
            await stray.delete()
        except (discord.NotFound, discord.HTTPException, discord.Forbidden):
            _log.warning("stray panel delete failed; continuing", ...)
        try:
            await msg.pin()
        except discord.HTTPException:    # <- DISC-07 site: Forbidden is swallowed here too;
                                          #    needs its own `except discord.Forbidden:` branch
                                          #    BEFORE this one, logging a distinct message.
            _log.critical("panel pin failed at cap even after evicting a stray", ...)
    else:
        ...
```

### Pattern 3: Cleanup-list bookkeeping tied to operation success (DISC-08's template)

**What:** `matches.pop(0)` at `gateway.py:208` removes the stray from `matches` UNCONDITIONALLY,
before its `delete()` is even attempted. If that `delete()` then fails (caught at
`gateway.py:210-215`), the stray is already gone from `matches` and is never retried by the
cleanup loop `for old in matches:` at `gateway.py:237-244`. DISC-08's fix: only remove the stray
from `matches` on a SUCCESSFUL delete, so a failed eviction delete is retried by the loop at line
237 exactly like any other stray.

**Example (current live source, `gateway.py:207-215`):**
```python
if len(matches) >= 1:
    stray = matches.pop(0)          # unconditional pop — DISC-08's bug
    try:
        await stray.delete()
    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
        _log.warning("stray panel delete failed; continuing", ...)
        # stray is gone from `matches` here even though delete() failed — it will
        # NOT be retried by the `for old in matches:` loop below (line 237).
```

**Fix shape (illustrative — planner owns the exact form):** peek `matches[0]` instead of popping;
`await stray.delete()`; only call `matches.pop(0)` (or equivalent removal) INSIDE the `try` block's
success path, after `delete()` returns without raising.

### Pattern 4: Signature-assertion regression tests (SURF-02's D-63 template)

**What:** No static type checker runs in this repo, so SURF-02's RED-first test asserts the
annotation directly via `typing.get_type_hints`. Independently verified this session:

```python
# ReadyGate.on_online — works cleanly, no gotcha (HealthResult and Callable are both
# imported at module scope in ready_gate.py, not TYPE_CHECKING-guarded):
import typing
from typing import Callable
from yahir_reusable_bot.lifecycle.ready_gate import ReadyGate
from yahir_reusable_bot.lifecycle.health import HealthResult

hints = typing.get_type_hints(ReadyGate.__init__)
# PRE-fix: hints["on_online"] == typing.Optional[typing.Callable[..., NoneType]]
# POST-fix (after narrowing to Callable[[HealthResult], None] | None):
assert hints["on_online"] == Callable[[HealthResult], None] | None   # True, verified
```

**Pitfall discovered — `panelkit.py`'s `render` needs `localns`:**
```python
# This RAISES NameError: name 'SelectedContext' is not defined — because
# `from yahir_reusable_bot.discord.selection import SelectedContext` in panelkit.py
# is guarded by `if TYPE_CHECKING:` (panelkit.py:50-51), so the name does not exist
# in the module's runtime globals that get_type_hints evaluates the (stringified,
# `from __future__ import annotations`) annotations against.
hints = typing.get_type_hints(PanelKit.__init__)   # NameError

# The fix — pass the missing name explicitly via localns:
from yahir_reusable_bot.discord.selection import SelectedContext
hints = typing.get_type_hints(
    PanelKit.__init__, localns={"SelectedContext": SelectedContext}
)
# hints["render"] == typing.Callable[..., discord.embeds.Embed]  (pre-fix, verified)
```

### Anti-Patterns to Avoid

- **Fixing the test double instead of production (HYG-03):** `_FakeCloseableClient.close`
  is synchronous-shaped only in that it returns a coroutine when called — making it
  `def close(self): pass` (non-async) would silence the warning but mask the live
  production TOCTOU orphan at `gateway.py:353`. Rejected explicitly in CONTEXT.md (D-64's
  rejected alternative) — do not resurrect it.
- **Fully decoding CPython's short-option-bundling grammar (LIFE-05):** rejected in D-61 as
  strictly worse (false positives, SIGHUP to a wrong PID) than the current documented limitation.
  Do not "improve" `_argv_matches_marker` beyond the attached-form fix already shipped.
- **Casefolding `spec.name` at match time instead of rejecting at registration (MATCH-03):**
  the D-34 loop's own docstring (`registry.py:46-51`) already rejected this as a tolerant
  fallback that hides a wiring bug and pays a per-match cost. MATCH-03's uniqueness check follows
  the same posture — raise once, at construction.
- **Rewriting the archived `04-*` files instead of annotating them (DOCS-02):** `04-01-PLAN.md:257`
  is the primary evidence for the audit's own headline lesson (a `<automated>` check that passed
  by grepping the wrong string). Rewriting it destroys that evidence — D-66 requires a drift
  banner, not a rewrite.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Asserting structured-log kwargs in a test | A custom logging handler / manual `sys.stdout` capture | `structlog.testing.capture_logs()` | Already available in the pinned `structlog>=26.1.0`; verified this session to return a plain list of dicts (`{"label": ..., "event": ..., "log_level": ...}`) with zero setup — no fixture, no monkeypatch needed |
| Verifying a narrowed annotation without a type checker | A hand-rolled `inspect.signature` string-diff | `typing.get_type_hints(cls.__init__, localns=...)` | Handles `from __future__ import annotations` string-deferral, `X \| None` normalization, and forward-ref resolution correctly — a manual string comparison would be fragile against those three concerns |
| A standing check that a planning doc doesn't drift again | A one-off shell script run manually before each release | A `pytest` test under `tests/` (DOCS-02's new gate) | The repo's existing convention (`test_import_hygiene.py`) is exactly this shape — a standing, always-runs pytest gate with an explicit exempt-list, not a script someone has to remember to run |

**Key insight:** every "don't hand-roll" item above is really "the repo already has (or the pinned
dependency already ships) the exact primitive this fix needs — use it, don't reinvent it inside
the fix itself."

## Common Pitfalls

### Pitfall 1: `filterwarnings = ["error"]` (D-65) catches a DIFFERENT pytest warning class than the one visible today

**What goes wrong:** Running `uv run pytest -q` today shows the HYG-03 defect as a plain
`RuntimeWarning` in pytest's default warnings summary (`158 passed, 1 warning`). But running the
equivalent of D-65's ini-option filter (`uv run pytest -q -o 'filterwarnings=error'`) does NOT
fail via that same `RuntimeWarning` — it fails via
`pytest.PytestUnraisableExceptionWarning: Exception ignored in: <coroutine ... close at ...>`,
raised by pytest's separate `unraisableexception` plugin, which intercepts the interpreter's
garbage-collection-time "Exception ignored in" report for the orphaned coroutine object.

**Why it happens:** These are two different pytest warning-capture pathways watching the same
underlying defect (a coroutine object created and never awaited, then garbage collected). The
default `-ra` summary mode surfaces the `RuntimeWarning` your Python interpreter's own
`asyncio` machinery emits. Under `-W error`/`filterwarnings=error`, pytest's unraisable-exception
plugin ALSO turns the GC-time report into a test failure, and it does so with a distinct warning
class and message shape.

**How to avoid:** After D-64's production fix lands (the coroutine is explicitly `.close()`d on
the scheduling-failure branch, so it is never left to be garbage-collected unawaited), BOTH
pathways should go quiet together, since they share the same root cause. The planner's
verification step for D-65 must run the suite with the actual filter active
(`uv run pytest -q -o 'filterwarnings=error'`, or the real `pyproject.toml` edit in place) — not
just eyeball the default `pytest -q` summary — because a fix that only silences the
`RuntimeWarning` path (e.g., by suppressing the warning some other way) would NOT necessarily
silence the `PytestUnraisableExceptionWarning` path, and the two must both be clean before D-65's
filter is safe to commit.

**Warning signs:** if `uv run pytest -q -o 'filterwarnings=error'` still fails after the HYG-03
production fix lands, re-check that `coro.close()` genuinely runs on every path where the
coroutine is constructed but never scheduled — a partial fix (e.g., only closing on one of several
possible exception types from `run_coroutine_threadsafe`) would leave this second pathway red.

### Pitfall 2: `get_type_hints` on `PanelKit.__init__` fails for an unrelated reason without `localns`

**What goes wrong:** A RED-first test written as
`typing.get_type_hints(PanelKit.__init__)` raises `NameError: name 'SelectedContext' is not
defined` — a failure that looks like it's testing something (RED!) but is actually failing on
setup, before it ever reaches the assertion about `render`'s annotation. A planner who doesn't
know this will either write a broken test or waste time debugging what looks like a real defect.

**Why it happens:** `panelkit.py` imports `SelectedContext` only under `if TYPE_CHECKING:`
(module lines 50-51) to avoid a real runtime import (it's used purely for annotations). With
`from __future__ import annotations` active (module line 41), the `selection: "SelectedContext"`
parameter annotation is a deferred string that `get_type_hints` must `eval()` against the module's
runtime globals — where `SelectedContext` does not exist.

**How to avoid:** always pass
`localns={"SelectedContext": SelectedContext}` (importing `SelectedContext` directly in the test
file, which is safe outside `TYPE_CHECKING`) when calling `get_type_hints` on anything from
`panelkit.py`. Verified working this session.

**Warning signs:** a `NameError` mentioning a name that is never directly referenced in your
test's own assertion is the tell — check the target class's other annotations for a
`TYPE_CHECKING`-guarded import before assuming the annotation itself is broken.

### Pitfall 3: The retry-pin `except` order matters, and `Forbidden` being a subclass of `HTTPException` is easy to get backwards

**What goes wrong:** Python evaluates `except` clauses in order and stops at the first match.
Placing `except discord.Forbidden:` AFTER `except discord.HTTPException:` (instead of before) is a
silent no-op fix — `Forbidden` is a subclass of `HTTPException`
(`discord.Forbidden.__mro__` includes `discord.HTTPException`, independently confirmed this
session), so the broader clause always wins and the more specific one is unreachable dead code.

**Why it happens:** it's the opposite ordering rule from what many exception hierarchies expect
intuitively — but Python's `try/except` is strictly first-match, not most-specific-match, so
ordering is load-bearing, not cosmetic.

**How to avoid:** mirror the ORDER already used at `gateway.py:194-200` for the first `msg.pin()`
call exactly — `Forbidden` before `HTTPException`, every time this pattern is repeated.

**Warning signs:** a new test asserting the `Forbidden`-specific log message never fires (silently
falls into the generic-cap message instead) even though the `except Forbidden:` branch was added —
check clause order first.

## Code Examples

### `structlog.testing.capture_logs()` — verified working, exact output shape

```python
# Source: structlog (pinned >=26.1.0), stdlib-adjacent testing helper — independently
# executed this session, output shape confirmed exactly as shown:
import structlog
from structlog.testing import capture_logs

log = structlog.get_logger("test")

with capture_logs() as cap:
    log.warning("hook failed; engine result unaffected", label="on_online")

# cap == [{"label": "on_online", "event": "hook failed; engine result unaffected",
#          "log_level": "warning"}]
```

Use this directly for HYG-02 (assert `cap[0]["label"] == "on_online"` / `"on_fail"` /
`"reload-rejected"` / `"reconcile-rolled-back"` / `"reload-applied"` and that no f-string-baked
label appears in `cap[0]["event"]`), and for DISC-07 (assert the retry-pin `Forbidden` case
produces a DIFFERENT `event` string than the generic-cap `HTTPException` case, using the same
`_FakeAtCapMessage`-style double already established in `tests/test_gateway.py`).

### `discord.Forbidden` subclass relationship — verified at runtime

```python
# Independently executed this session against the pinned discord.py==2.7.1:
import discord
issubclass(discord.Forbidden, discord.HTTPException)   # True
issubclass(discord.NotFound, discord.HTTPException)    # True
discord.Forbidden.__mro__
# (<class 'discord.errors.Forbidden'>, <class 'discord.errors.HTTPException'>,
#  <class 'discord.errors.DiscordException'>, <class 'Exception'>,
#  <class 'BaseException'>, <class 'object'>)
```

Confirms PC-C exactly: DISC-07 is an ordering/branch-visibility fix, not a missing branch.

## State of the Art

Not applicable in the usual "ecosystem moved on" sense — this is an internal-only cleanup phase
with no external framework version churn to track. One dated fact worth restating from the live
docstring (`gateway.py:50-51`, already correct in current source, not a finding — noted only so
the planner doesn't second-guess it): Discord split `PIN_MESSAGES` out of `MANAGE_MESSAGES`
(effective 2026-01-12), and `discord.py` 2.7 exposes the new bit as `Permissions.pin_messages`;
`REQUIRED_PANEL_PERMS` already checks the correct, current permission name. No action needed —
included here only to confirm this phase's DISC-07/DISC-08 work sits on already-current permission
handling.

## Assumptions Log

Every claim in this document was verified directly against live source, live runtime behavior, or
independent filesystem/grep checks performed during this research session — none rely on training
data alone.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

**This table is empty.** All claims in this research were verified this session (source reads,
`uv run python -c ...` runtime checks, `grep`/`find` filesystem checks, and one live
`uv run pytest` execution) — no user confirmation needed beyond the decisions already locked in
`07-CONTEXT.md`.

## Open Questions

1. **Exact wording of DISC-07's new log message and HYG-03's two split messages.**
   - What we know: CONTEXT.md explicitly marks the HYG-03 code shape as "illustrative, not a
     literal patch — the planner owns the final form," and DISC-07 has no prescribed string either
     (Claude's Discretion section only pins the `except` clause placement and the mirrored idiom).
   - What's unclear: the exact `event=` string text.
   - Recommendation: follow the existing house style at the mirrored site
     (`gateway.py:219-222`'s `"panel pin failed at cap even after evicting a stray"` for the
     cap-fail case) — a short, `snake_case`-free, human-readable sentence, structured fields via
     kwargs (`channel_id=...`), never an f-string. This is a plan-time wording choice, not a
     research gap.

2. **Whether DOCS-03's corrected three-site enumeration needs its own standing test, or rides
   entirely on DOCS-02's `ops/daemon` gate.**
   - What we know: D-67's gate asserts a STRING (`ops/daemon`) is absent from active artifacts —
     it does not assert that a CORRECT enumeration is present (i.e., it can't verify
     `weatherbot/ops/selfcheck.py` is actually mentioned anywhere).
   - What's unclear: whether the planner should add a second, positive assertion (e.g., "the
     corrected `REQUIREMENTS.md` block mentions all three sites") or treat DOCS-03 as satisfied by
     the one-time filesystem-verification record in the phase SUMMARY (D-67's second mechanism)
     plus a manual read of the corrected text.
   - Recommendation: treat DOCS-03 as primarily manual-only (see Validation Architecture below) —
     a positive-content grep test is easy to write but low-value (it would need updating every
     time the enumeration's prose changes, exactly the kind of over-fitted check the audit warned
     about). Record the three-site correctness in the phase SUMMARY instead, consistent with D-67's
     own "evidence, not test" treatment of the filesystem-existence half.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | test/lint runner | ✓ | (repo-pinned via `uv.lock`) | — |
| `pytest` | all new RED-first tests | ✓ (`158 passed, 1 warning` baseline reproduced live this session) | `>=9.0.3` per `pyproject.toml` | — |
| WeatherBot sibling repo (`/home/yahir/Projects/WeatherBot`) | DOCS-02/DOCS-03 filesystem verification | ✓ (reachable on disk, read-only reference) | — | If unreachable on a future machine: this is exactly why D-67 splits into a standing in-suite gate (no dependency) + one-time recorded evidence (dependency, but only needed once, at authoring time) |
| `structlog.testing` | HYG-02/DISC-07 new log-content tests | ✓ (ships inside pinned `structlog>=26.1.0`, `capture_logs` verified callable this session) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none — WeatherBot's read-only reachability is already
handled by D-67's two-mechanism split, not by this phase needing a runtime fallback.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest >=9.0.3` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (D-65 adds `filterwarnings = ["error"]` here) |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest -q` (the whole suite runs in ~2s; there is no separate "quick" subset in this repo) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MATCH-03 | Duplicate `spec.name` raises `ValueError` at construction | unit | `uv run pytest tests/test_registry.py -k duplicate -x` | ✅ `tests/test_registry.py` exists — extend it |
| LIFE-05 | Bundled `-Om<module>` stays undecoded (no behavior change); `EXTENSION-GUIDE.md` states the constraint | manual-only for the doc; the behavior itself is already GREEN | Doc: manual read of `EXTENSION-GUIDE.md` §4; behavior: `uv run pytest tests/test_identity.py -k bundled_short_option -x` (already-passing pinned test, D-61a) | ✅ both — no new test file |
| SURF-02 (`on_online`) | `ReadyGate.__init__`'s `on_online` annotation narrows | unit | `uv run pytest tests/test_ready_gate.py -k on_online_annotation -x` | ✅ `tests/test_ready_gate.py` exists — extend it |
| SURF-02 (`render`) | `PanelKit.__init__`'s `render` annotation narrows arity | unit | `uv run pytest tests/test_panelkit.py -k render_annotation -x` | ✅ `tests/test_panelkit.py` exists — extend it (needs the `localns` workaround, Pitfall 2) |
| SURF-02 (`callback`) | `SchedulerEngine.register`'s `callback` stays variadic, rationale recorded | manual-only | Manual read of `scheduler/engine.py`'s docstring/comment recording the decision | N/A — no test; a recorded non-issue |
| DISC-07 | Retry-pin `Forbidden` logged distinctly from `HTTPException` | unit | `uv run pytest tests/test_gateway.py -k retry_pin_forbidden -x` | ✅ `tests/test_gateway.py` exists — extend it |
| DISC-08 | Failed eviction-delete stray stays in cleanup, retried | unit | `uv run pytest tests/test_gateway.py -k eviction_delete_failure -x` | ✅ `tests/test_gateway.py` exists — extend it |
| HYG-02 | `label=` kwarg at both `_best_effort_hook` sites | unit | `uv run pytest tests/test_ready_gate.py tests/test_reload.py -k label_kwarg -x` | ✅ both files exist — extend them |
| HYG-03 | Production coroutine leak fixed; zero warnings | unit + suite-level | `uv run pytest tests/test_gateway.py -k stop_does_not_raise -x` then `uv run pytest -q -o 'filterwarnings=error'` (full suite, see Pitfall 1) | ✅ `tests/test_gateway.py` exists — extend it |
| DOCS-02 | No active planning artifact carries the bare `ops/daemon` string outside the exempt-list | unit (new standing gate) | `uv run pytest tests/test_doc_drift.py -x` | ❌ Wave 0 — new file |
| DOCS-03 | Corrected enumeration names all three de-hack sites, including the producing site | manual-only | Manual read of the corrected `REQUIREMENTS.md`/`HUB-HARDENING-REPORT-v0.1.2.md` text against the phase SUMMARY's filesystem-verification record | N/A — see Open Question 2 |
| GATE-02 | Full suite + import-hygiene gates green; every requirement has a RED-first test (except LIFE-05, exempted) | suite-level | `uv run pytest -q` (all pass, zero warnings) + `uv run pytest tests/test_import_hygiene.py -q` | ✅ both exist |

### Sampling Rate

- **Per task commit:** the specific `-k`-filtered command from the table above.
- **Per wave merge / plan commit:** `uv run pytest -q` (whole suite, ~2s — no reason to sample less
  than the full run in this repo).
- **Phase gate:** `uv run pytest -q -o 'filterwarnings=error'` (or the real `pyproject.toml` D-65
  edit in place) MUST be green — this is the actual enforcement mechanism HYG-03/D-65 exists to
  prove, and per Pitfall 1 it is not equivalent to eyeballing the default summary.

### Wave 0 Gaps

- [ ] `tests/test_doc_drift.py` — new file, covers DOCS-02's standing gate. Suggested shape:
  walk `.planning/**/*.md` (via `Path(__file__).resolve().parent.parent / ".planning"`, mirroring
  `test_import_hygiene.py`'s `_MODULE_ROOT` convention at line 64), search each file for the bare
  regex `ops[/.]daemon` (the pattern must be bare, not `weatherbot/ops/daemon` — PC-D's own
  lesson), and assert every match falls inside an explicit, commented exempt-list of
  `(relative_path, line_number)` tuples covering the 3 intentional mentions
  (`REQUIREMENTS.md:217`, `v0.1.2-MILESTONE-AUDIT.md:21`, `v0.1.2-MILESTONE-AUDIT.md:142`) and the
  7 annotated-archive files. A self-proof half (a synthetic string injected into a temp file,
  proving the scan logic itself catches an unexempted match) would match this repo's established
  `test_import_hygiene.py` convention of "every gate has a self-proof."
- [ ] No other test-infrastructure gaps — every other requirement extends an existing test file
  using an already-established convention (plain-construction doubles, no mocking library, `_spec`
  /`_Fake*` factory helpers).

*(Framework install: none needed — `pytest` and `structlog` are already pinned and installed.)*

## Security Domain

Not applicable in the ASVS sense — this phase touches no authentication, session, or input-surface
boundary from an external network caller. The closest analog, DISC-07/DISC-08's Discord permission
handling, is already covered by the existing `REQUIRED_PANEL_PERMS` preflight and the TOCTOU
backstop (`gateway.py:252-260`) — this phase corrects LOGGING/CLEANUP accuracy around that
existing boundary, it does not change the trust boundary itself. MATCH-03's `ValueError` guard is
a construction-time consumer-input validation (matching the existing D-34/D-41 precedent, both of
which the CONTEXT.md decisions explicitly cite as the reasoning template) — not a new external
attack surface.

## Sources

### Primary (HIGH confidence — live source reads, this session)
- `yahir_reusable_bot/registry/registry.py` (full file) — MATCH-03 site
- `yahir_reusable_bot/lifecycle/identity.py` (full file) — LIFE-05 site + docstring reasoning
- `yahir_reusable_bot/discord/gateway.py` (full file) — DISC-07/DISC-08/HYG-03 sites
- `yahir_reusable_bot/lifecycle/ready_gate.py` (full file) — SURF-02 (`on_online`) + HYG-02 site
- `yahir_reusable_bot/config/reload.py` (full file) — HYG-02 clone site
- `yahir_reusable_bot/discord/panelkit.py` (full file) — SURF-02 (`render`) site
- `yahir_reusable_bot/scheduler/engine.py` (full file) — SURF-02 (`callback`) site
- `pyproject.toml` (full file) — dependency pins, `[tool.pytest.ini_options]` current state
- `tests/test_gateway.py`, `tests/conftest.py`, `tests/test_identity.py`, `tests/test_ready_gate.py`,
  `tests/test_registry.py`, `tests/test_import_hygiene.py` — existing test conventions
- `/home/yahir/Projects/WeatherBot/weatherbot/scheduler/wiring.py`,
  `weatherbot/scheduler/daemon.py`, `weatherbot/ops/selfcheck.py` — DOCS-02/03 cross-repo
  verification (read-only)
- `EXTENSION-GUIDE.md` (Plug-Point Summary + §4 Health-check) — D-61's doc-insertion target
  location confirmed

### Verified via direct execution (HIGH confidence, this session)
- `uv run pytest -q` → `158 passed, 1 warning` (baseline reproduced exactly as CONTEXT.md states)
- `uv run pytest -q -o 'filterwarnings=error'` → surfaces `PytestUnraisableExceptionWarning`, a
  distinct pathway from the default summary's `RuntimeWarning` (Pitfall 1, new finding)
- `discord.Forbidden.__mro__` / `issubclass(discord.Forbidden, discord.HTTPException)` → `True`
  (confirms PC-C independently)
- `typing.get_type_hints(ReadyGate.__init__)` and `typing.get_type_hints(PanelKit.__init__)` →
  the `localns` gotcha (Pitfall 2, new finding) and the correct pre/post-fix `on_online` hint shape
- `structlog.testing.capture_logs()` → exact output shape confirmed
- `grep -rnE "ops[/.]daemon" --include="*.md" .` → independently reproduces CONTEXT.md's 9-file/
  14-line drift map exactly (no discrepancy found)
- `test -f weatherbot/ops/daemon.py` (absent) / `weatherbot/scheduler/daemon.py` (present) /
  `weatherbot/ops/selfcheck.py` (present) → independently reconfirms D-67's filesystem evidence

### Secondary / Tertiary
None used — this phase's research does not draw on external web sources per the task's explicit
instruction (well-understood internal codebase cleanup); every claim above traces to a live file
read, a live command execution, or the locked `07-CONTEXT.md`/`07-DISCUSSION-LOG.md` decision
record.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all pins re-read live from `pyproject.toml`
- Architecture: HIGH — every site's current code was read in full this session, not inferred
- Pitfalls: HIGH — all three flagged pitfalls were reproduced via direct command execution, not
  hypothesized

**Research date:** 2026-08-03
**Valid until:** effectively indefinite for the source-shape claims (this is a point-in-time
snapshot of `main` at a clean working tree — re-verify only if `main` moves before planning
completes). 7 days for the `structlog`/`pytest` version-availability claims, consistent with this
repo's fast-moving dev-dependency posture.
