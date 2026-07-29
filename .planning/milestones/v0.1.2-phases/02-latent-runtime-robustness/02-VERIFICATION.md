---
phase: 02-latent-runtime-robustness
verified: 2026-07-27T23:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: Latent Runtime Robustness Verification Report

**Phase Goal:** Close real hub bugs that need specific runtime conditions to bite.
**Verified:** 2026-07-27T23:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|---|---|---|
| 1 | CFG-01: A PHASE-2 reconcile failure fires `on_rejected` before re-raising; original error still re-raised; rollback byte-identical | ✓ VERIFIED | `reload.py:139` binds `except Exception as exc:`; `_best_effort_hook(self._on_rejected, exc, label="reconcile-rolled-back")` fires at `:169-171`, immediately before `raise` at `:172`. Rollback block (`:156-163`, holder replace + restore + log) is unchanged from PHASE-1's ordering shape. `tests/test_reload.py::test_reconcile_failure_fires_on_rejected_once_and_rolls_back` asserts: `fired == [reconcile_exc]` (exactly once), `exc_info.value is reconcile_exc` (original exception unmasked), `holder.current() == old_cfg`, `restored == [old_cfg]` — all four assertions pass (`uv run pytest tests/test_reload.py -q` → 1 passed). |
| 2 | DISC-01: `BotThread` exposes a death-reason accessor (login_failure/crashed) alongside unchanged `is_alive()`; NO hub-side reconnect wrapper (D-21 liveness-only) | ✓ VERIFIED | `gateway.py:328-337` — `death_reason()` accessor returns `self._death_reason`, set in `_run`'s two except branches (`:371-385`) to `REASON_LOGIN_FAILURE`/`REASON_CRASHED` (module constants `:66-67`). `is_alive()` body (`:319-326`) is textually unchanged from a pure liveness check (`not self._failed and self._thread.is_alive()`). No reconnect/backoff loop exists anywhere in `_amain`/`_run`/`start()` — grepped the diff and full file, only a single `client.start(token)` call. Two tests (`test_bot_thread_records_login_failure_death_reason`, `test_bot_thread_records_crashed_death_reason_on_generic_exception`) pass, sampling both branches independently. WR-02 (code-review fix, commit `6024336`) additionally closes a write-order race by setting `_death_reason` before `_failed` in both branches — confirmed present at `:372-377` and `:382-384`. |
| 3 | DISC-02: re-summon cannot leave 2+ live pinned panels or a fresh-but-unpinned panel; per-item HTTPException/NotFound handling; create-before-delete preserved; pin-cap headroom (incl. single-owned-panel case, WR-01); pin-cap number NOT hardcoded | ✓ VERIFIED | `gateway.py:185-260` (`summon_panel`). Create-before-delete preserved byte-identically: `channel.send()` (`:193`) precedes the delete loop (`:237-244`). Per-item delete catch: `except (discord.NotFound, discord.HTTPException, discord.Forbidden)` wraps each `old.delete()` (`:238-244`) — a failed delete logs+continues, never aborts the rest. Pin-cap headroom-reserve: `except discord.HTTPException` on the fresh pin (`:200-232`) evicts one owned stray `if len(matches) >= 1` (`:207`, the WR-01 fix — was `>= 2`, corrected via RED test `0918db6`→GREEN `331e0e5`) then retries the pin. No cap number (50/250) hardcoded anywhere in `gateway.py` or `tests/test_gateway.py` (grepped, zero hits). Three independent tests cover: (a) NotFound-mid-delete (2 remaining deletes still run, net 1 pinned panel), (b) at-cap with 2 owned (headroom-reserve, fresh pinned), (c) at-cap with exactly 1 owned (the WR-01 boundary — fresh pinned, `freed_count >= 1`). All three pass. |
| 4 | DISC-03: `stop()` cannot raise RuntimeError and always joins (TOCTOU degrade) | ✓ VERIFIED | `gateway.py:339-360` — `asyncio.run_coroutine_threadsafe(...)` (`:353`) is now INSIDE the same `try` as `future.result()` (`:352-357`), guarded by `except Exception` (`:355`) which logs a WARNING and falls through; `self._thread.join(timeout=timeout)` (`:358`) is unconditionally reached (no early return in the except). `test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call` uses a REAL closed loop (`asyncio.new_event_loop()` + `.close()`) wrapped in a fast-path proxy reporting `is_running()==True`, asserting `bot.stop()` returns without raising AND `fake_thread.joined == [True]`. Passes. |
| 5 | DISC-04: `SelectedContext.snapshot()` exists (lock-free read-once) + await-safety docstring contract; consumer `wiring.py` NOT touched (contract+API only) | ✓ VERIFIED | `selection.py:61-72` — `snapshot(self) -> I` returns `self._value`, semantically identical to `.value`, docstring states the capture-before-await contract. Class docstring (`:23-33`) extended with an explicit "Interleaved-await hazard (DISC-04/H08, D-30)" paragraph naming the race and prescribing `snapshot()`-before-`await`. No lock/context-manager/frozen type added — `.value`/`.set()` unchanged, confirmed `.value` still reflects a later `set()` (not frozen). `git diff` / repo search confirms WeatherBot's `wiring.py` is not part of this repo — hub-side only, correctly out of scope. `test_snapshot_is_stable_across_interleaved_set_but_value_reflects_it` asserts BOTH halves in one test: `snap_result == "A"` (stable) and `value_result == "B"` (reflects write, guards against over-fix). Passes. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `tests/test_reload.py` | First-ever coverage for `config/reload.py`, RED-first CFG-01 test | ✓ VERIFIED | Exists, 1 test function, imports `ReloadEngine` from hub, no mocking library, passes. |
| `tests/test_gateway.py` (grown) | New DISC-01/02/03 test functions | ✓ VERIFIED | Grew from 1 to 8 test functions (2 death, 3 summon [incl. WR-01 boundary], 1 stop, +1 pre-existing recursion test, +1 not counted twice). All pass. |
| `tests/test_selection.py` | First-ever coverage for `discord/selection.py`, RED-first DISC-04 test | ✓ VERIFIED | Exists, 1 test function, no discord.py import (Pitfall 4 honored), passes. |
| `yahir_reusable_bot/config/reload.py` | PHASE-2 fires `on_rejected` before re-raise | ✓ VERIFIED | Confirmed above (Truth 1). |
| `yahir_reusable_bot/discord/gateway.py` | DISC-01/02/03 fixes + WR-01/WR-02 review fixes | ✓ VERIFIED | Confirmed above (Truths 2-4), plus WR-01/WR-02 review-cycle corrections present in source. |
| `yahir_reusable_bot/discord/selection.py` | DISC-04 snapshot() + docstring contract | ✓ VERIFIED | Confirmed above (Truth 5). |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `reload.py:146` except block | `_best_effort_hook` | exception bound + hook call before raise | ✓ WIRED | `except Exception as exc:` (`:139` in current HEAD numbering for PHASE-1, `:152` for PHASE-2 block) binds; `_best_effort_hook(self._on_rejected, exc, label=...)` called at `:169-171` before `raise` at `:172`. |
| `gateway.py` `_run` except branches | `death_reason()`/`is_alive()` | reason set alongside `_failed` | ✓ WIRED | Both except branches (`:371-385`) set `_death_reason` then `_failed`; accessor and `is_alive()` both read the live attributes. |
| `gateway.py` `summon_panel` pin() HTTPException | headroom-reserve eviction | `len(matches) >= 1` branch | ✓ WIRED | `:207-222` — evicts stray, retries pin; verified by 2 independent tests plus the WR-01 boundary test. |
| `gateway.py` `stop()` | `run_coroutine_threadsafe` | moved inside `try` | ✓ WIRED | `:352-357` — schedule + result both inside the guarded try; join at `:358` always reached. |
| `selection.py` `snapshot()` | `SelectedContext._value` | direct return | ✓ WIRED | `:72` returns `self._value`; test proves stability across interleaved `set()`. |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full suite green | `uv run pytest -q` | 35 passed, 1 warning (documented, non-fatal — IN-03 triaged) | ✓ PASS |
| GATE-01 import-hygiene | `uv run pytest tests/test_import_hygiene.py -q` | 8 passed | ✓ PASS |
| CFG-01 RED-first ancestry | `git log --oneline -1 3bcd174^` | `4853c78` (test-only) | ✓ PASS |
| DISC-01 RED-first ancestry | `git log --oneline -1 7173027^` | `510ef05` (test-only) | ✓ PASS |
| DISC-02 RED-first ancestry | `git log --oneline -1 f06f20e^` | `ca5114e` (test-only) | ✓ PASS |
| DISC-03 RED-first ancestry | `git log --oneline -1 8f715b2^` | `5b8427d` (test-only) | ✓ PASS |
| DISC-04 RED-first ancestry | `git log --oneline -1 d8502e5^` | `cbc08ae` (test-only) | ✓ PASS |
| WR-01 RED-first ancestry | `git log --oneline -1 331e0e5^` | `0918db6` (test-only) | ✓ PASS |
| No mocking-library imports | grep `unittest.mock\|pytest-mock` across new test files | 0 hits | ✓ PASS |
| No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) | grep across all phase-touched files | 0 hits | ✓ PASS |
| No hardcoded pin-cap number | grep `50\|250` in `gateway.py`/`test_gateway.py` | 0 hits | ✓ PASS |
| No repin/tag/deploy performed | `git tag --contains e971ebf`, `pyproject.toml` diff | no new tags, no pyproject changes | ✓ PASS (human-gated close-out correctly not executed) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| CFG-01 | 02-01 | PHASE-2 reconcile failure fires `on_rejected` before re-raising | ✓ SATISFIED | Truth 1 above; `[x]` in REQUIREMENTS.md:57-58 |
| DISC-01 | 02-02 | Non-recoverable disconnect leaves operator-visible signal | ✓ SATISFIED | Truth 2 above; `[x]` in REQUIREMENTS.md:62-64 |
| DISC-02 | 02-02 | Re-summon never leaves 2+ live panels or fresh-but-unpinned panel | ✓ SATISFIED | Truth 3 above; `[x]` in REQUIREMENTS.md:66-68 |
| DISC-03 | 02-02 | `stop()` never raises RuntimeError on TOCTOU | ✓ SATISFIED | Truth 4 above; `[x]` in REQUIREMENTS.md:70-71 |
| DISC-04 | 02-03 | `SelectedContext` await-safety contract explicit, snapshot-safe consume offered | ✓ SATISFIED | Truth 5 above; `[x]` in REQUIREMENTS.md:73-76 |
| GATE-01 | 02-01, 02-02, 02-03 | Full suite + import-hygiene/litmus/grimp gates stay green | ✓ SATISFIED | 35 passed incl. 8 import-hygiene tests; `[x]` in REQUIREMENTS.md:105-107 |

No orphaned requirements found — every requirement REQUIREMENTS.md maps to "Phase 2" (CFG-01, DISC-01..04, GATE-01) appears in at least one plan's `requirements` frontmatter field and is checked off (`[x]`).

### Anti-Patterns Found

None. Scanned all phase-modified files (`reload.py`, `gateway.py`, `selection.py`, `test_reload.py`, `test_gateway.py`, `test_selection.py`) for debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER), empty implementations, hardcoded empty returns, and console.log-only stubs — zero hits. `ruff check` on the same files surfaces exactly 2 pre-existing findings (unused `pathlib.Path` import in `reload.py`, ambiguous `I` TypeVar name in `selection.py`), both traced via `git log -S` to the initial-import commit `138a907`, predating Phase 2 entirely — correctly out of this phase's scope per the SUMMARY's Rule 1-4 deviation-scope boundary.

### Code-Review Loop (02-REVIEW.md / 02-REVIEW-FIX.md)

A standard-depth review found 0 Critical, 2 Warning, 3 Info findings across all 6 phase files. Both Warnings were real behavior bugs in the freshly-shipped fixes and were closed:
- **WR-01** (pin-cap eviction off-by-one, `>=2` should be `>=1`) — fixed RED-first (`0918db6`→`331e0e5`), verified above as part of Truth 3.
- **WR-02** (`_failed`/`_death_reason` write-order race) — fixed (`6024336`), verified above as part of Truth 2.

The 3 Info findings (IN-01 retry-pin Forbidden mislabeling, IN-02 failed-eviction-delete drop, IN-03 unawaited-coroutine RuntimeWarning) were triaged with explicit rationale, not silently dropped, and do not block the phase goal — none contradict a ROADMAP success criterion; all are narrow residual edges explicitly accepted with reasoning recorded in `02-REVIEW-FIX.md`.

### Human Verification Required

None. Every ROADMAP success criterion is either a pure control-flow/state-transition assertion covered by a passing hub-assertable synthetic-double test (D-17 discipline: fake client/channel/loop doubles, no live Discord dependency), or a documented contract/API-only scope (DISC-04) whose consumer-side adoption is explicitly out of hub scope. Per the verification focus's guidance, green hub tests with synthetic doubles are treated as sufficient proof — no live-Discord UAT is demanded for mechanisms already exercised by the doubles (pin-cap behavior, TOCTOU loop-close, LoginFailure/crash death paths, interleaved-await race).

### Gaps Summary

No gaps. All 5 ROADMAP success criteria are observably true in the codebase, all 6 REQ-IDs (CFG-01, DISC-01, DISC-02, DISC-03, DISC-04, GATE-01) are satisfied and traced to passing tests, the RED-first two-commit discipline (D-13) holds for every one of the 6 fix pairs (5 phase findings + WR-01 review-cycle fix), GATE-01 (import-hygiene/litmus/grimp) is green, no domain nouns leaked into the hub (no new imports, all fixes are internal control-flow changes), and no repin/tag/deploy was performed (correctly deferred to the human-gated close-out per ECOSYSTEM.md §3).

---

_Verified: 2026-07-27T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
