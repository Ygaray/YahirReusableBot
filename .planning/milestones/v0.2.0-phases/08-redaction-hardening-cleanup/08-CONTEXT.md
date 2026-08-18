# Phase 8: Redaction-hardening cleanup - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the four remaining redaction-hardening debt items before the v0.2.0 repin: pin the
write-path malformed-pattern contract, formally resolve the raw-pattern reflection residual, stand
up a static type-check gate for the narrowed `on_online` annotation, and non-vacuously
regression-gate EXTENSION-GUIDE.md §7's prose-only telemetry/reconfigure claims. No new mechanism —
this is hardening, pinning, and gate-building on already-shipped redaction code.

</domain>

<decisions>
## Implementation Decisions

### Redaction write-path hardening
- **D-01 [malformed-write]:** Keep the fail-closed fixed placeholder (`yahir_reusable_bot/redact/sink.py:50-54,157-164`) and pin it as the contract with a RED-first test, AND add an optional `on_error` hook mirroring `on_redaction` so a malformed (`re.error`) pattern on the write path is observable rather than silently swallowed. Never fail-open (would emit the very secret the backstop exists to catch); never raise on the hot path (honors the locked D-52 "never raise inside logging" posture). _(source: human — 06's self-UAT flagged this for owner Gate-2 judgment)_

### Reflection residual
- **D-02 [reflection]:** Formally ACCEPT the raw-pattern-source reflection residual (`dataclasses.asdict`/`astuple`, `.pattern.pattern` echoing a `RedactionPattern.literal(...)` secret). Record the close-vs-accept decision, keep the rationale in `yahir_reusable_bot/redact/core.py`'s docstring + `05-SECURITY.md` (already logged as UF-01), and pin current behavior with a RED-first test. Do NOT introduce an opaque pattern wrapper — a breaking API-shape change to a type WeatherBot is about to pin against immediately before the v0.2.0 repin, and `redact_secrets` needs `.pattern.sub()` reachable. Accidental `vars`/`__dict__` paths are already closed by `slots=True`. _(source: human)_

### Type-checking gate
- **D-03 [type-checker]:** Adopt pyright in `basic` mode with a first-run baseline (baseline-and-burn-down); land the gate green now and keep the existing `get_type_hints` assertions as the narrow enforcement for SURF-02's three signatures (retire-vs-belt-and-suspenders decided explicitly at plan time). Not mypy; not strict/whole-surface now — the surface is deliberately `Any`-at-seams and a fix-all would flood this bounded pre-repin cleanup phase. _(source: human)_

### Documentation regression gates
- **D-04 [doc-gate]:** Add two token-anchored regression tests to `tests/test_extension_guide.py` — one pinning the "changed writes, not substitutions / monotonic" telemetry semantics, one pinning the "call `assert_redaction_active` again after any reconfiguration" discipline — each with its own non-vacuity self-proof (write a broken temp copy → re-run the gate → assert it fails), mirroring the existing Known-limitations gate at `tests/test_extension_guide.py:324-403`. The only real optionality is anchor-token selection; avoid colliding with the recipe-2 `"before any"` assertion at `:123`. _(source: ai-auto — research recommendation; low optionality)_

### Claude's Discretion
- Anchor-token selection for the two D-04 doc-gate tests (subject to the no-collision constraint above).
- Whether the D-01 `on_error` hook's signature/payload mirrors `on_redaction` exactly or carries the offending pattern identity — decide at plan time against the existing hook shape.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Decisions source
- `.planning/v0.2.0-DECISION-MAP.md` § Phase 8 — the four resolved gray areas (WR-03, WR-02, HYG-04, DOCS-05) that this CONTEXT captures.

### Roadmap & requirements
- `.planning/ROADMAP.md` § Phase 8 — phase goal/scope and the human-gated repin close-out that follows this phase.
- `.planning/REQUIREMENTS.md` — REDACT-09 (WR-02), REDACT-10 (WR-03), HYG-04, DOCS-05 (T-06-16), SURF-02.
- `.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md` — type-checker adoption rationale feeding D-03.

### Implementation surfaces
- `yahir_reusable_bot/redact/sink.py` §§ 50-54, 157-164 — the fail-closed write-path placeholder pinned by D-01.
- `yahir_reusable_bot/redact/core.py` — `RedactionPattern` reflection paths + docstring rationale for D-02.
- `tests/test_extension_guide.py` §§ 324-403 (Known-limitations gate pattern), :123 (recipe-2 `"before any"` anchor to avoid) — model + constraint for D-04.
- `.planning/phases/05-redaction-core-pattern-registration/05-SECURITY.md` — UF-01, the accepted-residual ledger D-02 extends.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `on_redaction` hook: the D-01 `on_error` hook mirrors its shape/registration path.
- Known-limitations regression gate (`tests/test_extension_guide.py:324-403`): the non-vacuity self-proof pattern D-04's two new tests copy.
- `get_type_hints` runtime assertions: already enforce SURF-02's three signatures; the pyright gate (D-03) sits alongside them.

### Established Patterns
- RED-first pinning tests: D-01 and D-02 both land as RED-first contract pins before any code change.
- `slots=True` on `RedactionPattern`: already closes the accidental `vars`/`__dict__` reflection paths (D-02 only concerns the explicit paths).

### Integration Points
- `RedactingWriter.write` (`sink.py`) is the hot path where the D-01 malformed-pattern contract lives.
- pyright config + baseline file (new) become a standing CI/local gate (D-03).

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the four resolved decisions — standard RED-first pinning and gate-building approaches apply.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. The v0.2.0 repin/deploy itself remains human-gated and out of this phase (see ROADMAP.md close-out).

</deferred>

---

## Runtime Decisions

- **2026-08-18 — HYG-04 pyright install APPROVED (operator).** The execute stage held on
  `uv add --dev pyright` because the automated package-legitimacy check returned SUS — caused
  solely by a `pypistats.org` rate-limit (HTTP 429) that emptied the download-count signal, not by
  any real red flag. Operator reviewed and approved the install: `pyright` (the
  `RobertCraigie/pyright-python` wrapper — the de-facto PyPI channel for Microsoft's pyright, 206
  releases over ~6 years, active repo) lands in `[dependency-groups].dev` ONLY, never
  `[project].dependencies`, so it can never reach a hub consumer. This confirms locked decision
  **D-03** (pyright basic-mode static type check). Proceed with the install and complete HYG-04.

---

*Phase: 8-redaction-hardening-cleanup*
*Context gathered: 2026-08-17*
