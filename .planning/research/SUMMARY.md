# Project Research Summary — v0.2.0 PC-01 Secret-Redaction Backstop

**Project:** yahir_reusable_bot (reusable hub)
**Milestone:** v0.2.0 — Redaction promotion + hardening debt
**Domain:** Generic log secret-redaction backstop for a channel-agnostic bot library
**Researched:** 2026-07-29
**Confidence:** HIGH

**Scope note:** This summary covers **PC-01 only**. The v0.2.0 milestone also contains 7 code-debt
items (from the v0.1.2 audit) and 2 doc-drift corrections. Those needed no research and are
deliberately absent here.

---

## Executive Summary

The research converges on a concrete, already-proven design: generalize WeatherBot's production
`_redact.py` / `_LiveStderr` backstop into a hub mechanism serving N consumers with N patterns.
**Zero new dependencies** — `structlog` is already pinned (resolved 26.1.0) and stdlib `re` covers
the entire redaction core.

Three of the four researchers independently concluded that the **sink/stream-wrapper seam is the
load-bearing insertion point**, not a processor alone. The processor chain has a structural blind
spot: exception renderers such as `dev.ConsoleRenderer` self-render tracebacks directly to the
output stream, bypassing `event_dict` entirely. Only a sink-level hook sees the fully-rendered text
(event + formatted traceback) that the original F12 leak proved needs scrubbing. This convergence
was reached from three different angles — stack-level API introspection, production-code evidence,
and direct source inspection of the installed `structlog` — which is why it is stated here as a
finding rather than an option.

The one genuine API conflict (global mutable registry vs. explicit construction) is **resolved and
compatible** — see below.

---

## Key Findings

### Recommended Stack

**ZERO new dependencies.**

- **`structlog` (resolved 26.1.0, already pinned `>=26.1.0`)** — the hub's sole logging library.
  Two insertion seams exist: the processor chain (operates on `event_dict` pre-render) and the
  `PrintLoggerFactory(file=...)` duck-typed sink (fully-rendered text). Both are reused as-is.
- **stdlib `re` (Python 3.12+)** — pattern compilation and substitution. Note: stdlib `re` has **no
  timeout**, so ReDoS mitigation must happen at registration time, not runtime.

**Rejected prior art:** `scrubadub` (drags in scikit-learn/faker/dateparser/textblob — an NLP/PII
stack, wildly disproportionate); `loggingredactor` (right API shape, but a young 0.0.x package
delivering nothing `structlog` + `re` don't already cover in ~15 lines).

**Ordering constraint (stack-verified):** a redaction *processor* must run after
`format_exc_info` / `ExceptionRenderer` / `dict_tracebacks` and as late as possible in the chain,
or it never sees formatted traceback text at all.

### Expected Features

**Table stakes:**
- Scrub the fully-rendered output (event + formatted traceback in one pass), not just structured fields
- Work independently of processor-chain order and renderer choice
- Preserve non-secret diagnostics — mask the value, keep endpoint / HTTP status / surrounding params
- Idempotent; tolerate non-`str` input (e.g. bytes) without raising mid-exception-handling
- Zero behavior change beyond redaction (exception type, `.response`, log level all untouched)

**Differentiators (candidates, not table stakes):**
- Per-pattern replacement string (default `***`, overridable)
- Redaction-count telemetry / a self-check canary helper (`assert_redaction_active`)

**Anti-features — explicitly reject:**
- **Entropy-based auto-detection** — nondeterministic, false-positives on ordinary high-entropy log
  data (request IDs, hashes), and destroys diagnosability
- **Built-in secret patterns shipped in the hub** — violates the "no domain noun in the hub surface"
  litmus; patterns belong to consumers
- **Processor-only design** — proven by the originating incident to miss the traceback path
- **Failing open by swallowing exceptions inside the log path** — masks the very error being logged

### Pattern-Registration API — conflict resolved

The three researchers who touched this reached **compatible**, not opposing, conclusions:

| Researcher | Position |
|---|---|
| FEATURES | Reject a global mutable registry; use explicit constructor-threaded patterns |
| ARCHITECTURE | House pattern registration in a `redact/registry.py` module |
| PITFALLS | Prefer an explicit constructed object over a global mutable singleton |

**Resolution:** `redact/registry.py` houses a **stateless API and the pattern type** — not a
process-wide singleton consumers mutate at import time. Patterns are registered once at the
consumer's composition root, compiled once, frozen into an immutable tuple, and passed *explicitly*
into the seam constructors. This satisfies "compile once, reuse many times" without import-order
dependence or cross-test pollution, and it matches the hub's existing dependency-injection shape
(the same posture as the `Channel` and `JobStore` ports).

The module name `registry.py` is therefore fine; a module-level mutable singleton inside it is not.

### Architecture Approach

**Two insertion seams over one shared `redact_secrets()` core:**

1. **Sink / stream wrapper — PRIMARY, load-bearing.** Wraps the `PrintLoggerFactory(file=...)`
   target. Intercepts fully-rendered text (event + formatted traceback fused into one `write()`
   call) and scrubs before forwarding. The only point guaranteed to catch both event fields and
   tracebacks regardless of renderer. Generalizes WeatherBot's proven `_LiveStderr`.
2. **Structlog processor — SECONDARY, optional, additive.** Walks `event_dict` string values.
   Catches field-level secrets, and formatted exception text *only if* placed after the exception
   formatters in the consumer's own chain. That conditionality is exactly why it cannot be the sole
   seam for a security backstop.

**New subpackage `yahir_reusable_bot/redact/`:**

```
redact/
├── __init__.py     # public surface re-exports
├── core.py         # redact_secrets(text, patterns) -> str; RedactionPattern type
├── registry.py     # stateless registration API + frozen pattern collection
├── sink.py         # RedactingWriter — wraps a file-like target (PRIMARY seam)
└── processor.py    # redaction_processor — optional structlog processor (SECONDARY seam)
```

**Import-hygiene impact: none structural.** `redact/` is a pure leaf subpackage (stdlib, plus
`structlog` for `processor.py` only). All three existing gates auto-cover it with no test changes.
The only discipline required is naming: `redact_secrets(text, patterns)`, never `redact_appid` or an
`appid` parameter.

**New seam SEAM-08** in `EXTENSION-GUIDE.md` — architecturally inverted relative to the other seams:
the hub provides a toolkit the consumer wires into its own `structlog.configure()`, rather than a
Protocol the hub calls. Note: `SEAM-02` is missing from the guide with no explanation in any
artifact; 08 is the next free number by exhaustive search.

**Relevant fact:** no hub module calls `structlog.configure()` today — every module only calls
`structlog.get_logger(__name__)`. Logging configuration is 100% consumer composition-root policy.
PC-01 must therefore ship as a toolkit the consumer wires, never a hub-owned `configure()` call.

### Critical Pitfalls (top 5 of 10)

1. **Processor-chain redaction has a structural traceback blind spot.** *Mitigation:* sink primary,
   processor optional-additive; test both against `logger.exception(...)` with a real traceback.
2. **A second `structlog.configure()` call silently drops the backstop.** *Mitigation:* anchor the
   backstop at a shared sink object that all configure sites route through, not in one site's
   processor list. Consider a self-check helper.
3. **ReDoS from a consumer-supplied pattern.** Amplified here: hub logging is synchronous and the
   Discord adapter runs an asyncio gateway loop, so a pathological pattern can starve heartbeats and
   drop the live connection. Stdlib `re` has no timeout. *Mitigation:* registration-time adversarial
   vetting against a wall-clock budget; reject patterns that blow it. Prefer a safe pattern-builder
   over raw regex.
4. **Over-broad patterns destroy diagnosability; under-broad ones leak partial tokens.**
   *Mitigation:* character-class-negation boundary style; support literal-value redaction; port
   WeatherBot's boundary-case test matrix into the hub suite.
5. **Swapping WeatherBot's proven `_redact.py` without proving parity first.** *Mitigation:* run
   WeatherBot's existing, **unmodified** `tests/test_redact_hygiene.py` (verified: 6 tests) against
   the hub-backed replacement *before* deleting the app-local copy. Scope the swap to the backstop
   only — `client.py`'s domain-specific redacted re-raise stays app-local permanently and is
   explicitly out of PC-01 scope.

---

## Implications for Roadmap

**Decisions the requirements phase must make:**

1. **Ship both seams, or only the proven sink?** Research recommends both, with the sink required
   and the processor optional-additive and clearly documented as chain-order-sensitive.
2. **Telemetry / self-check canary in scope?** Leaning defer — differentiators, not table stakes.
3. **Literal-value redaction mode** — recommended for inclusion (addresses unanticipated leak paths
   that pattern-based matching misses).
4. **Registration-time ReDoS vetting** — treated as non-negotiable by the pitfalls research.
5. **Migration parity gate** — WeatherBot's 6 existing tests must pass against the hub-backed
   replacement before `_redact.py` is deleted.

**Build order (dependency-respecting):**
core → registry/pattern type → **sink (prove this first — it alone satisfies the hard requirement)**
→ processor → public re-exports → `EXTENSION-GUIDE.md` SEAM-08 → GATE-01 → [human-gated] tag /
repin / WeatherBot swap.

> **Orchestrator note (not a research finding):** the synthesizer proposed a 9-phase structure that
> is over-decomposed for a milestone this size — "public re-exports", "import-hygiene gates", and
> "documentation" are task-sized, not phase-sized, and the hygiene gates are a standing gate
> (GATE-01) rather than a phase. Treat the build order above as a **dependency ordering**, and let
> the roadmapper set actual phase boundaries. This milestone also carries the debt and doc-drift
> work, which the research phase structure does not account for at all.

---

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Stack | HIGH | Verified against this repo's `uv.lock` + `uv pip show` + live introspection of the installed package — not recalled |
| Features | HIGH | Grounded in real production code and its regression suite; table stakes proven by a live incident |
| Architecture | HIGH | Direct read of the actual package tree, the import-hygiene gates, and ECOSYSTEM.md |
| Pitfalls | HIGH | Proven implementation + regression suite + direct source inspection of installed `structlog` (empirically verified the exc_info blind spot) |
| Prior-art libraries | LOW–MEDIUM | Web-search digests only; used purely to justify rejection, never adopted |
| ReDoS specifics | MEDIUM | Community/security consensus, not project-specific measurement |

**Overall: HIGH**

---

## Sources

- **Primary (direct inspection):** this repo's `uv.lock`, `pyproject.toml`, `tests/test_import_hygiene.py`,
  `EXTENSION-GUIDE.md`, `ECOSYSTEM.md`, and the full `yahir_reusable_bot/` package tree.
- **Installed-package introspection:** `structlog` 26.1.0 in this repo's `.venv` — processor signature,
  `PrintLoggerFactory.__init__`, and `structlog/dev.py` `ConsoleRenderer` traceback-rendering path.
- **Promotion source (production evidence):** `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py`,
  its `_LiveStderr` wiring, and `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` (6 tests).
- **Project artifacts:** `.planning/PROJECT.md`, `.planning/backlog/PROMOTION-CANDIDATES.md`,
  `.planning/v0.1.2-MILESTONE-AUDIT.md`.
- **Surveyed and rejected:** `scrubadub` 2.0.1, `loggingredactor` 0.0.7 (web sources; rejection rationale only).
- **Detail files:** `.planning/research/STACK.md`, `FEATURES.md`, `ARCHITECTURE.md`, `PITFALLS.md`.

---

_Synthesized: 2026-07-29. Note: written by the orchestrator via the #222 self-heal path — the
synthesizer agent returned this document inline while fabricating a file-write restriction instead
of writing it. Content is the agent's; the Sources section and the orchestrator note above were
added during persistence, and the phase-structure claim was annotated rather than silently kept._
