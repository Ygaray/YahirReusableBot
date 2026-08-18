# Phase 8: Redaction-hardening cleanup - Pattern Map

**Mapped:** 2026-08-17
**Files analyzed:** 7 (2 modified source, 2 modified/new test, 1 doc, 1 config, 1 net-new script)
**Analogs found:** 6 / 7 (1 explicitly has no analog — noted below, not force-matched)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `yahir_reusable_bot/redact/sink.py` (add `on_error` hook) | service (hot write-path hook) | event-driven | same file, `on_redaction` hook (`sink.py:66-90,169-174`) | exact — same file, same pattern, existing sibling hook |
| `yahir_reusable_bot/redact/core.py` (docstring addition) | model / doc-only | n/a (no behavior change) | same file, existing `Scope (WR-02)` docstring block (`core.py:100-122`) | exact — extending an existing docstring section, not new code |
| `tests/test_redact_sink.py` (new `on_error` RED-first tests) | test | event-driven | same file, `test_on_redaction_hook_receives_count_and_cannot_break_logging` (`:405-432`) + `test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern` (`:435-458`) | exact — sibling hook test in the same file |
| `tests/test_extension_guide.py` (2 new doc-gate tests) | test | transform (doc-content extraction + assertion) | same file, Known-limitations gate (`:324-403`) + `_extract_seam_08_section` helper (`:49-73`) | exact — explicitly named as the template by CONTEXT.md |
| `EXTENSION-GUIDE.md` §7 (new paragraph) | config/doc | n/a | same file, "Telemetry, described accurately." / "Proving it is on." paragraphs (`:185-187`, `:202-206`) | exact — new paragraph in the same section, same prose style |
| `pyproject.toml` (`[tool.pyright]` table + dev dep) | config | n/a | same file, `[tool.pytest.ini_options]` (`:37-48`) + `[dependency-groups].dev` (`:26-35`) | role-match — existing tool-config table + dev-dep-list conventions in the same file |
| baseline-diff script (new, e.g. `scripts/pyright_baseline.py`) | utility (CLI/script) | batch (diff two JSON reports) | — | **no analog** — see "No Analog Found" below |

## Pattern Assignments

### `yahir_reusable_bot/redact/sink.py` (service, event-driven) — add `on_error` hook

**Analog:** same file, `on_redaction` hook (constructor + invocation site)

**Constructor pattern to mirror** (`sink.py:66-90`... `__init__` signature, keyword-only optional hook):
```python
def __init__(
    self,
    target: object,
    patterns: Sequence[RedactionPattern],
    *,
    enabled: bool = True,
    on_redaction: Callable[[int], None] | None = None,
) -> None:
    ...
    self._on_redaction = on_redaction
    ...
```
New `on_error` param follows the identical shape: `on_error: Callable[..., None] | None = None`, stored as `self._on_error`. Payload shape is Claude's Discretion at plan time (no-arg vs. the malformed `RedactionPattern` instance — safe to pass since `__repr__` is already source-eliding per `core.py:88-128`).

**Invocation-guard pattern to mirror exactly** (`sink.py:169-174`, fired outside the `threading.Lock`, swallow-and-continue):
```python
hook = self._on_redaction
if hook is not None:
    try:
        hook(current)
    except Exception:  # noqa: BLE001 — never break the hot write path
        pass
```
The new `on_error` hook must be invoked inside the existing `except re.error:` branch (`sink.py:154-164`), wrapped in the identical `try/except Exception: pass` guard — this is the D-52 "never raise inside logging" contract; do not copy the signature without copying the guard (Pitfall 3 in RESEARCH.md).

**Existing fail-closed branch this hook attaches to** (`sink.py:154-164`, do not change its return behavior):
```python
if isinstance(data, str) and self._enabled and self._patterns:
    try:
        scrubbed = redact_secrets(data, self._patterns)
    except re.error:
        # WR-03 ... Fail CLOSED ...
        return self._target.write(_MALFORMED_PATTERN_PLACEHOLDER)
```

---

### `yahir_reusable_bot/redact/core.py` (model, doc-only) — docstring addition

**Analog:** same file's existing `Scope (WR-02)` docstring section (`core.py:100-122`), already verbatim quoted in RESEARCH.md.

No new pattern to copy from elsewhere — this task extends the existing docstring paragraph structure ("Accidental paths — CLOSED... / Explicit paths — STILL OPEN, by design...") with a Phase-8-dated cross-reference/acceptance marker, matching its own established prose voice. No behavior change; no code excerpt needed beyond what's already quoted in RESEARCH.md.

---

### `tests/test_redact_sink.py` (test, event-driven) — new `on_error` RED-first tests

**Analog:** same file — two sibling tests to model structure on:

**Hook-behavior test template** (`tests/test_redact_sink.py:405-432`):
```python
def test_on_redaction_hook_receives_count_and_cannot_break_logging():
    seen: list[int] = []
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture, (RedactionPattern.literal(SENTINEL),), on_redaction=seen.append
    )
    writer.write(f"{SENTINEL} one")
    writer.write(f"{SENTINEL} two")
    assert seen == [1, 2]

    def _boom(count: int) -> None:
        raise RuntimeError("hook exploded")

    capture_raising = _CaptureDouble()
    writer_raising = RedactingWriter(
        capture_raising, (RedactionPattern.literal(SENTINEL),), on_redaction=_boom
    )
    writer_raising.write(f"{SENTINEL} three")  # must not raise
    assert SENTINEL not in capture_raising.all_output
    assert writer_raising.redaction_count == 1
```

**Malformed-pattern setup template** (`tests/test_redact_sink.py:435-458`):
```python
def test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern():
    malformed = RedactionPattern(pattern=re.compile(r"(a)"), replacement=r"\2")
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (malformed,))

    result = writer.write(f"a secret appid={SENTINEL} a")  # must not raise

    assert isinstance(result, int)
    assert capture.pieces
    forwarded = capture.pieces[0]
    assert f"appid={SENTINEL}" not in forwarded
    assert SENTINEL not in forwarded
```

The new test(s) should combine both shapes: hand-build a malformed `RedactionPattern` (as above), construct `RedactingWriter` with an `on_error` callback, write through it, and assert (a) `write()` still returns normally, (b) no secret leaks, (c) the callback fired, and — mirroring `_boom` above — that a *raising* `on_error` callback still doesn't break `write()`.

**File-level conventions** (`tests/test_redact_sink.py:1-29`):
```python
from __future__ import annotations

import json
import logging
import re
import sys
import threading
import unicodedata

import pytest
import structlog
```
Module docstring convention: state which requirement/decision IDs the tests pin (e.g., "REDACT-10 / D-01") and note RED-first status before implementation exists, matching this file's own header style.

---

### `tests/test_extension_guide.py` (test, transform) — two new doc-gate tests

**Analog:** same file, Known-limitations gate (`tests/test_extension_guide.py:324-403`) — explicitly named by CONTEXT.md as the template to mirror twice.

**Content-assertion half** (structure from `:324-356`, using the existing `_extract_seam_08_section` helper at `:49-73` — do not duplicate its logic):
- Extract the SEAM-08 section via `_extract_seam_08_section`.
- Lowercase it.
- Assert a labelled heading substring is present.
- Assert a dict-comprehension `missing = {concept: token for concept, token in anchors.items() if token not in section_lower}` check is empty.

**Self-proof half** (`tests/test_extension_guide.py:359-403`, verbatim structure to copy):
```python
def test_selfproof_limitations_gate_catches_deleted_block():
    content = GUIDE_PATH.read_text(encoding="utf-8")
    broken_content = re.sub(
        r"\*\*Known limitations\.\*\*.*?(?=\*\*Implemented:\*\*)",
        "",
        content,
        flags=re.DOTALL,
    )
    assert "Known limitations" not in broken_content, (
        "Self-proof setup failed: the limitations block was not actually removed"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(broken_content)
        tmp_path = Path(tmp.name)
    try:
        original_path = globals()["GUIDE_PATH"]
        globals()["GUIDE_PATH"] = tmp_path
        try:
            test_seam_08_section_carries_the_known_limitations_block()
            assert False, "Self-proof FAILED: ... gate is vacuous"
        except AssertionError as e:
            if "vacuous" in str(e):
                raise
            pass
    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()
```

**Two new test pairs to write**, each following this exact 2-function shape:
1. Telemetry-semantics pair — target text at `EXTENSION-GUIDE.md:202-206` ("Telemetry, described accurately."). Anchor tokens: `"changed writes"` / `"monotonic"` (confirmed non-colliding).
2. Reconfigure-discipline pair — target text at `EXTENSION-GUIDE.md:185-187` ("Proving it is on."). Anchor tokens: `"after any reconfiguration"` / `"structlog's configuration is global mutable state"` (confirmed non-colliding with the existing `"before any"` assertion at `:123`, which belongs to a different test, `test_seam_08_section_documents_both_recipes`).

**Collision constraint:** do not select any anchor token containing the substring `"before any"` — that exact substring is already asserted by `tests/test_extension_guide.py:123` for a different claim (recipe-2 ordering).

---

### `EXTENSION-GUIDE.md` §7 (doc) — new malformed-pattern paragraph

**Analog:** same file's existing SEAM-08 §7 paragraphs — model prose style on the "Telemetry, described accurately." and "Proving it is on." bolded-lead-in paragraph format:
```
**Telemetry, described accurately.** `RedactingWriter.redaction_count` is readable off the
live writer instance, and an optional `on_redaction` push hook can be supplied at
construction. It counts **changed writes**, not individual substitutions, and is monotonic
for process lifetime — a rate is obtained by diffing two point-in-time reads, never by
treating it as a per-substitution total.
```
New paragraph (or fifth "Known limitations" bullet) should state the malformed-pattern fail-closed behavior explicitly and mention the new `on_error` hook, in this same bolded-lead-in style. Content to state (from `sink.py:114-127`'s existing docstring, "2a. WR-03 guard" paragraph, and the fail-closed branch at `sink.py:154-164`): a hand-built/unregistered pattern that raises `re.error` is handled by withholding the original payload behind a fixed placeholder — never fail-open, never raise on the hot path — and the optional `on_error` hook makes this observable.

---

### `pyproject.toml` (config) — `[tool.pyright]` table + dev dependency

**Analog:** same file's existing `[tool.pytest.ini_options]` table (config-table convention) and `[dependency-groups].dev` list (dev-dep convention):
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "ruff>=0.15.16",
    "syrupy>=5.3.4",
    "time-machine>=2.16",
    "grimp>=3.14",                  # import-hygiene gate (dev-only)
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra"
filterwarnings = ["error"]
```
New table follows the same `[tool.X]` convention:
```toml
[tool.pyright]
typeCheckingMode = "basic"    # MUST be explicit — pyright's own default is "standard" (Pitfall 2)
pythonVersion = "3.12"
include = ["yahir_reusable_bot"]
```
Add `"pyright"` to the `dev = [...]` list, with an inline comment matching the existing per-entry comment style (see `grimp` line above — "# import-hygiene gate (dev-only)").

**Legitimacy note (from RESEARCH.md):** `pyright` was flagged SUS by the automated legitimacy checker (download-count signal unavailable, not an adverse finding). Insert a `checkpoint:human-verify` before running `uv add --dev pyright`, per protocol.

---

## Shared Patterns

### Swallow-and-continue hook guard (D-52 "never raise inside logging")
**Source:** `yahir_reusable_bot/redact/sink.py:169-174`
**Apply to:** the new `on_error` hook invocation in `sink.py`, and its regression test in `test_redact_sink.py`
```python
try:
    hook(current)
except Exception:  # noqa: BLE001 — never break the hot write path
    pass
```

### RED-first / self-proof test discipline
**Source:** `tests/test_redact_sink.py:1-17` (module docstring convention) and `tests/test_extension_guide.py:359-403` (self-proof-by-mutation pattern)
**Apply to:** all new tests in this phase (`on_error` hook test, both D-04 doc-gate test pairs) — state RED-first status in the module/test docstring, and for doc-gate tests specifically, prove non-vacuity by breaking a temp copy and re-asserting failure.

### Bolded-lead-in doc paragraph style
**Source:** `EXTENSION-GUIDE.md:185-187, 202-206`
**Apply to:** the new §7 malformed-pattern paragraph — `**Label.** Sentence... — clause explaining the "why."`

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| baseline-diff script (e.g. `scripts/pyright_baseline.py`) | utility | batch (diff two JSON diagnostic sets) | No existing script/`scripts/` convention or JSON-diffing utility exists anywhere in this repo (confirmed by RESEARCH.md — no CI YAML, no baseline tooling precedent). RESEARCH.md's "Don't Hand-Roll" section confirms no upstream package fills this gap either (`pyright-baseline` 404s on both PyPI and npm). Planner should build this fresh per RESEARCH.md's recommended shape: run `pyright --outputjson`, diff against a committed baseline file, key on `(file_path, rule, message)` tuples (not line numbers — see Pitfall 4), fail only on new diagnostic keys. No in-repo pattern to copy; use RESEARCH.md's "Recommended pattern" prose as the spec instead. |

## Metadata

**Analog search scope:** `yahir_reusable_bot/redact/`, `tests/test_redact_sink.py`, `tests/test_redact_core.py`, `tests/test_extension_guide.py`, `EXTENSION-GUIDE.md`, `pyproject.toml` (all read directly this session or already fully quoted in RESEARCH.md, which itself confirms full-file reads this session).
**Files scanned:** 7 target files + their in-file/in-repo analogs (no cross-repo search needed — every analog lives in the same file as its target, per this being a hardening/pinning phase over already-shipped code).
**Pattern extraction date:** 2026-08-17
</content>
</invoke>
