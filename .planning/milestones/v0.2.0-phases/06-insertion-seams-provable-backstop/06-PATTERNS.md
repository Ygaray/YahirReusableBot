# Phase 6: Insertion seams + provable backstop - Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 6 (3 source, 3 test) + 2 modified (`__init__.py`, `test_import_hygiene.py`) + 1 doc
**Analogs found:** 6 / 6 (all files have a strong analog; none is a "no analog" case — Phase 5
itself is the direct precedent, and WeatherBot's `_LiveStderr` is the literal promotion source for
the sink)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `yahir_reusable_bot/redact/sink.py` (`RedactingWriter` + telemetry, REDACT-04/08) | utility (stream proxy / sink) | streaming (write-intercept) | `weatherbot/__init__.py`'s `_LiveStderr` (promotion source, generalize) + `yahir_reusable_bot/redact/core.py` (project doc/style conventions) | exact (behavioral) / role-match (project style) |
| `yahir_reusable_bot/redact/sink.py`'s `assert_redaction_active` (REDACT-07, co-located per research) | utility (introspection/self-check) | request-response (call-and-raise/pass) | `yahir_reusable_bot/redact/registry.py`'s `register_patterns` (fail-loud-at-wiring-time posture, `ValueError` with non-leaking message) | role-match |
| `yahir_reusable_bot/redact/processor.py` (`redaction_processor`, REDACT-05) | utility (structlog processor factory) | transform (event_dict → event_dict) | `yahir_reusable_bot/redact/core.py`'s `redact_secrets` (the transform this wraps) — no existing structlog-processor analog in the repo, first structlog import under `redact/` | partial (transform pattern reused, no direct structlog-processor precedent) |
| `yahir_reusable_bot/redact/__init__.py` (extend exports) | config (package barrel) | — | itself (Phase 5 version, extend in place) | exact |
| `tests/test_redact_sink.py` (REDACT-04, REDACT-08, D-55 both-recipe tests) | test | CRUD-ish (construct → write → assert) | `tests/test_redact_core.py` (module-local `SENTINEL`, hand-written doubles, boundary-case matrix style) + WeatherBot's `tests/test_redact_hygiene.py` (capsys aggregation convention, non-str tolerance test) | exact |
| `tests/test_redact_processor.py` (REDACT-05) | test | transform | `tests/test_redact_core.py` (same conventions) | role-match |
| `tests/test_redact_verify.py` (REDACT-07, D-60 ordering) | test | request-response (raises/warns) | `tests/test_redact_registry.py` (fail-loud `pytest.raises(ValueError)` assertions, `ReDoS`/wiring-bug test shape) | role-match |
| `tests/test_import_hygiene.py` (`redact_scanned` coverage-guard extension) | test (config/gate) | — | itself, lines ~290-296 (`redact_scanned` assertion) — extend the existing set, same file | exact |
| `EXTENSION-GUIDE.md` (SEAM-08 row + section) | config/doc | — | itself, SEAM-04..07 rows/sections (lines 16-23, 77-115) | exact |

## Pattern Assignments

### `yahir_reusable_bot/redact/sink.py` (utility, streaming)

**Analog 1 (behavior to generalize):** `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` lines 26-56

```python
class _LiveStderr:
    def write(self, data: object) -> int:
        if isinstance(data, bytes):
            data = data.decode("utf-8", "replace")
        if isinstance(data, str):
            return sys.stderr.write(redact_appid(data))
        return sys.stderr.write(data)

    def flush(self) -> None:
        sys.stderr.flush()
```

**What to copy:** the non-`str` triage order (`bytes` decode-with-replace first, then the
`isinstance(data, str)` guard, else forward untouched) — this is D-52's contract, now owned by
`sink.py` instead of the app. **What to change:** `_LiveStderr` hardcodes `sys.stderr` and one
hardcoded `redact_appid` call; `RedactingWriter` must instead wrap an injected `target: object`
and call the generic `redact_secrets(data, patterns)` from `core.py`, per the research's verified
code shape (RESEARCH.md "Pattern 1"). Add the D-53 `enabled: bool = True` explicit constructor
param (default ON), the D-59 `threading.Lock`-guarded counter, and the D-57 optional
`on_redaction` hook wrapped in a swallow-and-continue `try/except Exception: pass` (mirrors D-52's
posture — never raise on the hot write path).

**Docstring / project-voice pattern to copy:** `yahir_reusable_bot/redact/core.py` lines 1-17 and
`RedactionPattern`'s docstring style (lines 28-53) — long-form rationale docstrings citing the
decision ID (`D-52`, `D-53`, `D-58`, `D-59`) inline, explaining *why* not just *what*, and
explicitly naming the rejected alternative. Every new file in this phase should open with a module
docstring in this voice, and every public class/function docstring should cite its governing
decision IDs the same way `RedactionPattern`'s docstring cites D-48.

**Error handling / fail-loud pattern to copy (for `assert_redaction_active`):**
`yahir_reusable_bot/redact/registry.py` lines 195-204 (`register_patterns`'s ReDoS rejection):

```python
raise ValueError(
    f"RedactionPattern at index {index} rejected at registration — it "
    f"triggered the nested-quantifier structural check or exceeded the "
    f"ReDoS wall-clock budget against the adversarial probe corpus: "
    f"{rp!r}. Rewrite the pattern to avoid catastrophic backtracking "
    ...
)
```

**What to copy:** raise `ValueError` (not `AssertionError`, so it survives `-O`), a message that
names *what* was checked and *why* it failed, and — critically — the message-never-leaks-secret
discipline (`{rp!r}` uses the source-eliding `__repr__`, never `rp.pattern.pattern`). Apply the
same discipline to `assert_redaction_active`'s three distinct raise sites (wrong factory type,
missing `_file` attribute i.e. structlog version drift, wrong/missing writer type) — each needs
its **own** distinguishable message per Pitfall 5 in RESEARCH.md, not one generic `except` that
collapses "structlog changed" into "consumer forgot to wire it."

**Concrete target shape (from RESEARCH.md, verified live against structlog 26.1.0 this session —
copy this structure, not the WeatherBot original):**

```python
class RedactingWriter:
    def __init__(
        self,
        target: object,
        patterns: Sequence[RedactionPattern],
        *,
        enabled: bool = True,                                    # D-53
        on_redaction: Callable[[int], None] | None = None,       # D-57
    ) -> None:
        self._target = target
        self._patterns = patterns
        self._enabled = enabled
        self._on_redaction = on_redaction
        self._lock = threading.Lock()                             # D-59
        self._count = 0

    def write(self, data: object) -> int:
        if isinstance(data, bytes):
            data = data.decode("utf-8", "replace")
        if isinstance(data, str) and self._enabled and self._patterns:
            scrubbed = redact_secrets(data, self._patterns)
            if scrubbed != data:                                  # D-58
                with self._lock:
                    self._count += 1
                    current = self._count
                if self._on_redaction is not None:
                    try:                                           # D-52/D-57
                        self._on_redaction(current)
                    except Exception:
                        pass
            return self._target.write(scrubbed)
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()

    @property
    def redaction_count(self) -> int:
        with self._lock:
            return self._count
```

---

### `yahir_reusable_bot/redact/sink.py`'s `assert_redaction_active` (utility, request-response)

**Analog:** `yahir_reusable_bot/redact/registry.py`'s overall shape — validate-then-derive, fail
loud at wiring/registration time, never at the hot path (lines 136-205). No direct introspection
analog exists in this repo; this is genuinely new mechanism, built per RESEARCH.md's verified
"Pattern 3" code (lines 452-526 of `06-RESEARCH.md`). Copy the **three-distinct-ValueError-message**
structure from that research example verbatim (wrong factory type / missing `_file` attribute /
wrong writer type), and the `_warn_if_processor_misordered` split into its own private helper using
`warnings.warn(...)` (never raise — D-60), following the same "one function, one guarded concern"
decomposition `registry.py` uses (`_looks_pathological` / `_blows_budget` as separate helpers
composed inside the public `register_patterns`).

---

### `yahir_reusable_bot/redact/processor.py` (utility, transform)

**Analog:** `yahir_reusable_bot/redact/core.py`'s `redact_secrets` (the transform being wrapped) —
no structlog-specific analog exists anywhere in this repo; this is the **first** module under
`redact/` (or anywhere in the hub) permitted to import `structlog`. Build directly from
RESEARCH.md's verified "Pattern 2" (lines 410-450):

```python
def redaction_processor(patterns: Sequence[RedactionPattern]):
    """... chain-order precondition stated LOUDLY in the docstring (REDACT-05) ..."""

    def _processor(logger, method_name, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, str):
                event_dict[key] = redact_secrets(value, patterns)
        return event_dict

    return _processor
```

**Imports pattern to copy:** `yahir_reusable_bot/redact/registry.py` lines 25-31 — `from __future__
import annotations`, stdlib imports, then one absolute intra-package import
(`from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets`). Add `import
structlog` as the one exception this module is allowed (per RESEARCH.md's Architecture note and
CLAUDE.md's litmus/grimp gates) — no other file under `redact/` should import it.

**Docstring pattern to copy:** the loud precondition warning block in RESEARCH.md's own example
(lines 427-441) — this is the literal text of REDACT-05's requirement, reproduce its structure
(⚠ CHAIN-ORDER PRECONDITION ... ⚠ EVEN CORRECTLY ORDERED ...) rather than writing new prose from
scratch, since RESEARCH.md's phrasing was tuned against the verified live pitfall (Pitfall 1).

---

### `yahir_reusable_bot/redact/__init__.py` (config, barrel)

**Analog:** itself (Phase 5 version), lines 1-25 — same file, extend in place.

```python
from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets
from yahir_reusable_bot.redact.registry import register_patterns

__all__ = ["RedactionPattern", "redact_secrets", "register_patterns"]
```

**Pattern to copy exactly:** absolute intra-package imports, one line per source module, `__all__`
listing every export in import order. Add `RedactingWriter`, `assert_redaction_active` (from
`sink.py`) and `redaction_processor` (from `processor.py`) as three new import lines + three new
`__all__` entries. Update the module docstring's opening paragraph (lines 1-17) to describe the
now-complete PC-01 surface — follow the existing docstring's non-domain-noun, mechanism-only voice.

---

### `tests/test_redact_sink.py` (test, CRUD-ish construct/write/assert)

**Analog 1 (house test conventions):** `tests/test_redact_core.py` lines 1-31 —

```python
"""...Self-proof note...EVERY assertion in this module is genuinely RED pre-fix..."""
from __future__ import annotations
...
SENTINEL = "SENTINELKEY_do_not_leak_123"
```

**What to copy:** the RED-first self-proof docstring convention (state explicitly that the module
doesn't exist yet, so collection itself fails), the module-local `SENTINEL` constant (never a
fixture — D-10), and citing the exact requirement IDs the test covers in each test's own docstring
(e.g. `"""REDACT-04 / SC1: ..."""`).

**Analog 2 (capture-double + aggregation convention — critical, from RESEARCH.md Pitfall 2):**
WeatherBot's `tests/test_redact_hygiene.py` — uses `capsys.readouterr().err` throughout, never
asserts against a single intercepted call. RESEARCH.md's own verified `_CaptureDouble` (lines
690-704 of `06-RESEARCH.md`) is the concrete pattern to copy verbatim:

```python
class _CaptureDouble:
    def __init__(self):
        self.pieces: list[str] = []

    def write(self, data: object) -> int:
        self.pieces.append(data if isinstance(data, str) else str(data))
        return len(self.pieces[-1])

    def flush(self) -> None:
        pass

    @property
    def all_output(self) -> str:
        return "".join(self.pieces)
```

**Do NOT use** `structlog.testing.capture_logs` (RESEARCH.md Pitfall 4 — it skips the renderer and
sink entirely, structurally cannot exercise `RedactingWriter`).

**Adversarial traceback test to copy verbatim (verified live this session, RESEARCH.md lines
706-726):** configure `dev.ConsoleRenderer` with **zero** exception-formatting processors, raise
and `log.exception(...)`, assert `SENTINEL not in capture.all_output` — proves the sink catches
what a processor-only design structurally cannot.

**JSON round-trip test to copy verbatim (RESEARCH.md lines 731-751):** use a boundary-class pattern
(not a literal with an embedded quote — Pitfall 3), assert `json.loads(line)` succeeds and a
non-secret field survives.

**D-55 both-recipes test:** install `RedactingWriter(sys.stderr, patterns)` as `sys.stderr` before
`logging.basicConfig()` (per Pitfall 6's ordering requirement), emit a bare `print()` and a stdlib
`logging.info(...)` call, assert both come out scrubbed via `capsys.readouterr().err`.

---

### `tests/test_redact_processor.py` (test, transform)

**Analog:** `tests/test_redact_core.py` conventions (same as above). Cover: `redaction_processor`
scrubs string `event_dict` values (positive case); and the documented negative case — a
processor-only configuration (no sink) still leaks a `logger.exception(...)` traceback under
`dev.ConsoleRenderer` (RESEARCH.md Pitfall 1's live-reproduced finding) — this is a **pinned
limitation test**, not a regression, and its docstring must say so explicitly (mirrors
`test_redaction_pattern_asdict_still_exposes_raw_pattern_source`'s "tripwire, NOT an endorsement"
framing in `tests/test_redact_core.py` lines 255-269).

---

### `tests/test_redact_verify.py` (test, request-response raise/warn)

**Analog:** `tests/test_redact_registry.py` (not read in full this pass, but same house convention
as `test_redact_core.py`/`test_redact_hygiene.py` — `pytest.raises(ValueError)` around a wiring-bug
scenario). Cover: raises when no `structlog.configure()` backstop is installed; raises after a
second `configure()` call drops it (Pitfall 7); passes silently when correctly wired; the three
*distinct* ValueError messages (wrong factory / missing `_file` / wrong writer type — Pitfall 5);
and the D-60 ordering check via `pytest.warns(...)` (never `pytest.raises`) for a mis-ordered
optional processor, plus the "could not verify order" generic-warning case for an unrecognized
formatter type.

---

### `tests/test_import_hygiene.py` (test/gate, modify in place)

**Analog:** itself, lines ~290-296 (verified above) —

```python
redact_scanned = {
    path.name for path in (_MODULE_ROOT / "redact").rglob("*.py")
}
assert {"core.py", "registry.py"} <= redact_scanned, (
    "redact package not in the litmus scan tree (coverage gap): "
    f"{sorted(redact_scanned)}"
)
```

**Change required:** extend the asserted set from `{"core.py", "registry.py"}` to
`{"core.py", "registry.py", "sink.py", "processor.py"}` (exact filenames pending the final module
split decided at plan time). This is the litmus coverage-guard pattern already established for
`lifecycle`, `registry`, and `discord` packages just above it in the same file — copy that exact
three-line assert shape.

**Also verify (do not assume passes unchanged):** the two grimp graph gates
(`test_module_imports_zero_app_code` and its sibling around line 129-184) — `processor.py`
importing `structlog` for the first time under `redact/` is a *different* dependency-graph shape
than Phase 5's pure-stdlib leaf; RESEARCH.md's Architecture note and CONTEXT.md's Integration
Points section both flag this must be re-tested, not assumed clean.

---

### `EXTENSION-GUIDE.md` (doc, SEAM-08 row + section)

**Analog:** SEAM-04..SEAM-07's existing rows and sections — table row at lines 16-23, sections at
lines 77-115 (`## 3.` through `## 6.`), e.g. SEAM-06 (lines 96-105):

```markdown
## 5. Command registration — `registry` / `bind` (SEAM-06, implemented)

**Source:** `yahir_reusable_bot/registry/` (`spec.py`, `registry.py`, `match.py`, `dispatch.py`, `__init__.py`)

The generic command-registry + dispatcher mechanism. A host registers its own commands into
the generic `CommandSpec` + `DispatchContext`, ...
```

**What to copy exactly:** the row format (`` | `Plug point` | SEAM-NN (P##) | **status** | what
ships | deferred | ``), and the section format (`## N. Title — description (SEAM-NN, status)`,
`**Source:** path (files)`, then a prose paragraph naming what the module owns vs. what the host
injects). **What to add uniquely for SEAM-08** (per RESEARCH.md's "SEAM-08 documentation shape"
section, lines 533-543): an explicit note that this seam is **architecturally inverted** relative
to every other row — SEAM-01/03/05/06/07 are "host implements a Protocol the hub calls"; SEAM-08 is
"hub provides callable mechanism the host wires into its OWN `structlog.configure()`." State this
so a future reader does not go looking for a nonexistent `Redactor` Protocol. Use `SEAM-08` (next
free number; `SEAM-02` stays absent, pre-existing gap, not this phase's concern).

## Shared Patterns

### Fail-loud-at-wiring-time (D-34 → D-50 → D-56)
**Source:** `yahir_reusable_bot/redact/registry.py` lines 136-205 (`register_patterns`)
**Apply to:** `assert_redaction_active`'s primary check (raises `ValueError` on any inconclusive
or negative introspection result). Exception: D-60's processor-ordering sub-check inside the same
function **warns**, never raises — document this asymmetry explicitly in the function's own
docstring so a reader doesn't assume uniform raise behavior.

### Non-`str`/`bytes` triage at the seam, not in the pure core (D-52)
**Source:** `weatherbot/__init__.py` lines 35, 48-52 (`_LiveStderr.write`)
**Apply to:** `RedactingWriter.write` only — `redact_secrets` in `core.py` stays strict `str ->
str` (unchanged, pinned Phase-5 contract per CONTEXT.md's explicit-NOT-in-scope list).

### Secret-non-leaking error messages (PR-02 / T-05-02)
**Source:** `yahir_reusable_bot/redact/registry.py` lines 191-204 (never interpolates raw pattern
source; uses `{rp!r}` which routes through `RedactionPattern`'s source-eliding `__repr__`)
**Apply to:** every raise/warn site in `sink.py` and `processor.py` — never echo a scrubbed value,
a raw pattern, or `patterns` contents in an error/warning message.

### Module-local test constants, no new fixtures (D-10)
**Source:** `tests/test_redact_core.py` line 30 (`SENTINEL = "SENTINELKEY_do_not_leak_123"`)
**Apply to:** all three new test files — reuse the same `SENTINEL` string literal (do not invent a
new one) unless a test specifically needs a distinct value (e.g. the D-56 dry-run probe's sentinel,
which RESEARCH.md's Open Question 1 recommends deriving separately and documenting as non-secret).

### Full-output aggregation, never single-call assertion (Pitfall 2)
**Source:** WeatherBot's `tests/test_redact_hygiene.py` (`capsys.readouterr().err` convention);
concrete `_CaptureDouble.all_output` pattern in RESEARCH.md lines 690-704
**Apply to:** every `test_redact_sink.py` assertion — `PrintLoggerFactory` emits 2 `write()` calls
per log line (body + trailing `"\n"`); a test asserting only the first call structurally cannot
prove absence of a secret.

### Decision-ID-cited docstrings (project house style)
**Source:** `yahir_reusable_bot/redact/core.py` and `registry.py` throughout (every non-trivial
docstring cites `D-NN`/`REDACT-NN`/`WR-NN`/`T-05-NN` inline)
**Apply to:** every new public class/function in `sink.py`, `processor.py`, and every new test
docstring — this phase's CONTEXT.md decisions (D-54 through D-60) are the citation set to draw
from.

## No Analog Found

None — every file in this phase has at least a role-match or better analog, either from Phase 5's
own module conventions or from WeatherBot's proven promotion source. `processor.py` is the closest
to novel (first `structlog` import under `redact/`), but RESEARCH.md supplies a verified, concrete
code shape in place of a codebase analog.

## Metadata

**Analog search scope:** `yahir_reusable_bot/redact/`, `tests/` (test_redact_*.py,
test_import_hygiene.py), `EXTENSION-GUIDE.md`, and the promotion source at
`/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` + `weatherbot/weather/client.py` +
`weatherbot/tests/test_redact_hygiene.py`.
**Files scanned:** `redact/core.py`, `redact/registry.py`, `redact/__init__.py`,
`tests/test_redact_core.py`, `tests/test_import_hygiene.py` (litmus section), `EXTENSION-GUIDE.md`
(SEAM table + sections 3-6), `weatherbot/__init__.py`.
**Pattern extraction date:** 2026-08-03
