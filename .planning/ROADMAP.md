# YahirReusableBot — Roadmap

## Milestone v0.1.0 — Initial extraction (DONE)

Imported from the WeatherBot v2.0 "Bot Module Extraction" milestone (Phases 22–28). The module
core, the standing import-hygiene suite, and the `EXTENSION-GUIDE` ship in the single clean
import commit tagged `v0.1.0`.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Initial import (module tree, pyproject, re-scoped import-hygiene suite, EXTENSION-GUIDE, GSD init) | done |

## Milestone v0.1.2 — Hub hardening (SHIPPED 2026-07-28, tag `v0.1.2`)

Close all 17 audit-surfaced hub defects (H01–H17) plus the H18 `ReadyGate` fatal-outcome
enhancement. Sequencing is correctness-first, reachable-first, then reusability hardening,
cleanup last. Source of record: `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md`.

All 18 findings re-verified against source before roadmapping — no semantic drift; two line
numbers moved within their own function (H07 `gateway.py:246`, H04 `gateway.py:278`).

**Standing gate for every phase (GATE-01):** full pytest suite + import-hygiene / litmus / grimp
layering checks stay green. **Every fix ships a RED-first regression test** — it must fail against
current source first. Existing tests cover only decoy cases for several findings, so the
adversarial case gets added rather than a new happy path.

> **Outcome:** 4/4 phases complete, 19/19 requirements satisfied, tagged `v0.1.2` (`60698b1`),
> repinned into WeatherBot and deployed live on `yahir-mint`. Retrospective audit:
> `.planning/v0.1.2-MILESTONE-AUDIT.md` — status `tech_debt`, no blockers, 9 open items. Phase
> artifacts archived to `.planning/milestones/v0.1.2-phases/`. The 9 open items (minus the parked
> EXT points) are Milestone v0.2.0's Track B below.

### Phase 1: Reachable reliability

**Goal:** Close the only two defects live and unmitigated in a real consumer today.
**Requirements:** RELY-01 (H02), LIFE-01 (H01)
**Depends on:** —
**Plans:** 4/4 plans complete

Success criteria:

- `is_transient` classifies `httpx.RemoteProtocolError` and `httpx.WriteError` as transient; a
  server hangup mid-response drives the two-burst retry and reports `transient_exhausted` on
  exhaustion instead of `internal_error`.

- `LocalProtocolError` still classifies non-transient (the fix is not a blanket `TransportError`).
- The identity guard does not match a recycled PID running the marker as a positional arg
  (`python -m pytest <marker>`), and *does* match a daemon started as `python -O -m <marker> run`.

- New regression tests for both fail against pre-fix source.

> Criterion 1's `transient_exhausted` clause is satisfied via the D-17 hub-scoped restatement:
> `REASON_TRANSIENT_EXHAUSTED` is *defined* at `retry.py:75` but assigned only by consumer-side
> `fire_slot`, so the hub-assertable equivalent is "an exhausted `RemoteProtocolError` escapes
> `Retrying.__call__` as itself, not as a `tenacity.RetryError`".

Plans (sequential — Plan 03 waits on 02 so a deliberately RED test never overlaps a sibling's
full-suite gate):

- [x] 01-01-PLAN.md — Phase branch, pre-fix baseline capture, and `tests/conftest.py` (the hub's
  first fixtures, D-09/D-10)

- [x] 01-02-PLAN.md — RELY-01: `tests/test_retry.py` committed RED, then the `is_transient` fix
- [x] 01-03-PLAN.md — LIFE-01: `tests/test_identity.py` committed RED, then the
  `_argv_matches_marker` first-`-m` scan fix

- [x] 01-04-PLAN.md — Phase gate audit, RED-first history proof, authorized merge to `main`

### Phase 2: Latent runtime robustness

**Goal:** Close real hub bugs that need specific runtime conditions to bite.
**Requirements:** CFG-01 (H03), DISC-01 (H04), DISC-02 (H05), DISC-03 (H07), DISC-04 (H08)
**Depends on:** Phase 1
**Plans:** 3/3 plans complete

Success criteria:

- A PHASE-2 reconcile failure fires `on_rejected` before re-raising, and the rollback/restore
  behavior is otherwise byte-identical (the original error is still the one raised).

- A non-recoverable gateway disconnect leaves an operator-visible signal rather than a silently
  dead bot — **the retry/backoff contract is an open design decision to settle in this phase.**

- Re-summoning a panel cannot leave two live pinned panels or a fresh-but-unpinned panel, with
  `HTTPException`/`NotFound` handled per-item.

- `stop()` cannot raise `RuntimeError` when the loop stops mid-call.
- **DISC-04 is contract + API only** — the observed defect's fix site is consumer-side; this phase
  makes the `SelectedContext` await-safety contract explicit, it does not chase the consumer bug.

Plans (sequential Waves 1→2→3 — each plan runs the full-suite GATE-01 as its wave gate and every
plan commits a deliberately-RED test, so plans are staggered so a RED test never overlaps a
sibling's full-suite gate; the Phase-1 "Plan 03 waits on 02" lesson):

- [x] 02-01-PLAN.md — CFG-01: `tests/test_reload.py` RED, then fire `on_rejected` on the PHASE-2
  reconcile-failure path (D-31/D-32)

- [x] 02-02-PLAN.md — gateway.py DISC-01/02/03: death-reason accessor (liveness-only, D-21/D-22),
  `summon_panel` per-item delete + pin-cap headroom (D-24..D-27), `stop()` TOCTOU degrade (D-28)

- [x] 02-03-PLAN.md — DISC-04: `tests/test_selection.py` RED, then `SelectedContext.snapshot()` +
  await-safety docstring contract (D-29/D-30), contract + API only

### Phase 3: Reusable public-surface footguns

**Goal:** Harden the public surface against footguns unreachable in the current consumer but
guaranteed to bite the next one. This is the hub's entire reason to exist.
**Requirements:** MATCH-01 (H06), MATCH-02 (H13), RELY-02 (H09), RELY-03 (H10), DISC-05 (H11), DISC-06 (H12), LIFE-02 (H14), LIFE-03 (H15), SCHED-01 (H16)
**Depends on:** Phase 2
**Plans:** 5/5 plans complete

**Pairing constraints — these must land together, not as independent tasks:**

- **MATCH-01 + MATCH-02** — both are `registry/match.py` casefold symmetry. Fixing one without the
  other leaves the matcher half-consistent.

- **RELY-02 + RELY-03** — both are the `retry.py` `burst_size` coupling.

Success criteria:

- A length-changing casefold (`ßtatus arg`, `ﬁnd hello`) extracts the correct arg; an empty
  `spec.name` cannot claim blank input; an uppercase registered name is matchable.

- `burst_size == 1` degrades instead of raising `ZeroDivisionError` from inside the tenacity wait.
- `interaction_check` returns False for an absent `interaction.user`; an empty `marker` is
  rejected at construction.

- `write_pid_atomic` cannot double-close an fd; the non-Linux degrade holds for a path-shaped marker.
- `SchedulerEngine.remove` has a tested, stated contract for an already-gone id.

Plans (strictly serial Waves 1→5, one per disjoint file — each plan commits its RED test then its
GREEN fix and re-verifies GATE-01 green before the next plan's RED commit, so a deliberately-RED test
never overlaps a sibling's full-suite gate; the two ROADMAP pairings each stay within one plan):

- [x] 03-01-PLAN.md — SCHED-01: `tests/test_engine.py` RED, then idempotent `SchedulerEngine.remove`
  via dependency-free `except KeyError:` + module logger (D-38)

- [x] 03-02-PLAN.md — LIFE-02 + LIFE-03: `tests/test_identity.py` RED, then the `write_pid_atomic`
  fd-double-close guard (D-42) and the `_argv_matches_marker` basename-both-sides fix (D-39)

- [x] 03-03-PLAN.md — MATCH-01 + MATCH-02 (pairing): new `tests/test_registry.py` / `tests/test_match.py`
  RED, then registration-time `spec.name` validation (D-34) and the original-index boundary slice (D-35)

- [x] 03-04-PLAN.md — RELY-02 + RELY-03 (pairing): `tests/test_retry.py` RED, then the `burst_size <= 1`
  degrade guard (D-36) and the `two_burst_wait` standalone-desync precondition docstring + mid-pause pin (D-37)

- [x] 03-05-PLAN.md — DISC-05 + DISC-06: new `tests/test_panelkit.py` RED, then the `interaction_check`
  None/MISSING falsy guard (D-40) and the empty-marker construction reject (D-41)

### Phase 4: Cleanup + ReadyGate fatal outcome

**Goal:** Fix public-surface drift and give consumers a fatal outcome to de-hack against.
**Requirements:** SURF-01 (H17), LIFE-04 (H18)
**Depends on:** Phase 3
**Plans:** 2/2 plans complete

Plans:

- [x] 04-01-PLAN.md — LIFE-04: ReadyGate fatal outcome (ReadyOutcome enum + HealthResult.fatal + run rewrite + de-hack docs)
- [x] 04-02-PLAN.md — SURF-01: summon_panel re-export from the discord subpackage

Success criteria:

- `from yahir_reusable_bot.discord import summon_panel` succeeds, with docstring,
  `gateway.__all__`, and the package `__init__` in agreement.

- `ReadyGate.run` surfaces a fatal probe result as a distinct outcome a consumer branches on —
  no `stop`-Event overload required. The ok and clean-shutdown paths keep their current
  semantics and emit ordering (`on_online` → log → `READY=1`).

- The de-hack is documented for the repin: the two WeatherBot sites that collapse onto the new
  outcome are named in the phase summary.

**Human-gated close-out — surfaced, never performed autonomously** (`ECOSYSTEM.md` §3):
bump `pyproject.toml` `0.1.1 → 0.1.2` · cut tag `v0.1.2` · repin WeatherBot `[tool.uv.sources]`
`v0.1.1 → v0.1.2` + `uv sync --frozen` · re-run WeatherBot's suite against the repinned hub.
**Executed 2026-07-28.**

## Milestone v0.2.0 — Redaction promotion + hardening debt (ACTIVE)

Two tracks in one milestone, **phase numbering continues from v0.1.2** (which ended at Phase 4).

- **Track A — PC-01, the hub's first *promotion* (Phases 5–6).** Generalize WeatherBot's
  production-proven app-local secret redactor into a generic `yahir_reusable_bot/redact/`
  subpackage. Source of record: `.planning/backlog/PROMOTION-CANDIDATES.md`; research:
  `.planning/research/SUMMARY.md` (+ STACK / FEATURES / ARCHITECTURE / PITFALLS). Verified
  verdict: **zero new dependencies** — `structlog` (already pinned, resolved 26.1.0) plus stdlib
  `re` cover the whole mechanism.

- **Track B — v0.1.2 debt paydown (Phase 7).** Clear every open item the retrospective audit
  surfaced (`.planning/v0.1.2-MILESTONE-AUDIT.md`, 9 items). Independent of Track A and mostly of
  each other; sequenced last so the headline promotion lands first and the debt absorbs any slip.

**Standing gate for every phase (GATE-02):** the full pytest suite plus the standing
import-hygiene gates (grimp graph + isolated-import + AST signature litmus,
`tests/test_import_hygiene.py`) stay green, and **every requirement ships a RED-first regression
test** that fails against pre-fix source before the fix lands. No change may regress the one-way
dependency or the generic-surface litmus. GATE-02 is milestone-standing — it is stated here once
and asserted in every phase, not carried as a phase of its own.

**Standing PC-01 litmus:** the mechanism is fully generic. Only the *pattern* is
consumer-specific and it is always injected, never hardcoded — `redact_secrets(text, patterns)`,
never `redact_appid` or an `appid` parameter. No domain noun may enter the hub surface.

**Standing plan-sequencing rule (hard-won in Phases 1–3):** plans within a phase are ordered so a
deliberately-RED test never overlaps a sibling plan's full-suite gate. Each plan commits its RED
test, then its GREEN fix, and re-verifies GATE-02 green before the next plan's RED commit.

**Naming collision to call out at plan time:** the hub already has a *command* `registry/`
subpackage (SEAM-06). The new `redact/registry.py` is a different, much smaller thing (a pattern
collection) at a distinct dotted path — do not merge the two by analogy-confusion.

### Phases

- [x] **Phase 5: Redaction core + pattern registration** - The generic scrubbing primitive and a safe-by-construction pattern API (completed 2026-07-29)
- [x] **Phase 6: Insertion seams + provable backstop** - The load-bearing sink, the additive processor, and proof the backstop is live (completed 2026-08-04)
- [x] **Phase 7: v0.1.2 debt paydown** - Every open audit item closed; no known footgun, no stale doc (completed 2026-08-04)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 5. Redaction core + pattern registration | 3/3 | Complete    | 2026-07-29 |
| 6. Insertion seams + provable backstop | 4/4 | Complete    | 2026-08-04 |
| 7. v0.1.2 debt paydown | 7/7 | Complete    | 2026-08-04 |

### v0.2.0 Phase Details

### Phase 5: Redaction core + pattern registration

**Goal**: The hub owns a generic secret-scrubbing primitive and a safe-by-construction way to
register the patterns it uses — no domain noun, no process-wide mutable state, no ReDoS surface.
**Depends on**: Nothing (first phase of the milestone; v0.1.2 shipped)
**Requirements**: REDACT-01, REDACT-02, REDACT-03, REDACT-06
**Success Criteria** (what must be TRUE):

  1. `redact_secrets(text, patterns)` masks the secret value while the surrounding diagnostics
     survive intact (endpoint, HTTP status, neighbouring params), is idempotent under
     re-application, and returns non-`str` input without raising mid-exception-handling —
     WeatherBot's boundary-case matrix, ported into the hub suite, passes.

  2. Patterns are compiled once at registration and frozen into an immutable collection; the hub's
     own suite produces identical results run in isolation and run in full-suite order — no
     cross-test pollution, no import-order dependence, no module-level mutable singleton.

  3. A pattern with nested/overlapping quantifiers that blows a wall-clock budget against
     adversarial input is **rejected at registration** with a raised error, never silently accepted
     to hang at log time.

  4. A registered literal secret value is blocked wherever it appears — including inside a
     `repr()` of an object that embeds it — not only in a `name=value` shape.

  5. Every `def`/`class`/param/annotation name under `redact/` passes the AST signature litmus, and
     `redact/` imports no sibling `yahir_reusable_bot` subpackage (pure leaf: stdlib only).

**Plans**: 3/3 plans executed

Plans (strictly serial Waves 1→2→3 — each plan commits its RED test then its GREEN fix and
re-verifies the standing gates green before the next plan's RED commit, so a deliberately-RED test
never overlaps a sibling plan's full-suite gate; the Phases 1–3 lesson):

- [x] 05-01-PLAN.md — REDACT-01 / REDACT-06 / REDACT-02 (type half): `tests/test_redact_core.py` RED,
  then `redact/core.py` — the `RedactionPattern` pattern+replacement pair (D-48), the escaped-literal
  constructor (D-51), and the `redact_secrets` scrubbing loop (D-49/D-52/D-53)

- [x] 05-02-PLAN.md — REDACT-02 (registration half) / REDACT-03: `tests/test_redact_registry.py` RED,
  then `redact/registry.py` — `register_patterns` with the structural check plus a
  bounded-termination wall-clock ReDoS probe (D-50)

- [x] 05-03-PLAN.md — Phase gate: confirm the import-hygiene no-edit claim, add the `redact/` litmus
  coverage guard, and audit GATE-02's RED-first ancestry + the human-gated close-out record

**Scope notes for discuss/plan:**

- Build order inside the phase is `core.py` → `registry.py` (research ARCHITECTURE Q6 steps 1–2).
  REDACT-03's ReDoS vetting is part of the registration API, not bolted on afterwards — it is the
  registration call that raises.

- The API shape must make late compilation structurally impossible (accept compiled pattern
  objects / a registered handle, never raw strings at the call site) and must expose disablement
  as an explicit constructor parameter — **never** an env-var read inside the hub
  (PITFALLS 6, 7, 9). These are expensive to change once a consumer depends on them; settle them
  here, not retrofitted later.

- The parity-test plan for the human-gated close-out (which exact WeatherBot assertions must
  re-pass, and the explicit scope boundary around `client.py`) is written and agreed at this
  phase's discuss/plan time, not improvised at repin time (PITFALLS 10).

### Phase 6: Insertion seams + provable backstop

**Goal**: A consumer can wire the hub's redaction into its own `structlog.configure()` and have
every rendered log line — event fields and formatted tracebacks alike — provably scrubbed.
**Depends on**: Phase 5
**Requirements**: REDACT-04, REDACT-05, REDACT-07, REDACT-08, DOCS-04
**Success Criteria** (what must be TRUE):

  1. A `logger.exception(...)` rendered through `dev.ConsoleRenderer` — which formats tracebacks
     straight to the stream, bypassing `event_dict` — comes out of the wrapped sink with the secret
     masked, asserted against the **full captured output**, never `str(exc)` alone; and a
     `JSONRenderer`-produced line carrying an escaped secret still round-trips through
     `json.loads` after redaction.

  2. The optional structlog processor scrubs `event_dict` string values pre-render, and its
     chain-order precondition (must sit after the exception formatters) is stated loudly in its own
     docstring — shipped as additive defense-in-depth, never as the sole backstop.

  3. `assert_redaction_active` fails loudly when the backstop is not actually installed — e.g.
     after a second `structlog.configure()` call drops it — and passes when it is.

  4. Redaction-count telemetry reports how many substitutions fired, so a consumer can observe the
     backstop working rather than assume it.

  5. `EXTENSION-GUIDE.md` carries SEAM-08 with its row flipped to **implemented**, naming the
     architectural inversion explicitly: the hub supplies a toolkit the consumer wires into its own
     `structlog.configure()`, so no `Redactor` Protocol exists to go looking for.

**Plans**: 4/4 plans executed

Plans (strictly serial Waves 1→2→3→4 — each requirement plan commits its RED test then its GREEN fix
and re-verifies the standing gates green before the next plan's RED commit, so a deliberately-RED test
never overlaps a sibling plan's full-suite gate; the Phases 1–3 lesson, re-proven in Phase 5):

- [x] 06-01-PLAN.md — REDACT-04 / REDACT-08: `tests/test_redact_sink.py` RED, then `redact/sink.py` —
  `RedactingWriter` (rendered-text backstop, D-52 triage, D-53 explicit disablement, D-54 both wiring
  recipes proven per D-55), the D-59 lock-guarded D-58 changed-write counter with its D-57 optional
  hook, and the D-56 in-memory dry-run probe

- [x] 06-02-PLAN.md — REDACT-07: `tests/test_redact_verify.py` RED, then `redact/verify.py` —
  `assert_redaction_active` (D-56) with three distinct failure messages, the opt-in deep behaviour
  check, and D-60's warn-only processor-ordering sub-check discovered by a published marker attribute

- [x] 06-03-PLAN.md — REDACT-05: `tests/test_redact_processor.py` RED, then `redact/processor.py` —
  the optional additive `redaction_processor`, its loud chain-order docstring (D-60), and the pinned
  limitation test proving a processor-only configuration still leaks

- [x] 06-04-PLAN.md — DOCS-04 + phase gate: `EXTENSION-GUIDE.md` SEAM-08 flipped to implemented, the
  `redact/` litmus coverage guard extended, a new gate proving the load-bearing sink stays
  framework-agnostic, and GATE-02's RED-first ancestry re-derived from git

**Sequencing constraint — the sink is proven first:**

- **REDACT-04 (`RedactingWriter`) is load-bearing and lands before the processor.** It alone
  satisfies the hard requirement (event fields *and* formatted tracebacks, renderer-agnostic,
  chain-order-independent). Proving it first means the milestone goal is met even if scope pressure
  later trims REDACT-05.

- REDACT-05 (processor) is secondary and additive — it could be deferred within the milestone
  without breaking the goal. It lands last among the seams.

- REDACT-07 / REDACT-08 depend on a seam existing; they land after REDACT-04, and their own tests
  become the assertion mechanism for the seam integration tests rather than hand-rolled capture
  setup per test.

- DOCS-04 closes the phase: per `ECOSYSTEM.md` §6 the promotion is not *done* until the guide row
  flips. The hub must **not** call `structlog.configure()` itself at any point.

### Phase 7: v0.1.2 debt paydown

**Goal**: The hub carries forward no known footgun and no stale planning doc from v0.1.2 — every
open item from the retrospective audit is closed or explicitly decided.
**Depends on**: Nothing (independent of Phases 5–6; sequenced last so the promotion lands first)
**Requirements**: MATCH-03, LIFE-05, SURF-02, DISC-07, DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03
**Success Criteria** (what must be TRUE):

  1. Registering two `CommandSpec`s with the same `name` raises `ValueError` at registration, so
     `match_command` can never resolve a different `CommandSpec` than `by_name` holds.

  2. The retry-pin path's log distinguishes `discord.Forbidden` from a generic `HTTPException`, so
     a permissions failure is never mislabeled as a pin-cap failure; and a failed eviction-delete
     leaves that stray in the call's cleanup instead of dropping it.

  3. `_best_effort_hook` logs via a structured `label=` kwarg instead of an f-string, at both its
     sites; and `uv run pytest` completes with **zero** warnings — the unawaited-coroutine
     `RuntimeWarning` from the `test_gateway.py` fake client is gone.

  4. The identity guard's attached `-mmodule` behavior and `on_online`'s annotation each land as an
     explicitly decided outcome, with the reasoning recorded — see the human-decision note below.

  5. Every active planning artifact naming a consumer de-hack site names a path that **exists** in
     WeatherBot, and the enumeration includes the *producing* site (`weatherbot/ops/selfcheck.py`),
     not only the sites that consume the outcome — verified against the filesystem, not against the
     string that produced the drift.

**Plans**: 7/7 plans executed

Plans (strictly serial Waves 1→7 — each plan commits its RED test then its GREEN fix and re-verifies
the standing gates green before the next plan's RED commit, so a deliberately-RED test never overlaps
a sibling plan's full-suite gate; the Phases 1–3 lesson, re-proven in 5 and 6):

- [x] 07-01-PLAN.md — MATCH-03: `tests/test_registry.py` RED, then a `seen: set[str]` uniqueness
  check inside the existing D-34 validation loop, raising `ValueError` naming the duplicate

- [x] 07-02-PLAN.md — DISC-07 + DISC-08 (pairing): `tests/test_gateway.py` RED, then the retry-pin
  `except discord.Forbidden` branch ordered before `HTTPException` with its own message, and
  eviction removal tied to a successful delete

- [x] 07-03-PLAN.md — HYG-03 + D-65: `tests/test_gateway.py` RED, then `BotThread.stop` bound-coroutine
  restructure with cause-split logging, then `filterwarnings = ["error"]` verified under the real filter

- [x] 07-04-PLAN.md — SURF-02: `get_type_hints` assertions RED, then the three D-62 verdicts
  (`on_online` narrowed, `panelkit.render` arity-narrowed, `scheduler` callback left variadic with
  the reason recorded)

- [x] 07-05-PLAN.md — HYG-02 + LIFE-05: `capture_logs` RED at both `_best_effort_hook` sites, then the
  structured `label=` kwarg at both, then D-61's ratified `-m` boundary stated consumer-facing in
  `EXTENSION-GUIDE.md` with the stale requirement/audit text corrected

- [x] 07-06-PLAN.md — DOCS-02 + DOCS-03: new `tests/test_doc_drift.py` standing gate RED, then the two
  active artifacts corrected to name paths that exist plus the producing site, then drift banners on
  the seven archived v0.1.2 phase-4 records

- [x] 07-07-PLAN.md — Phase gate: GATE-02 RED-first ancestry derived from git trees, the D-61a
  exemption and three manual-only sign-offs recorded, the deferred type-checker backlog entry filed,
  and the human-gated close-out surfaced

**Pairing constraint — these must land together, not as independent tasks:**

- **DISC-07 + DISC-08** — both touch `summon_panel` in `discord/gateway.py`. Splitting them across
  plans is a guaranteed collision on the same function.

**Shared-site note:**

- **HYG-02** touches `_best_effort_hook` at `lifecycle/ready_gate.py:175` *and* the verbatim clone
  at `config/reload.py:326`. One fix, two sites — do not leave the clone drifted.

**⚠ Two items require an explicit human decision at discuss time — do not default:**

- **LIFE-05** (v0.1.2 Phase 1 WR-01): the attached `-mmodule` form false negative. Documentation
  was applied in v0.1.2 and the behavioral fix was **deliberately deferred to a human call**. The
  discuss step must surface "fix the behavior" vs. "document as a permanent limitation, with
  reasoning" as a decision, not pick one.

- **SURF-02** (v0.1.2 Phase 4 IN-02): narrowing `on_online` from `Callable[..., None] | None` to
  `Callable[[HealthResult], None]`. This is a **public hub-surface change** — deferred deliberately
  in v0.1.2 as needing a decision, not a drive-by. The discuss step must surface it.

**Consumer-breaking note:** MATCH-03 turns a previously-silent duplicate registration into a
`ValueError`. The repin needs a WeatherBot sweep for duplicate `spec.name` values.

**Doc-fix verification note (DOCS-02/03):** the v0.1.2 audit's own lesson applies here — *an
automated check derived from the same source as the claim it verifies cannot catch an error in
that source*. The DOCS-02 check must assert the named path resolves on disk in WeatherBot, not
that some string matches another string. `ECOSYSTEM.md` is already clean (it correctly references
`weatherbot/scheduler/wiring.py`); the drift is in
`.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:213` and the artifacts that inherited it.
Historical phase records under `.planning/milestones/v0.1.2-phases/` are an archive — decide at
discuss time whether they are corrected or annotated.

### Human-gated close-out — surfaced, never performed autonomously (`ECOSYSTEM.md` §3)

1. Bump `pyproject.toml` `0.1.2 → 0.2.0` · cut tag `v0.2.0`.
2. Repin WeatherBot `[tool.uv.sources]` `v0.1.2 → v0.2.0` + `uv lock --upgrade` + `uv sync`.
3. **Parity gate — prove before deleting anything.** Run WeatherBot's existing
   `tests/test_redact_hygiene.py` (6 tests) against the hub-backed replacement. All 6 assertions
   must pass. **Correction (06-04-SUMMARY §1 — the earlier "re-pass *unmodified*, only the import
   swapped" framing is overstated):** `RedactingWriter.__init__(target, patterns, *, enabled,
   on_redaction)` is not a parameterless constructor like `_LiveStderr()`, so two of the six test
   bodies (`test_discord_on_message_does_not_dump_key`,
   `test_livestderr_write_tolerates_and_scrubs_bytes`) need a signature-level update — construct
   `RedactingWriter(sys.stderr, patterns)` with WeatherBot's own registered pattern set, not merely
   an import swap. Plan the repin against that, not a false zero-touch expectation. **Only then**
   delete the app-local `weatherbot/_redact.py` in favour of the hub import — deleting it in the
   same commit that wires the replacement is the failure mode this gate exists to prevent.

4. **Adopt — or consciously decline — D-54 recipe 2 (the httpx-class gap; Phase 6 threat T-06-20).**
   The hub upgrade does **not** by itself close WeatherBot's stdlib-`logging` bypass:
   `weatherbot/weather/client.py:48-54` documents that httpx's stdlib-`logging` INFO line (API key
   in the request URL) bypasses a structlog-only backstop. D-54 recipe 2
   (`sys.stderr = RedactingWriter(sys.stderr, patterns)`) is the hub-side answer and ships in
   v0.2.0, but *adopting* it is a consumer composition-root decision the repin must make explicitly
   — **the repin must not silently assume the upgrade closed this gap.** **If adopted,** the
   `sys.stderr` assignment must run **before** any stdlib `logging` handler is constructed (a
   Python-level stream proxy cannot intercept a raw-buffer or file-descriptor write — see
   `EXTENSION-GUIDE.md` §7 *Known limitations*).

5. **Sweep WeatherBot for duplicate `spec.name` values** (MATCH-03 is consumer-breaking).
6. **Confirm the SURF-02 blast radius before narrowing the annotation.** SURF-02 narrows `on_online`
   from `Callable[..., None] | None` to `Callable[[HealthResult], None]` — a public hub-surface
   change. The v0.2.0 work verified on disk that WeatherBot's only handler is already a
   single-positional-param function whose tests pass single-arg lambdas (recorded in `STATE.md` and
   `07-07-SUMMARY.md`), so nothing breaks today — but that confirmation lives in the phase
   artifacts, not here. Re-confirm it against live WeatherBot at repin, as its own check.

7. Verify the PC-01 parity suite, the MATCH-03 duplicate sweep, and the SURF-02 confirmation as
   **separate, individually green checks** before treating the combined repin as ready — one
   bundled repin otherwise conflates the failure causes.

8. Confirm the live daemon picked the change up: check the startup `module provenance` log line
   against `deploy/PROMOTION-LEDGER.md` post-deploy (`ECOSYSTEM.md` §7).

9. **Permanently out of PC-01 scope:** `weatherbot/weather/client.py`'s domain-specific redacted
   re-raise (with `from None`) stays app-local forever — it is domain logic, not a generic
   backstop, and it must be confirmed *untouched* by the swap.

## Deferred Extension Points (future milestones)

Built under build-in-consumer-then-promote / rule of three when a consumer needs them.

| Phase (future) | Scope | Tracks |
|----------------|-------|--------|
| EXT-A | Durable `JobStore` impl + serialization contract (promote from a consumer that needs persistence) | EXT-01 |
| EXT-B | Second `Channel` adapter (Telegram / SMS / Slack) | EXT-02 |

**Out of Milestone v0.2.0 — deliberately parked.** EXT-01 and EXT-02 stay deferred *by design*
under rule of three. No consumer needs either today; building them now would mean designing
against imagined requirements.

## Backlog

Unsequenced parking lot. Source of record for every item below lives in `.planning/backlog/`:

- `HUB-HARDENING-REPORT-v0.1.2.md` — **the planning document.** 17 audit defects (H01–H17) +
  1 enhancement (H18), each with a fix direction verified against hub HEAD `50e8f09`, plus a
  consumer-impact triage. Supersedes the raw handoff for planning.

- `HUB-FINDINGS-HANDOFF.md` — evidence appendix: full failure scenario + evidence per finding.
- `PROMOTION-CANDIDATES.md` — new reusable mechanisms to pull up from consumers (not bugs).

The H01–H18 defect items that once lived here were grouped per the report's §3 sequencing and
have since been promoted. Anything landed from this parking lot is **human-gated** at close-out
(`ECOSYSTEM.md` §3): fixes + green gates are autonomous; the tag cut, the `pyproject.toml`
version bump, and the consumer repin are yours.

> **999.1–999.4 promoted to Milestone v0.1.2 on 2026-07-22** — they are now Phases 1–4 above.
> Their phase directories were renumbered `999.N-*` → `0N-*`.
>
> **999.5 promoted to Milestone v0.2.0 on 2026-07-29** — PC-01 is now Phases 5–6 above
> (REDACT-01..08 + DOCS-04). The parked section below is **superseded** and kept only as the
> origin record; the empty `.planning/phases/999.5-secret-redaction-promotion/` directory is
> retired in favour of the real phase directories. Nothing remains parked in this section.

### Phase 999.5: PC-01 — log secret-redaction backstop promotion (SUPERSEDED — promoted to Phases 5–6)

**Goal:** Promote WeatherBot's app-local secret redactor into a generic hub mechanism.
**Requirements:** REDACT-01..08, DOCS-04 (assigned at v0.2.0 roadmapping)
**Plans:** 7/7 plans complete

**Separate track — a promotion, not a fix.** WeatherBot ships this app-local in its Phase 30
(`HARD-SEC-01`, origin finding F12) to keep that phase cheap and avoid a mid-phase hub tag cut.

The hub should own a renderer-agnostic backstop that scrubs secrets from **all** rendered log
output — event fields *and* formatted tracebacks — independent of the structlog processor chain:
a `redact_secrets(text, patterns) -> text` core, a drop-in wrapper for a structlog
`PrintLoggerFactory` file target (WeatherBot's seam is the shared `_LiveStderr.write` choke point)
and/or a processor, plus a config-driven pattern list.

**Litmus:** the *mechanism* is fully generic; only the *pattern* (`appid=<key>` for OpenWeather) is
domain-specific. Hub owns mechanism + pattern-registration API; the consumer registers its patterns.
Landing it replaces WeatherBot's app-local copy with a hub import.

## Notes

- The first consumer is **WeatherBot**, depending on this module via a uv git dependency
  tag-pinned for deploy (currently `tag = "v0.1.2"`, reproducible `uv.lock`).

- A real GitHub remote for this repo is a deploy prerequisite for pinning from a host
  (the local `file://` git URL is sufficient for development / Gate-1 verification only).
