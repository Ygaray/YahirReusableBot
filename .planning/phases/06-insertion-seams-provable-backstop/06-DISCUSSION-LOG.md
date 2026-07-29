# Phase 6: Insertion seams + provable backstop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 6-Insertion seams + provable backstop
**Areas discussed:** Scrub coverage, Proving it's on, Telemetry, Mis-wiring protection (all four
selected), plus one follow-up on test scope
**Mode:** advisor (USER-PROFILE.md present) — four parallel `gsd-advisor-researcher` agents,
calibration tier `standard` (vendor_philosophy: pragmatic-fast)

---

## ⚠ Premise correction raised mid-discussion

The gray areas were presented on the stated assumption that WeatherBot's proven `_LiveStderr` wraps
`sys.stderr` process-wide. The coverage researcher read the source and found this false: it is only
ever a `structlog.PrintLoggerFactory(file=...)` target. Verified consequence at
`weatherbot/weather/client.py:48-54` — httpx's stdlib-`logging` line carrying the API key bypasses
the backstop entirely.

This was surfaced to the user before any decision was taken, because it inverted the framing of
area 1 from "preserve broad coverage" to "make broad coverage possible." Recorded in CONTEXT.md
`<decisions>` so downstream agents do not re-derive the wrong premise from requirement text.

---

## Scrub coverage (REDACT-04)

| Option | Description | Selected |
|--------|-------------|----------|
| One primitive, two recipes | Ship `RedactingWriter` wrapping any file-like target; SEAM-08 documents the required structlog-target recipe and an optional broader `sys.stderr = RedactingWriter(sys.stderr)` recipe the consumer installs | ✓ |
| Narrow only | Document it solely as structlog's `PrintLoggerFactory` file target; smallest surface, matches REDACT-04's literal wording | |
| Hub ships a global installer | A hub function performing the `sys.stderr` assignment; one-line adoption, broadest default coverage | |

**User's choice:** One primitive, two recipes (the researched recommendation)
**Notes:** Not a compromise — `RedactingWriter` must wrap an arbitrary file-like target anyway to
satisfy REDACT-04, so it can stand in for `sys.stderr` with zero extra code. The global-installer
option was rejected as both constitutionally awkward (hub actively mutating process state, against
D-53's reasoning) and redundant. → **D-54**

---

## Proving it's on (REDACT-07)

| Option | Description | Selected |
|--------|-------------|----------|
| Introspect + opt-in dry-run probe | Default: read `structlog.get_config()`, confirm the writer is installed, raise `ValueError` if not. Opt-in: ask the located live instance to scrub a non-secret sentinel **in memory only**, never calling `.write()` | ✓ |
| Introspection only | Config check alone; simplest, one code path. Proves wiring, not behavior | |
| Canary through the real logger | Push a sentinel through the actual configured logger and capture output; proves end-to-end behavior but needs capture machinery and can leak the sentinel if capture is imperfect | |

**User's choice:** Introspect + opt-in probe (the researched recommendation)
**Notes:** The in-memory dry-run is what made the probe acceptable — it structurally removes the
"canary leaks when the backstop is broken" failure mode, since the probe never touches the real
output path. Raising (not returning a result object) matches the standing D-34/D-50
fail-loud-at-wiring-time posture. Known fragility accepted and recorded: introspection reaches
structlog's private `_file` attribute and is blind to consumer-side proxy nesting — the plan must
make that degrade to an explicit "could not verify", never a false pass. → **D-56**

---

## Telemetry (REDACT-08)

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid, count changed writes | Lock-guarded monotonic counter as source of truth + optional `on_redaction` hook; counts writes where output changed | ✓ |
| Pull-only attribute | Just the counter, no hook; smallest surface, consumer polls it | |
| Pay for exact substitution counts | Honor "substitutions" literally via `.subn()`, at roughly double the regex cost on every log line — or a second copy of the scrub loop | |

**User's choice:** Hybrid, count changed writes (the researched recommendation)
**Notes:** The unit question was the substantive part. `redact_secrets` is pinned and returns only
the string, so exact substitution counts are not cheaply obtainable — the alternatives were doubling
hot-path regex work forever or duplicating a security-sensitive loop. Changed-writes is one `!=` on
strings already in memory and answers what the requirement exists for. Recorded as a deliberate
reading of REDACT-08's wording so verification does not flag it as drift. Separately: use a
`threading.Lock` rather than `itertools.count`'s atomicity, which is a GIL-era detail that stops
holding under free-threaded builds. → **D-57, D-58, D-59**

---

## Mis-wiring protection (REDACT-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Docstring + ordering check folded into R-07, warns | Loud docstring plus an index comparison inside `assert_redaction_active`; warns rather than raises | ✓ |
| Docstring only | Exactly the requirement's letter, zero machinery | |
| Chain-builder helper | Return a correctly-ordered processor list so mis-ordering is structurally impossible | |

**User's choice:** Docstring + fold check into R-07, warn (the researched recommendation)
**Notes:** Feasibility verified live — `get_config()["processors"]` exposes the chain and every
built-in exception formatter is an `isinstance` of `structlog.processors.ExceptionRenderer`, so the
check is an index comparison with no new API. Warns rather than raises because the sink catches
tracebacks regardless of processor order, making mis-ordering reduced defense-in-depth rather than a
regression — and a hard crash over a component the ROADMAP says is droppable is disproportionate.
The chain-builder was declined for annexing composition-root policy (it must know the consumer's
renderer/formatter choice) however the "only returns, never configures" framing is phrased.
→ **D-60**

---

## Follow-up: is the second recipe tested or documented only?

| Option | Description | Selected |
|--------|-------------|----------|
| Tested — prove both recipes | Ship a test installing `RedactingWriter` as a stand-in stream, asserting non-structlog output (`print()` / stdlib-`logging`) comes out scrubbed | ✓ |
| Documentation only | SEAM-08 describes it; tests cover only the structlog file-target path | |
| Drop recipe 2 entirely | Ship and document the structlog wiring alone | |

**User's choice:** Tested — prove both recipes
**Notes:** Asked because it changes plan scope and test count. Rationale accepted: a documented
wiring nobody has run is exactly how the httpx gap got missed. → **D-55**

---

## Claude's Discretion

- Module split within `redact/` for the new files (research proposed `sink.py` + `processor.py`).
- Exact public names, subject to the AST signature litmus; `RedactingWriter` and
  `assert_redaction_active` are fixed by the requirements themselves.
- The disablement parameter's name and signature position — D-53 locks only that it is an explicit
  constructor parameter, never an env read. **Default must be redaction ON.**
- The non-secret sentinel constant used by the dry-run probe.
- Whether the telemetry hook receives the current count or no argument.
- SEAM-08's layout within `EXTENSION-GUIDE.md`'s existing conventions.

## Deferred Ideas

- **The httpx / stdlib-`logging` gap in WeatherBot** — hub-side answer is in scope (D-54's second
  recipe); actually adopting it is a consumer decision for the human-gated repin. Flag at repin;
  do not assume the hub upgrade closes it alone.
- **`RedactionPattern.asdict()`/`astuple()` still expose raw pattern source** — Phase 5's WR-02
  residual. Revisit if this phase's processor or telemetry ends up serializing pattern objects into
  an `event_dict`.
- **A safe pattern-builder helper** — carried from Phase 5; strongest follow-up candidate.
- **Per-pattern replacements beyond the template mechanism; partial masking for correlation** —
  differentiators, rule of three.
- **Config-driven pattern loading** — no second consumer to justify the shape.
- **A chain-builder helper for processor ordering** — rejected here; revisit only if REDACT-05 stops
  being optional.
