# Phase 5: Redaction core + pattern registration - Pattern Map

**Mapped:** 2026-07-29
**Files analyzed:** 5 (2 source + 2 test + 1 `__init__.py`)
**Analogs found:** 5 / 5

## Naming trap — read this first

The hub already has a *command* `registry/` subpackage (`yahir_reusable_bot/registry/registry.py`,
SEAM-06) with a `CommandRegistry` class and `build_registry()` function. **`redact/registry.py` is
an unrelated, much smaller module at a distinct dotted path** (`yahir_reusable_bot.redact.registry`,
not `yahir_reusable_bot.registry.registry`). Do not import from, subclass, or structurally mirror
`CommandRegistry`'s class-based, multi-view design. The only thing to borrow from
`registry/registry.py` is the *shape of the idiom* — "fail loud inside a single validation pass,
before any derived state is computed" — applied here as a **single pure function**
(`register_patterns(patterns) -> tuple[RedactionPattern, ...]`), matching `build_registry`'s
free-function entry point, not `CommandRegistry`'s stateful class.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `yahir_reusable_bot/redact/__init__.py` | config (package re-export) | — | `yahir_reusable_bot/registry/__init__.py` (if present) — else any subpackage `__init__.py` re-exporting its two symbols | role-match |
| `yahir_reusable_bot/redact/core.py` (`RedactionPattern`, `redact_secrets`) | model + utility (pure transform) | transform (str→str) | `yahir_reusable_bot/registry/spec.py` (dataclass shape) + `WeatherBot/weatherbot/_redact.py` (the actual transform being generalized) | exact (behavior) / role-match (dataclass convention) |
| `yahir_reusable_bot/redact/registry.py` (`register_patterns`) | utility (validation/registration, NOT the command registry) | request-response (call-once, raise-or-return) | `yahir_reusable_bot/registry/registry.py`'s `build_registry` + validation loop; fail-loud precedent at `yahir_reusable_bot/discord/panelkit.py:180-185` | role-match |
| `tests/test_redact_core.py` | test | unit | `tests/test_registry.py` (house test style) + `WeatherBot/tests/test_redact_hygiene.py` (behavioral spec / boundary matrix) | exact |
| `tests/test_redact_registry.py` | test | unit | `tests/test_registry.py` (fail-loud `pytest.raises(ValueError)` idiom) | exact |

## Pattern Assignments

### `yahir_reusable_bot/redact/core.py` (model + utility, transform)

**Analog 1 — dataclass convention:** `yahir_reusable_bot/registry/spec.py`

**Frozen-dataclass pattern** (lines 39-54, `CommandSpec`):
```python
@dataclass(frozen=True)
class CommandSpec:
    """One registered command — the immutable, surface-agnostic spec."""

    name: str
    group: str
    summary: str
    bind: Callable[["DispatchContext"], Any]
    needs_flags: bool = False
```
Copy this exact shape for `RedactionPattern`: `@dataclass(frozen=True)`, a short docstring stating
the frozen/immutability guarantee, required fields first, defaulted fields last
(`skip_redos_check: bool = False` plays the same trailing-default-field role as `needs_flags`).

**Imports pattern** (lines 33-36, `spec.py`):
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
```
`redact/core.py` mirrors this exactly but swaps `typing.Callable` for `re` + `collections.abc.Sequence`
(per RESEARCH.md's stdlib-only Pattern 1/2 code).

**Analog 2 — the actual transform being generalized:** `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` (28 lines, read in full above)

**Core substitution pattern** (lines 23-28, verbatim parity target):
```python
_APPID_RX = re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE)


def redact_appid(text: str) -> str:
    """Replace every ``appid=<value>`` with ``appid=***``, preserving endpoint + status."""
    return _APPID_RX.sub(r"\1***", text)
```
This IS the pattern `RedactionPattern(pattern=_APPID_RX, replacement=r"\1***")` must reproduce
unchanged when registered by a future WeatherBot repin. Preserve the comment style documenting the
boundary character class (`[^&\s"'<>\\]+`) — that comment is load-bearing spec, not decoration; port
it into `redact/core.py`'s module or class docstring, generalized (no `appid` noun — litmus gate).

**Error handling:** None in this file — `redact_secrets` never raises (D-52: pure `str -> str`,
non-`str` triage explicitly deferred to Phase 6's seam). Do not add a try/except here.

**Validation:** None at the `core.py` level — all validation (ReDoS vetting) lives in
`registry.py`, never in `core.py`'s hot function (Pitfall 1: no `re.compile` may appear inside
`redact_secrets`).

---

### `yahir_reusable_bot/redact/registry.py` (`register_patterns`)

**Analog 1 — fail-loud-at-construction idiom:** `yahir_reusable_bot/registry/registry.py`

**Validation-loop-before-derived-state pattern** (lines 39-64, `CommandRegistry.__init__`):
```python
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    for spec in self.commands:
        if not spec.name or spec.name != spec.name.casefold():
            raise ValueError(
                f"CommandSpec.name must be non-empty and already casefolded "
                f"(match_command folds input, never spec.name); got {spec.name!r}"
            )
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    ...
```
Structural idiom to copy (NOT the class shape — `redact/registry.py` has no state to derive, so
this becomes a single function, not a class): validate every item in one loop, `raise ValueError`
naming the offending value via `!r`, **before** any downstream derivation/return happens. Map this
onto `register_patterns`'s loop over `patterns`, raising `ValueError` naming
`rp.pattern.pattern!r` on either vetting failure, mirroring RESEARCH.md's own sketch:
```python
def register_patterns(patterns):
    for rp in patterns:
        if rp.skip_redos_check:
            continue
        if _looks_pathological(rp.pattern) or _blows_budget(rp.pattern):
            raise ValueError(
                f"pattern rejected at registration — exceeds ReDoS wall-clock "
                f"budget or contains a nested-quantifier shape: {rp.pattern.pattern!r}"
            )
    return tuple(patterns)
```

**Free-function entry point convention** (lines 99-105, `build_registry`):
```python
def build_registry(specs: Iterable[CommandSpec]) -> CommandRegistry:
    """Build a :class:`CommandRegistry` from app-supplied ``specs`` (the app entry).

    ``specs`` is required — the module never holds a default command set; a reminder
    bot calls ``build_registry(its_own_specs)`` with its own handler closures.
    """
    return CommandRegistry(specs)
```
`register_patterns` should read as this module's equivalent public entry: a top-level function,
no default arg for `patterns` (required — matches D-49's "consumer explicitly hands zero patterns"
posture), returning a frozen collection, never mutating shared/module state (Pitfall 2/7 —
`register_patterns` must be pure, unlike a hypothetical stateful-registry copy of `CommandRegistry`).

**Analog 2 — fail-loud-at-construction, non-class-based:** `yahir_reusable_bot/discord/panelkit.py:180-185`
```python
if not marker or not marker.strip():
    raise ValueError(
        f"PanelKit marker must be a non-empty, non-whitespace string "
        f"(an empty marker makes cid.startswith(marker) match every "
        f"bot-authored pin); got {marker!r}"
    )
```
Copy the **comment-then-guard-then-raise** shape and the "explain WHY this raises here, not later"
inline-comment convention (see the comment block at lines 173-179 of `panelkit.py`, immediately
above this guard) for the docstring/inline comment preceding `register_patterns`'s ReDoS check —
this repo's established convention is to justify a `ValueError` raise site with a one-paragraph
"why this, why here, why ValueError not assert" comment, not just the raise itself.

**Error handling:** `ValueError` only, raised eagerly (never returned as a result object, never
logged-and-swallowed) — matches both analogs above. No try/except anywhere in this module.

---

### `tests/test_redact_core.py`

**Analog — house test-file style:** `tests/test_registry.py` (full file, 80+ lines read above)

**Structure to copy:**
- Module docstring names the requirement IDs it covers (REDACT-01, REDACT-06) and states the
  RED/self-proof reasoning explicitly, matching `test_registry.py`'s docstring (lines 1-19):
  which assertions are genuinely RED pre-fix vs. which would pass unchanged either way.
- A small private factory helper at module level (`_spec()` at line 29) — mirror this as a
  `_pattern()` or similar helper if repeated construction is needed across tests, or just inline
  `RedactionPattern(...)` directly per RESEARCH.md's Code Examples (both are this repo's house
  style; `test_registry.py` uses a factory because `CommandSpec` has more fields).
- Plain construction, no mocking library anywhere (`from __future__ import annotations`; only
  `pytest` + the module under test imported).

**Behavioral source — the actual assertions to port verbatim (adapted, no `appid` noun in
identifiers, but the STRING content of the assertions is allowed to reference the generic
mechanism):** `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`

**Boundary-case matrix** (lines 56-82, `test_redact_helper_boundaries` — 5 sub-assertions):
```python
def test_redact_helper_boundaries():
    real = f"for url 'x?lat=1&appid={SENTINEL}&units=imperial'"
    out = redact_appid(real)
    assert SENTINEL not in out
    assert "appid=***" in out
    assert "units=imperial" in out  # following params preserved

    out2 = redact_appid(f"appid={SENTINEL}&next=1")
    assert out2 == "appid=***&next=1"

    out3 = redact_appid("appid=A%2Fdef&units=x")
    assert out3 == "appid=***&units=x"

    out4 = redact_appid(f"...appid={SENTINEL}'")
    assert out4 == "...appid=***'"

    out5 = redact_appid(f"APPID={SENTINEL}&units=x")
    assert SENTINEL not in out5
    assert "units=x" in out5
```
Port this whole matrix into `test_redact_core.py`, calling `redact_secrets(text, (rp,))` with a
`RedactionPattern(pattern=re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE), replacement=r"\1***")`
constructed inline (litmus-clean: no `appid`-named identifier, just a string literal inside a test
body — the litmus gate scans `def`/`class`/param/annotation names, not string contents, so using
`"appid="` as test data text is fine, but do NOT name a test function/variable/param `appid_*`).

**Idempotence + zero-pattern no-op** — use RESEARCH.md's Code Examples section verbatim
(`test_redact_secrets_idempotent`, `test_redact_secrets_zero_patterns_is_identity`) — these are
already litmus-clean and directly testable against `core.py`.

**Literal-inside-repr() proof** — use RESEARCH.md's `test_literal_matches_inside_repr` sketch
verbatim (Code Examples section); this is the direct generalization of
`test_reraised_exception_request_carries_no_key` (lines 194-218 of `test_redact_hygiene.py`),
minus the httpx/exception machinery (Phase 6 seam concern, not this phase's).

**Frozen-dataclass immutability test** — mirror `test_registry.py`'s `pytest.raises(ValueError)`
idiom, but here it's `pytest.raises(dataclasses.FrozenInstanceError)`:
```python
def test_redaction_pattern_is_frozen():
    rp = RedactionPattern(pattern=re.compile(r"x"), replacement="y")
    with pytest.raises(FrozenInstanceError):
        rp.replacement = "z"
```

**Shared sentinel constant convention:** `test_redact_hygiene.py:29` — `SENTINEL = "SENTINELKEY_do_not_leak_123"`
at module level, not a fixture (per RESEARCH.md's Wave-0-gaps note: no new `conftest.py` fixtures
needed; a bare module-level constant is this repo's convention for shared test literals).

---

### `tests/test_redact_registry.py`

**Analog — fail-loud `pytest.raises(ValueError)` idiom:** `tests/test_registry.py` (lines 39-67)

```python
def test_empty_name_raises_at_construction():
    with pytest.raises(ValueError):
        CommandRegistry([_spec("")])


def test_empty_name_raises_through_build_registry():
    with pytest.raises(ValueError):
        build_registry([_spec("")])
```
Mirror this exact two-tier pattern for `register_patterns`: one test asserting the underlying
vetting check triggers, one confirming the raise actually propagates through the public entry
point (in this phase there is only one entry point — `register_patterns` itself — so this
collapses to a single assertion tier per RESEARCH.md's test map, e.g.
`test_register_patterns_rejects_catastrophic_pattern`).

**Regression / non-breaking-valid-input test** — mirror `test_valid_names_still_construct_without_regression`
(lines 70-80): after adding the ReDoS gate, a known-benign pattern (WeatherBot's real `_APPID_RX`,
per RESEARCH.md's Assumptions Log A1) must still pass registration unchanged —
`test_register_patterns_accepts_proven_appid_pattern`.

**`skip_redos_check` opt-out test** — new behavior with no direct prior-repo analog; construct
directly per RESEARCH.md's Architecture Pattern 3 code (`RedactionPattern(..., skip_redos_check=True)`
must bypass both the structural and timing checks even for an objectively pathological pattern —
prove the opt-out is genuinely load-bearing, not a no-op, by using a pattern that WOULD fail
vetting and confirming it's accepted only when the flag is set).

## Shared Patterns

### Fail-loud-at-registration (`ValueError`, never degrade)
**Sources:** `yahir_reusable_bot/registry/registry.py:52-57`, `yahir_reusable_bot/discord/panelkit.py:180-185`
**Apply to:** `redact/registry.py`'s `register_patterns` only. `redact/core.py`'s `redact_secrets`
must NEVER raise (D-52) — this is the one place in the phase where the fail-loud convention does
**not** apply; do not let planner or implementer accidentally add a raise to `core.py`.

### `@dataclass(frozen=True)` construction convention
**Source:** `yahir_reusable_bot/registry/spec.py:39-71` (`CommandSpec`, `DispatchContext`)
**Apply to:** `RedactionPattern` in `redact/core.py`.

### Hand-written-doubles-only test style, no mocking library
**Source:** `tests/conftest.py` module docstring (lines 9-19) + `tests/test_registry.py` (uses
zero mocks, only plain construction)
**Apply to:** Both new test files. Do not introduce `unittest.mock`/`pytest-mock`. No new
`conftest.py` fixtures are needed (RESEARCH.md Wave-0-gaps already confirms this) — module-level
constants (`SENTINEL`) suffice, per `test_redact_hygiene.py:29`'s precedent.

### Module-per-requirement-ID docstring convention
**Source:** `tests/test_registry.py:1-19`
**Apply to:** Both new test files — open with a docstring naming the REDACT-0x IDs covered and
explicitly stating which assertions are genuinely RED pre-fix (this repo's RED-first, two-commit
discipline per GATE-02, referenced in 05-CONTEXT.md's Established Patterns section).

## No Analog Found

None — every file in this phase's scope has a strong (exact or role-match) analog. The zero-new-
dependency, pure-stdlib nature of this phase (confirmed in RESEARCH.md) means no external-library
integration pattern needed to be sourced.

## Metadata

**Analog search scope:** `yahir_reusable_bot/registry/`, `yahir_reusable_bot/discord/panelkit.py`,
`tests/` (hub), `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py`,
`/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`.
**Files scanned:** 6 read in full, 1 (`test_import_hygiene.py`) partially (header + scope-note only,
per CONTEXT.md's confirmation no edits are needed there).
**Pattern extraction date:** 2026-07-29
