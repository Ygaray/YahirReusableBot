---
phase: 03-public-surface-footguns
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - yahir_reusable_bot/scheduler/engine.py
  - yahir_reusable_bot/lifecycle/identity.py
  - yahir_reusable_bot/registry/registry.py
  - yahir_reusable_bot/registry/match.py
  - yahir_reusable_bot/reliability/retry.py
  - yahir_reusable_bot/discord/panelkit.py
  - tests/test_engine.py
  - tests/test_identity.py
  - tests/test_match.py
  - tests/test_panelkit.py
  - tests/test_registry.py
  - tests/test_retry.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-07-27T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Reviewed the six fixed modules (SCHED-01, LIFE-02, LIFE-03, MATCH-01, MATCH-02, RELY-02, RELY-03, DISC-05, DISC-06) and their six regression suites at standard depth, including a diff-by-diff trace of every phase-3 commit (`5e6fbf8`..`2a3e0c7`) against the pre-fix source, plus a live `pytest`/`ruff` run.

The nine footguns' **core fixes are all correct** and match the locked design decisions called out in the phase context (the `except KeyError:` in `engine.py`, the falsy `interaction.user` guard, the `two_burst_wait` docstring-only precondition, the `burst_size <= 1` degrade). I traced `_keyword_boundary` character-by-character against multiple multi-char casefold-expansion cases (`ß`->`ss`, `ﬁ`->`fi`, `ﬆ`->`st`, single-char overshoot) and found the accumulation logic mathematically sound — no off-by-one. All 53 tests in the six new/extended suites pass against current `HEAD`, and each "RED pre-fix" claim I spot-checked by re-deriving the pre-fix diff is genuine (not a tautology): the `test_remove_is_idempotent_*`, `test_length_changing_casefold_*`, `test_rely_02_burst_size_one_*`, `test_disc_05_*`, `test_disc_06_*`, and `test_life_02_*`/`test_life_03_*` assertions all fail against the commit immediately prior to their respective fix and pass after.

Two real gaps remain, both adjacent to code this phase touched:

1. The LIFE-02 fd-guard fix (`identity.py`) removed the blanket `except OSError: pass` around the except-path `os.close(fd)` call and replaced it with an unguarded call gated only on `fd != -1`. This correctly prevents the double-close it targets, but it also removes the original defense against a *first* `close()` failing for an unrelated reason (I/O error, `ENOSPC` on a lazy-writeback filesystem) — that scenario is no longer tested and, if it occurs, masks the original write/replace exception and skips the temp-file cleanup.
2. The MATCH-02 validation loop added this phase checks non-empty + already-casefolded `spec.name`, but not uniqueness — a duplicate name still silently overwrites an entry in `by_name` while `render_help`/`by_keyword_len_desc` still carry both specs, producing an inconsistent view a consumer wiring bug would never see at build time.

One minor logging-clarity nit in `panelkit.py` rounds out the findings.

## Warnings

### WR-01: `write_pid_atomic`'s except-path close is no longer defended against a genuine (non-double) close failure

**File:** `yahir_reusable_bot/lifecycle/identity.py:82-90`
**Issue:** The LIFE-02 fix (commit `0c14258`) replaced:
```python
try:
    os.close(fd)
except OSError:
    pass
```
with:
```python
if fd != -1:
    os.close(fd)
```
This correctly stops a **double**-close (the fd was already closed on the happy path, `fd == -1`, so this branch is skipped) — that's the fix this phase set out to make, and it's proven by `test_life_02_write_pid_atomic_closes_temp_fd_exactly_once_on_replace_failure`.

But the only remaining caller of this branch is the case where `os.write(fd, ...)` raised *before* the happy-path close ran (`fd` is still the live, open descriptor). In that case `os.close(fd)` is now completely unguarded. If that close *itself* raises (e.g. a delayed `ENOSPC`/`EIO` surfacing on close for a filesystem that buffers writes — plausible on the very disk-full condition that made `os.write` fail in the first place), the new exception from `os.close` propagates out of the `except BaseException:` block, which:
- replaces the original, diagnostically useful exception (e.g. "disk full") with the close error,
- skips `Path(tmp).unlink(missing_ok=True)` entirely, leaking the temp PID file, and
- skips the final `raise` that was supposed to re-raise the *original* failure.

The module's own docstring states the writer "deliberately re-raises (a startup PID-write failure must be visible)" — this still raises *something*, but it can raise the wrong thing while leaking a file and burying the actual root cause. This exact code path (`fd != -1` branch) was not exercised by any new test; only the `fd == -1` (already-closed, no-op) branch was tested.

**Fix:** Keep the double-close guard but restore exception-safety around the close call itself so a close failure can never mask the original error or skip cleanup:
```python
except BaseException:
    if fd != -1:
        try:
            os.close(fd)
        except OSError:
            pass
    Path(tmp).unlink(missing_ok=True)
    raise
```

### WR-02: `CommandRegistry`'s new name validation doesn't catch duplicate names

**File:** `yahir_reusable_bot/registry/registry.py:52-59`
**Issue:** D-34's validation loop (added this phase, commit `fd38b47`) checks that every `spec.name` is non-empty and already casefolded, but never checks that names are unique across the tuple. The very next line's comment even documents the assumption it doesn't enforce:
```python
# name -> spec (every name is unique; one entry per spec).
self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
```
If a consumer's spec tuple contains two `CommandSpec`s with the same `name` (a realistic wiring mistake — e.g. a copy-pasted spec whose `name` field wasn't updated), `by_name` silently keeps only the *last* one, while `self.commands` (used by `render_help`) and `by_keyword_len_desc` (used by `match_command`) still carry both. This produces a build that constructs without error but where `render_help()` prints two lines for the same-looking command and `match_command` can resolve to a **different** `CommandSpec` object than `registry.by_name[name]` returns for the same name — an inconsistency invisible until an operator taps the "wrong" one's handler. This is precisely the class of build-time wiring bug this phase's validation pass is otherwise designed to close.

**Fix:** Extend the same loop (no second pass needed):
```python
seen: set[str] = set()
for spec in self.commands:
    if not spec.name or spec.name != spec.name.casefold():
        raise ValueError(
            f"CommandSpec.name must be non-empty and already casefolded "
            f"(match_command folds input, never spec.name); got {spec.name!r}"
        )
    if spec.name in seen:
        raise ValueError(f"CommandSpec.name must be unique; duplicate name {spec.name!r}")
    seen.add(spec.name)
```

## Info

### IN-01: Identical log message for two distinct failure branches in `_safe_error_edit`

**File:** `yahir_reusable_bot/discord/panelkit.py:483` and `yahir_reusable_bot/discord/panelkit.py:485`
**Issue:** Both the inner "edit failed and the interaction was already acked, so no fallback is attempted" branch and the outer "the fallback send also failed" catch-all log the exact same string `"panel error reply failed"`. Since this is the *last* line of failure isolation for the whole panel, an operator/dev grepping logs after an incident can't tell from the message alone which of the two distinct failure modes occurred (no ack existed vs. the ack path itself blew up).
**Fix:** Give the two branches distinct messages, e.g. `"panel error reply failed (already acked, no fallback)"` for line 483 and `"panel error reply failed (fallback send also failed)"` for line 485.

---

_Reviewed: 2026-07-27T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
