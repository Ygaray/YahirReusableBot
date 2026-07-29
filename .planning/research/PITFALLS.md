# Pitfalls Research: Secret-Redaction Backstop Promotion (PC-01)

**Domain:** Adding a generic secret-redaction logging backstop to an existing, shipped Python
library (`yahir_reusable_bot`) consumed by a live production bot via a human-gated tag pin.
**Researched:** 2026-07-29
**Confidence:** HIGH — grounded in (1) direct inspection of WeatherBot's proven app-local
`_redact.py` / `_LiveStderr` implementation and its verified regression suite (this IS the thing
being promoted), (2) source inspection of the installed `structlog` package in this repo's own
`.venv` (`processors.py`, `dev.py`) proving the exc_info/ConsoleRenderer blind spot empirically,
and (3) established CS literature on regex catastrophic backtracking (web-verified).

---

## Critical Pitfalls

### Pitfall 1: Processor-chain redaction has a structural blind spot for tracebacks

**What goes wrong:** The redaction mechanism is wired only as a structlog *processor* (something
that mutates `event_dict` before the renderer runs). It faithfully scrubs string fields like
`event`, bound kwargs, and anything already stringified — but the exception/traceback either
never reaches it as text, or reaches a completely different code path, so a raw secret sails
through untouched. Two concrete ways this happens, both verified against the installed
structlog:
1. **`exc_info` isn't a string when your processor runs.** If your processor sits *before*
   `structlog.processors.format_exc_info` / `ExceptionRenderer` in the chain, `event_dict["exc_info"]`
   is still a live `(exc_type, exc_value, traceback)` tuple or exception object — not text a regex
   can scrub. `ExceptionRenderer.__call__` (`structlog/processors.py:413-420`) is what turns it
   into the `event_dict["exception"]` *string* — your redactor must run **after** that step, or it
   silently does nothing to the traceback.
2. **`dev.ConsoleRenderer` never puts the traceback in the event_dict at all.** Verified at
   `structlog/dev.py:930-956`: `ConsoleRenderer.__call__` calls
   `self._exception_formatter(sio, exc_info)` directly, rendering the traceback straight into the
   output stream `sio`. This bypasses `event_dict` entirely — a processor sitting anywhere in the
   chain, before or after, structurally cannot see this text. `pretty_exceptions` (rich-formatted
   tracebacks) is the *default* renderer behavior for `ConsoleRenderer`.

**Why it happens:** "Add a processor to the chain" is the natural, well-documented structlog
extension point, and it genuinely works for ordinary event fields. It's easy to test it against a
plain `logger.error("leaked secret", key=SENTINEL)` call, see the sentinel scrubbed, and conclude
the backstop works — without ever exercising the `logger.exception(...)` / `exc_info=True` path
that WeatherBot's real leak (HARD-SEC-01, F12) came through.

**How to avoid:** Ship **two independent insertion points**, not one, exactly as PC-01's own scope
already anticipates ("a sink wrapper and/or processor"):
- A **processor** for event-dict fields (structured-log-safe: mutates values before serialization).
- A **sink/stream wrapper** (the generalized `_LiveStderr.write` pattern) that scrubs the fully
  rendered output string regardless of which renderer produced it. This is the only insertion
  point proven to catch `ConsoleRenderer`'s self-rendered tracebacks.
Document explicitly that the processor alone is **not** sufficient — the sink wrapper is the load-
bearing piece for traceback coverage, matching what WeatherBot already proved in production.

**Warning signs:** A test suite that only asserts against `logger.<level>(msg, key=value)` calls,
never against `logger.exception(...)` / `raise ... ` + `_log.exception(...)`, will pass green while
the real leak path (traceback) stays open.

**Phase to address:** The redaction insertion-seam phase (whichever phase builds the
processor/sink API) — must ship an adversarial `logger.exception()` test as a *hub-suite*
requirement, not deferred to the consumer's own tests.

---

### Pitfall 2: A second `structlog.configure()` call silently drops the backstop

**What goes wrong:** The hub never calls `structlog.configure()` itself — it's a library with no
console script; every consumer owns its own structlog configuration (WeatherBot has *two*
configure sites already: `weatherbot/__init__.py` and `cli.py`). If the redaction processor is
wired into one `configure()` call's `processors=[...]` list, any other configure call in the same
process (a test harness, a second entry point, a future consumer's own reconfiguration) that
doesn't include it silently produces unredacted logs. There is no error, no warning — logging
"just works," minus the scrub.

**Why it happens:** structlog's `configure()` is global mutable state by design (that's the whole
point of the library); nothing enforces that every call site includes every processor. A
promotion review that only checks "does WeatherBot's `__init__.py` include the processor" will
miss `cli.py`'s independent configure call — this already happened once for the app-local version
(30-PATTERNS.md flagged `cli.py`'s configure as a "CONFIRM only" step precisely because it's easy
to forget).

**How to avoid:** Prefer the **sink/stream wrapper** as the primary defense here too — it wraps the
underlying file/stream object once (shared by both configure sites in WeatherBot, since both point
at the same `_LiveStderr` class), not the processor list, so it survives reconfiguration as long as
the same sink object is reused. Additionally, ship a small **self-check helper** the consumer can
call once at startup — e.g. `assert_redaction_active(logger, patterns)` that emits a canary secret
through the *actual* configured logger and asserts it comes out scrubbed — so a broken wiring fails
loudly at boot instead of silently in production.

**Warning signs:** Redaction works in the hub's own unit tests (which construct a logger directly)
but a consumer's *actual* runtime configuration was never exercised end-to-end.

**Phase to address:** Insertion-seam phase — ship the self-check helper alongside the
processor/sink API, and use it in the hub's own integration tests as the assertion mechanism
rather than hand-rolling capture setup per test.

---

### Pitfall 3: ReDoS from a consumer-supplied pattern is a hub-wide outage, not just a slow log line

**What goes wrong:** PC-01's stated shape is "config-driven pattern list (each consumer registers
its own secret patterns)." Python's stdlib `re` module has **no built-in protection against
catastrophic backtracking** — a pattern shaped like `(x+)+y` or with nested/overlapping quantifiers
can take exponential time on adversarial (or even accidental) input, and Python's `re` has no
timeout parameter (a `re`-timeout proposal is only a 2026 python.org discussion, not shipped). If
a consumer registers a badly-shaped pattern — even unintentionally, e.g. a copy-pasted regex with
a stray `+` inside a group — and a log line (or a large traceback) matches it adversarially, the
`redact_secrets()` call hangs. Because this hub's Discord adapter runs an asyncio gateway loop and
logging calls are synchronous, a hang inside a log call **blocks the event loop**, which can starve
heartbeats and drop the gateway connection — this is a full bot outage, not a slow log line.

**Why it happens:** Regex authors reason about the "happy path" match, not adversarial rejection
time; nested quantifiers look innocuous when writing the pattern and only misbehave on inputs that
almost-but-don't match.

**How to avoid:**
- **Prefer not exposing raw regex at all** for the common case. Provide a safe pattern-*builder*
  (e.g. a `field_pattern(name: str) -> Pattern` helper that generates the exact proven bounded
  shape WeatherBot already validated — `(name=)[^&\s"'<>\\]+` — internally) so most consumers never
  hand-write a regex.
- If raw regex registration must be supported, **validate at registration time, not at log time**:
  run the candidate pattern against a small adversarial fixture (e.g. `"a" * 10_000 + "!"`, plus a
  string built from the pattern's own literal prefix repeated) with a wall-clock budget (e.g.
  50-100ms); reject (raise, don't silently skip) patterns that blow the budget. This is a one-time
  cost at startup, not a per-log-line cost.
- Precompile all patterns at registration (never at log time — see Pitfall 6).
- Do not rely on runtime interruption (`signal.alarm` doesn't work reliably off the main thread and
  is meaningless inside an asyncio loop) — registration-time vetting is the only practical
  mitigation available in stdlib `re`.

**Warning signs:** A registered pattern that "looks fine" in code review but contains a quantified
group inside another quantified group (`(a+)+`, `(a*)*`, `(a|ab)*`, etc.).

**Phase to address:** The pattern-registration API phase — the adversarial-input test belongs in
the hub's own RED-first suite (per this project's test posture) as a permanent regression, not a
one-off manual check.

---

### Pitfall 4: Over-broad patterns destroy diagnosability (or under-broad ones leak partial tokens)

**What goes wrong:** Two opposite failure modes from the same root cause — getting the pattern's
value-boundary wrong:
- **Too greedy** (`key=.*`): eats everything after the secret — the following query params, the
  HTTP status, the MDN link in httpx's message — making the log line useless for on-call debugging.
- **Too narrow / wrong-shape**: the pattern only matches `key=<value>` but the exact same secret
  value also appears bare in a different representation the hub author didn't anticipate: a
  URL-encoded form (`%XX` sequences) inside a query string, a JSON-escaped form once
  `JSONRenderer`/`json.dumps` has run, inside a traceback frame's local-variable `repr()` (e.g. an
  `httpx.Request.__repr__` embedding the full URL — WeatherBot's own regression suite
  (`test_reraised_exception_request_carries_no_key`) exists *because* this happened: the secret
  rode on `exc.request.url`/`repr(exc.request)`, not just `str(exc)`), or split across two separate
  structlog `bind()` calls that get merged into one event.

**Why it happens:** The proven WeatherBot regex is narrowly shaped for one call-site pattern
(`appid=<value>` in a URL). A generic hub mechanism must handle secrets that appear in many shapes
across many future consumers — the temptation is to either genericize by loosening the pattern
(dangerous: Pitfall 4a) or to leave it exactly as narrow as the one proven case (dangerous:
Pitfall 4b, misses the next consumer's different leak shape).

**How to avoid:**
- Keep the **character-class-negation boundary style** WeatherBot already validated —
  `(name=)[^&\s"'<>\\]+` stops at the first delimiter, never at end-of-string via `.*`. Make this
  the default/only shape the pattern-builder helper produces.
- Support redacting a **known literal secret value**, not only a `key=` shape — i.e. accept "block
  this exact string wherever it appears" as a first-class registration mode, independent of any
  field-name heuristic. This is the only way to catch a secret riding on an unanticipated attribute
  (`.request.url`, a `repr()`, a different exception subclass) that a `key=` regex was never shaped
  for.
- For literal-value matching, normalize before comparing: check both the raw value and its
  URL-percent-encoded / JSON-escaped forms, since a secret containing special characters (e.g.
  base64 `+`, `/`, `=`) will appear differently encoded across a query string vs. a JSON log field.
- Case: field-*name* matching should stay case-insensitive (an uppercase `APPID=` must still be
  caught, as WeatherBot's regex already does); secret-*value* matching should stay case-sensitive
  (loosening case on a literal value risks mangling unrelated text that happens to share the
  substring).

**Warning signs:** A parity test where a boundary-case input (URL-encoded value, `repr()` of an
exception, a second `bind()`-merged field) still contains the raw secret after redaction, or where
`units=imperial`-equivalent trailing content is missing after redaction (over-eating).

**Phase to address:** Redaction-core phase — port WeatherBot's exact boundary-case test matrix
(5+ cases in `test_redact_hygiene.py::test_redact_helper_boundaries` plus the `.request`/`repr()`
canary) as the hub's own regression suite before generalizing the pattern shape.

---

### Pitfall 5: `raise ... ` without `from None` re-leaks through `__context__` in the full traceback

**What goes wrong:** This is not new to the hub, but it is the single most likely regression if
the redaction promotion touches (or a future consumer copies) any exception re-raise logic near
the backstop. `str(exc)` can be perfectly clean while the *full* traceback — exactly what
`_log.exception(...)` renders — still shows the original, secret-bearing exception under "During
handling of the above exception, another exception occurred." Python auto-chains the in-flight
exception as `__context__`, and `traceback.format_exception(...)` prints the whole chain.
WeatherBot's own research (30-RESEARCH.md, Pitfall 1) reproduced this empirically: identical code
minus `from None` leaks the sentinel in the full traceback even though `str(exc)` is clean.

**Why it happens:** A quick manual check (`print(str(exc))`) looks clean and developers stop
there; the chained-context leak only shows up in a full traceback capture.

**How to avoid:** This particular pitfall belongs to *source-level* redaction (the domain-specific
re-raise in a consumer's own client code, e.g. WeatherBot's `client.py` — which stays app-local per
the litmus, PC-01 does not promote it). The hub-side relevance is: the hub's own regression tests
for the sink/processor backstop must assert against the **full rendered traceback**
(`traceback.format_exception(...)` or the captured stderr from `logger.exception(...)`), never
only `str(exc)` — otherwise a hub-side test could pass while missing the exact class of leak the
backstop exists to catch.

**Warning signs:** A test that asserts `SENTINEL not in str(exc)` and stops there.

**Phase to address:** Redaction-core / insertion-seam phase test suite — mandate a full-traceback
assertion (not just `str(exc)`) in every adversarial test.

---

### Pitfall 6: Compiling patterns at log time (not registration time) taxes every log line

**What goes wrong:** `redact_secrets(text, patterns)` looks innocuous as a signature, but if
`patterns` are raw strings compiled inside the hot function (`re.compile(p)` per call, or per log
line), every single log emission pays full regex-compilation cost — orders of magnitude slower
than matching against an already-compiled pattern object. In a daemon that logs on every scheduler
tick, this is a real, measurable, entirely avoidable tax.

**Why it happens:** The simplest possible API (`redact_secrets(text: str, patterns: list[str])`)
invites recompiling on every call because the function signature doesn't make "these are
precompiled" obvious or enforced.

**How to avoid:**
- The public API should take **precompiled pattern objects** (or an opaque `Redactor`/registry
  object that compiles once at construction/registration time), never raw pattern strings at the
  call site.
- Short-circuit on the empty case: if a consumer registers zero patterns, `redact_secrets` should
  be a no-op that returns the input unchanged with no regex work at all — don't force a loop over
  an empty list on every call, and don't force the caller through a wrapper indirection when
  disabled.
- For the common case where most log lines contain no secret at all, consider a **cheap literal
  pre-check** (does the text contain the pattern's fixed anchor substring, e.g. `"appid="`, via a
  plain `in` check) before invoking the full regex — turns "no match" into an O(1)-ish substring
  scan instead of a full regex engine invocation, for the majority of log lines that carry nothing
  sensitive. This is a real, standard optimization in redaction-focused tooling; don't
  over-engineer it (e.g. don't build an alternation-merge across all patterns) unless a benchmark
  shows the naive N-precompiled-patterns loop is actually a bottleneck — with a realistic pattern
  count (single digits to low tens), N precompiled `.sub()` calls over a short log line is
  microseconds, dwarfed by any network I/O the daemon does per tick.

**Warning signs:** `re.compile` (or pattern-string-to-Pattern coercion) appearing inside a function
that's called once per log emission, rather than once at startup/registration.

**Phase to address:** Redaction-core phase — the public API shape itself should make late
compilation structurally impossible (accept only compiled `Pattern` objects, or wrap
compilation inside a registration method that's called once).

---

### Pitfall 7: A global mutable pattern registry causes test pollution and import-order dependence — inside the hub's *own* test suite

**What goes wrong:** The intuitive API — `yahir_reusable_bot.redaction.register_pattern(pattern)`
writing into a module-level global list — creates exactly the failure class this project's test
posture is designed to catch: one test registers a pattern and a later test (in the same pytest
process) either sees it unexpectedly (assertion about "clean state" fails) or the registry
persists across the RED-first test that's supposed to prove a *specific* fix, coupling unrelated
tests through shared global state. It also invites import-order-dependent registration (e.g. a
decorator-style `@register_secret_pattern` fired at module import time), where *which* modules
happened to be imported first determines what's actually active — surprising and hard to reason
about, and nearly impossible to unit test in isolation.

**Why it happens:** A single hub-global registry is the path of least resistance and mirrors how
some logging frameworks work (implicit global config). It is not obviously wrong until the second
test file registers a conflicting or overlapping pattern.

**How to avoid:** Make the redaction mechanism an **explicit, constructed object** — e.g. a
`Redactor(patterns=[...])` (or equivalent) that the consumer builds once at its composition root
and passes explicitly into the processor/sink factory — rather than a module-level mutable
singleton the consumer mutates via a bare function call. This:
- eliminates cross-test leakage structurally (each test constructs its own instance),
- eliminates import-order dependence (no import-time side effects),
- matches this hub's existing pattern of dependency injection at the composition root (the same
  shape as `Channel`, `JobStore` Protocol, etc. — see `EXTENSION-GUIDE.md`) rather than introducing
  a new, inconsistent global-state mechanism into an otherwise injection-based library.
If a convenience global default is still wanted for ergonomics, keep it as a thin wrapper around an
explicit instance, and provide (and use, via an autouse fixture) an explicit reset/teardown for the
hub's own tests.

**Warning signs:** A test failure that only reproduces when the full suite runs (not in isolation),
or a test needing `del registry[...]`/manual cleanup at the end to pass.

**Phase to address:** Redaction-core / pattern-registration API phase — this is an API-shape
decision that's expensive to change after consumers depend on it; get it right in the phase that
defines the public surface, not retrofitted later.

---

### Pitfall 8: Redaction implemented as blind post-render string surgery can corrupt structured log consumers

**What goes wrong:** If the *only* insertion point is a sink-level string scrub running after
`JSONRenderer` has already produced JSON text, a regex substitution that spans (or lands adjacent
to) a JSON escape sequence (`\"`, `\\`, `\/`) can — in edge cases — produce malformed JSON that a
downstream log aggregator (Loki/ELK/etc.) fails to parse. Conversely, event-dict-level (processor)
redaction that mutates Python string *values* before serialization is structurally safe (JSON
serialization of an already-redacted plain string like `***` is always well-formed) but, per
Pitfall 1, doesn't reach traceback text at all.

**Why it happens:** The two insertion points have different safety/coverage tradeoffs and it's
tempting to pick only one because "it passed the smoke test."

**How to avoid:** Use **both**, for their respective strengths — the processor for event-dict
fields (safe for structured consumers, runs before serialization), the sink/stream wrapper for
renderer-produced text including tracebacks (renderer-agnostic, but operates on final bytes). Test
the sink-level scrub specifically against a `JSONRenderer`-produced line containing an escaped
secret (e.g. a value with an embedded `"`) to prove the substitution doesn't straddle an escape
boundary and break JSON parseability.

**Warning signs:** A downstream log parser (or a `json.loads()` round-trip test) failing only on
redacted lines, never on unredacted ones.

**Phase to address:** Insertion-seam phase — add a JSON-round-trip test as part of the sink-wrapper
test suite, not just a "sentinel absent" assertion.

---

### Pitfall 9: Making redaction impossible to disable turns into its own footgun (and making it *too easy* to disable is worse)

**What goes wrong:** Two failure modes at opposite extremes:
- Hard-coding redaction as always-on with zero override means a developer debugging a live 401/403
  locally can't see the actual secret value reaching the API, even when they legitimately need to
  (e.g. confirming *which* rotated key is in play).
- An implicit toggle (an env var like `DISABLE_REDACTION=1` read directly by the hub) is worse: it
  can be left set in a deploy environment by accident, silently defeating the backstop in
  production with no code-visible trace of the decision.

**Why it happens:** Env-var toggles are the path of least resistance for "just let me debug this
once," and their easy of use is exactly what makes them dangerous to leave lying around.

**How to avoid:** Expose disablement only as an **explicit constructor parameter** at the
consumer's composition root (e.g. `Redactor(patterns=[...], enabled=True)`), never as an implicit
environment-variable read inside the hub. This keeps the decision visible in a diff/code review —
turning redaction off requires a conscious code change, not an environment artifact nobody notices.

**Warning signs:** A `os.environ.get(...)` call inside the hub's redaction module itself, rather
than the consumer's own composition-root wiring deciding the flag value (which the consumer may of
course choose to source from its own env var — that's a consumer decision, not a hub one).

**Phase to address:** Redaction-core phase — API-shape decision, same phase as Pitfall 7.

---

### Pitfall 10: Swapping WeatherBot's proven app-local `_redact.py` for the hub version without proving parity first

**What goes wrong:** This is the migration-specific pitfall the milestone explicitly calls out —
and the highest-risk one, because it's the one step with a live, currently-correct implementation
already in production. The temptation, once the hub mechanism exists and passes its own tests, is
to treat "hub tests are green" as sufficient proof to delete WeatherBot's `weatherbot/_redact.py`
and its `tests/test_redact_hygiene.py`. It is not. Concrete ways this goes wrong:

1. **Boundary-behavior drift.** The hub's generalized `redact_secrets`/pattern API might not
   reproduce *exactly* the same boundary behavior WeatherBot's narrow `_APPID_RX` proved (delimiter
   set, case-insensitivity default, placeholder text `***` vs. something else). A subtle difference
   either under-redacts (regression: HARD-SEC-01 reopens) or over-redacts (regression: violates
   D-03, destroys `units=imperial`/status diagnosability that the live daemon depends on).
2. **Scope confusion — the hub only replaces the backstop, not the source-level fix.** WeatherBot's
   secret hygiene is *two* mechanisms: (a) a domain-specific redacted re-raise with `from None` at
   the `httpx.HTTPStatusError` raise sites in `client.py` (root fix — stays app-local forever, it's
   OpenWeather/httpx-specific, fails the litmus), and (b) the generic `_LiveStderr.write` backstop
   (PC-01's actual promotion target). If whoever performs the repin mistakenly deletes or weakens
   (a) while wiring in the hub's (b), the root fix regresses silently — the backstop still catches
   it *at the logging boundary*, but any code path that reads `exc.request.url` / `repr(exc)`
   directly (not through the logger — e.g. a future APM/Sentry integration) would leak again,
   exactly as WeatherBot's own `test_reraised_exception_request_carries_no_key` test exists to
   prevent.
3. **Bundled repin conflates failure causes.** This milestone ships PC-01 (redaction promotion) in
   the *same* tag/repin as WR-02 (duplicate `spec.name` becomes a hard `ValueError` — an unrelated,
   deliberately breaking change). If the WeatherBot repin fails post-deploy, it's genuinely
   ambiguous at a glance whether the redaction swap or the registry-duplicate change caused it,
   unless each is verified independently before the combined repin ships.

**Why it happens:** "The hub's tests pass" is a true but insufficient signal — the hub's tests
prove the *mechanism* works in isolation; they say nothing about whether the specific instantiation
wired into WeatherBot reproduces the exact, already-proven behavior at WeatherBot's exact call
sites.

**How to avoid:**
- **Prove parity before deleting anything.** Run WeatherBot's *existing, unmodified*
  `tests/test_redact_hygiene.py` regression suite (all 6 tests: helper boundaries, onecall,
  geocode, Discord `on_message` end-to-end, `.request`/`repr()` canary, `_LiveStderr` bytes-input
  tolerance) against the hub-backed replacement — with only the import swapped
  (`from weatherbot._redact import redact_appid` → the hub's equivalent), before deleting
  `weatherbot/_redact.py`. Every one of those assertions must still pass, unchanged, byte-for-byte.
- **Scope the swap explicitly to the backstop.** The repin/migration step should touch only
  `weatherbot/__init__.py`'s `_LiveStderr.write` wiring (and the `_redact.py` deletion). `client.py`'s
  redacted re-raise + `from None` (the root fix) is out of scope for this swap and must be
  confirmed untouched — re-run `test_reraised_exception_request_carries_no_key` specifically as a
  scope-boundary check, since it exercises the source-level fix independent of the logging layer.
- **Verify the two repin changes (PC-01 + WR-02) independently.** Confirm the redaction parity
  suite passes and confirm the duplicate-`spec.name` sweep passes as two *separate* checks before
  treating the combined repin as ready to surface for human confirmation.
- **Confirm the live daemon actually picked up the change.** Per `ECOSYSTEM.md` §7, check the
  startup `module provenance` log line against `deploy/PROMOTION-LEDGER.md`'s latest row after
  deploy — a green CI run does not prove the systemd service on `yahir-mint` restarted with the new
  code.

**Warning signs:** Deleting `_redact.py` in the same commit/PR that wires in the hub replacement,
without a prior commit that ran the old test file against the new implementation and left it green.

**Phase to address:** This is the **human-gated migration/repin step** (`ECOSYSTEM.md` §3/§6),
downstream of all hub-side phases — but the *parity test plan* (which exact WeatherBot tests must
re-pass, and the explicit scope boundary around `client.py`) should be written and agreed at
discuss/plan time for the redaction phases, not improvised at repin time.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|-----------------|
| Raw regex strings as the pattern-registration API (no builder helper) | Faster to ship, matches PC-01's literal wording | Full ReDoS surface exposed to every future consumer; every consumer re-derives boundary-safe regex from scratch | Never as the *only* option — fine as an escape hatch alongside a safe builder helper |
| Processor-only redaction (skip the sink wrapper) | Simpler, one insertion point, "structlog-idiomatic" | Structural blind spot for `ConsoleRenderer`-rendered tracebacks (Pitfall 1) — a false sense of security | Never for a security backstop; acceptable only for a "nice to have" scrub with no security claim attached |
| Module-global mutable pattern registry | Simplest possible API, no object to construct/pass around | Test pollution in the hub's own suite, import-order dependence | Never — costs nothing extra to make it an explicit constructed object instead |
| Skip the WeatherBot parity re-run; trust hub CI green | Faster repin | Silent regression of a previously-proven, security-relevant behavior in production | Never — this is exactly the scenario a live tag-pinned consumer exists to prevent |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| WeatherBot's two `structlog.configure()` sites (`__init__.py`, `cli.py`) | Wiring the redaction processor into only one configure call | Anchor the backstop at the shared `_LiveStderr`-equivalent sink object both sites already route through, not at the processor list of just one site |
| WeatherBot's `client.py` redacted re-raise (`from None`) | Treating it as replaced by the hub promotion and deleting/weakening it during repin | Explicitly out of scope for PC-01 — stays app-local (fails the litmus, it's httpx/OpenWeather-specific); re-verify with its own test after the swap |
| Bundling PC-01 + WR-02 in one repin | Assuming one green CI run validates both independently | Verify the redaction parity suite and the duplicate-registration sweep as two separate, individually-green checks before combining |
| Live `yahir-mint` systemd deploy | Assuming a merged/tagged change is live | Check the startup `module provenance` log line against `deploy/PROMOTION-LEDGER.md` post-deploy |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Compiling patterns at log-call time instead of registration time | Logging shows up as non-trivial CPU in profiling on a scheduler-tick-heavy daemon | Precompile at registration; API accepts only compiled pattern objects or an opaque registered-pattern handle | Noticeable once log volume exceeds a handful of lines per tick, or as pattern count grows |
| No short-circuit for the empty-pattern-set / no-match case | Every log line pays full regex overhead even when nothing sensitive is logged | No-op fast path for zero patterns; cheap literal substring pre-check before invoking a full regex | Matters most in a daemon that logs frequently (heartbeats, scheduler ticks) with mostly-clean lines |
| ReDoS from an adversarial or accidentally-shaped consumer pattern | A single log call hangs; if it's on the asyncio event loop thread, the whole gateway connection can drop | Registration-time adversarial-input vetting with a wall-clock budget; prefer a safe pattern-builder over raw regex | Any time a pattern with nested/overlapping quantifiers meets an almost-but-not-quite-matching input |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Redacting only the `key=value` shape, not the literal secret value itself | A secret riding on an unanticipated attribute (`.request.url`, `repr()`, a different exception type) leaks undetected | Support literal-value redaction as a first-class registration mode, independent of field-name pattern matching |
| Trusting `str(exc)` cleanliness as proof of no leak | The full traceback (via `__context__` chaining, or via a renderer that self-formats tracebacks) can still leak even when `str(exc)` is clean | Every adversarial test must assert against the full rendered traceback / captured stderr output, never `str(exc)` alone |
| Implicit env-var kill switch for redaction | Accidentally-set env var silently disables a security backstop in production with no code trail | Explicit constructor parameter at the composition root only |
| Treating "hub CI green" as sufficient before deleting the app-local implementation | Silent regression of a live, previously-proven security fix | Re-run the exact existing WeatherBot regression suite against the hub-backed replacement before deletion |

## "Looks Done But Isn't" Checklist

- [ ] **Redaction backstop:** Often missing traceback coverage — verify a `logger.exception(...)`
      call (not just `logger.error(msg, key=value)`) is scrubbed, using the actual renderer the
      consumer configures (especially `ConsoleRenderer`'s self-rendered tracebacks).
- [ ] **Pattern registration API:** Often missing ReDoS vetting — verify an adversarial-shaped
      pattern is rejected at registration, not silently accepted to hang at log time.
- [ ] **Parity with the app-local implementation:** Often missing an actual side-by-side run of the
      old test suite against the new implementation — verify every existing WeatherBot
      `test_redact_hygiene.py` assertion still passes, unchanged, before deleting `_redact.py`.
- [ ] **Disablement:** Often missing an explicit, code-visible way to turn redaction off for local
      debugging — verify it exists as a constructor parameter, not an env var read inside the hub.
- [ ] **Structured-log safety:** Often missing a JSON-round-trip test on a redacted line — verify a
      `JSONRenderer`-produced log line with an escaped secret value stays valid JSON after
      redaction.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|------------------|
| Processor-only redaction shipped, traceback leak discovered later | MEDIUM | Add the sink/stream wrapper as a second insertion point; re-run adversarial `logger.exception()` tests; cut a patch tag; repin |
| Global mutable registry causing test flakiness | LOW–MEDIUM | Refactor to an explicit constructed object; add autouse teardown fixture in the interim if a full refactor must wait |
| Parity gap discovered post-repin (a WeatherBot leak reopens) | HIGH | Immediate: revert to the app-local `_redact.py` (still in git history) via a fast-follow patch; do not wait for a full hub fix cycle given the security nature of the regression |
| ReDoS pattern registered and deployed | HIGH (live outage risk) | Emergency: remove/replace the offending pattern at the consumer's composition root immediately (no hub tag needed if only the app-side pattern list changes); follow up with hub-side registration-time vetting so it can't recur |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| 1. Processor-chain traceback blind spot | Insertion-seam phase | Adversarial `logger.exception()` test against both a processor-only config and the sink-wrapper config |
| 2. Second `structlog.configure()` bypass | Insertion-seam phase | Self-check helper (`assert_redaction_active`) exercised in hub integration tests; sink-wrapper-anchored design |
| 3. ReDoS from consumer patterns | Pattern-registration API phase | Registration-time adversarial-input test with wall-clock budget, in the hub's own RED-first suite |
| 4. Over/under-broad pattern boundaries | Redaction-core phase | Ported WeatherBot boundary-case matrix + `.request`/`repr()` literal-value canary |
| 5. Missing `from None` re-leak via `__context__` | Redaction-core / insertion-seam test suite | Full-traceback assertion (not `str(exc)` alone) in every adversarial test |
| 6. Late pattern compilation on the hot path | Redaction-core phase (API shape) | API accepts only precompiled/registered patterns; no-op fast path for empty pattern set |
| 7. Global mutable registry / test pollution | Pattern-registration API phase (API shape) | Explicit constructed `Redactor`-style object; hub's own suite runs clean in isolation and in full-suite order |
| 8. Post-render string surgery corrupting JSON | Insertion-seam phase | JSON-round-trip test on a `JSONRenderer`-produced, redacted line |
| 9. Impossible/unsafe-to-disable redaction | Redaction-core phase (API shape) | Explicit constructor `enabled` flag; no env-var read inside hub code |
| 10. App-local → hub migration parity gap | Human-gated migration/repin step (planned at discuss/plan time) | WeatherBot's existing `test_redact_hygiene.py` suite re-run unchanged against the hub-backed implementation before `_redact.py` deletion; `client.py` re-raise scope explicitly unchanged; PC-01 and WR-02 verified independently before combined repin |

## Sources

- `weatherbot/_redact.py`, `tests/test_redact_hygiene.py` — the proven app-local implementation
  this milestone promotes/replaces. Read directly from `/home/yahir/Projects/WeatherBot`. HIGH
  confidence (this is the ground truth being migrated).
- `.planning/milestones/v2.1-phases/30-secret-hygiene/30-RESEARCH.md` and `30-PATTERNS.md`
  (WeatherBot repo) — the original verified research behind HARD-SEC-01, including the empirically
  reproduced `from None` / `__context__` chain leak and the `capsys`-vs-`caplog` blindness. HIGH
  confidence (empirically verified in that phase).
- `.venv/lib/python3.13/site-packages/structlog/processors.py` (`ExceptionRenderer.__call__`,
  `structlog/processors.py:413-420`) — verified directly in this repo's installed dependency: the
  processor-level exc_info→string conversion point. HIGH confidence (source inspection).
- `.venv/lib/python3.13/site-packages/structlog/dev.py` (`ConsoleRenderer.__call__`,
  `structlog/dev.py:930-956`) — verified directly: `ConsoleRenderer` renders `exc_info` straight to
  the output stream, bypassing `event_dict`. HIGH confidence (source inspection).
- `ECOSYSTEM.md` (this repo) — the human-gated repin ritual, the litmus, the quarantine/promotion
  model, `deploy/PROMOTION-LEDGER.md` provenance check. HIGH confidence (canonical project doc).
- `.planning/backlog/PROMOTION-CANDIDATES.md` (PC-01) — the exact shape and scope this promotion is
  bound to. HIGH confidence (canonical project doc).
- Python catastrophic-backtracking / ReDoS mitigation landscape — web search, 2026: confirms
  stdlib `re` has no built-in timeout (an opt-in timeout parameter is only a 2026 python.org
  discussion, not shipped), RE2 forbids backtracking entirely as the strongest alternative,
  nested-quantifier shapes (`(a+)+b`) are the canonical trigger pattern. MEDIUM confidence (web,
  general community/security consensus, not project-specific) —
  [Add an opt-in timeout parameter to re to mitigate catastrophic backtracking](https://discuss.python.org/t/add-an-opt-in-timeout-parameter-to-re-to-mitigate-catastrophic-backtracking/107766),
  [Add linter to check for catastrophic backtracking in Python re module](https://github.com/duo-labs/dlint/issues/41),
  [Guard against slow regular expressions to prevent ReDoS](https://www.aikido.dev/code-quality/rules/guard-against-slow-regular-expressions-preventing-redos-attacks).

---
*Pitfalls research for: secret-redaction backstop promotion into a shipped, tag-pinned Python
library hub*
*Researched: 2026-07-29*
