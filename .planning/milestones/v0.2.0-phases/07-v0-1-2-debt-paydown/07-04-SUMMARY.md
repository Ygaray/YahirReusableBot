---
phase: 07-v0-1-2-debt-paydown
plan: 04
subsystem: testing
tags: [typing, get_type_hints, discord.py, apscheduler, signature-assertion]

# Dependency graph
requires:
  - phase: 07-03
    provides: "filterwarnings=error active in [tool.pytest.ini_options], 171 passed / zero warnings baseline"
provides:
  - "on_online narrowed to Callable[[HealthResult], None] | None in ready_gate.py, matching on_fail's sibling shape"
  - "render arity-narrowed to Callable[[Any, Any], discord.Embed] in panelkit.py"
  - "SchedulerEngine.register's callback left Callable[..., Any] with the D-62 leave-variadic rationale recorded in its docstring"
  - "Two get_type_hints signature-assertion regression tests that fail if either narrowed annotation is widened back"
affects: [surface-audit, weatherbot-repin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "typing.get_type_hints signature-assertion tests as the enforcement mechanism in a repo with no static type checker (D-63)"
    - "localns={'SelectedContext': SelectedContext} workaround for get_type_hints on a TYPE_CHECKING-only-imported annotation under from __future__ import annotations (RESEARCH.md Pitfall 2)"

key-files:
  created: []
  modified:
    - yahir_reusable_bot/lifecycle/ready_gate.py
    - yahir_reusable_bot/discord/panelkit.py
    - yahir_reusable_bot/scheduler/engine.py
    - tests/test_ready_gate.py
    - tests/test_panelkit.py

key-decisions:
  - "D-62 (three-part SURF-02 verdict): on_online narrowed, render arity-narrowed, callback deliberately left variadic with rationale recorded — all three sites now decided, none left as an unexamined gap"
  - "D-63 reaffirmed: get_type_hints assertions ARE the enforcement mechanism in this repo (no pyright/mypy); adopting a static type checker stays deferred to backlog, not introduced here"

patterns-established:
  - "SURF-02 signature-assertion regression test template (Pattern 4 in 07-RESEARCH.md) — reusable for any future annotation-narrowing plan in this repo"

requirements-completed: [SURF-02]

coverage:
  - id: D1
    description: "on_online annotation narrowed from Callable[..., None] | None to Callable[[HealthResult], None] | None, matching on_fail's sibling shape"
    requirement: "SURF-02"
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_on_online_annotation_is_narrowed_to_health_result"
        status: pass
      - kind: unit
        ref: "tests/test_ready_gate.py#test_on_fail_annotation_is_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "PanelKit.render annotation arity-narrowed to Callable[[Any, Any], discord.Embed]"
    requirement: "SURF-02"
    verification:
      - kind: unit
        ref: "tests/test_panelkit.py#test_render_annotation_is_arity_narrowed_to_two_positional_args"
        status: pass
    human_judgment: false
  - id: D3
    description: "SchedulerEngine.register's callback deliberately left Callable[..., Any], with the D-62 leave-variadic rationale recorded in the method's docstring (no test — recorded non-issue, manual-only by design per 07-VALIDATION.md)"
    requirement: "SURF-02"
    verification: []
    human_judgment: true
    rationale: "This is a documentation-only verdict with zero runtime behavior delta by design (the plan explicitly instructs no test for this site) — confirming the rationale paragraph reads correctly and matches the file's existing prose style needs a human read, not an automated check."

duration: ~5min
completed: 2026-08-04
status: complete
---

# Phase 7 Plan 4: SURF-02 Loose-Callable Cleanup Summary

**Narrowed `on_online` and `panelkit.render` annotations to their real call-site arity, and recorded the deliberate leave-variadic verdict for `SchedulerEngine.register`'s `callback` — closing SURF-02's all-three-sites decision (D-62).**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-08-03T23:12Z (commit-timestamp-derived)
- **Completed:** 2026-08-04T05:15Z
- **Tasks:** 2 completed
- **Files modified:** 5 (3 source, 2 test)

## Accomplishments

- `ready_gate.py`'s `on_online` annotation narrowed from `Callable[..., None] | None` to `Callable[[HealthResult], None] | None` — now byte-identical in shape to its sibling `on_fail`, which was already correct.
- `panelkit.py`'s `render` annotation arity-narrowed from `Callable[..., discord.Embed]` to `Callable[[Any, Any], discord.Embed]`, matching the module's always-two-positional-arg `render(reply, render_arg)` call site.
- `scheduler/engine.py`'s `register` left with `callback: Callable[..., Any]` unchanged — a deliberate D-62 verdict, not an oversight, with the rationale (opaque args/kwargs forwarded straight through to `add_job`, host-agnostic seam) recorded as a new paragraph in the method's existing docstring.
- Two new `get_type_hints`-based signature-assertion regression tests (`test_on_online_annotation_is_narrowed_to_health_result`, `test_render_annotation_is_arity_narrowed_to_two_positional_args`) now fail if either narrowed annotation is ever widened back, plus a sibling regression guard (`test_on_fail_annotation_is_unchanged`) proving the edit didn't perturb `on_fail`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit the SURF-02 signature-assertion tests RED** - `7f60a90` (test)
2. **Task 2: Apply the three SURF-02 verdicts (GREEN)** - `94e14d9` (refactor)

**Plan metadata:** (this commit)

## Files Created/Modified

- `tests/test_ready_gate.py` - Added `test_on_online_annotation_is_narrowed_to_health_result` (RED then GREEN) and `test_on_fail_annotation_is_unchanged` (sibling regression guard, GREEN both ways).
- `tests/test_panelkit.py` - Added `test_render_annotation_is_arity_narrowed_to_two_positional_args` (RED then GREEN), using the load-bearing `localns={"SelectedContext": SelectedContext}` workaround for the `TYPE_CHECKING`-guarded import under `from __future__ import annotations`.
- `yahir_reusable_bot/lifecycle/ready_gate.py` - `on_online` parameter annotation narrowed; inline comment records the D-62 rationale and the test that pins it.
- `yahir_reusable_bot/discord/panelkit.py` - `render` parameter annotation arity-narrowed; inline comment records the D-62 rationale and the test that pins it.
- `yahir_reusable_bot/scheduler/engine.py` - No signature change; `register`'s docstring gained a new paragraph recording the D-62 leave-variadic verdict and its reasoning.

## Decisions Made

- D-62 confirmed as a three-part outcome, exactly as CONTEXT.md locked it: two sites narrowed, one site deliberately left variadic with the reason written into the source rather than defaulted or silently dropped.
- No static type checker introduced. `[dependency-groups].dev` (`pytest`, `ruff`, `syrupy`, `time-machine`, `grimp`) is unchanged — verified via `git diff pyproject.toml` showing zero hunks. Per D-63, the `get_type_hints` assertions ARE this repo's enforcement mechanism for annotation accuracy in the absence of a type checker; adopting one stays an explicitly deferred backlog item, not something this plan reopens.

## Deviations from Plan

None — plan executed exactly as written. Both RED-phase acceptance criteria (non-zero exit before Task 2; the `render` failure being an assertion mismatch, never a `NameError` mentioning `SelectedContext`) were verified live before proceeding to Task 2, and every Task 2 acceptance-criteria grep/test command passed unmodified from the plan's literal text.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

SURF-02 is closed: all three sites in `ready_gate.py`, `panelkit.py`, and `scheduler/engine.py` are in a decided state, two of them pinned by regression tests that fail if widened back. This is a **public hub-surface change** (per the plan's `<output>` note): `on_online` and `render`'s annotations are part of the hub's published constructor contract for consumer-supplied callables. The only live consumer (WeatherBot) already conforms — its `on_online` handler is already a single-positional-param function and its tests already pass single-arg callables — so nothing breaks today, but the narrowing does not take effect for that consumer until a human-gated repin (new tag → `[tool.uv.sources]` bump → `uv lock --upgrade` → `uv sync` → deploy, per `ECOSYSTEM.md` §3). No version bump, tag, repin, `uv sync`, or deploy was performed by this plan.

Full suite: 174 passed (171 baseline + 3 new), zero warnings under the now-active `filterwarnings=error` filter from 07-03. `test_import_hygiene.py` (10 tests) and `ruff check` both green. Ready to proceed to 07-05.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*

## Self-Check: PASSED

All created/modified files verified present on disk; both task commit hashes (`7f60a90`, `94e14d9`) verified present in `git log --oneline --all`.
