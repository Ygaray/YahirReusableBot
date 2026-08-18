# Phase 5: Redaction core + pattern registration - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers the **generic secret-scrubbing primitive and the pattern API a consumer
registers against** — `redact_secrets()`, the `RedactionPattern` type, the registration path
including its ReDoS vetting, and the literal-value mode. Requirements: **REDACT-01, REDACT-02,
REDACT-03, REDACT-06**.

This is the entire public pattern surface a consumer will pin against, deliberately settled in one
phase because API shape is expensive to change once WeatherBot depends on it.

**Explicitly NOT in this phase** (Phase 6 — REDACT-04/05/07/08 + DOCS-04): the `RedactingWriter`
sink, the structlog processor, `assert_redaction_active`, redaction-count telemetry, and the
`EXTENSION-GUIDE.md` SEAM-08 row. Do not build a seam here. Phase 5 ends at "a consumer can build
and validate a pattern set"; Phase 6 is "a consumer can wire it into logging."

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues the project-wide sequence. Phase 4 reached **D-47**, so Phase 5
> starts at **D-48**. Distinct namespace from the module docstrings' own extraction decisions
> (`D-01..D-09` inside the source files).
>
> **The user reviewed the gray areas and elected to take the researched recommendations** ("do not
> understand most of these, research recommendations are fine"). Every decision below is therefore
> a locked recommendation derived from `.planning/research/` — recorded with its rejected
> alternatives so the planner sees the reasoning, not just the verdict. This continues the
> Phase-3/Phase-4 pattern.
>
> **Framing note for downstream agents:** the user is highly technical in this project's domain
> (Python services, systemd, deployment) but is *not* fluent in regex internals or structlog
> plumbing, and said so plainly. Surface future decisions in this area in plain language with a
> concrete recommendation. Do not present bare trade-off menus that presume regex fluency.

### Pattern + replacement shape (REDACT-01, REDACT-02)

- **D-48 (a pattern carries its own replacement — the API is a PAIR, not a bare regex):** the
  public unit is a `RedactionPattern` frozen dataclass pairing a **pre-compiled** `re.Pattern` with
  a **replacement template string**, consumed by `redact_secrets(text, patterns)` via `pattern.sub`.

  **Why this is forced, not preferred.** The proven source is:

  ```python
  _APPID_RX = re.compile(r"(appid=)[^&\s\"'<>\\]+", re.IGNORECASE)
  return _APPID_RX.sub(r"\1***", text)
  ```

  The replacement `r"\1***"` backreferences the `(appid=)` capture group — that backreference *is*
  the mechanism behind the "mask the value, preserve the diagnostics" table stake. An API accepting
  a bare compiled pattern and applying a fixed `***` would replace the **whole match**, destroying
  the `appid=` label and producing strictly worse logs than the app-local code being replaced. It
  would also fail the human-gated parity gate. So the replacement must travel with the pattern.

  Pre-compiled (not raw strings) is mandated at the API boundary so late compilation is
  structurally impossible and flags (`re.IGNORECASE` above) travel with the pattern rather than
  being a separate parameter that can desync.

  - **Rejected — bare `Iterable[re.Pattern]` + a fixed `***` replacement:** simplest signature, but
    breaks the preserve-diagnostics table stake and the parity gate, as above.
  - **Rejected — mandate named groups (`(?P<keep>...)`) instead of positional backrefs:** more
    robust in principle (a positional `\1` silently shifts if a consumer later adds a group), but
    mandating it forces every consumer to rewrite working patterns, including the exact one we must
    prove parity against. **Resolved as a synthesis:** accept any valid `re.sub` replacement
    template — so both `r"\1***"` and `r"\g<keep>***"` work — and *document named groups as the
    recommended convention* for new patterns. Parity is preserved; the robustness path is available
    without being compulsory.
  - **Rejected — accept raw pattern strings and compile internally:** friendlier signature, but
    re-introduces the late-compilation footgun the research explicitly warns against and separates
    flags from their pattern.

- **D-49 (zero patterns is a valid, silent identity no-op):** `redact_secrets(text, ())` returns
  `text` unchanged without raising or warning. A consumer wiring the mechanism before registering
  anything is a legitimate intermediate state, not an error. Overlapping patterns apply
  **sequentially in registration order** — documented, not special-cased.

### ReDoS vetting at registration (REDACT-03)

- **D-50 (vet at registration, default-ON, generous budget, explicit opt-out, raise `ValueError`):**
  the registration path probes each pattern against adversarial input under a wall-clock budget and
  raises `ValueError` naming the offending pattern if it blows the budget. Vetting is **on by
  default** with an explicit opt-out parameter for a pattern known to be legitimately slow.

  **Why default-on and why it raises rather than degrades.** Stdlib `re` has **no timeout**. Hub
  logging is synchronous and the Discord adapter runs an asyncio gateway loop, so a catastrophically
  backtracking pattern does not merely slow a log line — it starves the gateway heartbeat and drops
  the live connection. There is no runtime rescue available, so registration is the only place the
  check can exist. This matches the project's established **fail-loud-at-registration** posture
  (D-34): a pathological pattern is a consumer wiring bug that must surface at build time.

  Note this does **not** contradict D-36 ("degrade, don't raise"), which governed a *wait callable
  on a hot path* where raising would crash a running retry. Here the raise happens at wiring time,
  before anything is serving.

  - **Budget must be generous, not tight.** Pure-Python wall-clock timing is machine-dependent; a
    tight budget would false-reject a legitimate pattern on a loaded CI box or a busy host. Prefer
    a budget large enough that only genuinely catastrophic backtracking trips it. **Open to the
    planner:** the exact budget value and the adversarial input corpus. Pair the timing probe with
    a cheap structural check (e.g. nested quantifiers) so the verdict does not rest on timing alone.
  - **Rejected — no vetting, document the hazard:** cheapest, but hands every consumer a live
    footgun whose failure mode is a dropped production connection with no diagnostic pointing at the
    pattern.
  - **Rejected — runtime timeout / interrupt around `sub`:** stdlib `re` cannot be interrupted;
    achieving it would mean a signal-based or subprocess hack in a logging path, which is far more
    dangerous than the problem.

### Literal-value mode (REDACT-06)

- **D-51 (a literal is a pattern whose regex is escaped — one pipeline, two entry points):** expose
  literal registration as a named constructor (e.g. `RedactionPattern.literal("<secret value>")`)
  that `re.escape()`s the value and feeds the **same** compiled-pattern pipeline. There is exactly
  one scrubbing loop in `redact_secrets`; a literal is not a second code path.

  A literal replaces the whole matched value with the placeholder — unlike a `name=value` pattern
  there is no surrounding label to preserve, so there is nothing to keep.

  - **Rejected — a separate `literals` parameter and a second substitution pass:** conceptually
    tidy but doubles the scrubbing loop, doubles the ordering rules, and doubles the test surface
    for no behavioral gain.

### Core contract edges (REDACT-01)

- **D-52 (the core is strict `str -> str`; non-`str` triage belongs to the Phase-6 seam):**
  `redact_secrets(text: str, patterns) -> str` accepts and returns `str` only. The messy real-world
  type triage lives at the seam, exactly where the proven implementation puts it
  (`_LiveStderr.write`):

  ```python
  if isinstance(data, bytes):
      data = data.decode("utf-8", "replace")
  if isinstance(data, str):
      return sys.stderr.write(redact_appid(data))
  return sys.stderr.write(data)     # any other type forwarded untouched
  ```

  `bytes` are decoded with `"replace"` and scrubbed; any other type is forwarded untouched for the
  underlying stream to accept or reject. **Nothing in that path may raise** — a crash inside the
  logging path, mid-exception-handling, would mask the very error being logged.

  This keeps the core a pure, trivially-testable function and locates tolerance where the writes
  actually arrive.

  > **⚠ REQUIREMENTS.md wording adjustment — tracked deliberately, not a silent drift.**
  > `REDACT-01` is written as *the core* being "tolerant of non-`str` input (never raises
  > mid-exception-handling)". This decision relocates that clause's implementation to the seam
  > (**REDACT-04, Phase 6**), matching the proven design. The *mechanism as a whole* still satisfies
  > the requirement — nothing in the redaction path raises on non-`str` input. Phase 5 verification
  > must NOT report a gap because `redact_secrets` rejects `bytes`; that is the locked contract.
  > Phase 6 verification owns the tolerance assertion.

- **D-53 (disablement is an explicit parameter, never an environment read):** the ability to turn
  redaction off for local debugging is exposed as an explicit constructor/parameter value on the
  seam (Phase 6). The hub **never** reads an environment variable to decide this. A library that
  silently changes security behavior based on ambient process state is unauditable, and it makes
  the "is the backstop actually on?" question untestable. Recorded here because it constrains the
  core's signature (the core itself has no enabled/disabled concept — it is a pure function; zero
  patterns is the only no-op, per D-49).

### Claude's Discretion

The user delegated these to the researched recommendation. The planner has latitude on:
- Exact module split within `redact/` (`core.py` / `registry.py` — see ARCHITECTURE.md Q1/Q6).
- The precise ReDoS budget value and adversarial-input corpus (D-50).
- Whether `RedactionPattern` is a frozen dataclass or a `NamedTuple` — the pairing is locked, the
  container type is not.
- The exact placeholder default (`***` matches the proven code and should be the default).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The promotion source — read before writing any code
- `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` — the 28-line production implementation
  being generalized. Its regex, boundary character class, `re.IGNORECASE` flag, and `\1***`
  backreference are the parity target.
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py` (`_LiveStderr.write`, ~lines 26–56) —
  the proven wiring seam and the exact non-`str` triage locked by D-52.
- `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` — **6 tests**; the human-gated
  close-out parity gate runs these *unmodified* against the hub-backed replacement. Their
  assertions are the de facto behavioral spec.

### This milestone's research
- `.planning/research/SUMMARY.md` — synthesis; the registry-statefulness resolution and the
  seam recommendation.
- `.planning/research/STACK.md` — zero-new-dependency verdict; verified `structlog` 26.1.0 API
  surfaces; `re` guidance (pre-compiled patterns, named groups, callable `repl` escape hatch).
- `.planning/research/FEATURES.md` — table stakes vs differentiators vs anti-features; the
  pattern-registration API comparison.
- `.planning/research/ARCHITECTURE.md` — `redact/` module tree, build order (Q6), import-hygiene
  analysis.
- `.planning/research/PITFALLS.md` — 10 pitfalls with phase mapping; ReDoS, traceback coverage,
  and the app-local→library migration hazards.

### Project constitution and scope
- `.planning/ROADMAP.md` § "Milestone v0.2.0" → Phase 5 — goal, 5 success criteria, and the
  in-phase scope notes.
- `.planning/REQUIREMENTS.md` § "Milestone v0.2.0" — REDACT-01/02/03/06 full text (note the D-52
  wording adjustment above).
- `.planning/backlog/PROMOTION-CANDIDATES.md` — PC-01's litmus test and when-actioned sequence.
- `ECOSYSTEM.md` §3 (human-gated repin) and §6 (promotion mechanics).
- `EXTENSION-GUIDE.md` — seam conventions; SEAM-08 is added in Phase 6, not here.
- `tests/test_import_hygiene.py` — the standing gate every change must keep green.

### Prior locked decisions still binding
- `.planning/milestones/v0.1.2-phases/03-public-surface-footguns/03-CONTEXT.md` — **D-34**
  (fail-loud-at-registration posture, directly precedent for D-50), **D-36** (degrade-don't-raise
  for hot-path callables, scoped narrowly — see D-50's note).
- `.planning/milestones/v0.1.2-phases/04-cleanup-readygate-fatal/04-CONTEXT.md` — **D-45**
  (additive-and-defaulted field posture).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`WeatherBot/weatherbot/_redact.py`** — not merely a reference; the parity target. Its
  `[^&\s"'<>\\]+` boundary class is the concrete expression of "stop at the value boundary so the
  scrub never eats the following query params, the trailing quote, or the MDN link."
- **`tests/conftest.py`** — the hub's existing fixture module (added Phase 1, D-09/D-10). New
  redaction fixtures belong here, following its no-`yahir_reusable_bot`-import convention.
- **Hub test conventions** — hand-written doubles only; `unittest.mock` / `pytest-mock` are not
  used anywhere in this suite and must not be introduced.

### Established Patterns
- **Fail loud at construction/registration** (D-34, `registry.py`; `panelkit.py:207`) — a malformed
  consumer input raises `ValueError` at wiring time rather than degrading at runtime. D-50 follows
  this directly.
- **RED-first, two-commit discipline** (GATE-02) — each requirement lands as a test-only commit
  that genuinely fails against pre-fix source, then the fix commit. Phase verification re-derives
  this ancestry with `git rev-parse`, so the two commits must be real and adjacent.
- **Plans sequenced so a deliberately-RED test never overlaps a sibling plan's full-suite gate** —
  hard-won across Phases 1–3.
- **Module logger via `structlog.get_logger(__name__)`** — every hub module does this and none
  calls `structlog.configure()`. Configuration is 100% consumer policy; `redact/` must not break
  that.

### Integration Points
- **New leaf subpackage `yahir_reusable_bot/redact/`** — pure leaf: stdlib only in this phase
  (`structlog` enters only with Phase 6's `processor.py`). It must import **no sibling**
  `yahir_reusable_bot` subpackage, which keeps the grimp layering graph unchanged and requires
  **no edits to `tests/test_import_hygiene.py`**.
- **Litmus discipline is the only real hygiene risk:** every `def`/`class`/param/annotation name
  under `redact/` must be domain-noun-free. `redact_secrets(text, patterns)` — never
  `redact_appid`, never an `appid` parameter. The AST signature litmus will catch a violation, but
  the naming must be right by intent, not by gate.
- **Naming collision to avoid:** the hub already has a *command* `registry/` subpackage (SEAM-06).
  `redact/registry.py` is a different, much smaller thing at a distinct dotted path. Do not merge
  them by analogy-confusion.

</code_context>

<specifics>
## Specific Ideas

- The user explicitly delegated these decisions to the researched recommendations rather than
  selecting per-area, stating they did not follow the technical framing. The decisions above are
  recommendations locked on their behalf — each is recorded with its rejected alternatives so the
  reasoning is auditable and reversible if a later phase surfaces a problem.
- Consequent instruction for downstream agents: when a decision in this area needs the user, lead
  with a plain-language statement of what changes for them and a concrete recommendation. A bare
  menu of regex/structlog trade-offs is not a usable question for this user.

</specifics>

<deferred>
## Deferred Ideas

- **Per-pattern replacement strings beyond the template mechanism, and partial masking that
  preserves a token prefix/suffix for correlation** — classed as differentiators by the FEATURES
  research, not table stakes. No consumer need yet; revisit under rule-of-three.
- **Config-driven pattern loading** (patterns from a config file rather than code) — out of scope;
  no second consumer to justify the shape.
- **A safe pattern-builder helper** (constructing `name=value` patterns without hand-writing regex)
  — genuinely attractive given this user's stated non-fluency with regex, and it would reduce the
  ReDoS surface at the source. But it is additional public surface beyond REDACT-01/02/03/06.
  **Flagged as the strongest candidate for a follow-up** once the core API proves out.
- **`weatherbot/weather/client.py`'s domain-specific redacted re-raise** — permanently out of PC-01
  scope. It is domain logic and stays app-local forever, per REQUIREMENTS.md close-out item 5.

</deferred>

---

*Phase: 5-Redaction core + pattern registration*
*Context gathered: 2026-07-29*
