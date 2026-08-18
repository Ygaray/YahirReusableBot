# Phase 5: Redaction core + pattern registration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 5-redaction-core-pattern-registration
**Areas discussed:** Pattern + replacement shape, ReDoS vetting policy, Literal-value mode shape, Core contract edges
**Mode:** advisor (calibration tier `standard`; `NON_TECHNICAL_OWNER` resolved false — see note)

---

## How this discussion actually went

All four gray areas were presented in one multi-select turn. The user replied:

> "do not understand most of these, research recommandations are fine"

That is a single delegation covering all four areas, not four separate selections. No per-area
advisor research agents were spawned: the milestone's four project researchers
(STACK / FEATURES / ARCHITECTURE / PITFALLS) had already covered every one of these areas in depth,
so the recommendations were derived from `.planning/research/` rather than re-researched. That saved
four agent runs without reducing the evidence behind any decision.

**Advisor-mode framing miss, recorded for future phases.** `NON_TECHNICAL_OWNER` was resolved to
`false` at the start, on the reasoning that the profile is prose-formatted (lacking the literal
`learning_style: guided` field the rule keys on) and that the user is demonstrably technical in this
project's domain. That was the wrong call *for this topic*. The user is fluent in Python services,
systemd, and deployment, but not in regex internals or structlog plumbing — and said so. The four
areas were framed presuming regex fluency and were not usable as posed. After the reply, each locked
decision was re-explained in plain language before being written to CONTEXT.md. CONTEXT.md carries a
standing instruction to downstream agents to lead with plain language and a concrete recommendation
in this area.

---

## Pattern + replacement shape

| Option | Description | Selected |
|--------|-------------|----------|
| `RedactionPattern` pair (compiled pattern + replacement template) | The unit carries both "what to find" and "what to leave behind", so `appid=SECRET` → `appid=***` keeps the label | ✓ (D-48) |
| Bare `Iterable[re.Pattern]` + fixed `***` | Simplest signature; replaces the whole match | |
| Mandate named groups `(?P<keep>...)` | More robust than positional `\1`, but forces rewriting the exact pattern we must prove parity against | partial |

**User's choice:** delegated — "research recommendations are fine."
**Notes:** This one turned out to be forced rather than preferred. Reading the promotion source
(`weatherbot/_redact.py`) showed the replacement `r"\1***"` backreferences the `(appid=)` capture
group, and that backreference *is* the "mask the value, keep the label" mechanism. A bare-pattern
API replacing the whole match would produce strictly worse logs than the app-local code being
replaced, and would fail the human-gated parity gate. The named-group option was resolved as a
synthesis rather than a rejection: any valid `re.sub` template is accepted (so both `\1***` and
`\g<keep>***` work) and named groups are *documented* as the recommended convention for new
patterns. Parity preserved, robustness path available, neither compulsory.

---

## ReDoS vetting policy

| Option | Description | Selected |
|--------|-------------|----------|
| Vet at registration, default-on, generous budget, explicit opt-out, raise `ValueError` | Probe each pattern against adversarial input at wiring time; refuse bad ones loudly | ✓ (D-50) |
| No vetting, document the hazard | Cheapest; hands every consumer a live footgun | |
| Runtime timeout around `sub` | Stdlib `re` cannot be interrupted; would require a signal/subprocess hack inside a logging path | |

**User's choice:** delegated — "research recommendations are fine."
**Notes:** Registration is the *only* place this check can exist — stdlib `re` has no timeout, so
there is no runtime rescue. The consequence is unusually severe here: hub logging is synchronous and
the Discord adapter runs an asyncio gateway loop, so a catastrophically backtracking pattern starves
the heartbeat and drops the live connection. Follows the project's established fail-loud-at-
registration posture (D-34). Explicitly reconciled against D-36 ("degrade, don't raise") — that
governed a *wait callable on a hot path*, where raising would crash a running retry; here the raise
happens at wiring time before anything is serving. Budget deliberately left generous and its exact
value delegated to the planner, because pure-Python wall-clock timing is machine-dependent and a
tight budget would false-reject legitimate patterns on a loaded CI box.

---

## Literal-value mode shape

| Option | Description | Selected |
|--------|-------------|----------|
| Named constructor that `re.escape()`s into the same pipeline | One scrubbing loop, two entry points; a literal is just a pattern whose regex is escaped | ✓ (D-51) |
| Separate `literals` parameter + second substitution pass | Conceptually tidy; doubles the loop, the ordering rules, and the test surface | |

**User's choice:** delegated — "research recommendations are fine."
**Notes:** A literal replaces the whole matched value — unlike a `name=value` pattern there is no
surrounding label to preserve, so there is nothing to keep.

---

## Core contract edges

| Option | Description | Selected |
|--------|-------------|----------|
| Core strict `str -> str`; non-`str` triage at the Phase-6 seam | Matches the proven `_LiveStderr.write` split exactly; core stays pure and trivially testable | ✓ (D-52) |
| Core tolerates non-`str` itself | Matches REQUIREMENTS.md REDACT-01 as literally worded | |

**User's choice:** delegated — "research recommendations are fine."
**Notes:** The proven implementation puts the triage at the write seam: `bytes` decoded with
`"replace"` then scrubbed, `str` scrubbed, any other type forwarded untouched — and nothing in that
path may raise, since a crash inside logging would mask the very error being logged. Locking the
proven split means **REDACT-01's wording is adjusted**: its "tolerant of non-`str` input" clause is
implemented at the seam (REDACT-04, Phase 6) rather than in the core. This is flagged prominently in
CONTEXT.md so Phase 5 verification does not report a false gap when `redact_secrets` rejects
`bytes`. Disablement was locked alongside (D-53): an explicit parameter, never an environment read —
a library that silently changes security behavior from ambient process state is unauditable.

---

## Claude's Discretion

Delegated to the researched recommendation and left open for the planner:

- Exact module split within `redact/` (`core.py` / `registry.py`).
- The precise ReDoS budget value and the adversarial-input corpus.
- Whether `RedactionPattern` is a frozen dataclass or a `NamedTuple` — the *pairing* is locked, the
  container type is not.
- The placeholder default (`***` matches the proven code and should be the default).

## Deferred Ideas

- **Per-pattern replacement beyond the template mechanism; partial masking preserving a token
  prefix/suffix for correlation** — differentiators, not table stakes. Revisit under rule-of-three.
- **Config-driven pattern loading** — no second consumer to justify the shape.
- **A safe pattern-builder helper** (build `name=value` patterns without hand-writing regex) —
  strongest follow-up candidate. Directly relevant given the user's stated non-fluency with regex,
  and it would shrink the ReDoS surface at the source. Out of scope for REDACT-01/02/03/06.
- **`weatherbot/weather/client.py`'s domain-specific redacted re-raise** — permanently app-local,
  per REQUIREMENTS.md close-out item 5.
