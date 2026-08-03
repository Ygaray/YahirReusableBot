# Phase 6: Insertion seams + provable backstop - Research

**Researched:** 2026-08-03
**Domain:** structlog insertion seams (sink wrapper + optional processor), wiring-time self-check,
concurrency-safe telemetry, for a reusable Python bot library
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

> Decision numbering continues the project-wide sequence. Phase 5 reached **D-53**, so Phase 6
> starts at **D-54**. All four gray areas were researched by parallel advisor agents and the user
> took every researched recommendation, plus one follow-up on test scope.

**Premise correction (read first):** `_LiveStderr` was never assigned to `sys.stderr`
process-wide — verified at `weatherbot/__init__.py:26-62`. It is only ever passed as
`structlog.PrintLoggerFactory(file=_LiveStderr())`. httpx's stdlib-`logging` INFO line (carries
the API key) bypasses the backstop entirely (`weatherbot/weather/client.py:48-54`). structlog-only
coverage is the status quo, not a reduction — D-54 makes broad coverage *possible*, not preserves it.

**D-54 (one primitive, two documented recipes — the hub never mutates process state itself):**
ship exactly one class, `RedactingWriter`, wrapping any file-like target. Recipe 1 (required):
pass it as structlog's render target (`PrintLoggerFactory(file=RedactingWriter(...))`). Recipe 2
(optional, broader): the consumer writes `sys.stderr = RedactingWriter(sys.stderr)` in their own
composition root, picking up stdlib-`logging`, stray `print()`, and third-party output. Rejected:
narrow-only (leaves the httpx-class gap undocumented); a hub-shipped global installer function
(the hub would be actively mutating process-wide state — collides with D-53).

**D-55 (both recipes are TESTED, not just documented):** ship a test that installs
`RedactingWriter` as a stand-in stream and asserts non-structlog output (bare `print()` /
stdlib-`logging`) comes out scrubbed. Rejected: documentation-only; dropping recipe 2 entirely.

**D-56 (introspection by default, opt-in in-memory dry-run probe; raises `ValueError`):**
`assert_redaction_active` reads `structlog.get_config()` and confirms the hub's own writer
(and/or processor, by identity) is installed. Raises on failure, returns/passes silently when
present. An opt-in deeper check asks the already-located live instance to scrub a fixed,
non-secret sentinel **in memory only** — never calling `.write()`. This opt-in path is also the
assertion mechanism for this phase's own seam integration tests. Rejected: introspection-only
(proves wiring, not behavior — an empty pattern set would pass); a real end-to-end canary through
the logger (needs its own transient global-state capture machinery — same fragility class as the
bug being guarded against).

> **⚠ Known coupling the planner must handle explicitly:** introspection reaches
> `PrintLoggerFactory._file` / `WriteLoggerFactory._file` — a **private** attribute. Verified
> present on installed `structlog` 26.1.0, but it is an implementation detail, not public API. It
> is also blind if the consumer nests `RedactingWriter` inside their own proxy (WeatherBot's own
> `_LiveStderr` is exactly this shape). The plan must decide how this degrades — a clear "could not
> verify" signal, never a false pass — and must not let a structlog rename fail silently.

**D-57 (hybrid: lock-guarded monotonic counter is the source of truth, optional push hook):**
`RedactingWriter` carries a counter the consumer can read off the instance, plus an optional
`on_redaction`-style callable fired from inside the same guarded increment (off by default). One
lock, one increment site. Monotonic for process lifetime — no reset-on-read. Composes with D-56:
`assert_redaction_active` already has to locate the live instance. Any consumer-supplied hook
runs on the write path and inherits D-52 — must be wrapped in a swallow-and-continue guard.

**D-58 (the counter counts CHANGED WRITES, not individual substitutions):** Exact substitution
counts require re-running every pattern with `.subn()` (roughly doubling regex cost on every log
line, forever) or a drift-prone second copy of the scrub loop. Counting writes where output !=
input is one string comparison, and answers the operational question REDACT-08 exists for.
**Requirements-wording note:** Phase 6 verification must NOT report a gap because the counter
reports changed writes rather than exact substitution counts — that is the locked contract.

**D-59 (use a `threading.Lock`, not `itertools.count`'s incidental atomicity):** the sink is
written concurrently by an APScheduler thread pool, the asyncio Discord gateway loop, and the main
thread. `itertools.count()`'s atomicity is a GIL-era implementation detail, not a documented
guarantee. A one-line lock removes the doubt.

**D-60 (loud docstring PLUS an ordering check folded into `assert_redaction_active`; it WARNS,
never raises):** the processor's docstring states the chain-order precondition loudly. Detection
rides inside D-56's self-check: `structlog.get_config()["processors"]` exposes the live chain, and
every built-in exception formatter is an `isinstance` of `structlog.processors.ExceptionRenderer`
— so "is redaction positioned before a formatter" is an index comparison. **Why warn, not raise:**
the sink (REDACT-04) catches tracebacks unconditionally regardless of processor order, so a
mis-ordered *optional, additive* processor is reduced defense-in-depth, not a security regression.
When no recognized formatter type is found (a custom formatter), emit a generic "could not verify
order" warning — never a false pass. Rejected: docstring-only (invisible-failure class persists);
a chain-builder helper returning a pre-ordered list (annexes composition-root policy).

### Claude's Discretion

- Module split within `redact/` for the new files (`sink.py` / `writer.py` for REDACT-04,
  `processor.py` for REDACT-05 — research proposed `sink.py` + `processor.py`).
- Exact public names, subject to the AST signature litmus (domain-noun-free) and to
  `RedactingWriter` / `assert_redaction_active` being fixed by the requirements themselves.
- The disablement parameter's exact name and signature position (D-53 locks only that it is an
  explicit constructor parameter, never an env read). **Default must be redaction ON.**
- The sentinel constant used by D-56's dry-run probe (must be a non-secret literal).
- Whether telemetry's optional hook receives the current count or no argument.
- How `EXTENSION-GUIDE.md` SEAM-08 is laid out within the guide's existing conventions.

### Deferred Ideas (OUT OF SCOPE)

- The httpx / stdlib-`logging` coverage gap in WeatherBot — hub-side, D-54's second recipe is the
  answer and is in scope. Actually *adopting* it in WeatherBot is a human-gated repin decision.
- `RedactionPattern.asdict()`/`astuple()` still expose the raw pattern source — Phase 5's WR-02
  residual, deliberately left open.
- A safe pattern-builder helper (constructing `name=value` patterns without hand-writing regex).
- Per-pattern replacement strings beyond the template mechanism; partial masking.
- Config-driven pattern loading.
- A chain-builder helper for processor ordering (rejected as D-60's third option).

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| REDACT-04 | `RedactingWriter` sink wrapper scrubs event fields **and** formatted tracebacks, renderer-agnostic, chain-order-independent | Verified live against structlog 26.1.0: `dev.ConsoleRenderer` self-renders `exc_info` straight to the output stream (see Common Pitfalls #1); `RedactingWriter` code example below; both-recipes test pattern verified (see Code Examples "Recipe 2 ordering caveat") |
| REDACT-05 | Optional structlog processor scrubs `event_dict` string values pre-render, chain-order precondition stated loudly in its own docstring | `redaction_processor` code example below; ordering check verified via `isinstance(p, structlog.processors.ExceptionRenderer)` — confirmed live that both `format_exc_info` and `dict_tracebacks` are instances of that class |
| REDACT-07 | `assert_redaction_active` fails loudly when the backstop is not installed; passes when it is | `assert_redaction_active` code example below, built on verified `structlog.get_config()`/`_file` introspection; degrade-path guidance for the private-attribute and nested-proxy blind spots |
| REDACT-08 | Redaction-count telemetry reports how many substitutions fired | `RedactingWriter` counter design (lock-guarded, D-58/D-59 compliant) in Code Examples |
| DOCS-04 | `EXTENSION-GUIDE.md` SEAM-08 row flipped to implemented, naming the architectural inversion | Section shape verified against the guide's existing SEAM-01..07 convention (see Architecture Patterns → SEAM-08 documentation shape) |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **One-way dependency, enforced by gate.** `redact/` may import stdlib and (in `processor.py`
  only) `structlog`. It must never import `weatherbot`/`weatherbot.*`, and — as architectural
  discipline, not a hard gate — should not import any sibling `yahir_reusable_bot` subpackage.
  `tests/test_import_hygiene.py` is the standing enforcement; this repo has **no** self-proof for a
  real app-package edge (the app package doesn't exist in this standalone repo), so the synthetic
  self-proofs are what actually prove the gate logic bites.
- **No domain nouns in the public surface.** Every `def`/`class`/param/annotation under `redact/`
  must avoid `weather|forecast|location|openweather|\buv\b|briefing` (case-insensitive,
  signature-only). `test_litmus_clean` already asserts `redact/`'s scanned-file coverage includes
  `core.py`/`registry.py` — Phase 6 must extend that assertion set to include `sink.py` and
  `processor.py` (see `tests/test_import_hygiene.py:290-296`), matching the existing
  `lifecycle`/`registry`/`discord` coverage-guard pattern.
- **The hub must never call `structlog.configure()`.** Every existing hub module calls only
  `structlog.get_logger(__name__)`. Standing, re-asserted in Phase 6's own CONTEXT.md.
- **Toolchain:** Python 3.12+, `uv`, `hatchling`. `structlog>=26.1.0` (exact-pinned version
  resolved: 26.1.0). Run tests: `uv run pytest`. Lint: `uv run ruff check`. Import-hygiene gate:
  `uv run pytest tests/test_import_hygiene.py`. Ships **no console script** — a library only.
- **Ecosystem repin discipline (`ECOSYSTEM.md` §3/§6):** version bump, tag, WeatherBot repin, and
  `_redact.py` deletion are human-gated — never performed by the workflow. Per §6, the promotion is
  not *done* until `EXTENSION-GUIDE.md`'s row flips — this is why DOCS-04 is phase-closing, not a
  nicety.

## Summary

Phase 5 shipped the pure scrubbing core (`redact_secrets`, `RedactionPattern`, `register_patterns`)
as a stdlib-only leaf. Phase 6 wires that core into a live structlog pipeline through exactly the
insertion seam WeatherBot's production incident (HARD-SEC-01/F12) proved is load-bearing: a
file-like sink wrapper (`RedactingWriter`) intercepting the *fully rendered* text — event fields
and formatted tracebacks fused into one `write()` call — regardless of processor-chain order or
renderer choice. This was independently re-verified in this session by running structlog 26.1.0
live: `dev.ConsoleRenderer.__call__` formats `exc_info` directly to its output buffer even with
**zero** exception-formatting processors in the chain, so a processor-only design structurally
cannot see it. The processor (`redaction_processor`) is real, valuable, additive coverage for
structured `event_dict` fields — but its traceback coverage is conditional on chain order, verified
live via `isinstance(structlog.processors.format_exc_info, structlog.processors.ExceptionRenderer)
== True` (same for `dict_tracebacks`), which is exactly the mechanism `assert_redaction_active`'s
ordering check can use.

The two remaining requirements — `assert_redaction_active` (REDACT-07) and telemetry (REDACT-08) —
compose naturally on top of `RedactingWriter`: the self-check introspects
`structlog.get_config()["logger_factory"]._file` (verified live: this private attribute exists on
both `PrintLoggerFactory` and `WriteLoggerFactory` in 26.1.0, and holds exactly the object passed
as `file=...` at configure time), and the counter is a `threading.Lock`-guarded field on the same
instance the self-check already has to locate. `pyproject.toml` pins `structlog>=26.1.0` with **no
upper bound**, so this private-attribute coupling is a standing fragility the self-check's error
messages must surface loudly (never silently pass) if a future structlog release renames it.

**Primary recommendation:** build `RedactingWriter` first and prove it with an adversarial
`logger.exception(...)` test asserting against the *full captured output* (aggregating every
`write()` call in the assertion window — verified live that `PrintLoggerFactory` calls `.write()`
twice per emission, body then trailing `"\n"`, so a test capturing only the first call would miss a
secret that happened to land in a later call). Build `assert_redaction_active` and telemetry next
(they share the sink instance). Build `redaction_processor` last, explicitly documented as
non-substitutable defense-in-depth. Close with `EXTENSION-GUIDE.md` SEAM-08.

## Architectural Responsibility Map

This project is a library + consumer-composition-root architecture, not a web tier stack — the
table below maps capabilities to that shape instead of browser/API/CDN tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|-----------------|-----------|
| Fully-rendered text scrubbing (event + traceback) | Consumer composition root (wires hub's `RedactingWriter` into its own `PrintLoggerFactory(file=...)` / `WriteLoggerFactory(file=...)`) | Hub library (`redact/sink.py` supplies the mechanism) | The mechanism is generic hub code; the *installation* is always a line in the consumer's own `structlog.configure()` call — CLAUDE.md's hub-never-configures rule |
| Structured `event_dict` field scrubbing | Consumer's own processor chain (hub's `redaction_processor` appended to `processors=[...]`) | Hub library (`redact/processor.py`) | Additive, optional; the consumer decides chain position, the hub only documents the precondition |
| Broad stdlib-`logging` / bare-`print()` coverage | Consumer composition root (`sys.stderr = RedactingWriter(sys.stderr)`, wired **before** any stdlib logging handler is constructed — see Common Pitfalls #7) | OS process stream (`sys.stderr`) | Zero hub-owned process mutation (D-54); the consumer's own visible line of code performs it |
| Wiring-time proof the backstop is installed | Hub library (`redact/sink.py` or a new `redact/verify.py`, `assert_redaction_active`) | Consumer composition root (calls it once at boot, or mid-run) | Introspects the consumer's live `structlog.get_config()` — hub owns the check logic, consumer owns triggering it |
| Redaction-count telemetry | Hub library (`RedactingWriter` instance field) | Consumer (reads `.redaction_count` / supplies `on_redaction`) | Lives on the exact sink object the consumer already constructed and holds a reference to — no separate wiring |
| Documentation of the seam (DOCS-04) | Project docs (`EXTENSION-GUIDE.md`) | — | Not code; closes the promotion per `ECOSYSTEM.md` §6 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `structlog` | 26.1.0 (pinned `>=26.1.0`, no upper bound) `[VERIFIED: live introspection, this repo's venv]` | Processor chain + `PrintLoggerFactory`/`WriteLoggerFactory` sink target — the two insertion seams this phase wires | Already the hub's sole logging dependency; zero new dependency for this phase, matching Phase 5's milestone-level verdict `[VERIFIED: this repo's uv.lock + pyproject.toml]` |
| stdlib `re`, `threading` | bundled, Python 3.12+ | `RedactionPattern.pattern.sub` (already exists from Phase 5); `threading.Lock` for the telemetry counter (D-59) | No new dependency; `threading.Lock` is the correct primitive for a field mutated from an APScheduler thread pool, the asyncio gateway loop, and the main thread simultaneously |

**Version verification (2026-08-03):**
```
$ uv run python3 -c "import structlog; print(structlog.__version__)"
26.1.0
```
`[VERIFIED: live execution against installed package, this session]`

### Supporting

None. This phase adds zero new runtime dependencies. `structlog.testing` (stdlib-adjacent, ships
inside the `structlog` package) is relevant only as an **anti-pattern to avoid** for this phase's
own tests — see Common Pitfalls #4.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A hand-rolled `sys.meta_path`/monkeypatch-based global install helper | `sys.stderr = RedactingWriter(sys.stderr)` as a consumer-owned line | The hub performing a process-wide mutation on its own initiative was explicitly rejected (D-54) — it collides with D-53's "a library must not silently change security-relevant ambient state" and duplicates what the consumer's own one-line assignment already achieves for free |
| Real end-to-end canary log line through the configured logger for `assert_redaction_active`'s deep check | An in-memory-only scrub of a fixed sentinel, never calling `.write()` | Rejected (D-56): needs the same transient global-state capture machinery that's the fragility class this backstop exists to guard against, and a broken backstop could make the sentinel genuinely reach real output |

**Installation:** none — `structlog` is already an installed, pinned dependency.
`uv pip show structlog` confirms `26.1.0` present in `.venv`.

## Package Legitimacy Audit

**Not applicable.** This phase introduces zero new external packages. `structlog` is an existing,
already-verified hub dependency (Phase 5's `STACK.md` research audited it; re-confirmed live this
session at version 26.1.0). No `package-legitimacy check` run was needed — there is no package to
audit.

## Architecture Patterns

### System Architecture Diagram

```
Consumer's own domain code
    │  (builds a request/response/exception that may embed a secret — out of hub scope)
    ▼
log = structlog.get_logger(__name__)
log.warning(event, **fields)  /  log.exception(...)  [exc_info propagates]
    │
    ▼
Consumer's OWN processor chain (structlog.configure(processors=[...]))
    │
    ├──[OPTIONAL, ADDITIVE]── redact.processor.redaction_processor
    │     scrubs event_dict STRING VALUES here, pre-render.
    │     Traceback coverage ONLY if placed AFTER an ExceptionRenderer
    │     instance (format_exc_info / dict_tracebacks) in this SAME chain —
    │     verified live: both are isinstance(..., ExceptionRenderer).
    │     If the renderer self-formats exc_info (e.g. dev.ConsoleRenderer with
    │     NO exception-formatting processor at all), this seam sees NOTHING —
    │     verified live, reproduced empirically this session.
    ▼
Renderer (ConsoleRenderer / JSONRenderer / KeyValueRenderer / LogfmtRenderer)
    renders event + fields + any traceback into ONE text blob
    (dev.ConsoleRenderer formats a self-owned traceback here, bypassing
    event_dict entirely, REGARDLESS of processor order)
    ▼
structlog.PrintLoggerFactory(file=<target>) / WriteLoggerFactory(file=<target>)
    calls <target>.write(rendered_text)     [PrintLoggerFactory: 2 calls per
                                              emission — body, then "\n";
                                              WriteLoggerFactory: 1 call —
                                              verified live this session]
    │
    └──[REQUIRED, LOAD-BEARING]── redact.sink.RedactingWriter
          wraps <target>. Intercepts the FULLY RENDERED text — event fields
          AND formatted traceback are GUARANTEED to be in this string
          regardless of which processor/renderer produced it. Scrubs via
          redact_secrets(text, patterns), forwards to the real target.
          Non-str/bytes triage (D-52) lives HERE, not in redact_secrets.
          Increments the D-59 lock-guarded counter on any changed write.
    ▼
Real stream (sys.stderr / a file / a pytest capsys-captured buffer)
    ▼
Terminal / systemd journal / log file — scrubbed text only

── OPTIONAL BROADER RECIPE (D-54 recipe 2), a SEPARATE data path ──

Consumer's composition root, EARLY (before constructing any stdlib logging
handler — see Common Pitfalls #7):
    sys.stderr = redact.sink.RedactingWriter(sys.stderr, patterns)
        │
        ├── stdlib `logging.basicConfig()` default StreamHandler resolves
        │   sys.stderr AT CALL TIME → picks up the wrapped stream
        ├── a bare print(...) anywhere in the process
        └── a third-party library's own logging (e.g. httpx's INFO line
            carrying appid=<key> in its request URL — the exact WeatherBot
            gap this recipe closes)
    all route through the SAME RedactingWriter.write(), scrubbed identically

── WIRING-TIME PROOF (REDACT-07), a read-only side channel ──

Consumer calls redact.assert_redaction_active() once at boot (or mid-run):
    reads structlog.get_config()["logger_factory"]
        → isinstance check: PrintLoggerFactory / WriteLoggerFactory?
        → factory._file  (verified-present PRIVATE attribute, 26.1.0)
        → isinstance check: RedactingWriter?
    ALSO checks structlog.get_config()["processors"] for redaction_processor
    position relative to the first ExceptionRenderer instance (D-60, WARN only)
    RAISES ValueError on any inconclusive or negative result — never a false pass
```

### Recommended Project Structure

```
yahir_reusable_bot/redact/
├── __init__.py       # extend Phase 5's re-exports: add RedactingWriter,
│                      # assert_redaction_active, redaction_processor
├── core.py            # UNCHANGED (Phase 5) — redact_secrets, RedactionPattern
├── registry.py         # UNCHANGED (Phase 5) — register_patterns
├── sink.py             # NEW — RedactingWriter (REDACT-04), telemetry counter
│                        #       (REDACT-08); assert_redaction_active (REDACT-07)
│                        #       is a strong candidate to co-locate here since
│                        #       it introspects the SAME RedactingWriter type —
│                        #       see Claude's Discretion (module split)
└── processor.py         # NEW — redaction_processor (REDACT-05); the ONE module
                          #       under redact/ allowed to import structlog
                          #       (its processor calling-convention signature IS
                          #       the structlog dependency; sink.py's `.write()`
                          #       duck-type does NOT need it — verified: nothing
                          #       in RedactingWriter's contract requires
                          #       importing structlog, only file-like duck typing)
```

### Pattern 1: RedactingWriter — the load-bearing sink

**What:** a file-like proxy wrapping any object exposing `.write()`/`.flush()`.
**When to use:** always — this is the required piece (REDACT-04). Wire it as the structlog
`logger_factory`'s `file=` target (recipe 1) and/or as a `sys.stderr` replacement (recipe 2).

```python
# yahir_reusable_bot/redact/sink.py
from __future__ import annotations

import threading
from collections.abc import Callable, Sequence

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets


class RedactingWriter:
    """Wraps ANY file-like target; scrubs every write() call before forwarding.

    Renderer-agnostic BY CONSTRUCTION: this class never inspects event_dict —
    it only ever sees the text a renderer has already produced. Verified
    (this session, structlog 26.1.0) that dev.ConsoleRenderer self-renders a
    formatted traceback straight into the SAME write() call as the event
    line, with zero exception-formatting processors in the chain. This is
    why the sink, not the processor, is the requirement's load-bearing piece.
    """

    def __init__(
        self,
        target: object,
        patterns: Sequence[RedactionPattern],
        *,
        enabled: bool = True,  # D-53: explicit param, default ON, never env-read
        on_redaction: Callable[[int], None] | None = None,  # D-57, off by default
    ) -> None:
        self._target = target
        self._patterns = patterns
        self._enabled = enabled
        self._on_redaction = on_redaction
        self._lock = threading.Lock()  # D-59: real lock, GIL atomicity is not a contract
        self._count = 0

    def write(self, data: object) -> int:
        # D-52: non-str triage lives at THIS seam (matches proven _LiveStderr.write).
        if isinstance(data, bytes):
            data = data.decode("utf-8", "replace")
        if isinstance(data, str) and self._enabled and self._patterns:
            scrubbed = redact_secrets(data, self._patterns)
            if scrubbed != data:  # D-58: count CHANGED WRITES, not substitutions
                with self._lock:
                    self._count += 1
                    current = self._count
                hook = self._on_redaction
                if hook is not None:
                    try:  # D-52/D-57: swallow-and-continue on the hot path
                        hook(current)
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

**Recipe 1 (required):**
```python
structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(
        file=RedactingWriter(sys.stderr, patterns)
    ),
)
```

**Recipe 2 (optional, broader — must run EARLY, see Common Pitfalls #7):**
```python
sys.stderr = RedactingWriter(sys.stderr, patterns)
# then, and only then:
logging.basicConfig(...)
```

### Pattern 2: redaction_processor — additive, chain-order-sensitive

**What:** a standard-signature structlog processor scrubbing string `event_dict` values.
**When to use:** as an ADDITIONAL layer, never a substitute for `RedactingWriter`.

```python
# yahir_reusable_bot/redact/processor.py
from __future__ import annotations

from collections.abc import Sequence

from yahir_reusable_bot.redact.core import RedactionPattern, redact_secrets


def redaction_processor(patterns: Sequence[RedactionPattern]):
    """Returns a structlog processor scrubbing string event_dict values (REDACT-05).

    ⚠ CHAIN-ORDER PRECONDITION: place this AFTER any exception formatter
    (structlog.processors.format_exc_info / dict_tracebacks / any
    structlog.processors.ExceptionRenderer instance) in your processors=[...]
    list, or it never sees traceback text — exc_info is still a live
    (type, value, traceback) tuple, not a string, until an ExceptionRenderer
    runs. Verified (structlog 26.1.0): both format_exc_info and
    dict_tracebacks ARE ExceptionRenderer instances.

    ⚠ EVEN CORRECTLY ORDERED, this processor is NOT sufficient alone: some
    renderers (dev.ConsoleRenderer) format exc_info directly into their own
    output buffer, bypassing event_dict regardless of where THIS processor
    sits. RedactingWriter (redact.sink) is the load-bearing backstop; this
    processor is additive defense-in-depth for structured-log consumers that
    want field-level scrubbing before serialization.
    """

    def _processor(logger, method_name, event_dict):
        for key, value in event_dict.items():
            if isinstance(value, str):
                event_dict[key] = redact_secrets(value, patterns)
        return event_dict

    return _processor
```

### Pattern 3: assert_redaction_active — wiring-time self-check

**What:** introspects the consumer's live `structlog.get_config()` to prove the writer is
actually installed (REDACT-07), and warns (never raises) if the optional processor is mis-ordered
relative to the exception formatters (D-60).

```python
# candidate location: redact/sink.py (co-located with RedactingWriter, whose
# type identity it checks) — see Claude's Discretion on module split
from __future__ import annotations

import warnings

import structlog

from yahir_reusable_bot.redact.sink import RedactingWriter


def assert_redaction_active() -> None:
    """Prove the hub's RedactingWriter is installed in the LIVE structlog
    configuration (REDACT-07). Raises ValueError on ANY inconclusive or
    negative result — never a false pass (D-56). Also WARNS (never raises,
    D-60) if an optional redaction processor is present but positioned
    before every recognized exception formatter in the chain.

    KNOWN COUPLING: introspects PrintLoggerFactory._file / WriteLoggerFactory
    ._file, a PRIVATE attribute. Verified present on structlog 26.1.0. This
    repo pins structlog>=26.1.0 with NO upper bound — a future release that
    renames/removes this attribute must surface as a LOUD, distinct error
    here, never a silent pass.

    KNOWN BLIND SPOT: cannot see through a consumer's own proxy nested
    around RedactingWriter (e.g. a lazy sys.stderr resolver of the
    _LiveStderr shape). Surfaces as the same "could not verify" ValueError
    as a genuinely missing writer — see RESEARCH.md Open Questions.
    """
    factory = structlog.get_config()["logger_factory"]
    if not isinstance(
        factory, (structlog.PrintLoggerFactory, structlog.WriteLoggerFactory)
    ):
        raise ValueError(
            f"could not verify redaction is active: logger_factory is "
            f"{type(factory).__name__}, not PrintLoggerFactory/"
            f"WriteLoggerFactory — assert_redaction_active only knows how to "
            f"introspect these two factory types"
        )
    if not hasattr(factory, "_file"):
        raise ValueError(
            f"could not verify redaction is active: structlog "
            f"{structlog.__version__}'s {type(factory).__name__} no longer "
            f"exposes a private `_file` attribute — this introspection is "
            f"coupled to a structlog implementation detail that changed; "
            f"revisit against the installed version"
        )
    target = factory._file
    if not isinstance(target, RedactingWriter):
        raise ValueError(
            f"could not verify redaction is active: the configured "
            f"logger_factory's file target is {type(target).__name__}, not "
            f"RedactingWriter. If RedactingWriter is wrapped inside your own "
            f"proxy, assert_redaction_active cannot see through it — wrap "
            f"sys.stderr with RedactingWriter FIRST, then wrap that in any "
            f"additional proxy your project needs."
        )
    _warn_if_processor_misordered()


def _warn_if_processor_misordered() -> None:
    processors = structlog.get_config()["processors"]
    # ... locate the redaction processor by identity/type, locate the first
    # structlog.processors.ExceptionRenderer instance, compare indices.
    # Emit warnings.warn(...) — never raise (D-60). If no ExceptionRenderer
    # instance is found at all, warn "could not verify order" — never a
    # false pass, but also never a hard failure for an optional component.
```

`[VERIFIED: live structlog 26.1.0 introspection, this repo's venv, this session]` for:
`structlog.get_config()` returns a dict with a `logger_factory` key; a freshly-constructed
`PrintLoggerFactory()`/`WriteLoggerFactory()` both expose `_file`; `structlog.processors.format_exc_info`
and `structlog.processors.dict_tracebacks` are both `isinstance(..., structlog.processors.ExceptionRenderer)`.

### SEAM-08 documentation shape (DOCS-04)

`EXTENSION-GUIDE.md`'s summary table (`| Plug point | Seam | Status | What ships today | Deferred |`)
gets one new row; a new numbered section follows the existing SEAM-01..07 convention exactly (a
`**Source:**` line, implemented/deferred split). One structural note the section must state
explicitly (per the milestone's own `ARCHITECTURE.md`, still valid): SEAM-08 is architecturally
**inverted** relative to every other seam in the guide — SEAM-01/03/05/06/07 are "the host
implements a Protocol the hub calls"; SEAM-08 is "the hub provides callable mechanism + a
registration API the host wires into its OWN `structlog.configure()`." Call this out so a future
reader does not go looking for a `Redactor` Protocol that does not exist. `SEAM-02` stays absent
with no explanation (pre-existing gap, not this phase's concern) — `08` is the next free number.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Concurrency-safe counting | A lock-free counter relying on `itertools.count()` or plain `int +=` | `threading.Lock` around the increment (D-59) | The sink is written from an APScheduler thread pool, the asyncio gateway loop, and the main thread simultaneously; `int +=`'s atomicity under the GIL is an implementation detail, not a contract, and free-threaded Python builds are exactly where it stops holding |
| Global process-wide redaction install | A hub-owned `setup_logging()`/`install_redaction()` helper that mutates `sys.stderr` on its own initiative | The consumer's own `sys.stderr = RedactingWriter(sys.stderr)` line (D-54) | Explicitly rejected — a library performing a process-wide, security-relevant mutation on its own is unauditable and collides with D-53's "no ambient-state security toggles" |
| A real end-to-end canary log for the deep self-check | Configuring a temporary capture stream, emitting a real log line through the live logger, and asserting on captured output | The in-memory-only scrub (D-56) that never calls `.write()` | The real-canary approach needs its own transient global-state capture machinery — structurally the same fragility class as the bug being guarded against — and a genuinely broken backstop would let the sentinel reach real output |
| Exception-formatter detection for the D-60 ordering check | A hardcoded list of known formatter function names/types that must be manually kept in sync with structlog releases | `isinstance(p, structlog.processors.ExceptionRenderer)` | Verified live: both shipped formatters (`format_exc_info`, `dict_tracebacks`) are instances of this one public class — a single `isinstance` check covers both today and any future built-in formatter following the same shape |

**Key insight:** every hand-rolled temptation in this phase (a global installer, a real-canary
check, a hardcoded formatter list) fails for the same underlying reason — it re-introduces the
exact class of transient/ambient global-state fragility this backstop exists to eliminate. The
disciplined alternative in each case is either "make the consumer's own explicit line of code do
it" or "use structlog's own stable type system to introspect, rather than a name list."

## Common Pitfalls

### Pitfall 1: `dev.ConsoleRenderer` self-renders tracebacks, bypassing `event_dict` entirely

**What goes wrong:** A redaction mechanism built as a processor alone never sees a
`logger.exception(...)` traceback if the renderer formats it internally.
**Why it happens:** `ConsoleRenderer.__call__` calls its own `exception_formatter` directly on
`sio` (the output buffer) whenever `exc_info` is present in `event_dict` — regardless of whether
any prior processor already turned `exc_info` into a string.
**Verified this session (live, structlog 26.1.0):** configured a chain with **zero**
exception-formatting processors (`processors=[dev.ConsoleRenderer(colors=False)]`), called
`log.exception("boom", field=...)`, and the fully-formatted traceback still appeared in the
captured `write()` output — bypassing `event_dict` completely.
**How to avoid:** `RedactingWriter` must be the load-bearing backstop; `redaction_processor` is
additive only. Test both: an adversarial `logger.exception(...)` through a sink-wrapped
`PrintLoggerFactory`, and separately through a processor-only configuration (which should be shown
to still leak — a negative-case test proving the processor-alone gap, matching the requirement's
own coverage note).
**Warning signs:** A test suite that only exercises `logger.<level>(msg, key=value)`, never
`logger.exception(...)`.

### Pitfall 2: A single log emission spans multiple `write()` calls — capture must aggregate

**What goes wrong:** A test asserting on a single `write()` call's contents (or a hand-rolled
capture double that only stores the last call) can miss a secret that landed in a different call.
**Verified this session (live):** with `PrintLoggerFactory`, `log.exception(...)` produced **two**
`write()` calls per emission — the full event+field+traceback body, then a separate trailing
`"\n"`. `WriteLoggerFactory` produced exactly **one** call (`self._write(message + "\n")` in a
single invocation — read directly from `structlog._output.WriteLogger.msg` source).
**How to avoid:** the phase's own success criterion is explicit about this ("asserted against the
full captured output"). Tests must aggregate every `write()` call within the assertion window
(e.g. `capsys.readouterr().err`, or a hand-written double appending every call to a list and
joining), never assert against a single intercepted call. This matches WeatherBot's own proven
test convention (`test_redact_hygiene.py` uses `capsys.readouterr().err` throughout).
**Warning signs:** A capture double with a `.last_write` attribute instead of an accumulating list.

### Pitfall 3: A boundary-class regex can under-redact when the secret contains a JSON-escaped delimiter character

**What goes wrong:** A `name=value`-shaped pattern whose value-boundary character class excludes
`"` and `\` (WeatherBot's proven shape: `[^&\s"'<>\\]+`) will stop matching at the FIRST literal
backslash it encounters in already-JSON-rendered text — including a JSON escape sequence produced
by `json.dumps`/`JSONRenderer` when the secret value itself contains a quote or backslash character.
**Verified this session (live):** rendered `{"url": "...appid=SEC\"RET&units=x", ...}` via
`JSONRenderer` (secret value deliberately containing an embedded `"`), applied the exact WeatherBot
boundary-class pattern, and the result was `appid=***\"RET&units=x` — **the JSON stays
syntactically valid** (`json.loads` succeeds, satisfying the phase's literal round-trip
requirement) but only `SEC` was replaced; `RET` — part of the original secret — survived unredacted
in the output.
**Why it happens:** the boundary character class was authored against a query-string shape, not a
JSON-escaped shape; a secret containing a quote or backslash is genuinely rare for typical API-key
shapes, but not impossible.
**How to avoid:** for the phase's own JSON-round-trip test (success criterion 1), choose a sentinel
value with no embedded quote/backslash — this proves the structural claim (redaction doesn't break
JSON syntax) without conflating it with a different, separate concern (whether a boundary-class
pattern fully redacts a secret containing its own delimiter characters). Document the latter as a
known limitation of `name=value`-shaped patterns in the pattern-authoring guidance, not as a Phase
6 defect — literal-value mode (`RedactionPattern.literal`, shipped Phase 5) sidesteps this
entirely since it matches the value verbatim regardless of surrounding delimiters.
**Warning signs:** A JSON round-trip test using a sentinel containing `"` or `\` without separately
asserting on the redaction completeness of that specific case.

### Pitfall 4: `structlog.testing.capture_logs` disables the renderer entirely — wrong tool for this phase's tests

**What goes wrong:** `structlog.testing.capture_logs()` (read directly from source this session)
clears the configured `processors` list, appends a `LogCapture` collecting raw `event_dict`
snapshots, and yields those — it never runs the renderer or the `logger_factory`/sink at all.
**Why it's tempting:** it's the structlog-blessed testing helper and shows up first in
`structlog.testing`'s public surface.
**How to avoid:** never use it for REDACT-04/05/07/08 tests — it structurally cannot exercise
`RedactingWriter` (there is no render step, no `.write()` call). Use a real `structlog.configure()`
with a capture double as the `file=` target (matching WeatherBot's own `capsys`-based convention),
exactly as this repo's `EXTENSION-GUIDE.md`/`test_redact_hygiene.py` precedent already does.
**Warning signs:** a sink test importing `from structlog.testing import capture_logs`.

### Pitfall 5: `assert_redaction_active`'s private-attribute coupling has no upper version pin to catch drift

**What goes wrong:** `pyproject.toml` pins `structlog>=26.1.0` with **no upper bound**
`[VERIFIED: direct file read, pyproject.toml:12]`. If a future structlog release renames or removes
`PrintLoggerFactory._file`/`WriteLoggerFactory._file`, `uv lock --upgrade` could silently pull in a
version where `assert_redaction_active`'s introspection breaks — with no test in *this* repo
pinned to a specific structlog version to catch it before it reaches a consumer.
**How to avoid:** the `hasattr(factory, "_file")` check in the code example above must raise a
clearly distinct error message (naming `structlog.__version__` and the missing attribute) rather
than falling through to the generic "not RedactingWriter" branch — a future maintainer debugging a
raised `assert_redaction_active` needs to immediately distinguish "structlog changed" from "the
consumer forgot to wire the sink." This is exactly the CONTEXT.md instruction: "must not let a
structlog rename fail silently."
**Warning signs:** a single generic `except AttributeError: raise ValueError("not installed")`
that collapses both failure classes into one message.

### Pitfall 6: The `sys.stderr` replacement recipe only protects handlers constructed AFTER the swap

**What goes wrong:** `logging.StreamHandler()` (and `logging.basicConfig()`'s default handler)
resolves `sys.stderr` **at construction time**, not lazily on every write. If a consumer's own code
(or a third-party library imported earlier) already constructed a `StreamHandler` bound to the
original `sys.stderr` object before the swap, reassigning `sys.stderr = RedactingWriter(...)`
afterward does **not** retroactively redirect that already-bound handler.
**Verified this session (live):** confirmed the swap DOES work correctly when performed before
`logging.basicConfig()` runs (the default handler resolves `sys.stderr` dynamically at
`basicConfig()` call time, not at import time) — but this ordering dependency is real and easy to
get backwards, and is exactly the class of bug that produced WeatherBot's original httpx gap
(`logging.getLogger("httpx")`'s handler chain resolves through `basicConfig`, which was configured
independently of any redaction wrapper).
**How to avoid:** `EXTENSION-GUIDE.md`'s SEAM-08 recipe-2 documentation must instruct: perform the
`sys.stderr = RedactingWriter(sys.stderr)` swap as early as possible in the composition root —
before any stdlib `logging` configuration call and before importing any third-party library that
might construct its own handler at import time.
**Warning signs:** D-55's own recipe-2 test passing in isolation (a fresh process, nothing else
touched `sys.stderr` first) while a real consumer's ordering differs.

### Pitfall 7: A second `structlog.configure()` call silently drops the backstop unless anchored to a shared object

**What goes wrong:** if the sink is constructed fresh at each of a consumer's independent
`structlog.configure()` call sites (WeatherBot has two: `__init__.py` and `cli.py`), a reconfigure
missing the wrapper produces unredacted logs with no error.
**How to avoid:** `assert_redaction_active` exists precisely to catch this — call it once at boot
AND, per REDACT-07's own success criterion, after any reconfigure that might drop it. This is a
consumer-discipline concern the hub cannot structurally prevent (structlog's `configure()` is
global mutable state by design), only make loudly checkable.
**Warning signs:** redaction working in the hub's own unit tests (which construct a fresh logger
per test) but never exercised against a consumer's actual multi-entry-point configuration.

## Code Examples

### Adversarial full-traceback test pattern (verified structure, not asserting specific names)

```python
# Verified this session: PrintLoggerFactory + dev.ConsoleRenderer + NO exception-
# formatting processor in the chain still renders the full traceback into the
# SAME write() call as the event line. A double MUST aggregate all write() calls.
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


def test_sink_scrubs_full_rendered_traceback():
    capture = _CaptureDouble()
    pattern = RedactionPattern.literal(SENTINEL)
    structlog.configure(
        processors=[dev.ConsoleRenderer(colors=False)],  # deliberately NO
        # format_exc_info/dict_tracebacks — proves the SINK catches the
        # traceback even when the processor chain structurally cannot.
        logger_factory=structlog.PrintLoggerFactory(
            file=RedactingWriter(capture, (pattern,))
        ),
        cache_logger_on_first_use=False,
    )
    log = structlog.get_logger("t")
    try:
        raise ValueError(f"secret={SENTINEL}")
    except ValueError:
        log.exception("boom", field=f"appid={SENTINEL}")

    # Full captured output, NEVER str(exc) alone (matches success criterion 1).
    assert SENTINEL not in capture.all_output
```

### JSON round-trip test pattern (success criterion 1, second half)

```python
def test_sink_scrubbed_json_line_round_trips():
    capture = _CaptureDouble()
    # A boundary-class pattern (NOT a literal containing quote/backslash —
    # see Pitfall 3) is the right choice for THIS specific assertion.
    pattern = RedactionPattern(
        pattern=re.compile(r'("appid": ")[^"]+', re.IGNORECASE),
        replacement=r"\1***",
    )
    structlog.configure(
        processors=[structlog.processors.JSONRenderer()],
        logger_factory=structlog.PrintLoggerFactory(
            file=RedactingWriter(capture, (pattern,))
        ),
        cache_logger_on_first_use=False,
    )
    structlog.get_logger("t").warning("leak", appid=SENTINEL, units="imperial")
    line = capture.pieces[0]  # the JSON body, before the trailing "\n" write
    assert SENTINEL not in line
    parsed = json.loads(line)  # must not raise — the load-bearing assertion
    assert parsed["units"] == "imperial"  # D-03-style diagnosability check
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---------------|--------------------|----------------|--------|
| WeatherBot's app-local, single-hardcoded-pattern `_LiveStderr.write()` scrubbing exactly one `appid=<key>` regex | Generic hub `RedactingWriter` accepting any `Sequence[RedactionPattern]`, N consumers, N pattern sets | This phase (Phase 6, PC-01) | The mechanism generalizes; the proven boundary-safety and non-`str` tolerance behavior is preserved exactly, not reinvented |
| A processor-chain-only mental model ("structlog-idiomatic" — add to `processors=[...]` and done) | Sink-primary, processor-secondary — the sink is the requirement's load-bearing piece | Confirmed by this milestone's own research (Phase 5 `PITFALLS.md`) and re-verified live this session | A processor-only redaction design would pass a naive smoke test (`logger.warning(msg, key=value)`) while silently missing every `logger.exception(...)` traceback under `dev.ConsoleRenderer` |

**Deprecated/outdated:** none introduced by this phase. `structlog.threadlocal` (deprecated since
22.1.0, superseded by `contextvars`) and `better-exceptions` support (deprecated in 26.x) are both
unrelated to this phase's insertion seams — noted here only to confirm neither is accidentally
relevant to `RedactingWriter`/`redaction_processor`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | The recommended mitigation for `assert_redaction_active`'s nested-proxy blind spot (hard-raise with a documented limitation, rather than attempting to unwrap one level of a conventional proxy attribute) is the right tradeoff | Architecture Patterns → Pattern 3; Open Questions | If a future consumer routinely nests `RedactingWriter` inside a lazy-stream-resolving proxy (WeatherBot's own `_LiveStderr` shape does exactly this), every call to `assert_redaction_active` would report "could not verify" even when correctly wired — a false negative that could train consumers to distrust or stop calling the check. Low risk this phase (the check still satisfies the "never a false pass" requirement) but worth flagging for discuss-phase/planner attention |
| A2 | The exact semantics of D-56's opt-in deep dry-run probe — specifically, whether the "fixed, non-secret sentinel" is expected to match one of the consumer's REAL registered patterns (requiring the consumer or the hub's own tests to register a purpose-built canary pattern), or whether the deep check's value is limited to confirming (a) the pattern set is non-empty and (b) the scrub call executes without raising — could not be resolved with certainty from CONTEXT.md's phrasing alone | Architecture Patterns → Pattern 3 (deep-check design); see Open Questions | If the planner picks the wrong reading, the deep check either (a) requires consumers to register an unwanted permanent canary pattern just for self-checking, or (b) fails to actually prove "an empty pattern set would be caught" as D-56 explicitly claims it should. This is squarely worth resolving explicitly at plan time, not guessed at |

## Open Questions

1. **What exactly must the D-56 deep dry-run probe assert to prove "behavior, not just wiring"?**
   - What we know: it must catch a case introspection-only misses — specifically, an empty
     pattern set (D-56's own stated example). It operates in-memory only, never calling `.write()`.
   - What's unclear: whether it needs the consumer to have registered a pattern that matches the
     fixed sentinel (implying a documented "register a canary pattern for self-checking"
     convention), or whether "non-empty pattern set + the scrub call executes without raising" is
     itself sufficient proof of "behavior" for this requirement's purposes.
   - Recommendation: resolve at plan/discuss time. A pragmatic middle ground: the deep check
     confirms `patterns` is non-empty AND exercises `redact_secrets(SENTINEL, patterns)` without
     raising — this catches the stated "empty pattern set" gap without requiring any
     consumer-side canary-pattern convention, and is honestly describable as "behavior, not just
     wiring" (it proves the scrub code path executes, not merely that an object is present).

2. **Should `assert_redaction_active`'s nested-proxy blind spot get a documented unwrap
   convention, or stay a hard "could not verify" with no escape hatch?**
   - What we know: D-56 requires "never a false pass" — a hard raise trivially satisfies that.
   - What's unclear: whether the planner should design a conventional "expose the wrapped target"
     protocol (e.g. an attribute name RedactingWriter-wrapping proxies are documented to expose)
     so `assert_redaction_active` can walk one level deeper, reducing false-negative friction for
     consumers who legitimately need a lazy-stream-resolving proxy (WeatherBot's own shape).
   - Recommendation: ship the hard-raise version this phase (satisfies REDACT-07 completely and
     safely); note the unwrap-convention idea as a candidate follow-up if WeatherBot's actual repin
     hits this friction in practice — do not build it speculatively now (rule of three).

## Environment Availability

Not applicable — this phase adds zero new external dependencies, services, or CLI tools. `structlog`
is already installed and verified present (`26.1.0`) in this repo's `.venv`. No database, network
service, or external runtime is touched by `RedactingWriter`, `redaction_processor`, or
`assert_redaction_active` — all three operate entirely in-process against structlog's own
configuration object and stdlib primitives.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (dev dependency `pytest>=9.0.3`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_redact_sink.py tests/test_redact_processor.py -q` (file names per Claude's Discretion on module split) |
| Full suite command | `uv run pytest -q` (per `.planning/config.json` `workflow.test_command`) |

This phase's tests join `tests/test_redact_core.py` and `tests/test_redact_registry.py` (Phase 5)
as the established convention: module-local `SENTINEL` constant (not a fixture — D-10 house
convention, no new `conftest.py` fixture until a second caller exists), hand-written capture
doubles (no `unittest.mock`/`pytest-mock` anywhere in this repo's suite), RED-first two-commit
discipline per GATE-02.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| REDACT-04 | `RedactingWriter` scrubs event + full formatted traceback, asserted against full captured output (never `str(exc)` alone), regardless of processor-chain order/renderer | unit + adversarial | `uv run pytest tests/test_redact_sink.py -x` | ❌ Wave 0 |
| REDACT-04 | A `JSONRenderer`-produced line carrying an escaped secret still round-trips through `json.loads` after redaction | unit | `uv run pytest tests/test_redact_sink.py -k json -x` | ❌ Wave 0 |
| REDACT-04 (D-55) | `RedactingWriter` installed as `sys.stderr`, non-structlog output (bare `print()` / stdlib `logging`) comes out scrubbed | integration | `uv run pytest tests/test_redact_sink.py -k stderr_recipe -x` | ❌ Wave 0 |
| REDACT-05 | `redaction_processor` scrubs `event_dict` string values; docstring states the chain-order precondition | unit | `uv run pytest tests/test_redact_processor.py -x` | ❌ Wave 0 |
| REDACT-05 | Negative case: processor-only (no sink) configuration still leaks a traceback under `dev.ConsoleRenderer` — proves the sink's necessity, not a regression | unit (documents a known limitation) | `uv run pytest tests/test_redact_processor.py -k leaks_without_sink -x` | ❌ Wave 0 |
| REDACT-07 | `assert_redaction_active` raises when the backstop is absent, and after a second `structlog.configure()` drops it; passes when installed | unit + integration | `uv run pytest tests/test_redact_verify.py -x` | ❌ Wave 0 |
| REDACT-07 (D-60) | `assert_redaction_active` warns (never raises) when the optional processor is mis-ordered relative to the exception formatters | unit | `uv run pytest tests/test_redact_verify.py -k ordering -x` | ❌ Wave 0 |
| REDACT-08 | Redaction-count telemetry increments on changed writes only, is thread-safe under concurrent `.write()` calls | unit + concurrency | `uv run pytest tests/test_redact_sink.py -k telemetry -x` | ❌ Wave 0 |
| DOCS-04 | `EXTENSION-GUIDE.md` SEAM-08 row present and flipped to implemented | manual review (no automated doc-content test in this repo's convention) | — | — |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_redact_sink.py tests/test_redact_processor.py tests/test_redact_verify.py -q`
- **Per wave merge:** `uv run pytest -q` (full suite)
- **Phase gate:** Full suite green, plus `uv run pytest tests/test_import_hygiene.py -q` (import-hygiene/litmus/grimp gates), before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_redact_sink.py` — covers REDACT-04, REDACT-08 (co-located per the sink/telemetry
      coupling noted in Architecture Patterns)
- [ ] `tests/test_redact_processor.py` — covers REDACT-05
- [ ] `tests/test_redact_verify.py` — covers REDACT-07 (including the D-60 ordering-warning path)
- [ ] `tests/test_import_hygiene.py` — extend `test_litmus_clean`'s `redact_scanned` assertion set
      to include `sink.py` and `processor.py` (currently asserts only `{"core.py", "registry.py"}`
      — see `tests/test_import_hygiene.py:290-296`)
- [ ] No new framework/fixture install needed — pytest 9.1.1 and the hand-written-double
      convention are already established by Phase 5

*(File names above follow "Claude's Discretion" on the exact module split — adjust to match
whatever final `sink.py`/`processor.py`/co-located-`verify` layout the plan settles on.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|---------------------|
| V5 Input Validation | yes (carried from Phase 5, still binding) | `register_patterns`'s ReDoS wall-clock vetting (already shipped) — this phase does not re-open pattern validation, only consumes already-vetted patterns |
| V6 Cryptography | no | Redaction is string substitution, not a cryptographic control; no key material or crypto primitive is introduced |
| V7 Error Handling and Logging | **yes — this phase's entire domain** | `RedactingWriter`/`redaction_processor` ARE the standard control (OWASP Logging Cheat Sheet's masking-not-deletion guidance, already followed by the proven WeatherBot design and carried forward) |
| V14 Configuration | yes | D-53's explicit-constructor-parameter-only disablement (never an env-var read) is the standard control against an accidentally-left-set kill switch |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-------------------------|
| Secret leakage via rendered log output (event fields OR formatted tracebacks) | Information Disclosure | `RedactingWriter` as the load-bearing, renderer-agnostic backstop (REDACT-04); this phase's entire purpose |
| Silent backstop bypass via a second `structlog.configure()` call dropping the wired sink | Information Disclosure (delayed/latent) | `assert_redaction_active` (REDACT-07), called at boot and after any reconfigure |
| An implicit env-var kill switch silently disabling redaction in production | Tampering (of security-relevant ambient state) | D-53: disablement is an explicit constructor parameter only, never `os.environ.get(...)` inside hub code |
| A raising or slow consumer-supplied `on_redaction` hook breaking the logging path itself | Denial of Service (of the logging subsystem, potentially masking the original error being logged) | D-52/D-57: the hook call is wrapped in a swallow-and-continue guard on the hot write path |
| Redaction-count telemetry data race under concurrent writers (APScheduler pool + asyncio loop + main thread) producing a corrupted/lost count | Tampering (of the telemetry signal's integrity) | D-59: `threading.Lock` around the increment, not relying on GIL-era atomicity |

## Sources

### Primary (HIGH confidence)

- `structlog` 26.1.0 — live introspection this session (`uv run python3 -c "import structlog; ..."`):
  `get_config()` keys, `PrintLoggerFactory`/`WriteLoggerFactory` constructor signatures and `_file`
  attribute presence, `PrintLogger`/`WriteLogger` `.msg()` source (`inspect.getsource`),
  `format_exc_info`/`dict_tracebacks` `isinstance(..., ExceptionRenderer)` checks,
  `dev.ConsoleRenderer.__init__` default `exception_formatter=plain_traceback` (no `rich`/
  `better-exceptions` needed — confirmed neither installed), `structlog.testing.capture_logs`
  source (`inspect.getsource`).
- Live end-to-end reproductions this session: `dev.ConsoleRenderer` self-rendering a traceback with
  zero exception-formatting processors in the chain; `PrintLoggerFactory` producing 2 `write()`
  calls per emission vs. `WriteLoggerFactory`'s 1; a JSON-round-trip-but-partial-redaction edge case
  for a secret containing an embedded quote character; `sys.stderr` swap ordering relative to
  `logging.basicConfig()`.
- `/home/yahir/Projects/Reusable/YahirReusableBot/yahir_reusable_bot/redact/core.py`,
  `registry.py`, `__init__.py` — Phase 5's shipped, pinned public surface this phase builds on.
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` (`_LiveStderr`, lines 26-62),
  `weatherbot/weather/client.py` (lines 1-56), `tests/test_redact_hygiene.py` (all 6 tests) — the
  proven production design and its behavioral spec, read directly this session.
- `/home/yahir/Projects/Reusable/YahirReusableBot/EXTENSION-GUIDE.md`,
  `tests/test_import_hygiene.py`, `pyproject.toml`, `.planning/config.json` — read directly this
  session for house conventions, the litmus coverage-guard pattern, and the unbounded version pin.
- `.planning/phases/05-redaction-core-pattern-registration/05-CONTEXT.md` — D-52/D-53, binding on
  this phase's seam design.
- `.planning/phases/06-insertion-seams-provable-backstop/06-CONTEXT.md` — D-54 through D-60, this
  phase's locked decisions.

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `FEATURES.md`, `PITFALLS.md` —
  this milestone's own parallel-advisor research (2026-07-29), still valid for Phase 6; re-verified
  several of its specific technical claims live this session rather than taking them on faith.

### Tertiary (LOW confidence)

- None newly introduced this session — no new WebSearch/WebFetch was performed; every claim in
  this document is grounded in direct source reads or live code execution against the installed
  package.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, version verified live this session
- Architecture: HIGH — sink-primary design directly re-verified via live structlog execution, not
  just cited from the milestone research
- Pitfalls: HIGH — every pitfall in this document (except the two flagged genuinely open questions)
  was either read directly from source or empirically reproduced live this session

**Research date:** 2026-08-03
**Valid until:** 30 days, OR immediately upon any `structlog` version change in `uv.lock` (the
`_file` private-attribute coupling is version-sensitive by construction — see Pitfall 5)
