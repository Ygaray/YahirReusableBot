---
phase: 03-public-surface-footguns
verified: 2026-07-27T20:15:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Public-Surface Footguns Verification Report

**Phase Goal:** Harden the public surface against footguns unreachable in the current consumer but
guaranteed to bite the next one. This is the hub's entire reason to exist.
**Verified:** 2026-07-27T20:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (by requirement ID)

| # | Requirement | Truth | Status | Evidence |
|---|-------------|-------|--------|----------|
| 1 | SCHED-01 (H16) | `SchedulerEngine.remove` is idempotent for an already-gone job id — no-op success, not a raise; dependency-free `except KeyError:` (no apscheduler import) | VERIFIED | `yahir_reusable_bot/scheduler/engine.py:76-94` — `try: self._scheduler.remove_job(job_id) / except KeyError: _log.debug(...)`. No `import apscheduler` anywhere in module. `tests/test_engine.py` (4 tests: idempotent-swallow, present-id-forwards, idempotency-on-repeat, narrow-swallow-non-KeyError-reraises) all pass. RED-first proof: fix commit `5e6fbf8`'s direct parent is test-only commit `0d1f828` (verified via `git rev-parse`). |
| 2 | RELY-02 (H09) | `burst_size == 1` degrades instead of raising `ZeroDivisionError` from the tenacity wait | VERIFIED | `yahir_reusable_bot/reliability/retry.py:175-179` — `if burst_size <= 1: return burst_spread_s` placed after the mid-pause branch and before the division; `burst_size > 1` math (`:182-184`) is untouched. `tests/test_retry.py` RELY-02 tests (4) pass, including a `build_retrying(attempts_per_burst=1)` black-box exhaustion drive. RED-first proof: fix `5567a38` parent is test `4579dc5`. |
| 3 | RELY-03 (H10) | `two_burst_wait`'s standalone-desync precondition is documented loudly; the mid-pause fires exactly at `attempt_number == burst_size`, pinned by an executable test; no coupling machinery added | VERIFIED | `yahir_reusable_bot/reliability/retry.py:204-213` — PRECONDITION paragraph stating the `stop=stop_after_attempt(2 * burst_size)` requirement; function body unchanged (no factory/assert). `tests/test_retry.py#test_rely_03_mid_pause_pinned_and_precondition_documented` passes. RED-first proof: fix `3079e9c` parent is test `5c8b9cb`. This is a docstring-only fix per design (D-37), and its correctness is directly pinned by an executable test — not merely present-and-unexercised — so it is not treated as behavior-unverified. |
| 4 | DISC-05 (H11) | `interaction_check` returns `False` cleanly (falsy guard, not `is None`) when `interaction.user` is absent (`None` or `discord.utils.MISSING`), never raising `AttributeError` | VERIFIED | `yahir_reusable_bot/discord/panelkit.py:330-335` — `if not interaction.user:` (falsy check) at the TOP of the method, before the `.bot` dereference; emits reject log, returns `False`, no ephemeral ack. `tests/test_panelkit.py` DISC-05 rows (None-user, MISSING-shaped-falsy-user, legitimate-user-still-gated) all pass. RED-first proof: fix `ed18d8b` parent is test `18ea58d`. |
| 5 | DISC-06 (H12) | An empty/whitespace-only `marker` is rejected at `PanelKit` construction, closing the `cid.startswith("")` owns-everything hole | VERIFIED | `yahir_reusable_bot/discord/panelkit.py:180-185` — `if not marker or not marker.strip(): raise ValueError(...)` placed right after `super().__init__(timeout=None)`, before collaborator assignments. `tests/test_panelkit.py` DISC-06 rows (empty, whitespace, valid-marker-regression, message-names-value) all pass. RED-first proof: fix `2a3e0c7` parent is test `ee73757`. |
| 6 | LIFE-02 (H14) | `write_pid_atomic` never double-closes an fd; a failing `os.replace` cannot silently close an unrelated descriptor | VERIFIED | `yahir_reusable_bot/lifecycle/identity.py:76-97` — `fd = -1` set immediately after happy-path close; except-path close guarded `if fd != -1:`. `tests/test_identity.py#test_life_02_write_pid_atomic_closes_temp_fd_exactly_once_on_replace_failure` (monkeypatched real-delegating `os.close` counter) passes. RED-first proof: fix `0c14258` parent is test `a815e26`. **Post-review regression fix (WR-01):** the except-path close is additionally re-wrapped in `try/except OSError: pass` (identity.py:91-95) so a genuine close failure cannot mask the original error or skip the temp-file unlink — `test_life_02_except_path_close_failure_does_not_mask_original_error` passes (RED-first: fix `74cd090` parent is test `55ccfdd`). |
| 7 | LIFE-03 (H15) | The documented non-Linux "degrade to True" behavior holds even when the consumer supplies a path-shaped `proc_marker` | VERIFIED | `yahir_reusable_bot/lifecycle/identity.py:213-214` — `prog == Path(proc_marker.decode("utf-8", "replace")).name` (both sides basenamed, symmetric). `-m` module branch (`:222-226`) unchanged. `tests/test_identity.py` LIFE-03 rows (degrade-holds-for-path-shaped-marker, real-Linux-basename-match, plain-marker-no-op-regression) all pass. RED-first proof: fix `820353f` parent is test `bbfccca`. |
| 8 | MATCH-01 (H06) | A command argument is extracted correctly when the keyword's casefold changes length (`ß`→`ss`, `ﬁ`→`fi`); arg sliced from a string consistent with the string the prefix test matched | VERIFIED | `yahir_reusable_bot/registry/match.py:45-69,94-97` — new `_keyword_boundary` helper (O(n) accumulate-per-original-char-casefold-length scan); `match_command` slices `rest = stripped[boundary:]` (never `folded`). `tests/test_match.py` (7 tests: sharp-s, ﬁ-ligature, ﬆ-ligature, adversarial single-char overshoot non-match, empty/whitespace input, ASCII raw-case regression) all pass. RED-first proof: fix `2fa1908` parent is test `39ababf`. |
| 9 | MATCH-02 (H13) | `spec.name` is validated at registration so an empty name cannot claim blank input and an uppercase name cannot be permanently unmatchable | VERIFIED | `yahir_reusable_bot/registry/registry.py:52-57` — `if not spec.name or spec.name != spec.name.casefold(): raise ValueError(...)` inside the existing derivation pass, message names the offending value. `tests/test_registry.py` (7 tests: empty/uppercase raise at direct construction and via `build_registry`, message names value, valid specs unaffected) all pass. RED-first proof: fix `fd38b47` parent is test `d98d3fc`. |

**Score:** 9/9 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `yahir_reusable_bot/scheduler/engine.py` | Idempotent `remove()` + module logger | VERIFIED | `except KeyError:`, `_log = structlog.get_logger(__name__)` present; no apscheduler import |
| `tests/test_engine.py` | NEW, 4 tests | VERIFIED | Exists, all 4 tests pass |
| `yahir_reusable_bot/lifecycle/identity.py` | LIFE-02 fd guard + LIFE-03 basename fix | VERIFIED | Both fixes present and correct; WR-01 follow-up also present |
| `tests/test_identity.py` | Extended, LIFE-02/03 rows | VERIFIED | 17 tests total incl. 6 LIFE-02/03 rows, all pass |
| `yahir_reusable_bot/registry/registry.py` | D-34 validation | VERIFIED | Validation loop present, raises `ValueError` |
| `yahir_reusable_bot/registry/match.py` | `_keyword_boundary` helper | VERIFIED | Helper present, correctly wired into `match_command` |
| `tests/test_registry.py` | NEW, 7 tests | VERIFIED | Exists, all 7 tests pass |
| `tests/test_match.py` | NEW, 7 tests | VERIFIED | Exists, all 7 tests pass |
| `yahir_reusable_bot/reliability/retry.py` | RELY-02 guard + RELY-03 docstring | VERIFIED | Both present, byte-identical happy path preserved |
| `tests/test_retry.py` | Extended, RELY-02/03 rows | VERIFIED | 12 tests total, all pass |
| `yahir_reusable_bot/discord/panelkit.py` | DISC-05 falsy guard + DISC-06 marker raise | VERIFIED | Both present, correctly placed |
| `tests/test_panelkit.py` | NEW, 7 tests | VERIFIED | Exists, all 7 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `SchedulerEngine.remove` | host `remove_job` | `except KeyError:` swallow | WIRED | Confirmed at engine.py:91-94 |
| `CommandRegistry.__init__` D-34 validation | `match_command`'s `folded.startswith(spec.name)` | validation guarantees casefolded name | WIRED | registry.py:52-57 raises before any view derived; match.py:86 relies on it (no per-match casefold of name) |
| `_keyword_boundary` | `ParsedCommand.arg` RAW contract | boundary maps into original stripped string | WIRED | match.py:94-102, arg sliced from `stripped`, never `folded` |
| `write_pid_atomic` fd lifecycle | `os.close`/`os.replace` | fd=-1 guard | WIRED | identity.py:76-97 |
| `_read_proc_cmdline` non-Linux degrade | `_argv_matches_marker` | both sides basenamed | WIRED | identity.py:213-214, 240 |
| `interaction_check` falsy guard | discord.py 2.7.1 `MISSING` sentinel | `if not interaction.user:` | WIRED | panelkit.py:330 |
| `PanelKit._marker` | `is_owned_panel`'s `cid.startswith(marker)` | construction-time reject | WIRED | panelkit.py:180-185 |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite green (GATE-01) | `uv run pytest -q` | 71 passed, 0 failed | PASS |
| Import-hygiene gate green (GATE-01) | `uv run pytest tests/test_import_hygiene.py -q` | 8 passed | PASS |
| Each fix's RED-first two-commit proof (10 pairs incl. WR-01 follow-up) | `git rev-parse <fix>~1` vs test-commit sha | All 10 pairs match | PASS |
| Code-review follow-up fix (WR-01) executable | `uv run pytest tests/test_identity.py -k test_life_02_except_path_close_failure_does_not_mask_original_error` | 1 passed | PASS |
| No debt markers in modified files | `grep -n -E "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER"` across all 12 modified/created files | No matches | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MATCH-01 | 03-03 | Length-changing casefold arg extraction | SATISFIED | `_keyword_boundary` in match.py, test_match.py |
| MATCH-02 | 03-03 | Empty/uppercase name rejection at registration | SATISFIED | Validation loop in registry.py, test_registry.py |
| RELY-02 | 03-04 | `burst_size==1` degrade not raise | SATISFIED | Guard in retry.py, test_retry.py |
| RELY-03 | 03-04 | Standalone-desync precondition documented + pinned | SATISFIED | Docstring in retry.py, executable pin test |
| DISC-05 | 03-05 | `interaction_check` falsy guard | SATISFIED | Guard in panelkit.py, test_panelkit.py |
| DISC-06 | 03-05 | Empty marker rejected at construction | SATISFIED | Raise in panelkit.py, test_panelkit.py |
| LIFE-02 | 03-02 | fd double-close guard | SATISFIED | Guard in identity.py (+ WR-01 follow-up), test_identity.py |
| LIFE-03 | 03-02 | Basename-both-sides for path-shaped marker | SATISFIED | Fix in identity.py, test_identity.py |
| SCHED-01 | 03-01 | Idempotent `remove()` | SATISFIED | `except KeyError:` in engine.py, test_engine.py |
| GATE-01 | all 5 plans | Full suite + import-hygiene stay green | SATISFIED | 71 passed / 8 passed confirmed live |

All 9 phase requirement IDs (plus GATE-01) are declared in PLAN frontmatter across the 5 plans and
cross-referenced in REQUIREMENTS.md's "Milestone v0.1.2" section, all marked `[x]` there. No orphaned
requirements found for Phase 3.

### Anti-Patterns Found

None. Scanned all 6 modified source files and 6 test files for TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER,
`return null`/empty-implementation patterns, and stub phrasing — zero matches.

### Code Review Follow-Up (03-REVIEW.md / 03-REVIEW-FIX.md)

The phase's own code review found 3 findings (0 critical, 2 warning, 1 info):

- **WR-01 (in-scope regression):** LIFE-02's fd-guard fix removed exception-safety around the
  except-path close for the *first*-close scenario (not the double-close it targeted). **Fixed**
  RED-first (test `55ccfdd` → fix `74cd090`), confirmed present in current source
  (`identity.py:91-95`, wrapped in `try/except OSError: pass`) and its regression test passes.
- **WR-02 (deferred, correctly out of scope):** duplicate `spec.name` not rejected by MATCH-02's
  validation — genuine footgun but not one of the 9 audited H-numbers and not part of the locked
  D-34 decision (casefold symmetry, not uniqueness). Logged in `deferred-items.md` as a fast-follow
  candidate. Not a gap against this phase's declared scope.
- **IN-01 (deferred, correctly out of scope):** duplicate log message in `panelkit.py`'s
  `_safe_error_edit`, pre-existing code this phase did not touch. Logged, not a gap.

Both deferrals are consistent with the phase's locked scope (9 H-numbered findings only) and are
correctly tracked outside GATE-01/requirements coverage — they do not block phase completion.

### Human Verification Required

None. All 9 truths are code-verifiable via source inspection + passing regression tests; no
visual/UX/external-service behavior is involved in this phase's scope.

### Gaps Summary

None. All 9 requirement IDs (MATCH-01, MATCH-02, RELY-02, RELY-03, DISC-05, DISC-06, LIFE-02, LIFE-03,
SCHED-01) plus GATE-01 are verified against live source code, not merely SUMMARY.md claims. Every fix's
RED-first two-commit proof was independently re-derived via `git rev-parse` (not trusted from the
SUMMARY text). The full suite (71 passed) and import-hygiene gate (8 passed) were re-run live and match
the ground truth stated in the verification task. The one code-review-identified in-scope regression
(WR-01) was confirmed fixed and tested; the two deferred findings (WR-02, IN-01) are correctly
out-of-locked-scope and do not affect this phase's goal achievement.

---

_Verified: 2026-07-27T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
