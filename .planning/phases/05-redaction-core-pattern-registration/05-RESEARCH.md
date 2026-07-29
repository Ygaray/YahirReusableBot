# Phase 5: Redaction core + pattern registration - Research

**Researched:** 2026-07-29
**Domain:** Stdlib-only secret-redaction core (`re`-based substitution) + safe-by-construction
pattern-registration API, inside a pure-leaf Python subpackage of an existing hub library.
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-48 (a pattern carries its own replacement — the API is a PAIR, not a bare regex):** the
  public unit is a `RedactionPattern` frozen dataclass pairing a **pre-compiled** `re.Pattern` with
  a **replacement template string**, consumed by `redact_secrets(text, patterns)` via `pattern.sub`.
  Rejected: bare `Iterable[re.Pattern]` + fixed `***`; mandatory named groups; raw pattern strings
  compiled internally.

- **D-49 (zero patterns is a valid, silent identity no-op):** `redact_secrets(text, ())` returns
  `text` unchanged without raising or warning. Overlapping patterns apply **sequentially in
  registration order** — documented, not special-cased.

- **D-50 (vet at registration, default-ON, generous budget, explicit opt-out, raise `ValueError`):**
  the registration path probes each pattern against adversarial input under a wall-clock budget and
  raises `ValueError` naming the offending pattern if it blows the budget. Vetting is on by default
  with an explicit opt-out parameter for a pattern known to be legitimately slow. Budget must be
  GENEROUS (machine-dependent pure-Python timing; a tight budget false-rejects on a loaded CI box).
  Pair the timing probe with a cheap structural check (e.g. nested quantifier detection). Rejected:
  no vetting; runtime timeout/interrupt around `sub`.

- **D-51 (a literal is a pattern whose regex is escaped — one pipeline, two entry points):** expose
  literal registration as a named constructor (`RedactionPattern.literal("<secret value>")`) that
  `re.escape()`s the value and feeds the **same** compiled-pattern pipeline. Rejected: a separate
  `literals` parameter and a second substitution pass.

- **D-52 (the core is strict `str -> str`; non-`str` triage belongs to the Phase-6 seam):**
  `redact_secrets(text: str, patterns) -> str` accepts and returns `str` only. `bytes` decoding and
  non-raising tolerance for other types lives at the Phase-6 seam, matching `_LiveStderr.write`.
  **REQUIREMENTS.md wording adjustment (tracked deliberately):** REDACT-01's "tolerant of non-`str`
  input" clause is relocated to REDACT-04 (Phase 6). Phase 5 verification must NOT report a gap
  because `redact_secrets` rejects `bytes` — that is the locked contract.

- **D-53 (disablement is an explicit parameter, never an environment read):** the ability to turn
  redaction off is exposed as an explicit constructor/parameter value on the Phase-6 seam. The hub
  never reads an environment variable to decide this. Recorded here because it constrains the
  core's signature (the core itself has no enabled/disabled concept — zero patterns is the only
  no-op, per D-49).

### Claude's Discretion

- Exact module split within `redact/` (`core.py` / `registry.py`).
- The precise ReDoS budget value and adversarial-input corpus (D-50).
- Whether `RedactionPattern` is a frozen dataclass or a `NamedTuple` — the pairing is locked, the
  container type is not.
- The exact placeholder default (`***` matches the proven code and should be the default).

### Deferred Ideas (OUT OF SCOPE)

- Per-pattern replacement strings beyond the template mechanism, and partial masking that preserves
  a token prefix/suffix for correlation — differentiators, not table stakes. No consumer need yet.
- Config-driven pattern loading (patterns from a config file rather than code) — out of scope; no
  second consumer to justify the shape.
- A safe pattern-builder helper (constructing `name=value` patterns without hand-writing regex) —
  flagged as the strongest candidate for a follow-up once the core API proves out, but additional
  public surface beyond REDACT-01/02/03/06.
- `weatherbot/weather/client.py`'s domain-specific redacted re-raise — permanently out of PC-01
  scope; stays app-local forever.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REDACT-01 | `redact_secrets(text, patterns) -> str` scrubs every configured secret from a rendered string in one pass — idempotent, masks the value while preserving surrounding diagnostics (endpoint, HTTP status, neighbouring params). (Non-`str` tolerance clause relocated to REDACT-04/Phase 6 per D-52.) | Architecture Pattern 2 (sequential-apply core); Code Examples (idempotence + zero-pattern no-op tests); Common Pitfalls 3 (boundary style); Validation Architecture test map |
| REDACT-02 | A `RedactionPattern` type plus a stateless registration API — patterns compiled once and frozen into an immutable collection, with zero process-wide mutable state. A module-level singleton is explicitly rejected. | Architecture Pattern 1 (`RedactionPattern` dataclass) and Pattern 3 (`register_patterns` as pure function); Don't Hand-Roll table; Common Pitfalls 2; Validation Architecture test map |
| REDACT-03 | A pattern that exceeds a wall-clock budget against adversarial input is rejected at registration time — stdlib `re` has no timeout, hub logging is synchronous, the Discord adapter runs an asyncio gateway loop. | Architecture Pattern 3 (structural check + timing probe + budget/corpus); Common Pitfalls 4/5; Assumptions Log A1/A2/A4; Validation Architecture test map |
| REDACT-06 | A literal-value redaction mode blocks an exact secret string wherever it appears, catching leak paths that pattern matching misses. | Architecture Pattern 1 (`RedactionPattern.literal`); Code Examples (literal-inside-`repr()` proof); Common Pitfalls 3; Validation Architecture test map |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` (this repo is the hub of a multi-repo bot ecosystem):

- **One-way dependency, no domain nouns:** consumers import this hub; the hub imports no consumer
  (`weatherbot`). Enforced by `tests/test_import_hygiene.py` (`grimp` graph + AST signature litmus).
  `redact/` must satisfy this automatically as a pure leaf subpackage — confirmed compatible in
  Architecture Patterns above; no gate edits needed.
- **Changes here ripple to every consumer via a human-gated repin.** No version bump, tag cut,
  `uv sync`, or deploy is performed autonomously — those are surfaced for confirmation per
  `ECOSYSTEM.md` §3. This phase's own build (core.py + registry.py + tests) is fully autonomous;
  only the eventual WeatherBot repin (Phase 9+) is human-gated.
- **Plug points documented in `EXTENSION-GUIDE.md`; deferred implementations built in a consumer's
  `_promotable/` quarantine first, then promoted via `git mv`.** Not applicable to this phase directly
  (this IS a promotion already vetted by prior research), but SEAM-08 documentation is explicitly
  Phase 6's job (DOCS-04), not this phase's.
- **Toolchain:** Python 3.12+, `uv`, `hatchling`. Runtime deps: `discord.py==2.7.1` (exact),
  `httpx`, `structlog`, `tenacity` — none of which `redact/core.py` or `redact/registry.py` need to
  import. Dev deps: `pytest`, `ruff`, `grimp` — all already present, no dev-dependency change needed.
- **Test command:** `uv run pytest`. **Lint:** `uv run ruff check`. **Import-hygiene gate:**
  `uv run pytest tests/test_import_hygiene.py` — all three must stay green through this phase
  (matches `.planning/config.json`'s configured `test_command`).
- **Ships no console script** — this is a library; nothing in this phase adds an entry point.

None of these constraints conflict with the recommended design above; the design was built to
satisfy them by construction (pure-stdlib leaf subpackage, no hub-owned configuration, no new
dependency).

## Summary

This phase generalizes a 28-line, production-proven WeatherBot module
(`weatherbot/_redact.py` + its `_APPID_RX` pattern) into a hub-owned, consumer-agnostic pair:
`redact_secrets(text, patterns) -> str` and a registration API that compiles, ReDoS-vets, and
freezes a consumer's patterns exactly once. There is no new technology here — the entire milestone
research (STACK/ARCHITECTURE/FEATURES/PITFALLS, all HIGH confidence, all read this session) already
converged on stdlib `re` only, zero new dependencies, and the API shape is fully specified by
CONTEXT.md's locked decisions (D-48 through D-53). This phase's job is to execute that shape
precisely, port WeatherBot's boundary-case test matrix verbatim, and settle the two things CONTEXT.md
explicitly left open: the ReDoS wall-clock budget/corpus, and the module-internal container type.

The core is a pure `str -> str` function operating on rendered text after a pattern list has been
validated once at registration time — never at the log call site. Because the function works on
plain substrings, "block a literal secret wherever it appears — including inside a `repr()`" (success
criterion 4) requires **no special-casing**: `RedactionPattern.literal(value)` feeds `re.escape(value)`
into the exact same `pattern.sub()` loop as every other pattern, and a `repr()` string is just more
text the loop scans. This is confirmed by direct trace-through of the pipeline, not asserted.

**Primary recommendation:** Build `redact/core.py` (the `RedactionPattern` frozen dataclass +
`redact_secrets`) first and prove it in isolation against WeatherBot's ported boundary matrix, then
`redact/registry.py` (`register_patterns`, wrapping ReDoS vetting) second — exactly the dependency
order CONTEXT.md and ARCHITECTURE.md agree on. Do not build `sink.py`/`processor.py` in this phase;
they are Phase 6.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Secret-value substitution (`redact_secrets`) | Library core (pure function) | — | Stateless text transform; no I/O, no framework coupling — belongs in the leaf subpackage's core module, not a seam |
| Pattern validity + ReDoS vetting | Library core (registration-time) | — | Must run once, at wiring time, before anything is serving — never on the logging hot path (no runtime tier can rescue a hang; stdlib `re` has no timeout) |
| Pattern *authoring* (what regex a consumer writes) | Consumer composition root | — | Domain-specific (e.g. `appid=`) — explicitly out of hub scope per the litmus; the hub owns the mechanism, never the pattern content |
| Wiring redaction into a live logger (sink/processor) | Consumer composition root (Phase 6 toolkit) | — | Out of THIS phase's scope entirely — Phase 6 builds `sink.py`/`processor.py`; Phase 5 ends at "a consumer can build and validate a pattern set" |
| Disablement toggle | Consumer composition root (Phase 6 seam constructor param) | — | D-53: never an env-var read inside the hub; the *core* has no enabled/disabled concept at all (zero patterns is its only no-op, D-49) |

## Package Legitimacy Audit

**Not applicable to this phase.** Verified stack conclusion (STACK.md, HIGH confidence, direct
`uv.lock`/`uv pip show` inspection): zero new dependencies. `redact/core.py` and `redact/registry.py`
use only Python stdlib (`re`, `dataclasses`, `time`, `typing`/`collections.abc`). No package
installation occurs in this phase — the Package Legitimacy Gate protocol (registry lookup,
postinstall-script check) has nothing to check against. `structlog` enters the subpackage only in
Phase 6's `processor.py`, and it is already an existing, pinned hub dependency (`structlog>=26.1.0`,
resolved 26.1.0), not a new install.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stdlib `re` | bundled, Python 3.12/3.13 | Pattern compilation (consumer-side, before registration) + `Pattern.sub()` substitution core | `[VERIFIED: STACK.md — direct venv introspection]`. Bounded-scope string substitution is exactly `re`'s job; WeatherBot's proven 28-line implementation already does this in production with zero deps. |
| stdlib `dataclasses` | bundled | `RedactionPattern` frozen dataclass | `[VERIFIED: codebase]` — matches the existing hub convention (`registry/spec.py`'s `CommandSpec`/`DispatchContext`, both `@dataclass(frozen=True)`) — see Code Examples. |
| stdlib `time` | bundled | Wall-clock timing probe for the ReDoS vetting check (`time.perf_counter()`) | `[VERIFIED: stdlib]` — the only reliable wall-clock primitive available; no async/signal-based interruption is viable inside a synchronous registration call (PITFALLS.md Pitfall 3). |

### Supporting
None. `redact/core.py` and `redact/registry.py` need no supporting libraries — confirmed by
STACK.md's exhaustive check of the two candidate third-party packages (both rejected, see below).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `re` + hand-rolled ReDoS vetting | `scrubadub` | Pulls in `scikit-learn`/`faker`/`dateparser`/`textblob` — an NLP/PII stack wildly disproportionate to "substitute known-shape tokens." `[CITED: STACK.md]` Rejected outright. |
| stdlib `re` + hand-rolled ReDoS vetting | `loggingredactor` (0.0.7) | Confirms the "iterable of compiled patterns" API shape is ecosystem-standard prior art, but is a young, low-adoption 0.0.x package whose entire value (`compile` + `.sub()` loop) is ~15 lines the hub can own directly. `[CITED: STACK.md]` Rejected — used only as API-shape confirmation. |
| Registration-time wall-clock ReDoS probe | The third-party `regex` module's `timeout=` parameter | Would add a new runtime dependency for a check needed only once, at registration, in developer/CI time — not a hot-path concern. `[ASSUMED]` — not evaluated in prior research; rejected here as disproportionate for the same reason as `loggingredactor`. |

**Installation:**
```bash
# Nothing to install — pure stdlib. No pyproject.toml change for this phase.
```

**Version verification:** N/A — no new package. Python version already pinned `requires-python
>=3.12` in `pyproject.toml`; `re.Pattern[str]` generic-subscript typing syntax is satisfied.

## Architecture Patterns

### System Architecture Diagram

```
Consumer composition root (e.g. WeatherBot's __init__.py, Phase 6+ / out of this phase's scope)
        │
        │  1. author regex/literal patterns + replacement templates
        ▼
┌─────────────────────────────────────────────────────────────┐
│ yahir_reusable_bot.redact.core                              │
│                                                               │
│  RedactionPattern(pattern: re.Pattern[str], replacement: str)│
│  RedactionPattern.literal(value, replacement="***")          │
│      └─ re.escape(value) → same compiled-pattern shape        │
└───────────────────────────┬───────────────────────────────────┘
                             │  2. hand a sequence of RedactionPattern to
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ yahir_reusable_bot.redact.registry                           │
│                                                               │
│  register_patterns(patterns) -> tuple[RedactionPattern, ...] │
│      for each pattern (unless skip_redos_check):              │
│        ├─ cheap structural check (nested-quantifier scan)     │
│        │      fail → raise ValueError immediately             │
│        └─ wall-clock timing probe vs. adversarial corpus       │
│               fail → raise ValueError naming the pattern       │
│      success → freeze into an immutable tuple, return it      │
└───────────────────────────┬───────────────────────────────────┘
                             │  3. consumer stores the returned frozen tuple
                             │     (no hub-side global state — D-49/Pitfall 7)
                             ▼
                  consumer's own object / closure
                  (Phase 6 will thread this tuple into
                   RedactingWriter / redaction_processor —
                   OUT OF SCOPE for Phase 5)
                             │
                             │  4. at each log/error-format call site
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ yahir_reusable_bot.redact.core                               │
│                                                               │
│  redact_secrets(text: str, patterns) -> str                  │
│      patterns == ()  → return text unchanged (D-49 no-op)     │
│      else: for each pattern, in registration order:            │
│                text = pattern.pattern.sub(pattern.replacement, │
│                                             text)               │
│      return text                                                │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
                 scrubbed text (endpoint/status/params intact,
                 secret masked, idempotent under re-application)
```

A reader traces one use case end-to-end: a consumer authors a pattern (1), registers it once and
gets back a frozen, vetted tuple (2–3), then calls `redact_secrets` with that tuple on every rendered
string that might carry a secret (4) — the same tuple, reused, never recompiled, never mutated.

### Recommended Project Structure
```
yahir_reusable_bot/
└── redact/                  # NEW subpackage — pure leaf, stdlib only in this phase
    ├── __init__.py          # re-exports: redact_secrets, RedactionPattern, register_patterns
    ├── core.py               # redact_secrets(text, patterns) -> str; RedactionPattern dataclass
    └── registry.py           # register_patterns(patterns, ...) -> tuple[RedactionPattern, ...]
    # sink.py / processor.py do NOT exist yet — Phase 6 adds them
```
`[VERIFIED: ARCHITECTURE.md Q1/Q6, cross-checked against tests/test_import_hygiene.py]` — this
exact tree (minus `sink.py`/`processor.py`, deferred) is what the milestone's own architecture
research specified and what CONTEXT.md's scope notes confirm as this phase's build order.

### Pattern 1: Pair-not-bare-pattern (`RedactionPattern`, D-48)
**What:** The public unit is a frozen dataclass pairing a **pre-compiled** `re.Pattern[str]` with
its **replacement template string** — never a bare pattern, never a raw string compiled late.
**When to use:** Every registration call. This is the entire public pattern surface (REDACT-01/02).
**Example:**
```python
# Source: generalizing WeatherBot's proven weatherbot/_redact.py (read this session)
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionPattern:
    """A compiled pattern paired with its replacement template (D-48).

    ``pattern`` must be pre-compiled — accepting raw strings here would make late
    compilation (and desynced flags) structurally possible, which the public API
    must foreclose (Pitfall 6). ``replacement`` is any valid ``re.sub`` replacement
    template: a positional backreference (``r"\\1***"``, WeatherBot's proven shape)
    or a named-group reference (``r"\\g<keep>***"``, the recommended convention for
    new patterns) both work — this dataclass does not enforce either style.
    """

    pattern: re.Pattern[str]
    replacement: str
    skip_redos_check: bool = False  # D-50 explicit opt-out, per-pattern

    @classmethod
    def literal(cls, value: str, replacement: str = "***") -> "RedactionPattern":
        """A literal-value pattern (D-51/REDACT-06) — one pipeline, two entry points.

        ``re.escape(value)`` feeds the SAME compiled-pattern pipeline every other
        pattern uses; there is no second scrubbing loop. A literal replaces the
        WHOLE matched value (there is no surrounding label to preserve, unlike a
        ``name=value`` pattern).
        """
        return cls(pattern=re.compile(re.escape(value)), replacement=replacement)
```

### Pattern 2: Sequential-apply core (D-49) with a true zero-patterns no-op
**What:** `redact_secrets` folds `pattern.sub()` over the text in registration order; zero patterns
returns the input unchanged with **no regex work at all** (Pitfall 6's "no-op fast path").
**When to use:** The one scrubbing loop the whole phase builds toward.
**Example:**
```python
# Source: generalizing weatherbot/_redact.py's _APPID_RX.sub(r"\1***", text) shape
from collections.abc import Sequence


def redact_secrets(text: str, patterns: Sequence[RedactionPattern]) -> str:
    """Mask every registered secret in ``text``; preserve everything else (REDACT-01).

    Zero patterns is a legitimate no-op (D-49) — not an error. Overlapping patterns
    apply sequentially in registration order (documented, not special-cased): each
    pattern's substitution runs against the OUTPUT of the previous one.
    """
    if not patterns:
        return text
    for rp in patterns:
        text = rp.pattern.sub(rp.replacement, text)
    return text
```

### Pattern 3: Registration-time ReDoS vetting, default-on, explicit opt-out (D-50)
**What:** `register_patterns` runs a cheap structural pre-check plus a wall-clock timing probe
against an adversarial corpus, for every pattern **unless** that pattern set `skip_redos_check=True`.
A failing pattern raises `ValueError` naming the offending pattern's source text — at registration,
never at log time.
**When to use:** Every call to `register_patterns` — this IS the registration call (REDACT-03).
**Example:**
```python
# Source: hub-authored, synthesizing PITFALLS.md Pitfall 3 + CONTEXT.md D-50's
# "pair timing with a cheap structural check" instruction. [ASSUMED — budget/corpus
# values are this session's reasoned recommendation, not from an authoritative
# external source; see Common Pitfalls below and the Assumptions Log.]
import time

# Heuristic, NOT exhaustive: catches the textbook nested-quantifier shape
# (a group containing a quantifier, itself quantified) e.g. (a+)+, (x*)*.
# Does NOT catch every catastrophic shape (e.g. overlapping alternation like
# (a|ab)*c) — the timing probe below is the actual safety net; this is a
# fast, cheap, clearer-error-message first pass.
_NESTED_QUANTIFIER_RX = re.compile(r"\([^()]*[+*][^()]*\)[+*]")

# Generous, machine-independent-in-practice budget: benign patterns complete a
# ~10,000-char probe in low single-digit milliseconds even on a loaded box;
# genuinely catastrophic backtracking on this corpus takes multiple SECONDS even
# on a fast idle machine. 300ms leaves a >100x safety margin against false-reject
# while still tripping reliably on real catastrophic blowups.
_REDOS_BUDGET_S = 0.3

# Pattern-agnostic adversarial corpus (the pattern's own shape is unknown to the
# registry): three probe strings spanning the character classes most likely to
# appear in a consumer's known domain (query strings / URLs / tokens), each long
# enough that an exponential blowup dwarfs the budget, each ending in a character
# unlikely to satisfy a well-formed pattern's tail (forces "almost but not quite"
# backtracking, the trigger condition for catastrophic patterns).
_REDOS_CORPUS: tuple[str, ...] = (
    "a" * 8_000 + "!",
    ("0123456789" * 800) + "!",
    ("abc=def&" * 1_000) + "!",
)


def _looks_pathological(pattern: re.Pattern[str]) -> bool:
    return bool(_NESTED_QUANTIFIER_RX.search(pattern.pattern))


def _blows_budget(pattern: re.Pattern[str]) -> bool:
    for probe in _REDOS_CORPUS:
        start = time.perf_counter()
        pattern.search(probe)
        if time.perf_counter() - start > _REDOS_BUDGET_S:
            return True
    return False


def register_patterns(
    patterns: Sequence[RedactionPattern],
) -> tuple[RedactionPattern, ...]:
    """Vet, then freeze, a consumer's patterns (REDACT-02/REDACT-03).

    Raises ``ValueError`` naming the offending pattern's source text if it fails
    the structural check OR blows the wall-clock budget against the adversarial
    corpus — UNLESS that pattern set ``skip_redos_check=True`` (D-50's explicit,
    per-pattern opt-out for a pattern known to be legitimately slow). Vetting is
    a one-time registration cost, never a per-log-line cost.
    """
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

### Anti-Patterns to Avoid
- **Module-level mutable registry (`register_pattern()` writing into a global list):** eliminated
  by design — `register_patterns` is a pure function returning a new tuple, never mutating shared
  state. `[CITED: PITFALLS.md Pitfall 7, FEATURES.md Anti-Features]` This is the single highest-value
  API-shape decision in the phase; retrofitting it later would touch every consumer call site.
- **Compiling patterns inside `redact_secrets` itself:** the function signature only accepts
  `RedactionPattern` (which wraps an already-compiled `re.Pattern`) — there is no code path where a
  raw string could be compiled per-call. `[CITED: PITFALLS.md Pitfall 6]`
- **An implicit env-var kill switch inside `redact/`:** out of scope for the core (D-53) — the core
  has no enabled/disabled concept at all; disablement is a Phase 6 seam-constructor concern.
- **Runtime interruption of a hanging regex (`signal.alarm`, threads, subprocess):** rejected by
  CONTEXT.md and PITFALLS.md alike — stdlib `re` cannot be interrupted reliably, and none of these
  mechanisms work correctly inside an asyncio event loop. Registration-time vetting is the only
  practical mitigation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pattern compilation / substitution engine | A custom tokenizer or string-scanning replace loop | stdlib `re.Pattern.sub()` | This is exactly `re`'s job; WeatherBot's proven production code already does this in 2 lines. `[VERIFIED: weatherbot/_redact.py]` |
| Statistical/entropy-based secret detection | A heuristic "does this look like a secret" scorer | Explicit, consumer-authored patterns only | Rejected anti-feature — nondeterministic, false-positives on ordinary high-entropy log data (request IDs, hashes), destroys diagnosability. `[CITED: FEATURES.md]` |
| A general-purpose regex safety linter | A full static ReDoS analyzer (à la `redos-detector`) | The narrow structural heuristic + wall-clock probe above | Disproportionate for a single-digit pattern count registered once at startup; a full linter is a dependency this milestone's zero-new-deps verdict explicitly rejects. `[CITED: STACK.md verdict]` |
| Runtime regex timeout | `signal.alarm`, threading, or a subprocess wrapper around `.sub()` | Registration-time-only vetting | Stdlib `re` cannot be safely interrupted; none of these mechanisms are safe inside a synchronous logging path shared with an asyncio gateway loop. `[CITED: PITFALLS.md Pitfall 3]` |

**Key insight:** every "don't hand-roll" item above already has a proven, in-repo answer (the
WeatherBot source) or an explicit rejection with rationale from this milestone's own research — this
phase's job is precise generalization, not invention.

## Common Pitfalls

### Pitfall 1: Compiling patterns at log time (not registration time)
**What goes wrong:** A signature like `redact_secrets(text, patterns: list[str])` invites recompiling
a pattern on every call, taxing every single log emission.
**Why it happens:** The simplest possible signature doesn't make "these are precompiled" obvious.
**How to avoid:** The public API accepts only `RedactionPattern` (which wraps an already-compiled
`re.Pattern`) — late compilation is structurally impossible, not merely discouraged.
**Warning signs:** `re.compile(...)` appearing anywhere inside `core.py`'s hot function.
`[CITED: PITFALLS.md Pitfall 6]`

### Pitfall 2: A global mutable pattern registry causing cross-test pollution
**What goes wrong:** `register_pattern(p)` writing into a module-level list creates import-order
dependence and lets one test's registration leak into another's assertions — inside the hub's OWN
suite, which this project's test posture is specifically designed to catch (success criterion 2:
"identical results run in isolation and run in full-suite order").
**Why it happens:** A single hub-global registry is the path of least resistance.
**How to avoid:** `register_patterns` is a pure function; the consumer holds the returned frozen
tuple itself. No hub-side state exists to leak.
**Warning signs:** A test failure that only reproduces when the full suite runs, never in isolation.
`[CITED: PITFALLS.md Pitfall 7]`

### Pitfall 3: Over/under-broad pattern boundaries destroy diagnosability or leak partial tokens
**What goes wrong:** Too greedy (`key=.*`) eats the following query params/status/MDN link; too
narrow misses the secret riding on an unanticipated attribute (`.request.url`, a `repr()`).
**Why it happens:** A pattern proven for one call site doesn't automatically generalize.
**How to avoid:** Port WeatherBot's exact character-class-negation boundary style
(`[^&\s"'<>\\]+`) as the reference shape in tests, PLUS support literal-value matching (D-51) as the
independent backstop for unanticipated leak shapes — this phase's `RedactionPattern.literal()` exists
specifically to close this gap. Verify a literal matches inside a `repr()` string with an explicit
test (see Code Examples / Validation Architecture below): since `redact_secrets` operates on plain
text, a `repr()` output is simply more text the escaped-literal pattern scans — no special code path
needed, but the test must exist to PROVE this rather than assume it.
**Warning signs:** A boundary-case test where `units=imperial`-equivalent trailing content goes
missing (over-eating) or a secret survives inside a `repr()` (under-catching).
`[CITED: PITFALLS.md Pitfall 4, VERIFIED by direct trace-through of redact_secrets this session]`

### Pitfall 4: ReDoS from a consumer-supplied pattern is a hub-wide outage, not a slow log line
**What goes wrong:** Stdlib `re` has no timeout; a pathological pattern hangs `redact_secrets`,
which — because the Discord adapter runs an asyncio gateway loop and logging is synchronous —
starves heartbeats and drops the live connection.
**Why it happens:** Regex authors reason about the happy-path match, not adversarial rejection time.
**How to avoid:** `register_patterns` vets every pattern (structural + timing) before it can ever
reach `redact_secrets`. This is the phase's central design commitment (D-50, REDACT-03).
**Warning signs:** A registered pattern with a quantified group inside another quantified group
(`(a+)+`, `(a*)*`).
`[CITED: PITFALLS.md Pitfall 3]`

### Pitfall 5: Trusting the structural check alone (or the timing probe alone)
**What goes wrong:** The nested-quantifier regex heuristic above does NOT catch every catastrophic
shape (e.g. overlapping alternation `(a|ab)*c` has no literal nested-quantifier substring). Relying
on it alone would let some real ReDoS patterns through.
**Why it happens:** A cheap syntactic check looks sufficient after it catches the obvious `(a+)+`
textbook example in a demo.
**How to avoid:** CONTEXT.md's own instruction is explicit — "pair the timing probe with a cheap
structural check ... so the verdict does not rest on timing alone." Both checks run; either one
failing rejects the pattern. The timing probe is the actual safety net (it measures real behavior
against the actual corpus); the structural check is a fast first-pass with a clearer error message.
**Warning signs:** A test suite that only exercises `(a+)+`-shaped patterns and never an
alternation-based catastrophic shape.
`[ASSUMED — this session's synthesis of CONTEXT.md's instruction; flag for planner: write at least
one alternation-shaped adversarial test to confirm the TIMING probe (not the structural one) catches
it, proving the pairing is load-bearing and not redundant.]`

## Runtime State Inventory

> Omitted — this is a greenfield phase (new subpackage, no rename/refactor/migration of existing
> state). No stored data, live service config, OS-registered state, secrets/env vars, or build
> artifacts reference the `redact/` name anywhere yet — confirmed by `grep -ri redact
> yahir_reusable_bot/ tests/ pyproject.toml` returning zero hits before this phase, aside from this
> planning tree itself.

## Code Examples

Verified patterns from the actual proven source (read directly this session):

### The parity target being generalized
```python
# Source: /home/yahir/Projects/WeatherBot/weatherbot/_redact.py (read this session, verbatim)
import re

_APPID_RX = re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE)


def redact_appid(text: str) -> str:
    """Replace every ``appid=<value>`` with ``appid=***``, preserving endpoint + status."""
    return _APPID_RX.sub(r"\1***", text)
```
This is the load-bearing shape the whole phase generalizes: capture-group-preserving backreference,
character-class-negation boundary, `re.IGNORECASE`. WeatherBot's own composition root would register
this as `RedactionPattern(pattern=_APPID_RX, replacement=r"\1***")` unchanged — proving the new API
doesn't force a rewrite of the proven pattern.

### The literal-inside-repr() proof (success criterion 4)
```python
# Source: hub-authored test sketch, tracing the pipeline this session — NOT yet written
def test_literal_matches_inside_repr():
    class _Carrier:
        def __repr__(self) -> str:
            return f"<Carrier secret={SENTINEL!r}>"

    rp = RedactionPattern.literal(SENTINEL)
    text = f"got object {_Carrier()!r} while handling request"
    out = redact_secrets(text, (rp,))
    assert SENTINEL not in out
    assert "***" in out
```
This works with zero special-casing because `redact_secrets` never distinguishes "this text came from
`repr()`" — it is only ever handed a plain `str`. The literal's escaped pattern matches the SENTINEL
substring wherever it physically appears in that string.

### Idempotence + zero-pattern no-op (REDACT-01, D-49)
```python
# Source: hub-authored test sketch
def test_redact_secrets_idempotent():
    rp = RedactionPattern(pattern=re.compile(r"(k=)\w+"), replacement=r"\1***")
    once = redact_secrets("k=abc123&x=1", (rp,))
    twice = redact_secrets(once, (rp,))
    assert once == twice == "k=***&x=1"


def test_redact_secrets_zero_patterns_is_identity():
    assert redact_secrets("anything at all", ()) == "anything at all"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| WeatherBot's app-local, single-hardcoded-pattern `_redact.py` | Hub-owned `redact_secrets(text, patterns)` + registration API serving N consumers with N patterns | This phase (v0.2.0, Phase 5) | The pattern becomes injected, never hardcoded in the hub; the mechanism becomes reusable across future consumers without touching hub source per new secret shape |
| Bare `Iterable[re.Pattern]` (STACK.md's earlier framing) | `RedactionPattern` pairing pattern + replacement (D-48) | Superseded during CONTEXT.md's discuss-phase, this milestone | A bare-pattern API would replace the whole match with a fixed `***`, destroying the `appid=` label — the pairing is what makes "mask the value, preserve diagnostics" possible |

**Deprecated/outdated:** None — this is new, greenfield code; nothing in the hub is being deprecated
by this phase (the app-local `weatherbot/_redact.py` deletion is Phase-9/human-gated, out of this
phase's scope).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ReDoS wall-clock budget of 300ms and the specific 3-string adversarial corpus (repeated `a`, repeated digits, repeated `abc=def&`) are sufficient to reliably reject catastrophic patterns while never false-rejecting a legitimate bounded pattern | Architecture Pattern 3, Common Pitfalls 4/5 | If the budget is too tight: false-rejects a legitimate pattern on a loaded CI box (exactly what CONTEXT.md warns against). If too loose, or the corpus too narrow: a genuinely catastrophic pattern (especially an alternation-based one, not nested-quantifier-based) could slip through. **Mitigation already built into the design:** the corpus/budget are internal implementation details, not public API — they can be tuned in a follow-up commit without touching the public signature. The planner should verify both directions with an explicit test: one known-catastrophic pattern (`(a+)+$` against `"a"*30 + "!"`) MUST be rejected, and WeatherBot's own proven `_APPID_RX` MUST be accepted. |
| A2 | The nested-quantifier regex heuristic (`\([^()]*[+*][^()]*\)[+*]`) is a reasonable, cheap first-pass structural check | Architecture Pattern 3 | It is deliberately non-exhaustive (documented inline) — an alternation-based catastrophic pattern like `(a|ab)*c` would not be caught by this heuristic alone; the timing probe is the actual backstop. If the timing probe's corpus doesn't happen to trigger a given alternation-based pattern's worst case, that specific pattern shape could pass vetting undetected. |
| A3 | `RedactionPattern` should carry an optional `skip_redos_check: bool = False` field (rather than a separate exempt-list parameter to `register_patterns`) to satisfy D-50's "explicit opt-out for a pattern known to be legitimately slow" | Architecture Pattern 1/3 | Low risk — this is a naming/shape choice within Claude's Discretion per CONTEXT.md; either shape satisfies the requirement. If wrong, it's a small, localized rename before any consumer depends on it (this phase IS where the shape gets locked). |
| A4 | 300ms is "generous" enough to avoid false-rejects but was reasoned from general ReDoS literature (WebSearch, MEDIUM confidence) rather than measured against THIS project's actual CI/host hardware | Architecture Pattern 3 | If this host is unusually slow (e.g. under heavy concurrent load during a full-suite run), 300ms could still be tight for an unusually large registered pattern set run back-to-back. Recommend the planner add a task to actually TIME the vetting probe against WeatherBot's real `_APPID_RX` pattern during implementation and confirm it completes in well under 300ms (expect microseconds), rather than trusting this estimate alone. |

**If this table is empty:** N/A — see above; four assumptions need confirmation during
implementation/testing, none blocks planning.

## Open Questions

1. **Should `register_patterns`' return type be a bare `tuple[RedactionPattern, ...]` or a small
   wrapper class (e.g. `RegisteredPatterns`)?**
   - What we know: CONTEXT.md/REQUIREMENTS.md say "frozen into an immutable collection" — a tuple
     already satisfies "immutable."
   - What's unclear: whether a future Phase 6 seam constructor wants a distinguishable type to guard
     against a consumer accidentally passing an un-vetted raw list.
   - Recommendation: return a bare tuple in this phase (simplest, satisfies the requirement exactly
     as worded); if Phase 6 needs a distinguishable type for its seam constructors' type hints, that
     is a Phase 6 decision, not a Phase 5 blocker — a tuple is trivially wrappable later without
     breaking the registration call.

2. **Does `register_patterns` need to detect and reject a duplicate/identical pattern registered
   twice?**
   - What we know: MATCH-03 (Phase 7) established precedent for rejecting duplicates in the sibling
     command registry, but no REDACT requirement mentions duplicate detection.
   - What's unclear: whether two identical patterns registered together are a consumer bug worth
     flagging, or a harmless (if redundant) no-op (redacting the same value twice is idempotent
     per REDACT-01's own idempotence requirement).
   - Recommendation: do NOT add duplicate detection in this phase — it is out of scope
     (REDACT-01/02/03/06 say nothing about it), and idempotence already makes a duplicate harmless
     rather than incorrect. Flag as a candidate for a future rule-of-three revisit only if a real
     consumer hits a footgun from it.

## Environment Availability

> Skipped — this phase has no external dependency beyond the Python 3.12+ interpreter and stdlib
> already required by the whole hub. No new package, service, or CLI tool is introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3+ (already the hub's sole test framework) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q` |
| Full suite command | `uv run pytest -q` (project's configured `test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REDACT-01 | `redact_secrets` masks value, preserves surrounding diagnostics, idempotent, zero-patterns no-op | unit | `pytest tests/test_redact_core.py::test_redact_helper_boundaries -x` | ❌ Wave 0 |
| REDACT-01 | Ported WeatherBot boundary-case matrix (5+ cases: neighbouring params, `&`-stop, URL-encoded value, quote-terminated, case-insensitivity) | unit | `pytest tests/test_redact_core.py -k boundary -x` | ❌ Wave 0 |
| REDACT-01 | Idempotence: re-applying `redact_secrets` to already-redacted text is a no-op | unit | `pytest tests/test_redact_core.py::test_redact_secrets_idempotent -x` | ❌ Wave 0 |
| REDACT-02 | `RedactionPattern` is a frozen dataclass; mutating a field raises `FrozenInstanceError` | unit | `pytest tests/test_redact_core.py::test_redaction_pattern_is_frozen -x` | ❌ Wave 0 |
| REDACT-02 | `register_patterns` returns an immutable collection; identical output whether the hub suite runs `test_redact_registry.py` in isolation or as part of the full suite (no cross-test pollution, no import-order dependence) | unit + suite-order regression | `pytest tests/test_redact_registry.py -x` (isolation) AND `pytest -q` (full-suite order) | ❌ Wave 0 |
| REDACT-03 | A pattern with `(a+)+$`-shaped nested quantifiers is rejected at registration with `ValueError` naming the pattern | unit (adversarial) | `pytest tests/test_redact_registry.py::test_register_patterns_rejects_catastrophic_pattern -x` | ❌ Wave 0 |
| REDACT-03 | WeatherBot's proven `_APPID_RX` passes vetting (no false-reject) | unit (regression) | `pytest tests/test_redact_registry.py::test_register_patterns_accepts_proven_appid_pattern -x` | ❌ Wave 0 |
| REDACT-03 | `skip_redos_check=True` bypasses vetting for an explicitly-exempted pattern | unit | `pytest tests/test_redact_registry.py::test_register_patterns_honors_skip_redos_check -x` | ❌ Wave 0 |
| REDACT-06 | `RedactionPattern.literal(value)` blocks the exact value wherever it appears, including inside a `repr()` | unit | `pytest tests/test_redact_core.py::test_literal_matches_inside_repr -x` | ❌ Wave 0 |
| Litmus (success criterion 5) | Every `def`/`class`/param/annotation name under `redact/` passes the existing AST signature litmus; `redact/` imports no sibling subpackage | standing gate | `pytest tests/test_import_hygiene.py -x` | ✅ (existing, auto-covers new tree) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q`
- **Per wave merge:** `uv run pytest -q` (full suite) + `uv run pytest tests/test_import_hygiene.py -q`
- **Phase gate:** Full suite green, import-hygiene green, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_redact_core.py` — covers REDACT-01, REDACT-06 (core function + `RedactionPattern`
      + literal mode). Does not exist yet.
- [ ] `tests/test_redact_registry.py` — covers REDACT-02, REDACT-03 (registration + ReDoS vetting).
      Does not exist yet.
- [ ] No new fixtures needed in `tests/conftest.py` — every redaction test constructs its own
      `RedactionPattern`/text literals directly (per this repo's "hand-written doubles only, minimal
      conftest" convention, D-10); a shared `SENTINEL` constant (mirroring WeatherBot's
      `test_redact_hygiene.py:29`) may live at the top of each new test module rather than in
      `conftest.py`, since it is not a fixture, just a constant.
- [ ] Framework install: none — pytest is already a dev dependency.

### WeatherBot parity-test plan (human-gated close-out, prepared now per CONTEXT.md's Todos item)

This is NOT executed by this phase's workflow — it is the plan the human-gated repin step (Phase 9,
`ECOSYSTEM.md` §3) will execute, written now so it isn't improvised at repin time (PITFALLS.md
Pitfall 10, STATE.md Todos).

**Which exact WeatherBot assertions must re-pass**, run unmodified from
`/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` against the hub-backed replacement,
with only the import swapped:
1. `test_redact_helper_boundaries` — the 5 boundary-case sub-assertions (neighbouring-params
   preserved, `&`-stop, URL-encoded value, quote-terminated, case-insensitivity).
2. `test_onecall_failure_redacts_key_and_keeps_status` — `str(exc)` AND the FULL rendered traceback
   both clean; `.response.status_code`/exception type preserved.
3. `test_geocode_failure_redacts_key` — same shape, second call site.
4. `test_discord_on_message_does_not_dump_key` — end-to-end Discord path + explicit backstop
   independence assertion (raw un-redacted line still gets scrubbed).
5. `test_reraised_exception_request_carries_no_key` — the `.request`/`repr()` literal-value canary;
   THIS is the test that most directly exercises Phase 5's `RedactionPattern.literal()` mode once
   wired in.
6. `test_livestderr_write_tolerates_and_scrubs_bytes` — non-`str` tolerance; this exercises the
   Phase 6 seam (`_LiveStderr`/`RedactingWriter` wrapping), not the Phase 5 core directly, but must
   still pass unchanged since D-52 locates that tolerance at the seam.

**Explicit scope boundary around `client.py`:** `weatherbot/weather/client.py`'s domain-specific
redacted re-raise (`from None`) is permanently out of PC-01 scope — it is domain logic, stays
app-local forever. The repin step must re-run `test_reraised_exception_request_carries_no_key`
specifically as a scope-boundary check (it exercises the source-level fix independent of the logging
layer) and confirm `client.py` is untouched by the swap.

**Verify PC-01 and WR-02/MATCH-03 independently** before treating a combined repin as ready — this
milestone bundles the redaction promotion with an unrelated breaking change (duplicate `spec.name`
rejection); a single green CI run does not distinguish which change caused a given failure if both
land in the same repin.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — this phase has no auth surface |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A |
| V5 Input Validation | yes | `register_patterns`' ReDoS structural + wall-clock vetting IS the input-validation control for this phase — a consumer-supplied regex is untrusted input to a library that must not let it hang the host process |
| V6 Cryptography | no | No secret storage/hashing/encryption in scope — this phase masks secret VALUES in log text, it does not store or transmit them |

### Known Threat Patterns for stdlib `re` + a synchronous logging path

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| ReDoS via a consumer-registered pathological regex (nested/overlapping quantifiers) | Denial of Service | Registration-time structural + wall-clock vetting (D-50); raise `ValueError`, never accept-and-hang at log time |
| Secret leak via an unanticipated text shape (e.g. inside `repr()`, not just `name=value`) | Information Disclosure | Literal-value redaction mode (D-51/REDACT-06) as an independent, pattern-shape-agnostic backstop |
| Over-redaction destroying operational diagnosability (masking the whole line, not just the value) | (not STRIDE — an availability-of-diagnostics concern specific to this domain) | Character-class-negation boundary style (stop at first delimiter); ported WeatherBot boundary-case matrix as regression proof |
| A future consumer accidentally compiling patterns late / per-call | (performance/DoS-adjacent — a slow hot path degrades service, though not adversarially triggered) | API accepts only precompiled `RedactionPattern` objects; late compilation is structurally impossible, not merely discouraged |

## Sources

### Primary (HIGH confidence)
- `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` — read directly this session, the parity
  target and proven implementation being generalized.
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` (`_LiveStderr.write`) — read directly,
  the non-`str` triage locked by D-52 (Phase 6 seam, referenced here for the contract boundary).
- `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` — read directly, all 6 tests, the
  human-gated parity gate spec used to build the Validation Architecture parity-test plan above.
- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `FEATURES.md`, `PITFALLS.md` — all
  read directly this session, all rated HIGH confidence by their own authors (direct venv/source
  inspection, direct production-code inspection), synthesized here rather than re-derived.
- `.planning/phases/05-redaction-core-pattern-registration/05-CONTEXT.md` — read directly, the locked
  decisions (D-48 through D-53) this research plans against, not around.
- `tests/test_import_hygiene.py`, `tests/conftest.py`, `yahir_reusable_bot/registry/spec.py`,
  `yahir_reusable_bot/registry/registry.py` — read directly this session, confirming the
  `@dataclass(frozen=True)` convention and the D-34 fail-loud-at-registration precedent this phase's
  ReDoS vetting directly follows.
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `pyproject.toml`, `.planning/config.json` — read
  directly this session for requirement text, standing decisions, and dependency/workflow config.

### Secondary (MEDIUM confidence)
- WebSearch, cross-checked against multiple independent sources on ReDoS timeout budgets
  (codereviewlab.com, aikido.dev) confirming ~100ms is a commonly-cited single-check budget in
  general industry practice — used to calibrate this phase's more generous 300ms recommendation
  (A1/A4 in the Assumptions Log). `[classify-confidence: MEDIUM, verified=true — cross-checked
  across independent sources]`

### Tertiary (LOW confidence)
- WebSearch, single-pass, on static nested-quantifier detection tooling (Semgrep/Bento/Dlint
  DUO138) — used only to confirm the "group containing a quantifier, itself quantified" heuristic
  shape is a recognized detection pattern in the wider ecosystem, not adopted as a dependency.
  `[classify-confidence: LOW — single-pass, not independently cross-checked]`

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, verified against this repo's own `uv.lock` in prior
  research; nothing in this phase changes that verdict.
- Architecture: HIGH — the module tree, build order, and API shape are directly specified by
  CONTEXT.md's locked decisions plus ARCHITECTURE.md's Q1/Q6, both read this session.
- Pitfalls: HIGH for the 5 pitfalls sourced from PITFALLS.md (direct source inspection, proven
  production incident); MEDIUM for the specific ReDoS budget/corpus values (A1/A4 — reasoned from
  general literature, not measured against this exact host).

**Research date:** 2026-07-29
**Valid until:** 30 days (stable domain — stdlib `re`, no external dependency churn risk; the only
volatile element is the ReDoS budget/corpus, which the planner/implementer should confirm empirically
during Wave 0 rather than trusting this estimate indefinitely).
