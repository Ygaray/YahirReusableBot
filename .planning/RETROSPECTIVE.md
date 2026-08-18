# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v0.2.0 — Redaction promotion + hardening debt

**Shipped:** 2026-08-18
**Phases:** 4 (Phases 5–8) | **Plans:** 19 | **Tasks:** 44

### What Was Built
- **Generic secret-redaction core** — `redact_secrets(text, patterns)` with a frozen
  `RedactionPattern` pair type and a source-eliding literal-secret constructor, ported generically
  from WeatherBot's `_APPID_RX` (the hub's first *promotion*, not a defect fix).
- **Safe pattern registration** — `register_patterns` vets patterns with a structural
  nested-quantifier check plus a 13-rung escalating wall-clock ReDoS probe before freezing them into
  an immutable tuple; both halves proven independently load-bearing.
- **structlog insertion seams + provable backstop** — `RedactingWriter` (a file-like proxy scrubbing
  fully-rendered write text, incl. tracebacks that bypass `event_dict`), the optional additive
  `redaction_processor`, and `assert_redaction_active` (fails loud on a dropped-wiring reconfigure).
- **v0.1.2 debt paydown** — duplicate `CommandSpec.name` now rejected at registration (MATCH-03);
  `Forbidden` vs `HTTPException` logged distinctly + failed eviction retried (DISC-07/08); structured
  `label=` + no unawaited-coroutine warning (HYG-02/03); annotation narrowing recorded (SURF-02/LIFE-05);
  doc-drift gate (DOCS-02/03).
- **Hardening cleanup** — REDACT-09 (WR-02 accept ratified with a live-docstring rationale gate),
  REDACT-10 (`RedactingWriter.on_error` hook + fail-closed contract), DOCS-05 (three non-vacuous
  prose gates), HYG-04 (pyright `basic` dev-only gate with a hand-rolled, unit-tested baseline-diff).

### What Worked
- **Gate-1 as a wheel-in-scratch-venv rung** (`AGENT-LIBRARY-TESTING.md`): for a pure library with
  no device surface, building the wheel and driving the installed public API from a non-repo cwd
  caught packaging-level risks `uv run pytest` (with `pythonpath=["."]`) structurally cannot see.
- **RED-first ancestry proven from git trees, not prose** — every requirement's regression test was
  shown to fail against pre-fix source, verified from the actual commit trees.
- **Settling open decisions by experiment rather than argument** — D-03 (retire-vs-keep) was
  resolved by running the retirement and observing what broke, not by reasoning.

### What Was Inefficient
- **Phase 7/8 Gate-1 artifacts were skipped during execution** on a false "no drivable surface"
  premise and had to be produced retroactively at certification. The library IS driveable via its
  installed public API — the skip cost a full certify-repair cycle.
- **Concurrent Gate-1 agentic testers clobbered the shared UAT ledger** (`HUMAN-UAT-PENDING.md`):
  two parallel testers raced, one did a whole-file overwrite + `git checkout` revert and destroyed
  the other's uncommitted entry. Recovered by hand; filed as `INC-2026-08-18-01`.
- **Security audit staleness re-triggered re-audits** on `.planning`-only changes (tracked
  separately as `INC-2026-08-12-03`), adding tail-gate churn late in Phase 8.

### Patterns Established
- **Promotion discipline** — the redaction subsystem is the first mechanism promoted into the hub
  from a consumer; it names no domain nouns and injects the consumer-specific pattern, passing the
  import-hygiene litmus. This is the reference shape for future promotions.
- **Non-vacuous doc gates** — prose regression gates (DOCS-05) each ship a self-proof that excises
  the target paragraph and asserts the gate then fails, so the gate can't silently pass on absent prose.
- **Dev-only tooling gates stay out of the shipped wheel** — pyright (HYG-04) is confined to
  `[dependency-groups].dev` and verified absent from the built wheel; zero consumer blast radius.

### Key Lessons
1. **"Library ⇒ no agentic UAT" is wrong.** The drivable surface is the installed package's public
   API. Encode this once in the driver playbook so no future phase re-skips Gate-1 on that premise.
2. **Never fan out agents that write a shared, uncommitted planning file without a concurrency
   protocol.** Per-phase fragments or a lock — and never `git checkout` a file other agents may be
   editing.
3. **Accepted residuals are not gaps.** Four `signed-off-with-gap` sign-offs are documented
   accept-decisions (or deferred-to-repin actions), correctly landing the audit at `tech_debt`, not
   `gaps_found`.

### Cost Observations
- Model mix: predominantly opus for orchestration/verification; haiku for the integration checker.
- Sessions: multi-session (execution Jul 29 – Aug 18); this close ran in one session.
- Notable: the certify safety-net (producing the two missing Gate-1 artifacts + integration reuse)
  closed the milestone without re-running the whole pipeline.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Key Change |
|-----------|--------|------------|
| v0.1.2 Hub hardening | 4 | Keeper-branch + one-squash-on-main release ritual established; RED-first regression tests per fix. |
| v0.2.0 Redaction promotion + hardening debt | 4 | First hub *promotion* (redaction) under the no-domain-nouns litmus; Gate-1 formalized as a wheel-in-scratch-venv rung for a library; non-vacuous doc gates. |

### Cumulative Quality

| Milestone | Tests (full suite) | Import-hygiene | Notable gate additions |
|-----------|--------------------|----------------|------------------------|
| v0.1.2 | 80 passed | 8 passed | import-hygiene / litmus / grimp (GATE-01) |
| v0.2.0 | 218 passed | 10 passed | doc-drift gate, pyright `basic` (HYG-04), redact litmus coverage guard |

### Top Lessons (Verified Across Milestones)

1. Prove RED-first ancestry from git trees, not prose — holds across v0.1.2 and v0.2.0.
2. Close-out (version bump / tag / repin / deploy) is human-gated; autonomous work stops at green
   gates + a local tag.
