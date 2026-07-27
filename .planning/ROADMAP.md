# YahirReusableBot — Roadmap

## Milestone v0.1.0 — Initial extraction (DONE)

Imported from the WeatherBot v2.0 "Bot Module Extraction" milestone (Phases 22–28). The module
core, the standing import-hygiene suite, and the `EXTENSION-GUIDE` ship in the single clean
import commit tagged `v0.1.0`.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Initial import (module tree, pyproject, re-scoped import-hygiene suite, EXTENSION-GUIDE, GSD init) | done |

## Milestone v0.1.2 — Hub hardening (ACTIVE)

Close all 17 audit-surfaced hub defects (H01–H17) plus the H18 `ReadyGate` fatal-outcome
enhancement. Sequencing is correctness-first, reachable-first, then reusability hardening,
cleanup last. Source of record: `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md`.

All 18 findings re-verified against source before roadmapping — no semantic drift; two line
numbers moved within their own function (H07 `gateway.py:246`, H04 `gateway.py:278`).

**Standing gate for every phase (GATE-01):** full pytest suite + import-hygiene / litmus / grimp
layering checks stay green. **Every fix ships a RED-first regression test** — it must fail against
current source first. Existing tests cover only decoy cases for several findings, so the
adversarial case gets added rather than a new happy path.

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
**Plans:** 1/3 plans executed

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

- [ ] 02-02-PLAN.md — gateway.py DISC-01/02/03: death-reason accessor (liveness-only, D-21/D-22),
  `summon_panel` per-item delete + pin-cap headroom (D-24..D-27), `stop()` TOCTOU degrade (D-28)

- [ ] 02-03-PLAN.md — DISC-04: `tests/test_selection.py` RED, then `SelectedContext.snapshot()` +
  await-safety docstring contract (D-29/D-30), contract + API only

### Phase 3: Reusable public-surface footguns

**Goal:** Harden the public surface against footguns unreachable in the current consumer but
guaranteed to bite the next one. This is the hub's entire reason to exist.
**Requirements:** MATCH-01 (H06), MATCH-02 (H13), RELY-02 (H09), RELY-03 (H10), DISC-05 (H11),
DISC-06 (H12), LIFE-02 (H14), LIFE-03 (H15), SCHED-01 (H16)
**Depends on:** Phase 2
**Plans:** TBD

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

### Phase 4: Cleanup + ReadyGate fatal outcome

**Goal:** Fix public-surface drift and give consumers a fatal outcome to de-hack against.
**Requirements:** SURF-01 (H17), LIFE-04 (H18)
**Depends on:** Phase 3
**Plans:** TBD

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

## Deferred Extension Points (future milestones)

Built under build-in-consumer-then-promote / rule of three when a consumer needs them.

| Phase (future) | Scope | Tracks |
|----------------|-------|--------|
| EXT-A | Durable `JobStore` impl + serialization contract (promote from a consumer that needs persistence) | EXT-01 |
| EXT-B | Second `Channel` adapter (Telegram / SMS / Slack) | EXT-02 |

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
> Their phase directories were renumbered `999.N-*` → `0N-*`. Only 999.5 remains parked.

### Phase 999.5: PC-01 — log secret-redaction backstop promotion (BACKLOG)

**Goal:** Promote WeatherBot's app-local secret redactor into a generic hub mechanism.
**Requirements:** TBD
**Plans:** 0 plans

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

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

## Notes

- The first consumer is **WeatherBot**, depending on this module via a uv git dependency
  tag-pinned for deploy (`tag = "v0.1.0"`, reproducible `uv.lock`).

- A real GitHub remote for this repo is a deploy prerequisite for pinning from a host
  (the local `file://` git URL is sufficient for development / Gate-1 verification only).
