---
phase: 04-cleanup-readygate-fatal
reviewed: 2026-07-28T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - tests/test_discord_surface.py
  - tests/test_ready_gate.py
  - yahir_reusable_bot/discord/__init__.py
  - yahir_reusable_bot/lifecycle/health.py
  - yahir_reusable_bot/lifecycle/__init__.py
  - yahir_reusable_bot/lifecycle/ready_gate.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 04: Code Review Report

**Reviewed:** 2026-07-28T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the LIFE-04 (`ReadyOutcome`/fatal-path) and SURF-01 (`summon_panel` re-export) changes
against the locked decisions D-44 through D-47. I traced the diff line-by-line against the prior
commit (`7e08fad`) rather than trusting the docstrings' claims:

- **D-44 (`ReadyOutcome` + `__bool__`):** verified correct. `ReadyOutcome.__bool__` returns
  `self is ReadyOutcome.ONLINE`, so both `SHUTDOWN` and `FATAL` are falsy — confirmed by direct
  execution (`bool(ReadyOutcome.SHUTDOWN) is False`, `bool(ReadyOutcome.FATAL) is False`), and the
  test suite (`test_only_online_is_truthy`) samples all three members individually rather than
  only the two that matter for the "byte-compatible" claim, which is the right level of paranoia.
  `__bool__` overriding is safe on a plain `Enum` here — it does not touch `__eq__`/`__hash__`, so
  member identity/equality is unaffected.
- **D-45 (additive `fatal` field):** verified. `fatal: bool = False` is appended after `severity`
  (the last field), so all existing positional/keyword constructions of `HealthResult` remain
  valid. `Severity` (`WARNING=10`, `CRITICAL=30`) is untouched.
- **D-46 (fatal path ordering):** verified by reading the control flow directly (`ready_gate.py:130-141`).
  `on_fail` fires unconditionally before the `result.fatal` check; the fatal branch returns
  immediately (no `stop.wait()` call, enforced in tests by a stop double that raises if `.wait()`
  is ever invoked); `on_online` is only reachable from the `result.ok` branch, which the fatal
  branch cannot fall through to. The non-fatal failing-probe path is untouched (confirmed via the
  unified diff — no bytes changed on that path besides the new `if result.fatal` block inserted
  above it).
- **D-47 (`summon_panel` re-export):** verified. `discord/__init__.py` now imports and re-exports
  `summon_panel`, and the top-level `yahir_reusable_bot/__init__.py` was NOT touched (confirmed by
  reading it — it imports nothing), so the surface widening is scoped exactly as locked.
- **Import hygiene / no domain nouns:** `uv run pytest tests/test_import_hygiene.py` passes; the
  only "weather" tokens in the reviewed files are meta-references inside docstrings explaining the
  litmus rule itself (e.g. "weather-noun-free"), not actual domain vocabulary.
- Ran the full suite (`uv run pytest`, 79 passed) and `ruff check` (clean) against the reviewed
  files. RED-first process was verified via `git log`: each test file was committed failing
  (`175072b`, `1e762bf`) one commit before the corresponding fix (`d7939d8`, `eefffc9`) — genuine
  two-commit RED/GREEN proof, not a post-hoc single-commit rewrite.

No blocking defects found. Two coverage/robustness gaps and two pre-existing quality nits (visible
in, but not introduced by, this diff) are called out below.

## Warnings

### WR-01: No regression test guards the "not top-level" half of D-47

**File:** `tests/test_discord_surface.py`
**Issue:** D-47 locks two things: (1) `summon_panel` IS re-exported from
`yahir_reusable_bot.discord`, and (2) it is re-exported ONLY there — `yahir_reusable_bot`
(top-level) must NOT be widened. `test_summon_panel_reexport_succeeds` only proves half of the
contract (the positive import + `__all__` membership check). There is no test asserting
`yahir_reusable_bot.summon_panel` does not exist / is absent from the top-level package's
namespace or `__all__`. Today's `yahir_reusable_bot/__init__.py` is correctly un-widened, but
nothing in the suite would catch a future regression (e.g. someone later adds a convenience
`from .discord import summon_panel` at the top-level `__init__.py` for "ergonomics") — the
half of D-47 that is arguably the more failure-prone one (widening is an easy, well-intentioned
mistake; a missing re-export is caught immediately by any consumer's first import) is the
unguarded half.
**Fix:**
```python
def test_summon_panel_not_widened_to_top_level_package() -> None:
    import yahir_reusable_bot as pkg

    assert not hasattr(pkg, "summon_panel")
    assert "summon_panel" not in getattr(pkg, "__all__", [])
```

### WR-02: `ReadyGate.run`'s return-type change (`bool` -> `ReadyOutcome`) is byte-compatible only for truthy callers, not equality callers

**File:** `yahir_reusable_bot/lifecycle/ready_gate.py:64-65, 93`
**Issue:** The docstring (and D-44) claims "every existing `if gate.run(stop):` caller stays
byte-compatible." That's true for truthiness checks (`__bool__` correctly makes `SHUTDOWN`/`FATAL`
falsy), but it is NOT true for any caller that does an equality comparison against a bare bool,
e.g. `if gate.run(stop) == False:` or `if gate.run(stop) is False:` — a plain `Enum` member never
compares equal to (and is never identical to) the literal `False`, so such a caller would silently
flip from "detected shutdown" to "never detected shutdown" post-repin. This repo has no such
caller (confirmed — no other in-repo call sites exist besides the tests), so nothing here is
wrong, but the guarantee as documented is narrower than as stated, and every consumer's call site
must be grepped for `== False` / `is False` / `== True` against `gate.run(...)` (not just `if
gate.run(...):`) before the human-gated repin lands, per `ECOSYSTEM.md` §3.
**Fix:** Narrow the docstring's compatibility claim to explicitly call out the equality-comparison
caveat (e.g. "byte-compatible for truthy/falsy callers; a caller using `==`/`is` against a bare
bool must be migrated to `is ReadyOutcome.ONLINE` / `is ReadyOutcome.FATAL`"), and add that grep
to the repin checklist so it isn't only tribal knowledge in this file's docstring.

## Info

### IN-01: `_best_effort_hook`'s failure log uses raw f-string interpolation instead of a structured field

**File:** `yahir_reusable_bot/lifecycle/ready_gate.py:179`
**Issue:** `_log.warning(f"{label} hook failed; engine result unaffected")` interpolates `label`
directly into the message string, while every other log call in this same module passes
structured kwargs (`reason=result.reason, detail=result.detail`). This makes the hook-failure
event harder to query/filter by `label` in structured-log tooling (structlog's whole value
proposition). This is cloned verbatim from `config/reload.py`'s pre-existing `_best_effort_hook`
(same pattern, same line shape) so it's not new in this phase — flagging because it's visible in
a file under review and the inconsistency with the surrounding style is real, not because this
phase introduced it.
**Fix:**
```python
_log.warning("hook failed; engine result unaffected", label=label)
```

### IN-02: `on_online`'s type annotation is looser than `on_fail`'s despite an identical call-site contract

**File:** `yahir_reusable_bot/lifecycle/ready_gate.py:84-85, 126`
**Issue:** `on_fail` is typed `Callable[[HealthResult], None] | None`, but `on_online` is typed
`Callable[..., None] | None` (accepts anything). At the call site
(`self._best_effort_hook(self._on_online, result, label="on_online")`), `on_online` is invoked
with the exact same single `HealthResult` positional argument as `on_fail`. The looser annotation
means a type checker (mypy/pyright) would not flag an `on_online` callable with an incompatible
signature, even though the runtime contract is identical to `on_fail`. Pre-existing (not touched
by this diff), but worth tightening now that both hooks' contracts are documented side-by-side in
the same docstring.
**Fix:**
```python
on_online: Callable[[HealthResult], None] | None = None,
```

---

_Reviewed: 2026-07-28T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
