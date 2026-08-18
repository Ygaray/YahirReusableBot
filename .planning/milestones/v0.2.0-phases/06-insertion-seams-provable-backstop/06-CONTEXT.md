# Phase 6: Insertion seams + provable backstop - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers **the wiring layer** — the seams a consumer installs so the Phase-5 scrubbing
primitive actually runs against live log output, plus the means to prove it is running.
Requirements: **REDACT-04, REDACT-05, REDACT-07, REDACT-08, DOCS-04**.

Concretely: the `RedactingWriter` sink (load-bearing), the optional structlog processor,
`assert_redaction_active`, redaction-count telemetry, and the `EXTENSION-GUIDE.md` SEAM-08 row
flipped to **implemented**.

Phase 5 ended at "a consumer can build and validate a pattern set." Phase 6 is "a consumer can wire
it into logging and prove it's on." This phase closes PC-01's hub-side work.

**Explicitly NOT in this phase:**
- Any change to the Phase-5 pattern API (`RedactionPattern`, `redact_secrets`, `register_patterns`).
  It is **pinned** and WeatherBot is about to pin against it. Phase 6 consumes it, never reshapes it.
- The version bump, tag, WeatherBot repin, `_redact.py` deletion, and deploy — all human-gated
  (`ECOSYSTEM.md` §3).
- Track B debt (MATCH-03, LIFE-05, SURF-02, DISC-07/08, HYG-02/03, DOCS-02/03) — Phase 7.
- `weatherbot/weather/client.py`'s domain-specific redacted re-raise — permanently out of PC-01
  scope, app-local forever.

**The hub must NEVER call `structlog.configure()`.** Standing, repeatedly re-asserted. Any proposal
that violates it is disqualified regardless of convenience.

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues the project-wide sequence. Phase 5 reached **D-53**, so Phase 6
> starts at **D-54**.
>
> **All four gray areas were researched by parallel advisor agents and the user took every
> researched recommendation**, plus one follow-up on test scope. Each decision below records its
> rejected alternatives so the planner sees the reasoning, not just the verdict. This continues the
> Phase-3/4/5 pattern.
>
> **Framing note for downstream agents (carried from Phase 5, still binding):** the user is highly
> technical in this project's domain (Python services, systemd, deployment) but is *not* fluent in
> structlog internals, and said so plainly. Surface decisions in plain language with a concrete
> recommendation. Do not present bare trade-off menus that presume structlog fluency.

### ⚠ Premise correction discovered during this discussion (read this first)

**`_LiveStderr` was never assigned to `sys.stderr` process-wide.** The discussion opened on the
assumption that WeatherBot's proven backstop wraps the stream globally and therefore catches
everything. It does not. Verified at `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py`
lines 26–62: `_LiveStderr` is only ever passed as
`structlog.PrintLoggerFactory(file=_LiveStderr())` — structlog's own render target.

The consequence is documented in WeatherBot's own source at
`weatherbot/weather/client.py:48-54`: httpx's stdlib-`logging` INFO line, which carries the API key
in the request URL, **bypasses the backstop entirely**, because `logging.basicConfig` routes to the
raw `sys.stderr`.

So structlog-only coverage is the *status quo*, not a reduction. This reframed D-54 from "preserve
broad coverage" to "make broad coverage possible." Recorded here because a downstream agent reading
only the requirement text would re-derive the wrong premise.

### Scrub coverage (REDACT-04)

- **D-54 (one primitive, two documented recipes — the hub never mutates process state itself):**
  ship exactly one class, `RedactingWriter`, wrapping **any** file-like target. `EXTENSION-GUIDE.md`
  SEAM-08 documents two wirings:
  1. **Required** — the consumer passes it as structlog's render target
     (`PrintLoggerFactory(file=RedactingWriter(...))` / `WriteLoggerFactory(file=...)`).
  2. **Optional, broader** — the consumer writes `sys.stderr = RedactingWriter(sys.stderr)` in their
     own composition root, picking up stdlib-`logging`, stray `print()`, and third-party output.

  **Why this is not a compromise.** `RedactingWriter` already has to wrap an arbitrary file-like
  target to satisfy REDACT-04's core promise, so it can stand in for `sys.stderr` with **zero extra
  code**. Breadth becomes available without the hub ever performing the mutation — the consumer's
  own visible line of code does it.

  - **Rejected — narrow only (structlog file target, documented as the sole use):** matches
    REDACT-04's literal wording and is the smallest surface, but a consumer wanting the httpx-class
    coverage gets no guidance and will re-invent a fragile `sys.stderr =` hack badly. Leaves a known
    gap undocumented.
  - **Rejected — hub ships a global installer function:** one-line adoption and broadest coverage by
    default, but the hub would be *actively performing* a process-wide mutation. That collides with
    D-53's reasoning (a library must not silently change security-relevant ambient state) and is
    **redundant** — `RedactingWriter` already does this when the consumer assigns it.

- **D-55 (both recipes are TESTED, not just documented):** Phase 6 ships a test that installs
  `RedactingWriter` as a stand-in stream and asserts non-structlog output (a bare `print()` /
  stdlib-`logging` line) comes out scrubbed.

  **Why.** A documented wiring nobody has ever run is exactly how the httpx gap got missed. Costs a
  handful of tests; buys proof that the recipe SEAM-08 recommends actually works.

  - **Rejected — documentation only:** smaller plan, but the broader recipe stays unproven until a
    consumer tries it in production.
  - **Rejected — drop recipe 2:** cleanest scope, but leaves the stdlib-logging/`print()` blind spot
    both unaddressed and unmentioned — the same class of blind spot that produced the original leak.

### Proving the backstop is installed (REDACT-07)

- **D-56 (introspection by default, opt-in in-memory dry-run probe; raises `ValueError`):**
  `assert_redaction_active` reads `structlog.get_config()` and confirms the hub's own writer (and/or
  processor, by identity) is installed. It **raises** on failure — matching the D-34/D-50
  fail-loud-at-wiring-time posture `register_patterns` already uses — and returns/passes silently
  when present. Cheap, emits no log line, safe to call at boot **or** mid-run in production.

  An **opt-in** deeper check asks the *already-located live instance* to scrub a fixed, non-secret
  sentinel **in memory only** — never calling `.write()`, never touching the consumer's real
  destination.

  **Why the dry-run shape matters.** It structurally eliminates the "can the canary leak the
  sentinel?" failure mode: because the probe never routes through the real output path, there is no
  scenario where a *broken* backstop causes the probe itself to write anywhere. This is the specific
  reason a real end-to-end canary was rejected.

  Per the ROADMAP sequencing note, this opt-in path is also the assertion mechanism for the phase's
  own seam integration tests — so it must be usable as test infrastructure, not only as a
  consumer-facing wiring check.

  - **Rejected — introspection only:** simplest and one code path, but proves *wiring* not
    *behavior*; an empty pattern set or a mis-ordered processor would pass.
  - **Rejected — canary through the real logger:** proves true end-to-end behavior, but needs
    output-capture machinery that is itself transient global-state mutation (structurally the same
    fragility class as the bug being guarded against), and the sentinel genuinely reaches real
    output if capture is imperfect.

  > **⚠ Known coupling the planner must handle explicitly, not discover:** introspection reaches
  > `PrintLoggerFactory._file` / `WriteLoggerFactory._file` — a **private** attribute. Verified
  > present on the installed `structlog` 26.1.0, but it is an implementation detail, not public API.
  > It is also **blind if the consumer nests `RedactingWriter` inside their own proxy** (WeatherBot
  > already uses a lazy-`sys.stderr`-resolving wrapper of exactly that kind). The plan must decide
  > how this degrades — a clear "could not verify" signal, never a false pass — and must not let a
  > structlog rename fail silently.

### Telemetry (REDACT-08)

- **D-57 (hybrid — lock-guarded monotonic counter is the source of truth, optional push hook):**
  `RedactingWriter` carries a counter the consumer can read off the instance, plus an **optional**
  `on_redaction`-style callable fired from inside the same guarded increment (off by default). One
  lock, one increment site, so the two views can never disagree. Monotonic for process lifetime —
  no reset-on-read; a consumer wanting a rate diffs two point-in-time reads.

  This composes for free with D-56: `assert_redaction_active` already has to locate the live
  instance, so telemetry needs no separate wiring story.

  Any consumer-supplied hook runs **on the write path** and therefore inherits D-52 — it must be
  wrapped in a swallow-and-continue guard so a raising or slow hook can never break logging.

- **D-58 (the counter counts CHANGED WRITES, not individual substitutions — a deliberate, documented reading of REDACT-08):**
  the requirement says "how many substitutions fired." Exact substitution
  counts are **not cheaply obtainable**: `redact_secrets` returns only the scrubbed string (pinned,
  WeatherBot about to pin against it), so an exact count would mean either re-running every pattern
  with `.subn()` — roughly doubling regex cost on **every log line, forever** — or maintaining a
  second, drift-prone copy of a security-sensitive scrub loop.

  Counting writes where output differs from input is one `!=` on strings already held in memory, and
  answers the operational question REDACT-08 exists for: *is the backstop firing at all, and roughly
  how often.* This is a sanity signal, not a precision metric anyone will act on per-substitution.

  > **Requirements-wording note — tracked deliberately, not silent drift.** Phase 6 verification
  > must NOT report a gap because the counter reports changed writes rather than exact substitution
  > counts. That is the locked contract, with the cost of the literal reading recorded above.

- **D-59 (use a `threading.Lock`, not `itertools.count`'s incidental atomicity):** the sink is
  written concurrently by an APScheduler thread pool, the asyncio Discord gateway loop, and the main
  thread. `itertools.count()`'s atomicity is a GIL-era implementation detail, not a documented
  guarantee, and free-threaded builds are exactly where it stops holding. A one-line lock costs
  nothing at real log volumes and removes the doubt.

### Mis-wiring protection for the optional processor (REDACT-05)

- **D-60 (loud docstring PLUS an ordering check folded into `assert_redaction_active`; it WARNS, never raises):**
  the processor's docstring states the chain-order precondition loudly (the
  requirement's literal ask). The *detection* rides inside D-56's existing self-check rather than
  becoming its own API: `structlog.get_config()["processors"]` exposes the live chain, and every
  built-in exception formatter (`format_exc_info`, `dict_tracebacks`, `ExceptionRenderer`) is an
  `isinstance` of `structlog.processors.ExceptionRenderer` — so "is redaction positioned before a
  formatter" is an index comparison, not speculative machinery.

  **Why warn and not raise.** The sink (REDACT-04) catches tracebacks unconditionally regardless of
  processor order, so a mis-ordered *optional, additive* processor is reduced defense-in-depth, not
  a security regression. A hard startup crash over a component the ROADMAP explicitly says can be
  dropped under scope pressure is disproportionate.

  When no *recognized* formatter type is found (a consumer's custom formatter), emit a generic
  "could not verify order" warning — never a false pass.

  - **Rejected — docstring only:** exactly the requirement's letter with zero machinery, but the
    invisible-failure class persists: the consumer believes they have full defense-in-depth and
    partly do not.
  - **Rejected — chain-builder helper returning a pre-ordered list:** strongest guarantee, but to
    genuinely place the processor "after the exception formatters" it must know which renderer and
    which formatter the consumer chose — that annexes composition-root policy however the "it only
    returns, it never configures" phrasing is framed. Revisit only if REDACT-05 stops being
    optional in a later milestone.

### Claude's Discretion

The user delegated these to the researched recommendation / standard practice. The planner has
latitude on:
- Module split within `redact/` for the new files (`sink.py` / `writer.py` for REDACT-04,
  `processor.py` for REDACT-05 — research proposed `sink.py` + `processor.py`).
- Exact public names, subject to the AST signature litmus (domain-noun-free) and to
  `RedactingWriter` / `assert_redaction_active` being fixed by the requirements themselves.
- The disablement parameter's exact name and signature position (D-53 locks only that it is an
  explicit constructor parameter, never an env read). **Default must be redaction ON** — a
  security backstop that defaults to off is not a backstop.
- The sentinel constant used by D-56's dry-run probe (must be a non-secret literal).
- Whether telemetry's optional hook receives the current count or no argument.
- How `EXTENSION-GUIDE.md` SEAM-08 is laid out within the guide's existing conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The promotion source — the proven wiring being generalized
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` (`_LiveStderr`, lines ~26–62) — the
  proven seam. **Read it before assuming anything about its coverage** (see the premise correction
  in `<decisions>`): it is a `PrintLoggerFactory` target, NOT a global `sys.stderr` swap. Its
  non-`str` triage is the D-52 contract Phase 6 now owns.
- `/home/yahir/Projects/WeatherBot/weatherbot/weather/client.py` lines ~48–54 — the comment
  documenting that httpx's stdlib-`logging` line bypasses the backstop. Evidence for D-54's
  second recipe; the file itself is permanently out of PC-01 scope.
- `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` — the 6-test parity gate.
  **Only 4 of 6 are reachable after Phase 5**; `test_discord_on_message_does_not_dump_key` and
  `test_livestderr_write_tolerates_and_scrubs_bytes` depend on **this phase's** seam. Phase 6 is
  what makes the full 6-assertion gate passable.

### What Phase 5 shipped — PINNED, consume don't reshape
- `yahir_reusable_bot/redact/core.py` — `RedactionPattern` (frozen, **slotted**) + `redact_secrets`.
  Note `redact_secrets` returns only the string, which is what forces D-58.
- `yahir_reusable_bot/redact/registry.py` — `register_patterns` + its ReDoS vetting.
- `yahir_reusable_bot/redact/__init__.py` — the current public surface Phase 6 extends.
- `.planning/phases/05-redaction-core-pattern-registration/05-CONTEXT.md` — **D-52** (non-`str`
  triage belongs at THIS seam) and **D-53** (disablement is an explicit parameter, never an env
  read). Both are Phase-6 obligations recorded in Phase 5.
- `.planning/phases/05-redaction-core-pattern-registration/05-VALIDATION.md` § Manual-Only — the
  corrected 4-of-6 parity plan and the `client.py` scope boundary.

### This milestone's research
- `.planning/research/SUMMARY.md` — the sink-is-load-bearing convergence (three independent angles).
- `.planning/research/STACK.md` — verified `structlog` 26.1.0 API surfaces; the processor
  ordering constraint (must run after `format_exc_info` / `ExceptionRenderer` / `dict_tracebacks`).
- `.planning/research/ARCHITECTURE.md` — `redact/` module tree (`sink.py`, `processor.py`).
- `.planning/research/FEATURES.md` — table stakes vs differentiators; telemetry's classification.
- `.planning/research/PITFALLS.md` — 10 pitfalls; the traceback blind spot and migration hazards.

### Project constitution and scope
- `.planning/ROADMAP.md` § Phase 6 — goal, 5 success criteria, and the sequencing constraint
  (sink proven first; REDACT-05 lands last and is droppable).
- `.planning/REQUIREMENTS.md` — REDACT-04/05/07/08 + DOCS-04 full text.
- `EXTENSION-GUIDE.md` — seam conventions and the row table. **SEAM-08 is the next free number**
  (SEAM-02 is absent from the guide with no recorded explanation — do not reuse it).
- `ECOSYSTEM.md` §3 (human-gated repin) and §6 (the promotion is not *done* until the guide row
  flips — this is what makes DOCS-04 a phase-closing requirement, not a nicety).
- `CLAUDE.md` — the hub-never-configures rule and the no-domain-nouns litmus.
- `tests/test_import_hygiene.py` — the standing gate. **`processor.py` is the one module allowed to
  import `structlog`**; verify whether that changes the grimp layering expectations.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`redact_secrets(text, patterns) -> str`** — the sink's entire scrubbing body is one call to
  this. The sink adds triage (D-52), counting (D-57/58), and forwarding; it must not re-implement
  substitution.
- **`RedactingWriter` wraps any file-like target** — this single property is what makes D-54's two
  recipes one class instead of two.
- **`tests/conftest.py`** — existing fixtures; hand-written doubles only. A capture double for the
  sink tests belongs here or as a module-local helper, following the Phase-5 precedent of keeping
  constants module-local rather than making them fixtures.

### Established Patterns
- **Fail loud at wiring time** (D-34 → D-50 → now D-56): a consumer wiring bug raises at build
  time. Note the deliberate exception in D-60 — the *optional* processor's ordering only warns.
- **Degrade, don't raise, on a hot path** (D-36) — governs the write path: D-52 forbids raising
  inside logging, and D-57's optional hook must be guarded accordingly. D-56's raise happens at
  wiring time, before anything is serving, so the two do not conflict.
- **RED-first, two-commit discipline (GATE-02)** — each requirement lands as a test-only commit
  that genuinely fails against pre-fix source, then the fix commit. Verification re-derives this
  ancestry with `git rev-parse`, so the pairs must be real and adjacent.
- **Plans sequenced so a deliberately-RED test never overlaps a sibling plan's full-suite gate** —
  hard-won across Phases 1–3 and re-proven in Phase 5's strictly-serial waves.
- **Module logger via `structlog.get_logger(__name__)`; nothing calls `structlog.configure()`.**

### Integration Points
- **`redact/` gains its first non-stdlib import.** `processor.py` imports `structlog`. Everything
  else stays stdlib-only. The plan must verify the grimp layering and isolated-import gates still
  pass — Phase 5 confirmed a pure-stdlib leaf needed no gate edits; this is a *different* condition
  and the claim must be re-tested, not assumed.
- **`assert_redaction_active` reaches into structlog's private `_file`.** The one genuinely fragile
  coupling in this phase. Plan it explicitly (see D-56's warning block).
- **Litmus discipline** — every `def`/`class`/param/annotation under `redact/` must be
  domain-noun-free. Phase 5 added a `redact_scanned` coverage guard to `test_litmus_clean`; new
  files land under the same guard automatically.
- **`EXTENSION-GUIDE.md` row table** — SEAM-08 must be added to the summary table at the top AND
  get its own numbered section, matching how SEAM-04..SEAM-07 are laid out.

</code_context>

<specifics>
## Specific Ideas

- The user took **every** researched recommendation across all four gray areas, plus the
  "test both recipes" follow-up. Each decision is recorded with its rejected alternatives so the
  reasoning is auditable and reversible if a later phase surfaces a problem.
- Consequent instruction for downstream agents (carried from Phase 5, reaffirmed): when a decision
  in this area needs the user, lead with a plain-language statement of what changes for them and a
  concrete recommendation. A bare menu of structlog trade-offs is not a usable question here.
- The advisor research corrected a false premise the discussion opened on (see `<decisions>`).
  Downstream agents should treat requirement text as intent, not as verified fact about the proven
  source — read the source.

</specifics>

<deferred>
## Deferred Ideas

- **The httpx / stdlib-`logging` coverage gap in WeatherBot** — httpx's INFO line carries the API
  key in the request URL and bypasses the structlog-only backstop
  (`weatherbot/weather/client.py:48-54`). **Hub-side, D-54's second recipe is the answer and is in
  scope.** Actually *adopting* it in WeatherBot is a consumer decision for the human-gated repin,
  not hub work. Flag it at repin time — do not let the repin assume the hub upgrade closes this by
  itself.
- **`RedactionPattern.asdict()`/`astuple()` still expose the raw pattern source** — Phase 5's WR-02
  residual, deliberately left open (closing it needs an opaque wrapper, i.e. a public API shape
  change). **Revisit if this phase's processor or telemetry ends up serializing pattern objects
  into an `event_dict`** — that is exactly the accidental-serialization scenario the residual was
  judged acceptable against.
- **A safe pattern-builder helper** (constructing `name=value` patterns without hand-writing regex)
  — carried from Phase 5; still the strongest follow-up candidate given the user's stated
  non-fluency with regex. Additional public surface beyond this milestone's requirements.
- **Per-pattern replacement strings beyond the template mechanism; partial masking preserving a
  token prefix/suffix for correlation** — differentiators, not table stakes. Rule of three.
- **Config-driven pattern loading** — out of scope; no second consumer to justify the shape.
- **A chain-builder helper for processor ordering** — rejected as D-60's third option. Revisit only
  if REDACT-05 stops being optional/droppable in a later milestone.

</deferred>

---

*Phase: 6-Insertion seams + provable backstop*
*Context gathered: 2026-07-29*
