---
phase: 06-insertion-seams-provable-backstop
fixed_at: 2026-08-04T00:55:51Z
review_path: .planning/phases/06-insertion-seams-provable-backstop/06-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-08-04T00:55:51Z
**Source review:** .planning/phases/06-insertion-seams-provable-backstop/06-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (4 warning + 1 info — fix policy `all`)
- Fixed: 5
- Skipped: 0

All fixes were verified against the actual current source (matched the reviewer's
cited lines exactly, no drift), guarded by genuinely-RED-before-fix regression tests
in the established house style (module-local `SENTINEL` constants, hand-written
capture doubles, `pytest`'s built-in `monkeypatch` fixture — no `unittest.mock`
anywhere), and committed atomically. `uv run pytest -q` went from the 153-passed
baseline to 158 passed (5 new regression tests, one per finding); `uv run ruff
check` and `uv run pytest tests/test_import_hygiene.py -q` are clean after every
commit. No locked decision (D-52 … D-60) was touched: disablement stays an explicit
constructor parameter, the counter still counts changed writes not substitutions
inside the same `threading.Lock`, the `on_redaction` hook keeps its
swallow-and-continue guard, and the D-60 ordering check still only warns.

## Fixed Issues

### WR-01: Non-`str`/`bytes` buffer types silently bypass redaction in `RedactingWriter.write()`

**Files modified:** `yahir_reusable_bot/redact/sink.py`, `tests/test_redact_sink.py`
**Commit:** `cccdd0c`
**Applied fix:** Widened the non-text triage from `isinstance(data, bytes)` to
`isinstance(data, (bytes, bytearray, memoryview))`, normalizing all three through
`bytes(data).decode("utf-8", "replace")` (the identity-safe `bytes(existing_bytes)`
no-op means this is a drop-in replacement for the plain `bytes` case). Added
`test_sink_decodes_bytearray_and_memoryview_before_scrubbing`, confirmed genuinely
RED against pre-fix source (a `bytearray`/`memoryview` secret reached the capture
double completely unscrubbed), GREEN after.

### WR-02: `bytes` payloads bypass the "untouched and BY IDENTITY" guarantee when disabled or unpatterned

**Files modified:** `yahir_reusable_bot/redact/sink.py`, `tests/test_redact_sink.py`
**Commit:** `fa5e82b`
**Applied fix:** The bytes-like decode ran unconditionally, before the
`enabled`/`patterns` check — so a disabled or unpatterned writer silently converted
a `bytes`/`bytearray`/`memoryview` write into a brand-new `str` object instead of
forwarding the original by identity (and would raise `TypeError` against a real
binary-mode target). Moved the decode inside an explicit
`if not (self._enabled and self._patterns): return self._target.write(data)`
short-circuit, so a disabled/unpatterned writer now forwards the exact original
object untouched, matching the docstring's stated guarantee. Added
`test_sink_disabled_or_unpatterned_forwards_bytes_by_identity`, confirmed RED
(`assert capture.pieces[0] is payload` failed — a decoded `str` had replaced the
original `bytes` object) before the fix, GREEN after.

### WR-03: `verify.py` asserts `RedactingWriter.write()` "never raises," which `sink.py` did not itself guarantee

**Files modified:** `yahir_reusable_bot/redact/sink.py`, `yahir_reusable_bot/redact/verify.py`, `tests/test_redact_sink.py`
**Commit:** `992c574`
**Applied fix — reasoning recorded per the constraint's request:** `redact_secrets()`
is documented (`core.py`) to raise `re.error` for a hand-built, unregistered,
malformed pattern outside `register_patterns`'s vetting contract. Two failure modes
were on the table for `write()`: (a) let the exception propagate — rejected, because
that breaks the caller's hot logging call, precisely the outcome this module
otherwise guards against via the swallowed `on_redaction` exception a few lines
below; (b) fall back to forwarding the original, unscrubbed text — rejected, because
`write()` cannot prove that text is clean (the whole reason redaction exists), so
silently emitting it on error would be a worse security failure than either raising
or dropping the line. Chose to **fail CLOSED**: wrapped the `redact_secrets()` call
in `try/except re.error`, and on catch, write a fixed, non-secret placeholder string
(`_MALFORMED_PATTERN_PLACEHOLDER`, echoes neither the original text nor any pattern
source) instead of the original payload, without incrementing the counter or firing
`on_redaction` (no substitution actually happened — only a withholding). This makes
`write()` literally never raise, which is what makes `verify.py`'s existing "never
raises" claim true rather than merely asserted; updated `verify.py`'s module
docstring to name this guard explicitly so the two docstrings' claims about the same
method no longer disagree. Added
`test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern`,
confirmed RED (`re.PatternError`/`re.error` propagated out of `write()`) before the
fix, GREEN after, asserting both that nothing raised and that neither the sentinel
nor the withheld payload reached the target.

**Flagged for human verification:** this fix introduces new security-relevant
behavior (a fail-closed placeholder substitution) rather than purely applying a
mechanical patch — the review's own Fix guidance offered two options (qualify the
docstring, or harden `write()`) and left the trade-off to be decided. The
reasoning above is the trade-off actually chosen; please confirm the fail-closed
choice (and the exact placeholder wording) matches your judgment before treating
this as fully settled — tests pass, but this is a design decision, not just a bug
fix.

### WR-04: `warnings.warn(..., stacklevel=2)` misattributes the ordering-mismatch warning to `verify.py` instead of the consumer's call site

**Files modified:** `yahir_reusable_bot/redact/verify.py`, `tests/test_redact_verify.py`
**Commit:** `88518f9`
**Applied fix:** Changed `stacklevel=2` to `stacklevel=3` in both `warnings.warn(...)`
calls inside `_warn_if_processor_misordered()`. Reproduced the review's own live
verification first (`w[0].filename` reported `verify.py`, confirmed via a scratch
script and then via a real regression test) — `_warn_if_processor_misordered` is
one frame below `assert_redaction_active`, which is itself one frame below the
consumer's call site, so `stacklevel=3` is the correct depth to reach the consumer.
Added `test_ordering_warning_is_attributed_to_the_consumers_call_site`, confirmed
RED (`record[0].filename` was `.../yahir_reusable_bot/redact/verify.py`, not the
test's own file) before the fix, GREEN after.

### IN-01: `assert_redaction_active` reads live `structlog` configuration twice despite docstring's "read once" framing

**Files modified:** `yahir_reusable_bot/redact/verify.py`, `tests/test_redact_verify.py`
**Commit:** `402f9f9`
**Applied fix:** Captured `config = structlog.get_config()` once at the top of
`assert_redaction_active` and threaded it into
`_warn_if_processor_misordered(config)` instead of having the helper independently
call `structlog.get_config()` again. Added
`test_reads_live_configuration_exactly_once`, which wraps `structlog.get_config`
with a call counter via `monkeypatch` (this repo's house convention — no mocking
library). Confirmed genuinely RED before the fix (2 calls recorded) by temporarily
stashing just the `verify.py` change and re-running the test in isolation, then
restored the fix; GREEN after (1 call).

## Skipped Issues

None — all 5 in-scope findings were fixed.

---

_Fixed: 2026-08-04T00:55:51Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
