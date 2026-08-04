---
gsd_state_version: 1.0
milestone: v0.2.0
milestone_name: — Redaction promotion + hardening debt
current_phase: 06
current_phase_name: insertion-seams-provable-backstop
status: verifying
stopped_at: Completed 06-04-PLAN.md (Phase 6 closed)
last_updated: "2026-08-04T00:39:53.877Z"
last_activity: 2026-08-04
last_activity_desc: Phase 06 execution started
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 7
  completed_plans: 7
  percent: 67
---

# Project State

## Current Position

Phase: 06 (insertion-seams-provable-backstop) — EXECUTING
Plan: 4 of 4
Status: Phase complete — ready for verification
Progress: [###_______] 33% (1/3 phases)
Last activity: 2026-08-04 — Phase 06 execution started

## Milestone Shape

| Phase | Track | Goal | Requirements |
|-------|-------|------|--------------|
| 5 | A (PC-01) | Generic scrubbing primitive + safe-by-construction pattern API | REDACT-01, 02, 03, 06 |
| 6 | A (PC-01) | Load-bearing sink seam, additive processor, provable backstop, SEAM-08 | REDACT-04, 05, 07, 08, DOCS-04 |
| 7 | B (debt) | Every v0.1.2 audit item closed or explicitly decided | MATCH-03, LIFE-05, SURF-02, DISC-07, DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03 |

**GATE-02** is milestone-standing (spans all phases), not a phase: full suite + import-hygiene /
litmus / grimp green, and every requirement ships a RED-first regression test.

## Session

**Last session:** 2026-08-04T00:39:53.866Z
**Stopped at:** Completed 06-04-PLAN.md (Phase 6 closed)
**Resume file:** None

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
| Phase 06 P01 | 10min | 2 tasks | 3 files |
| Phase 06 P02 | ~12min | 2 tasks | 3 files |
| Phase 06 P03 | ~15min | 2 tasks | 3 files |
| Phase 06 P04 | ~10min | 3 tasks | 2 files |

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
- [Phase ?]: D-52 non-str/bytes triage order (bytes decode-with-replace, then str+enabled+non-empty-patterns gate) copied verbatim from WeatherBot's proven _LiveStderr.write into RedactingWriter (06-01)
- [Phase ?]: D-58 counter counts CHANGED WRITES via one != comparison, never re-running patterns with .subn() for an exact substitution total (06-01)
- [Phase ?]: D-59 threading.Lock guards only the increment + captured read; on_redaction hook fires OUTSIDE the lock so a slow/raising hook cannot hold up concurrent writers (06-01)
- [Phase ?]: D-56 introspection reads structlog.get_config()['logger_factory']._file and raises on any inconclusive result — never a false pass (06-02)
- [Phase ?]: D-60 ordering sub-check locates redaction processors via REDACTION_PROCESSOR_MARKER (not identity/import), so verify.py ships with zero dependency on the not-yet-built optional processor (06-02)
- [Phase ?]: RESEARCH open question 2 resolved as recommended (assumption A1): hard raise, no unwrap convention, for a writer nested inside a consumer's own proxy — message states the fix rather than attempting to walk the proxy (06-02)
- [Phase ?]: [Phase 6, 06-03] D-60's docstring half shipped verbatim to RESEARCH Pattern 2's two-warning structure; detection half proven wired end-to-end by the marker test placing the real processor before format_exc_info
- [Phase ?]: [Phase 6, 06-03] WR-02 residual re-checked per CONTEXT.md instruction and confirmed correctly closed: no RedactionPattern instance is ever placed into an event_dict by the processor
- [Phase ?]: [Phase 6, 06-03] Rule 1 fix: RED test's positive-scrub case used dict_tracebacks (nests exc info as structured data, not a flat string) instead of format_exc_info (flat string) — fixed in a separate follow-up commit (67a4f42), not an amend, to preserve GATE-02 RED->GREEN adjacency
- [Phase ?]: [Phase 6, 06-04] EXTENSION-GUIDE.md SEAM-08 flipped to implemented (table row + new ## 7. section) — the promotion is now hub-side done per ECOSYSTEM.md §6
- [Phase ?]: [Phase 6, 06-04] Rule 1/3 fix: the new test_redact_sink_never_imports_structlog gate required include_external_packages=True (grimp 3.14 default drops all third-party edges, making the gate permanently vacuous without it)
- [Phase ?]: [Phase 6, 06-04] Discovered processor.py does not declare a direct structlog import edge despite its docstring's 'permitted to import structlog' framing — it imports only REDACTION_PROCESSOR_MARKER from verify.py; the new gate's non-vacuity proof asserts the real edge only for verify.py
- [Phase ?]: [Phase 6, 06-04] GATE-02 RED-first ancestry re-derived from git trees for 06-01/06-02/06-03: all three pairs adjacent, genuinely RED, and pure — REDACT-04/05/07/08 all hold
- [Phase ?]: [Phase 6, 06-04] WeatherBot parity: both Phase-6-gated assertions are now mechanically satisfiable by RedactingWriter, but the repin needs a signature-level test update (RedactingWriter's constructor differs from _LiveStderr's), not merely an import swap as 05-VALIDATION.md implied

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
