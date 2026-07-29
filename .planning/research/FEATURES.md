# Feature Research

**Domain:** Log secret-redaction backstop (renderer-agnostic, structlog-hosted, library-owned mechanism / consumer-owned patterns)
**Researched:** 2026-07-29
**Confidence:** HIGH (primary evidence is a real, proven, production implementation read directly from source — see Sources) with LOW-confidence supplementary web context for general industry framing

## Primary Evidence

This research is grounded first in the actual, shipped, production implementation being
promoted — not speculation about how redaction "typically" works. Read directly:

- `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` (28 lines) — the pure `redact_appid(text) -> text` core, one hardcoded pattern (`appid=<value>`), non-greedy stop-at-delimiter regex.
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py:26-62` — the `_LiveStderr` choke point: a `structlog.PrintLoggerFactory(file=_LiveStderr())` sink whose `.write()` scrubs every rendered line (event + traceback, single call) before it reaches stderr, plus non-`str`/`bytes` input tolerance (WR-02).
- `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` — the regression suite proving the backstop independently catches a raw, un-redacted leak even when the source-level fix is also present ("belt-and-suspenders"), and that redaction preserves endpoint/status for diagnosability.
- `/home/yahir/Projects/WeatherBot/.planning/milestones/v2.1-phases/30-secret-hygiene/30-CONTEXT.md` — the design decisions (D-01/D-02/D-03) and the hard hard hard constraint that redaction must never change exception *type*.

General industry patterns (structlog docs, OWASP Logging Cheat Sheet, Python redaction
libraries, entropy-based secret-scanning tools) were checked via web search to confirm this
production implementation is not an outlier — see Sources. Those findings carry LOW confidence
individually (single-pass web search, not cross-verified) and are used only as corroborating
context, never as the basis for a table-stakes/anti-feature classification on their own.

## Feature Landscape

### Table Stakes (Consumers Expect These)

Features a generic redaction backstop must have, or it isn't actually a backstop.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Scrub the fully rendered/formatted message string, not just structured fields | This is the *entire reason* the backstop exists (F12): a raw `_log.exception(...)` call renders event + full traceback through the renderer in one shot, bypassing any per-field processor. Redacting only `event_dict` values misses this. | LOW | Core is a pure `redact_secrets(text, patterns) -> text` function — proven at `_redact.py`. |
| Scrub formatted exception tracebacks (not just `str(exc)`) | The proven leak path (D-02, `test_discord_on_message_does_not_dump_key`) is `_log.exception(...)` dumping a full traceback to stderr; `str(exc)` alone is insufficient — WeatherBot's test asserts the sentinel is absent from `traceback.format_exception(...)` output too. | MEDIUM | Only achievable by hooking the final-write choke point (structlog's `PrintLoggerFactory(file=...)` target) or an equivalent renderer-agnostic seam — NOT a mid-chain processor alone, since processors run before traceback rendering. |
| Work independent of / underneath the structlog processor chain | D-02's whole design point: "a safety net for future code" that catches a call site nobody remembered to scrub at the source. A processor-only design is defeated the moment a consumer's config omits it or a future call site is added carelessly. | MEDIUM | Depends on existing structlog usage (hub already has this dep) — the seam is `PrintLoggerFactory(file=<wrapped-stream>)`, generalizing `_LiveStderr`. |
| Preserve non-secret diagnostics (endpoint, status code, surrounding params) — mask, don't delete | D-03, hard requirement: "keep the failing endpoint URL and HTTP status visible." A redaction that nukes the whole line/value defeats live-debugging; this is the difference between a security fix and a logging blackout. | LOW-MEDIUM | Regex captures the value up to (not including) the first delimiter — proven boundary logic already exists to generalize. |
| Idempotence (redacting already-redacted text is a no-op) | A backstop is likely to run in more than one place (source-level scrub + sink backstop, "belt-and-suspenders" by design). If the placeholder itself could be re-matched or mangled, double-application would corrupt otherwise-clean log lines. | LOW | Natural consequence of a well-bounded regex + a placeholder token that can't itself match the pattern (e.g. `***` contains no `=` or key-like text) — worth one explicit regression test, not new mechanism. |
| Tolerate non-`str` input (e.g. stray `bytes` write) without raising | WR-02, already proven necessary in production: a crash *inside* the logging path — especially mid-exception-handling — can mask the original error, which is strictly worse than an unredacted line. | LOW-MEDIUM | `_LiveStderr.write` decodes `bytes` before scrubbing; anything else passes through untouched rather than raising. |
| Case-insensitive key matching | Proven test case: `APPID=` must redact same as `appid=`. A backstop that only catches the exact-case form a developer happened to type is fragile. | LOW | `re.IGNORECASE` — trivial to carry into the generalized core. |
| Zero behavior change beyond redaction (exception type, `.response`, log level, envelope semantics all untouched) | D-hard-constraint: 6+ downstream call sites branch on `httpx.HTTPStatusError` type/`.response.status_code`. Any redaction mechanism that requires changing an exception's type or losing attributes is disqualified regardless of how clean the redaction itself is. | LOW (given text-only scrubbing) | Reinforces: the backstop operates on *rendered text*, never on live exception/event objects — it can't accidentally violate a type contract if it never touches the objects. |

### Differentiators (Worth Considering, Not Required)

Features that improve on the proven WeatherBot baseline without contradicting it.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-pattern replacement string (not a single hardcoded `***`) | WeatherBot hardcodes `***`; a hub used by N consumers may want `appid=***` vs `token=[REDACTED]` vs a partial mask, without forking the core. | LOW | Natural generalization: each registered pattern carries its own compiled regex *and* its own replacement template (defaulting to `***` if unspecified). |
| Partial masking preserving a prefix/suffix for correlation (e.g. `sk-***last4`) | WeatherBot's full-mask (`appid=***`) throws away which key was in play — fine for a single-key app. A multi-key or key-rotation consumer may want to distinguish "which secret leaked" across log lines without ever printing the secret itself. | MEDIUM | Not proven by any current consumer — flag as differentiator, not table stakes, until a second consumer actually needs it (rule-of-three discipline already governs this repo). |
| A "did anything get redacted" signal (count or boolean return) | Useful as a build-time/test-time canary: "the backstop fired at least once" is exactly what `test_redact_hygiene.py` already asserts manually (`"appid=***" in err2`). Making it a first-class return value (e.g. `redact_secrets` returns `(text, count)` or the sink exposes a counter) turns that ad-hoc assertion into a supported API, and lets an operator alert on unexpectedly-high redaction counts (possible active leak). | LOW-MEDIUM | Optional — the simple `text -> text` signature is sufficient for the litmus; this is additive telemetry, not required for correctness. |
| Multiple independent named patterns registered together (e.g. tuple of `(name, regex, replacement)`) | The hub will serve more than one consumer with more than one secret shape over time (WeatherBot's `appid`; a future consumer's token, webhook secret, etc.) — the API should accept N patterns from day one even though today there is exactly one proven pattern. | LOW | This is really just "the construction API accepts a sequence, not a single value" — cheap to design in now, expensive to retrofit later (every call site would need updating). |
| Frozen/precompiled pattern set at construction (compile-once, not per-call) | Logging is on the hot path in a live daemon; recompiling regex per log line is wasteful. | LOW | `re.compile` once at wiring time, store as an immutable tuple — standard practice, not a novel feature. |

### Anti-Features (Reject These, With Reasons)

| Feature | Why It Looks Appealing | Why Reject | Alternative |
|---------|------------------------|------------|-------------|
| Entropy-based auto-detection of "secret-looking" strings (Shannon entropy / byte-pair heuristics) | Sounds like it would catch secrets nobody thought to pattern-match — "defense in depth without maintenance." | Entropy heuristics are a *discovery* tool for scanning large corpora (git history, codebases) where occasional false positives are cheap to triage by a human — see gitleaks/trufflehog, which still need per-rule tuning and layered signals to control noise from UUIDs, hashes, and base64 blobs. A per-line, always-on log backstop needs deterministic, zero-false-positive behavior on the happy path: a live daemon's stderr getting speckled with `***` over ordinary non-secret high-entropy tokens (request IDs, hashes) actively destroys the diagnosability D-03 explicitly protects. | Explicit, consumer-authored regex patterns only — deterministic, reviewable, testable per pattern. |
| Shipping dozens of built-in patterns for common secret shapes (AWS keys, JWTs, generic API-key regexes, etc.) | Feels like "batteries included" — a new consumer gets protection for free. | Violates this repo's own litmus directly: "no domain noun may enter the hub surface." A built-in `AWS_ACCESS_KEY_ID` pattern *is* a domain assumption baked into a supposedly generic hub, and it's also an unbounded maintenance surface (secret shapes change constantly; the hub would be perpetually behind). PROJECT.md's PC-01 constraint is explicit: only the *pattern* is consumer-specific and it must be *injected*, never hardcoded. | The hub ships the mechanism + zero patterns; every consumer (starting with WeatherBot's `appid=<key>`) supplies its own pattern list at its own composition root. |
| Redacting only structured `event_dict` fields (a pure structlog processor, no sink-level hook) | Simpler to implement — "just add a processor to the chain," idiomatic structlog. | This is the exact anti-pattern F12 already proved fails in production: `_log.exception(...)` renders the full traceback through the exception formatter, which runs downstream of / independent from the field-level processor chain. A processor-only design would have caught nothing in the Discord `on_message` leak that motivated this whole feature. | Hook the final render/write choke point (the `PrintLoggerFactory(file=...)` target), optionally *in addition to* a processor for consumers who configure an explicit chain — but never processor-only as the sole mechanism. |
| Making redaction failures silent/fail-open in a way that swallows exceptions from the logging path itself | Feels safer — "never let logging crash the app." | Taken too far, this becomes the WR-02 bug it's meant to prevent: if the redaction call itself can raise (e.g. `TypeError` on unexpected input) and that isn't specifically guarded, the exception surfaces *inside* exception-handling code, which can mask the original error being logged — worse than an unredacted line. The fix is a scoped, deliberate input-tolerance contract (decode bytes, pass through anything else), not a blanket try/except around all logging. | Explicit, narrow tolerance rules (documented input types accepted, documented fallback), never a bare `except Exception: pass` around the write path. |
| Deleting/blanking the entire matched value's surrounding line or query string rather than masking just the secret's value | Looks "safer" — less surface area for something to slip through. | D-03 is explicit and hard-won: over-redaction destroys live diagnosability (which endpoint failed, what status code) — exactly the operational data the daemon needs to distinguish "the API key rotated" from "the API is down." A backstop that isn't safe to leave on because it blinds operators isn't a backstop, it's a liability. | Bound each pattern's replacement to the *value* only, stopping at the first natural delimiter — proven boundary logic already exists to generalize. |
| A module-level mutable pattern registry with a global `register_pattern()` call, patterns accumulating as a process-wide singleton | Looks convenient — any module can call `register_pattern(...)` without threading an argument everywhere; mirrors how some logging libraries expose global filters. | This is the textbook "global mutable state in a reusable library" smell this codebase explicitly avoids elsewhere (per CLAUDE.md's litmus discipline). Concretely: (1) import order determines what's registered when, which is invisible and hard to reason about; (2) tests in the same process leak state into each other unless every test remembers to reset the registry — a footgun class this milestone (WR-02, review nits) already exists to close, not reopen; (3) a library should never assume it owns exactly one process-wide configuration — a caller wiring two independent bot instances (however unlikely) couldn't give them different pattern sets. | See the Pattern-Registration API Comparison below — explicit, constructor/factory-threaded patterns, frozen at wiring time. |

## Pattern-Registration API Comparison

The hub owns the mechanism; each consumer supplies its own patterns (WeatherBot: `appid=<key>`).
Four plausible shapes, evaluated for statefulness and testability in a **library** (not app)
context:

| Shape | Statefulness | Testability | Verdict |
|-------|--------------|--------------|---------|
| Module-level registry + `register_pattern()` | Process-wide mutable global; import-order-dependent; accumulates across the process lifetime | Poor — tests must reset/monkeypatch the registry or leak state across test files; no way to construct two independently-configured instances in one process | **Reject.** This is exactly the anti-feature above — a known smell explicitly flagged by the milestone's own concerns about statefulness. |
| Config-driven pattern list (parsed from YAML/env/file) | Stateless at the redaction layer, but pushes config-parsing responsibility onto the hub | Fine for the redaction core itself, but adds an unnecessary dependency/format the hub doesn't otherwise own — the hub has no existing config-loading mechanism to reuse (contrast: WeatherBot's `_redact.py` is a pure function with zero config) | **Reject as the primary shape.** Overbuilt for the actual need; a consumer can trivially load its own config and pass the resulting patterns through the explicit-argument shape below — no reason for the hub to parse config itself. |
| Explicit patterns argument threaded through construction (e.g. `redact_secrets(text, patterns)`, `RedactingSink(patterns=...)`) | Stateless core function; any state lives in one object instantiated once at the consumer's composition root | Excellent — pass a list of fixture patterns, assert output, no global to reset, no import-order sensitivity, trivially parallelizable in tests | **Recommended primary shape.** Directly generalizes the proven `redact_appid(text) -> text` shape (WeatherBot's `_redact.py`) from one hardcoded pattern to N injected ones — same mental model, same testability, zero new statefulness introduced. |
| Frozen tuple passed at wiring time (immutable snapshot, compiled once) | Effectively stateless from the caller's perspective — the "state" is an immutable value object, not mutable registry state | Excellent — same testability as above, plus guards against accidental runtime mutation (no `.append()`/`.register()` method to call mid-run) | **Recommended as the internal representation.** Combine with the row above: the public constructor accepts any `Sequence[Pattern]`, and internally freezes/compiles it once into a tuple at construction — the class becomes a thin, stateless-feeling wrapper around a pure `redact_secrets` fold. |

**Net recommendation:** a pure core `redact_secrets(text: str, patterns: Sequence[Pattern]) -> str`
(mirroring `_redact.py`'s proven shape exactly, generalized from a single hardcoded regex to an
injected sequence), plus a thin wrapper object (the `_LiveStderr`-equivalent choke point, or a
structlog processor) constructed **once** at the consumer's composition root with a frozen tuple
of compiled `(pattern, replacement)` pairs. No module-level state anywhere in the hub. This keeps
the mechanism testable as a pure function (unit tests pass literal pattern lists, assert output —
exactly like `test_redact_helper_boundaries` already does) while the wiring-time object satisfies
the "compile once, not per log line" performance concern.

## Composition Behavior (Edge Cases)

| Scenario | Expected Behavior | Complexity | Rationale |
|----------|--------------------|------------|-----------| 
| Consumer registers **zero** patterns | Identity/no-op passthrough — `redact_secrets(text, ())` returns `text` unchanged; constructing the wrapper with an empty sequence must not error | LOW | An empty pattern sequence is the natural base case of a sequential-substitution fold; no special-casing needed if the core is written as a plain loop/`functools.reduce` over patterns. A consumer with genuinely no secrets to scrub (however unlikely in practice) should still be able to wire the mechanism without contriving a placeholder pattern. |
| **Overlapping** patterns (two registered patterns could both match overlapping text) | Apply sequentially in registration order — each pattern's `re.sub` runs against the output of the previous one | LOW-MEDIUM | No new mechanism required (a straightforward sequential-apply loop already has this behavior for free), but the ordering contract must be **documented** explicitly so a consumer registering multiple patterns can reason about which one "wins" a shared span. Needs one explicit regression test, not new code. |
| A pattern that matches (or could match) the **entire line** | Accepted outcome: the whole line collapses to the replacement — this is a **consumer pattern-authoring responsibility**, not a hub-side defensive check | LOW | The hub's contract is "your regex, your bounding logic" — exactly as `_APPID_RX`'s non-greedy stop-at-delimiter design already is authored by the consumer, not imposed by a hub-side heuristic. Adding hub-side "don't let a pattern eat too much" logic would itself be a novel, untested, and unrequested safety net for a problem no consumer has actually hit — appropriately out of scope. Document the expectation ("scope your regex to the value, not the whole message") as guidance in the pattern-registration API's docstring/EXTENSION-GUIDE entry, not as enforced runtime behavior. |

## Feature Dependencies

```
Existing: structlog dependency (already in hub) + existing structlog.configure call sites
    └──required-by──> Sink/processor insertion seam (generalized _LiveStderr choke point)
                           └──required-by──> Full-traceback redaction (table stakes)

redact_secrets(text, patterns) pure core  [no new dependency]
    └──required-by──> Sink/processor wrapper (wiring-time object holding frozen pattern tuple)
                           └──required-by──> Pattern-registration API (constructor argument)

Pattern-registration API (explicit constructor arg)
    └──enables──> Zero-patterns no-op case
    └──enables──> Per-pattern replacement string (differentiator)
    └──enables──> Multiple named patterns (differentiator)

Per-pattern replacement string ──enables──> Partial masking (prefix/suffix preserved) (differentiator)

Module-level registry (rejected) ──conflicts-with──> Testability / statelessness (table-stakes-adjacent library requirement)
Entropy-based detection (rejected) ──conflicts-with──> Deterministic zero-false-positive redaction (table stakes)
```

### Dependency Notes

- **Full-traceback redaction requires the sink/choke-point seam, not the processor chain alone:**
  this is the single most load-bearing dependency in this feature — it's the reason PC-01 exists
  at all (F12's Discord `on_message` leak bypassed field-level processors entirely).
- **The pattern-registration API requires nothing new** beyond the pure `redact_secrets` core —
  it's a signature/construction-shape decision, not a new dependency. This is why it's the
  cheapest and highest-leverage decision to get right up front (retrofitting a single-pattern API
  into a multi-pattern one later would touch every call site).
- **The rejected module-level registry conflicts with** this repo's own stated concern (per the
  milestone brief) that "global mutable state is a known smell in a reusable hub" — this isn't a
  new judgment call, it's already the project's stated position, and the API comparison above
  simply confirms the explicit-construction alternative satisfies it.
- **No dependency on structlog beyond what already exists.** The hub already depends on
  `structlog`; the redaction sink/processor is additive wiring against an existing dependency, not
  a new one.

## MVP Definition

### Launch With (v1 — this milestone, PC-01)

- [ ] `redact_secrets(text: str, patterns: Sequence[Pattern]) -> str` pure core — generalizes
      `_redact.py`'s proven single-pattern regex-substitution to N injected patterns.
- [ ] A sink/choke-point wrapper (generalized `_LiveStderr`) that scrubs every rendered write —
      event fields AND formatted tracebacks — constructed once at the consumer's composition root
      with a frozen tuple of compiled patterns.
- [ ] Explicit-argument (not global-registry) pattern-registration API, per the comparison above.
- [ ] Idempotence, case-insensitivity, non-`str`/`bytes` input tolerance, value-boundary masking
      (mask the value, preserve the line) — all directly proven necessary by the WeatherBot
      production incident and its regression suite.
- [ ] Zero built-in patterns shipped in the hub — WeatherBot's `appid` pattern stays registered
      by WeatherBot at its own composition root, not hardcoded in the hub.

### Add After Validation (v1.x)

- [ ] Per-pattern replacement string (default `***`, override-able) — trivial to add once the
      multi-pattern API exists; add when/if a second consumer needs a different placeholder.
- [ ] "Did anything get redacted" count/signal — nice-to-have telemetry; add if operational
      visibility into backstop activity becomes a real ask.

### Future Consideration (v2+, only if a second consumer needs it — rule of three)

- [ ] Partial masking preserving a prefix/suffix for correlation — no current consumer need;
      building it now would be designing against an imagined requirement, which this repo's own
      Extension Discipline explicitly avoids.
- [ ] Named-pattern introspection/debugging helpers — defer until multiple consumers register
      enough patterns that "which pattern fired" becomes a real debugging question.

## Feature Prioritization Matrix

| Feature | Consumer Value | Implementation Cost | Priority |
|---------|-----------------|----------------------|----------|
| Pure `redact_secrets(text, patterns)` core | HIGH | LOW | P1 |
| Sink/choke-point full-render + traceback scrubbing | HIGH | MEDIUM | P1 |
| Explicit-argument pattern-registration API | HIGH | LOW | P1 |
| Zero built-in patterns (hub stays domain-free) | HIGH (litmus-critical) | LOW (it's an omission, not work) | P1 |
| Idempotence / case-insensitivity / bytes-tolerance | MEDIUM-HIGH (proven-necessary) | LOW | P1 |
| Per-pattern replacement string | MEDIUM | LOW | P2 |
| Redaction-count telemetry signal | LOW-MEDIUM | LOW-MEDIUM | P2 |
| Partial prefix/suffix masking | LOW (no proven consumer need yet) | MEDIUM | P3 |
| Config-driven pattern loading | LOW (hub shouldn't own config parsing) | MEDIUM | Rejected/P3 at most, if ever |
| Entropy-based auto-detection | Negative (introduces false positives) | HIGH | Rejected |
| Module-level global pattern registry | Negative (statefulness smell) | LOW (deceptively "cheap" but wrong) | Rejected |

## Competitor / Prior-Art Feature Analysis

| Feature | WeatherBot `_redact.py` (proven, app-local) | General Python ecosystem (loggingredactor, scrubadub, structlog docs) | Hub (PC-01) Approach |
|---------|-----------------------------------------------|--------------------------------------------------------------------------|------------------------|
| Insertion point | Single stderr choke point (`_LiveStderr.write`) shared by both `structlog.configure` sites | Logging `Filter` in front of handlers, or a structlog processor/`show_locals=False` on the exception transformer | Generalize the proven choke-point pattern; keep processor-chain insertion as an option but not the sole mechanism (matches table-stakes finding above) |
| Pattern source | One hardcoded regex (`appid=`), app-specific | Regex or dictionary-key based, often shipped with common built-in patterns (email, phone, password keys) | Zero built-in patterns; 100% consumer-injected (litmus-mandated) |
| Value handling | Mask value only, preserve delimiter-bounded structure | Masking (fixed-char placeholder preserving format) is OWASP's recommended default over deletion | Same — mask the value, preserve the line (D-03, proven) |
| Multi-pattern support | Not needed yet (one consumer, one pattern) | Most libraries support N named patterns/keys out of the box | Design in from day one (cheap now, expensive to retrofit) |
| Failure handling | Explicit non-`str`/`bytes` tolerance (WR-02) | Not universally addressed — many simpler examples assume `str` input | Carry WR-02's proven tolerance into the generalized core |

## Sources

- **Primary (HIGH confidence, direct source read):**
  - `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py`
  - `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py`
  - `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`
  - `/home/yahir/Projects/WeatherBot/.planning/milestones/v2.1-phases/30-secret-hygiene/30-CONTEXT.md`
  - `/home/yahir/Projects/Reusable/YahirReusableBot/.planning/PROJECT.md`
  - `/home/yahir/Projects/Reusable/YahirReusableBot/.planning/backlog/PROMOTION-CANDIDATES.md`
- **Supplementary (LOW confidence, single-pass web search, corroborating context only):**
  - [Exceptions — structlog stable documentation](https://www.structlog.org/en/stable/exceptions.html)
  - [Recipes — structlog stable documentation](https://www.structlog.org/en/stable/recipes.html)
  - [Logging Cheat Sheet — OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
  - [loggingredactor — GitHub](https://github.com/armurox/loggingredactor)
  - [Stop Secrets from Reaching Prefect Logs with a Logging Filter — Medium](https://medium.com/@bdalpe/stop-secrets-from-reaching-prefect-with-a-logging-filter-5384143ac5e2)
  - [How to reduce false positives while scanning for secrets — Security Boulevard](https://securityboulevard.com/2021/02/how-to-reduce-false-positives-while-scanning-for-secrets/)
  - [TruffleHog vs. Gitleaks — Jit](https://www.jit.io/resources/appsec-tools/trufflehog-vs-gitleaks-a-detailed-comparison-of-secret-scanning-tools)

---
*Feature research for: PC-01 secret-redaction backstop promotion (YahirReusableBot v0.2.0)*
*Researched: 2026-07-29*
