---
phase: 07-v0-1-2-debt-paydown
plan: 05
subsystem: lifecycle
tags: [structured-logging, capture_logs, ast-drift-guard, identity-guard, documentation]

# Dependency graph
requires:
  - phase: 07-04
    provides: "SURF-02 closed, 174 passed / zero warnings baseline"
provides:
  - "Both _best_effort_hook sites (ready_gate.py, config/reload.py) log via a structured label= kwarg instead of an f-string"
  - "AST-normalized (docstring-stripped) anti-drift guard proving the two _best_effort_hook bodies stay identical, standing from here on"
  - "LIFE-05 ratified as a decided, documented, consumer-visible limitation — no behavioral change to identity.py"
affects: [config-reload, ready-gate, weatherbot-repin, extension-guide]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "structlog.testing.capture_logs() for asserting structured log-content (event string + kwargs), zero new dependency"
    - "AST-normalized (ast.unparse, docstring dropped) source comparison as a clone anti-drift regression guard — immune to intentional per-site docstring divergence and incidental formatting, catches real logic drift between two intentionally-duplicated staticmethods"

key-files:
  created: []
  modified:
    - tests/test_ready_gate.py
    - tests/test_reload.py
    - yahir_reusable_bot/lifecycle/ready_gate.py
    - yahir_reusable_bot/config/reload.py
    - yahir_reusable_bot/lifecycle/identity.py
    - EXTENSION-GUIDE.md
    - .planning/REQUIREMENTS.md
    - .planning/v0.1.2-MILESTONE-AUDIT.md

key-decisions:
  - "D-09 clone anti-drift guard implemented via AST comparison with docstrings stripped, not a literal inspect.getsource() string diff — the two sites' docstrings legitimately differ (each names its own engine's outcome vocabulary: 'online transition / re-probe outcome' vs 'reject path's original error / applied path's committed swap'), so a literal-string comparison would never pass even when the clone is perfectly synced. Verified live before writing the test: the two bodies (minus docstring) were ALREADY identical pre-fix, confirming the plan's documented fallback (GREEN both ways, standing guard) applied rather than the RED-first path."
  - "D-61/D-61a executed exactly as CONTEXT.md locked them: zero behavioral change to _argv_matches_marker, the bundled short-option group form stays undecoded, and no artificial RED test was manufactured for LIFE-05."

requirements-completed: [HYG-02, LIFE-05]

coverage:
  - id: D1
    description: "_best_effort_hook logs via a structured label= kwarg at both ready_gate.py and config/reload.py sites, event string fixed regardless of label content"
    requirement: "HYG-02"
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_best_effort_hook_logs_the_label_as_a_structured_kwarg"
        status: pass
      - kind: unit
        ref: "tests/test_ready_gate.py#test_best_effort_hook_event_string_is_identical_across_labels"
        status: pass
      - kind: unit
        ref: "tests/test_reload.py#test_reload_best_effort_hook_logs_the_label_as_a_structured_kwarg"
        status: pass
    human_judgment: false
  - id: D2
    description: "A None hook is a no-op emitting no log record; a clean (non-raising) hook emits no log either — pinned both before and after the fix"
    requirement: "HYG-02"
    verification:
      - kind: unit
        ref: "tests/test_ready_gate.py#test_best_effort_hook_none_and_clean_hooks_emit_no_log"
        status: pass
    human_judgment: false
  - id: D3
    description: "The D-09 clone in config/reload.py moved together with ready_gate.py's fix — proven by an AST-normalized body comparison, not asserted in prose"
    requirement: "HYG-02"
    verification:
      - kind: unit
        ref: "tests/test_reload.py#test_reload_best_effort_hook_clone_matches_ready_gate_byte_for_byte"
        status: pass
    human_judgment: false
  - id: D4
    description: "identity.py ships zero behavioral change; the bundled short-option group form stays a documented, undecoded limitation"
    requirement: "LIFE-05"
    verification:
      - kind: unit
        ref: "tests/test_identity.py#test_bundled_short_option_group_not_matched"
        status: pass
    human_judgment: false
  - id: D5
    description: "The limitation is stated consumer-facing in EXTENSION-GUIDE.md section 4, not only in a private docstring"
    requirement: "LIFE-05"
    verification: []
    human_judgment: true
    rationale: "Prose-accuracy claim (the paragraph correctly states the launch-form constraint and its false-positive/SIGHUP reasoning) — mechanically checked by grep -c 'SIGHUP' EXTENSION-GUIDE.md >= 1, but the full read for tone/correctness is manual-only by design per 07-VALIDATION.md § Manual-Only Verifications."

duration: ~12min
completed: 2026-08-04
status: complete
---

# Phase 7 Plan 5: HYG-02 structured logging + LIFE-05 identity-guard ratification Summary

**Both `_best_effort_hook` clone sites now log via a fixed event string plus a structured `label=` kwarg instead of an f-string, with an AST-based anti-drift guard pinning the clone going forward; the identity guard's bundled short-option-group boundary ships zero behavioral change, ratified as a documented, consumer-visible limitation (D-61) with the false-positive/SIGHUP reasoning stated in `EXTENSION-GUIDE.md`.**

## GATE-02 exemption (D-61a)

LIFE-05 ships **no behavioral change** to `yahir_reusable_bot/lifecycle/identity.py` beyond a
docstring-only addition — `_argv_matches_marker` continues to leave the bundled short-option
group (`python -Om<module>` / `-Im<module>`) undecoded, exactly as before this plan. Per D-61a
(locked in `07-CONTEXT.md`), this requirement's GATE-02 RED-first obligation is satisfied by the
**already-green** pinned limitation test `tests/test_identity.py::test_bundled_short_option_group_not_matched`
— a boundary guard that was GREEN both before and after v0.1.2's WR-01 fix, and stays GREEN
both before and after this plan. **No artificial RED test was manufactured** for a decision whose
decided outcome is "no behavioral change." The plan 07-07 ancestry audit should read this as an
intentional exemption, not a gap: `git diff HEAD~4 -- yahir_reusable_bot/lifecycle/identity.py`
(spanning this plan's single docs commit) shows changes strictly inside a docstring, zero
executable lines added, removed, or modified.

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-04T05:16Z (STATE.md session timestamp)
- **Completed:** 2026-08-04T05:22Z
- **Tasks:** 3 completed
- **Files modified:** 8 (2 test, 3 source, 3 planning docs)

## Accomplishments

- `_best_effort_hook` at both `yahir_reusable_bot/lifecycle/ready_gate.py:194` and its D-09 clone
  in `yahir_reusable_bot/config/reload.py:339` now log `"hook failed; engine result unaffected"`
  as a fixed event string with the hook name carried in a separate structured `label=` field —
  closing the log-injection-shaped f-string violation (HYG-02) at both sites in one commit, so the
  clone never drifted even momentarily.
- A new AST-normalized anti-drift regression guard
  (`test_reload_best_effort_hook_clone_matches_ready_gate_byte_for_byte`) mechanically enforces
  "one fix, two sites" from here on: it strips each site's docstring (which legitimately differs
  per engine) before comparing the parsed function bodies, so it catches real logic drift between
  the two intentional clones without being defeated by their per-site prose.
  **Verified live before authoring the test:** the two bodies (minus docstring) were already
  identical pre-fix, so this guard is GREEN both before and after Task 2 — the plan's documented
  fallback path, not the RED-first path.
- `test_best_effort_hook_event_string_is_identical_across_labels` proves the label is carried as
  DATA, never interpolated: two calls with labels containing `{}` / `%` formatting characters and
  a non-ASCII character (`café`) produce the identical `event` string and their own distinct
  `label` values — the HYG-02/encoding probe from the plan's flagged-assumptions table.
- `EXTENSION-GUIDE.md` section 4 gained a consumer-facing paragraph stating the identity guard's
  launch-form constraint and its false-positive/SIGHUP reasoning in the guide's own voice — the
  limitation is now visible to the consumer who could trip it, not only buried in a private
  docstring.
- `REQUIREMENTS.md`'s LIFE-05 bullet corrected (PC-A) to name the BUNDLED short-option group form
  as the open item — the previous text named the ATTACHED `-mmodule` form, which was already fixed
  in v0.1.2 and needed no decision.
- `v0.1.2-MILESTONE-AUDIT.md` gained a correction blockquote immediately after the Tech Debt table,
  annotating row 9's stale premise without rewriting the historical record itself.
- `identity.py`'s `_argv_matches_marker` docstring gained one sentence recording that Phase 7
  (D-61) ratified this boundary rather than closing it — zero executable lines touched.

## Task Commits

Each task was committed atomically:

1. **Task 1: Commit the HYG-02 label-kwarg tests RED** — `b44e555` (test)
2. **Task 2: Replace the f-string with a structured label= kwarg at both sites (GREEN)** — `d2e9ca3` (fix)
3. **Task 3: Ratify the identity-guard boundary and make the limitation consumer-visible (LIFE-05)** — `0216c70` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `tests/test_ready_gate.py` — added three tests: structured `label=` kwarg assertion, event-string-identical-across-labels (encoding probe), and the None/clean-hook no-op guard (GREEN both ways).
- `tests/test_reload.py` — added the ReloadEngine-site label-kwarg test plus the AST-normalized (docstring-stripped) clone anti-drift guard and its `_code_body_without_docstring` helper.
- `yahir_reusable_bot/lifecycle/ready_gate.py` — `_best_effort_hook`'s f-string replaced with `_log.warning("hook failed; engine result unaffected", label=label)`.
- `yahir_reusable_bot/config/reload.py` — the D-09 clone's `_best_effort_hook` received the byte-identical edit in the same commit.
- `yahir_reusable_bot/lifecycle/identity.py` — one sentence added to `_argv_matches_marker`'s REMAINING BOUNDARY docstring paragraph; no executable line changed.
- `EXTENSION-GUIDE.md` — section 4 gained the consumer-facing launch-form constraint paragraph.
- `.planning/REQUIREMENTS.md` — LIFE-05 bullet corrected to name the bundled form and record its D-61 resolution; checkbox left `- [ ]` (flipped by the standard post-plan `requirements mark-complete` step, not manually).
- `.planning/v0.1.2-MILESTONE-AUDIT.md` — correction blockquote added after the Tech Debt table; table row 9 itself left byte-unchanged.

## Decisions Made

- The clone anti-drift guard compares AST-normalized (`ast.unparse`) function bodies with the
  leading docstring stripped, rather than a literal `inspect.getsource()` string diff. The two
  `_best_effort_hook` docstrings genuinely differ per site (each names its own engine's outcome
  vocabulary), so a literal comparison would fail permanently even with a perfectly-synced clone.
  This was verified live (both pre- and post-fix) before committing to the approach.
- D-61/D-61a executed exactly as locked in `07-CONTEXT.md`: LIFE-05 resolves as "ratify the
  boundary, document it, state it consumer-facing" — not "decode the bundled form." No behavioral
  change, no artificial RED test.

## Deviations from Plan

None — plan executed exactly as written. The one open question the plan flagged for verification
("verify [the two bodies] match before writing assertions... if already identical pre-fix, label
it GREEN both ways") was resolved by live verification (documented above) confirming the
GREEN-both-ways fallback applied, exactly as the plan anticipated as a possible outcome.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

HYG-02 and LIFE-05 are both closed. Full suite: **179 passed** (174 baseline + 5 new), zero
warnings under the active `filterwarnings=error` filter. `test_import_hygiene.py` (10 tests) and
`uv run ruff check` both green. `EXTENSION-GUIDE.md`'s SEAM-05 row needed no status change (it was
already `implemented`) — this plan added a constraint paragraph to existing prose, not a new seam.
No version bump, tag, repin, `uv sync`, or deploy performed — all human-gated per `ECOSYSTEM.md`
§3. Ready to proceed to 07-06.

---
*Phase: 07-v0-1-2-debt-paydown*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 9 created/modified files verified present on disk; all three task commit hashes
(`b44e555`, `d2e9ca3`, `0216c70`) verified present in `git log --oneline --all`.
