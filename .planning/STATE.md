---
gsd_state_version: 1.0
milestone: v0.2.0
milestone_name: — Redaction promotion + hardening debt
current_phase: 6
current_phase_name: Insertion seams + provable backstop
status: executing
stopped_at: Phase 6 context gathered
last_updated: "2026-08-04T00:01:59.403Z"
last_activity: 2026-07-29
last_activity_desc: Phase 05 complete, transitioned to Phase 6
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 33
---

# Project State

## Current Position

Phase: 6 — Insertion seams + provable backstop
Plan: Not started
Status: Ready to execute
Progress: [###_______] 33% (1/3 phases)
Last activity: 2026-07-29 — Phase 05 complete, transitioned to Phase 6

## Milestone Shape

| Phase | Track | Goal | Requirements |
|-------|-------|------|--------------|
| 5 | A (PC-01) | Generic scrubbing primitive + safe-by-construction pattern API | REDACT-01, 02, 03, 06 |
| 6 | A (PC-01) | Load-bearing sink seam, additive processor, provable backstop, SEAM-08 | REDACT-04, 05, 07, 08, DOCS-04 |
| 7 | B (debt) | Every v0.1.2 audit item closed or explicitly decided | MATCH-03, LIFE-05, SURF-02, DISC-07, DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03 |

**GATE-02** is milestone-standing (spans all phases), not a phase: full suite + import-hygiene /
litmus / grimp green, and every requirement ships a RED-first regression test.

## Session

**Last session:** 2026-07-29T20:05:33.891Z
**Stopped at:** Phase 6 context gathered
**Resume file:** .planning/phases/06-insertion-seams-provable-backstop/06-CONTEXT.md

## Performance Metrics

Carried from v0.1.2 for calibration (14 plans across 4 phases, ~3–25min per plan).

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01 P01 | 15min | 2 tasks | 1 files |
| Phase 01 P02 | ~20min | 2 tasks | 2 files |
| Phase 01 P03 | ~20min | 2 tasks | 2 files |
| Phase 01 P04 | ~25min | 3 tasks | 1 files |
| Phase 02 P01 | 15min | 2 tasks | 2 files |
| Phase 02 P02 | 25min | 3 tasks | 2 files |
| Phase 02 P03 | 10min | 2 tasks | 2 files |
| Phase 03 P01 | 10min | 1 tasks | 2 files |
| Phase 03 P02 | 10min | 2 tasks | 2 files |
| Phase 03 P03 | 6min | 2 tasks | 4 files |
| Phase 03 P04 | 8min | 2 tasks | 2 files |
| Phase 03 P05 | 12min | 2 tasks | 2 files |
| Phase 04 P01 | 12min | 3 tasks | 4 files |
| Phase 04 P02 | 3min | 2 tasks | 2 files |
| Phase 05 P01 | 18min | 2 tasks | 3 files |
| Phase 05 P02 | ~12min | 2 tasks | 3 files |
| Phase 05 P03 | ~10min | 2 tasks | 2 files |

## Decisions

Carried into v0.2.0 (standing constraints — re-asserted every phase):

- GATE-02 is milestone-standing and stays unchecked in REQUIREMENTS.md until green across all
  three phases — same treatment GATE-01 received in v0.1.2.

- Plans within a phase are sequenced so a deliberately-RED test never overlaps a sibling plan's
  full-suite gate (hard-won in Phases 1–3).

- No version bump, tag, repin, `uv sync`, or deploy is performed by the workflow — all human-gated
  per ECOSYSTEM.md §3.

- The hub must never call `structlog.configure()`; logging configuration is 100% consumer
  composition-root policy. PC-01 ships as a toolkit the consumer wires.

- `redact/` stays a pure leaf subpackage — stdlib only, plus `structlog` inside `processor.py`
  alone; it imports no sibling `yahir_reusable_bot` subpackage.

- No module-level mutable pattern singleton; patterns are compiled once at registration, frozen,
  and passed explicitly (matches the hub's existing DI posture).

- Disablement is an explicit constructor parameter, never an env-var read inside the hub.

Roadmapping decisions (2026-07-29):

- Phase numbering continues from v0.1.2 (which ended at Phase 4) — v0.2.0 is Phases 5–7, not a
  reset to 1.

- Track A ordered before Track B: the promotion is the milestone's headline and the close-out
  parity gate depends on it; Track B is independent and absorbs any slip.

- REDACT-06 (literal-value mode) placed in Phase 5, not with the seams — it is a pattern
  *registration mode*, so the whole public pattern surface settles in one phase (API shape is
  expensive to change once a consumer depends on it).

- REDACT-03 (ReDoS vetting) placed with REDACT-02 (registration API) rather than bolted on later —
  it is the registration call that raises.

- DOCS-04 (SEAM-08) folded into Phase 6 rather than a documentation phase: per ECOSYSTEM.md §6 the
  promotion is not *done* until the guide row flips to implemented.

- Research SUMMARY.md's 9-phase proposal deliberately not followed — it is annotated in that
  document as over-decomposed. Its build order is used as *dependency ordering within phases*.

- `.planning/phases/999.5-secret-redaction-promotion/` (empty, parked) is superseded by Phases 5–6;
  the ROADMAP records the promotion. Directory left in place, not deleted by the roadmapper.

Full v0.1.2 decision history is archived under `.planning/milestones/v0.1.2-phases/*/`
(`*-SUMMARY.md`, `*-VALIDATION.md`) and summarized in `.planning/v0.1.2-MILESTONE-AUDIT.md`.

- [Phase ?]: RedactionPattern.__repr__ is explicit and source-eliding (repr=False on the dataclass) so a literal-constructed instance can never leak its held secret through its own logging representation (PR-01, T-05-02).
- [Phase ?]: RedactionPattern.literal rejects empty/blank values with ValueError at construction, message never echoing the rejected value (D-41 precedent, stricter no-echo rule than panelkit.py's guard).
- [Phase ?]: Implemented the plan's escalating-ladder ReDoS probe (cumulative-elapsed check after every search) rather than RESEARCH.md's single-shot probe — a single long search over a catastrophic pattern would hang the vetting call itself (T-05-06).
- [Phase ?]: test_register_patterns_accepts_proven_appid_pattern (05-VALIDATION.md draft) renamed to test_register_patterns_accepts_proven_boundary_pattern — the draft name embedded a WeatherBot domain noun, forbidden under redact/'s litmus discipline.
- [Phase ?]: redact_scanned litmus coverage guard added to test_import_hygiene.py — an addition for convention consistency (standing gate already auto-covered redact/ unedited), not a fix, matching the lifecycle/registry/discord guard shape
- [Phase ?]: GATE-02 RED-first ancestry for REDACT-01/02/03/06 proven from git trees (git rev-parse adjacency + git ls-tree RED-ness + commit purity), not asserted in prose
- [Phase ?]: WeatherBot parity-test plan verified against actual source: 4 of 6 assertions are Phase-5-core-only, 2 of 6 (test_discord_on_message_does_not_dump_key, test_livestderr_write_tolerates_and_scrubs_bytes) depend on the Phase-6 sink/backstop seam and cannot fully re-pass until Phase 6 ships

## Todos

- Phase 7 discuss step must surface **LIFE-05** and **SURF-02** as explicit human decisions —
  both were deliberately deferred once already; neither may be defaulted.

- ~~Phase 5 discuss/plan must produce the WeatherBot **parity-test plan**~~ — **DONE (Phase 5).**
  Written in `05-RESEARCH.md` § Validation Architecture, corrected during execution, and finalized
  in `05-VALIDATION.md` § Manual-Only. **Correction worth carrying into Phase 6:** only **4 of 6**
  WeatherBot assertions are reachable after Phase 5. `test_discord_on_message_does_not_dump_key`
  and `test_livestderr_write_tolerates_and_scrubs_bytes` depend on the Phase-6 sink/backstop seam,
  so the full 6-assertion parity gate cannot pass until Phase 6 ships. The `client.py` scope
  boundary (domain logic, stays app-local forever) is recorded there too.

- ~~**Residual from Phase 5's code review (WR-02)**~~ — **RESOLVED as far as it can be without an
  API change (2026-07-29).** `RedactionPattern` is now `slots=True`, so the *accidental* leak paths
  are closed: `vars(rp)` raises `TypeError` and `rp.__dict__` raises `AttributeError` instead of
  handing back the raw `re.Pattern` whose default repr prints a literal-constructed secret. Those
  were the paths a generic serializer or logging helper hits without meaning to.
  **Remaining, deliberate:** `dataclasses.asdict()`/`astuple()` still expose the raw pattern. That
  is explicit dataclass introspection — no worse than reading the equally-public
  `rp.pattern.pattern` — and closing it needs an opaque wrapper, i.e. a public API shape change.
  Revisit only if a consumer actually needs a safe serialization form. Pinned both ways by
  `tests/test_redact_core.py` (`..._has_no_instance_dict_so_generic_serializers_cannot_leak` and
  `..._asdict_still_exposes_raw_pattern_source`).

## Blockers

None.
