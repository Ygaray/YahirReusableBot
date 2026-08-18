---
gsd_state_version: 1.0
milestone: v0.2.0
milestone_name: Redaction promotion + hardening debt
current_phase: 08
current_phase_name: redaction-hardening-cleanup
status: executing
stopped_at: Phase 8 wave 3 complete (08-03) — resuming wave 4
last_updated: "2026-08-18T05:30:00.000Z"
last_activity: 2026-08-17
last_activity_desc: Phase 8 wave 3 (08-03, REDACT-10 doc half + DOCS-05) executed and merged
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 19
  completed_plans: 16
  percent: 75
---

# Project State

## Current Position

Phase: 08 (redaction-hardening-cleanup) — EXECUTING
Plan: 3 of 5
Status: Executing Phase 08
Progress: [#######___] 75% (3/4 phases)
Last activity: 2026-08-17 — Phase 08 wave 3 (08-03) complete

## Milestone Shape

| Phase | Track | Goal | Requirements |
|-------|-------|------|--------------|
| 5 | A (PC-01) | Generic scrubbing primitive + safe-by-construction pattern API | REDACT-01, 02, 03, 06 |
| 6 | A (PC-01) | Load-bearing sink seam, additive processor, provable backstop, SEAM-08 | REDACT-04, 05, 07, 08, DOCS-04 |
| 7 | B (debt) | Every v0.1.2 audit item closed or explicitly decided | MATCH-03, LIFE-05, SURF-02, DISC-07, DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03 |
| 8 | C (cleanup) | Close the 4 actionable v0.2.0 audit residuals before repin | REDACT-09, REDACT-10, DOCS-05, HYG-04 |

### Roadmap Evolution

- Phase 8 added 2026-08-17: Redaction-hardening cleanup (Track C) — folds the four actionable
  tech-debt residuals from `.planning/v0.2.0-MILESTONE-AUDIT.md` (WR-02 source exposure, WR-03
  malformed-pattern design, T-06-16 doc gate, static type checker) into a planned phase. Milestone
  reopened from `completed` → `in_progress`; the human-gated repin now waits on Phase 8.

**GATE-02** is milestone-standing (spans all phases), not a phase: full suite + import-hygiene /
litmus / grimp green, and every requirement ships a RED-first regression test.

## Session

**Last session:** 2026-08-17T21:10:00-0600
**Stopped at:** Phase 8 added (Redaction-hardening cleanup) — not yet planned
**Resume file:** None
**Next:** `/gsd-plan-phase 8` (discuss-phase first to settle WR-03 design, mypy-vs-pyright, WR-02 close-vs-accept)

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
| Phase 07 P01 | 10min | 2 tasks | 2 files |
| Phase 07 P02 | 15min | 2 tasks | 2 files |
| Phase 07 P03 | 12min | 3 tasks | 3 files |
| Phase 07 P04 | ~5min | 2 tasks | 5 files |
| Phase 07 P05 | 12min | 3 tasks | 8 files |
| Phase 07 P06 | 15min | 3 tasks | 10 files |
| Phase 07 P07 | 20min | 2 tasks | 2 files |

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
- [Phase ?]: [Phase 7, 07-01] MATCH-03 closed: seen: set[str] added inside the existing D-34 loop (one pass), ValueError names only spec.name, no Unicode normalization applied to the uniqueness check — pinned by a dedicated NFC/NFD regression test
- [Phase ?]: [Phase 7, 07-02] DISC-07 retry-pin Forbidden branch ordered before HTTPException (subclass + first-match except) and logs-and-swallows rather than re-raises, preserving the cleanup loop
- [Phase ?]: [Phase 7, 07-02] DISC-08 eviction bookkeeping switched from unconditional matches.pop(0) to peek-then-conditional-pop tied to delete() success, so a failed eviction is retried by the cleanup loop instead of dropped
- [Phase ?]: [Phase 7, 07-03] HYG-03: coro = self._client.close() bound before scheduling; coro.close() reclaim runs ONLY in the scheduling-failure except (closing a live coroutine raises RuntimeError), so the schedule and await got split try/except/else blocks with two distinct log messages
- [Phase ?]: [Phase 7, 07-03] D-65: filterwarnings = ["error"] added to the existing [tool.pytest.ini_options] table; verified green under uv run pytest -q -o 'filterwarnings=error' (171 passed) BEFORE the config edit landed, confirming the production fix alone closed both the RuntimeWarning and PytestUnraisableExceptionWarning pathways per 07-RESEARCH.md Pitfall 1
- [Phase ?]: [Phase 7, 07-03] Deviation: two literal-grep acceptance criteria (coro.close()==1, run_coroutine_threadsafe==1, and the ignore:: absence check) conflicted with either a pre-existing out-of-scope class docstring or the plan's own instructed comment content; resolved by rephrasing prose to satisfy intent without gutting required documentation — see 07-03-SUMMARY.md Deviations
- [Phase ?]: [Phase 7, 07-04] D-62 SURF-02 three-part verdict applied: on_online and panelkit.render narrowed to their real call-site arity (pinned by get_type_hints regression tests), SchedulerEngine.register's callback deliberately left Callable[..., Any] with the leave-variadic rationale recorded in its docstring per D-63 (no static type checker introduced)
- [Phase ?]: [Phase 7, 07-05] HYG-02 clone anti-drift guard implemented via AST comparison (ast.unparse) with docstrings stripped, not literal inspect.getsource() string diff — the two _best_effort_hook sites' docstrings legitimately differ per engine; verified live the bodies (minus docstring) were already identical pre-fix (GREEN both ways, per plan's documented fallback)
- [Phase ?]: [Phase 7, 07-05] D-61/D-61a executed as locked: LIFE-05 ships zero behavioral change to identity.py, bundled short-option-group form stays undecoded and documented, no artificial RED test manufactured — GATE-02 exemption satisfied by the already-green pinned test_bundled_short_option_group_not_matched
- [Phase ?]: [Phase 7, 07-06] D-66/D-67/D-68 executed: gate regex kept bare (ops[/.]daemon), DOCS-02 exemption stayed line-scoped/content-located (not whole-file), corrected active-artifact prose avoids repeating the stale literal path so the correction cannot re-trigger the drift it fixes, 7 archive files annotated with an identical banner and bodies left byte-unchanged (git diff --stat: insertions only)
- [Phase ?]: [Phase 7, 07-07] GATE-02 RED-first ancestry re-derived from git trees for MATCH-03/DISC-07/DISC-08/SURF-02/HYG-02/HYG-03/DOCS-02 (adjacency + genuine RED-ness via git worktree checkout + commit purity); LIFE-05's D-61a exemption confirmed docstring-only via git diff
- [Phase ?]: [Phase 7, 07-07] Deferred static-type-checker idea filed to .planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md (pickup-ready, cites SURF-02/D-62/D-63); no type checker added to the toolchain
- [Phase ?]: [Phase 7, 07-07] Human-gated close-out surfaced (version bump 0.1.2->0.2.0, tag v0.2.0, WeatherBot repin, two separately-green checks, SURF-02 blast radius, Phase-6 parity-test carry-forward, permanent client.py scope boundary) — nothing performed, per ECOSYSTEM.md §3
- [Phase ?]: [Phase 8, 08-01] REDACT-09 settled as ACCEPT under D-02 — zero source-behavior change. Evidence sites: the __repr__ docstring's Scope (WR-02) block (yahir_reusable_bot/redact/core.py), 05-SECURITY.md's UF-01 row, and the two Phase-5 pinning tests (tests/test_redact_core.py:236-273). Held in place by the new standing _missing_wr02_anchors rationale-retention gate plus its three-case synthetic self-proof (tests/test_redact_core.py). No new residual pinning test was written for the asdict/astuple leak itself — 08-RESEARCH.md Pitfall 1 documents that the two Phase-5 pins already cover it GREEN and a third would be a documented anti-pattern, not an oversight.
- [Phase ?]: [Phase 8, 08-02] REDACT-10 code half closed under D-01: added an optional keyword-only `on_error: Callable[[re.error], None] | None = None` hook to `RedactingWriter` (yahir_reusable_bot/redact/sink.py), mirroring `on_redaction`'s registration shape. Fires only inside the existing `except re.error` branch, after the fail-closed placeholder already reached the wrapped target; receives only the caught exception, never the withheld payload; wrapped in the same swallow-and-continue guard as `on_redaction` so a raising/slow hook cannot break the hot logging path. Fixed placeholder, D-52 triage order, and counter block left byte-unchanged. RED-first four-test regression group added to tests/test_redact_sink.py (hook delivery, no-leak payload gate sweeping dir(exc), raising-hook survival, no-cross-firing). Full suite 199 passed, import-hygiene 10 passed, ruff clean.
- [Phase ?]: [Phase 8, 08-03] REDACT-10 doc half + all of DOCS-05 closed: `EXTENSION-GUIDE.md` §7 gained a "When a pattern is malformed." paragraph stating the fail-closed contract (withhold + fixed placeholder, never forward, never raise) plus the `on_error` hook contract. `tests/test_extension_guide.py` gained three gate/self-proof pairs (malformed contract, telemetry semantics, reconfigure discipline) plus a standing anchor-collision guard. REQUIREMENTS.md marks REDACT-10 and DOCS-05 complete. Full suite 206 passed, import-hygiene 10 passed, ruff clean. Deviation: an in-flight `git checkout --` momentarily reverted uncommitted Task 3 test additions before they were redone and re-verified — final committed content unaffected (full detail in 08-03-SUMMARY.md Deviations).
- [Phase ?]: [Phase 8, 08-05] D-03/HYG-04 retire-vs-keep settled as **KEEP**, decided on two observed run experiments (not reasoning): `on_online` and `render` were each scratch-widened back to their pre-SURF-02 loose form and, both times, `uv run python scripts/pyright_baseline.py` stayed green while the paired `get_type_hints` assertion went red — proving pyright checks annotation-internal-consistency while the runtime assertions check that three specific public signatures carry one specific narrowed type, and a silent re-widening satisfies the former while failing the latter. Rationale recorded in `tests/test_ready_gate.py`, `tests/test_panelkit.py`, and a `[tool.pyright]` comment in `pyproject.toml`. `REQUIREMENTS.md`'s HYG-04 bullet corrected to state KEEP instead of the stale supersede claim. GATE-02 RED-first ancestry independently re-derived from git trees for all four Phase-8 pairs (REDACT-09/REDACT-10 hook/REDACT-10 guide/HYG-04 diff gate — adjacency, genuine RED-ness via scratch `git worktree add --detach`, and commit purity); DOCS-05's two D-04 gates legitimately have no RED commit (they pin already-true prose) — their non-vacuity self-proofs stand in, per the Phase-6 Known-limitations precedent. REDACT-09 closed (checkbox + status row), the last of the four Phase-8 requirements. Also fixed a pre-existing Rule-1 bug in `scripts/pyright_baseline.py` (shipped by 08-04): the committed baseline stored the writing checkout's raw absolute paths and broke the gate on every other checkout; `_relativize_diagnostics` now persists repo-relative paths, baseline regenerated (same 12 diagnostics/34 files, now portable). Full suite 215 passed, import-hygiene 10 passed, doc-drift 5 passed, pyright gate exit 0, ruff clean.

## Human-Gated Close-Out — v0.2.0

Per `ECOSYSTEM.md` §3, the following is handed to the human for confirmation. **Nothing below has
been executed by any phase of this milestone.** Supersedes the Phase-7 close-out decision-log line
above with Phase 8's additions folded in.

1. **Version bump and tag cut** — `pyproject.toml` `0.1.2 → 0.2.0`, tag `v0.2.0`. Not done. Verified
   2026-08-18: `git tag --list 'v0.2.0'` is empty; `pyproject.toml` still reads `version = "0.1.2"`.
2. **The WeatherBot repin** — `[tool.uv.sources]` bump `v0.1.2 → v0.2.0`, `uv lock --upgrade`,
   `uv sync`. Not done.
3. **Two separately-green checks, never bundled:**
   - **(a) The PC-01 parity gate** — WeatherBot's existing, unmodified `tests/test_redact_hygiene.py`
     (6 tests) against the hub-backed replacement; all 6 must pass before `weatherbot/_redact.py` is
     deleted. Two of the six need a **signature-level test update**, not merely an import swap,
     because `RedactingWriter`'s constructor differs from the app-local `_LiveStderr` it replaces
     (Phase-6 carry-forward, unchanged).
   - **(b) The MATCH-03 duplicate-`spec.name` sweep** — WeatherBot's command specs must be swept for
     duplicate names before the repin lands.
4. **The SURF-02 blast-radius note** — narrowing `on_online` is a public hub-surface change; the only
   live consumer's handler already conforms.
5. **The permanent scope boundary** — `weatherbot/weather/client.py`'s domain-specific redacted
   re-raise stays app-local forever.
6. **NEW from Phase 8 — REDACT-10's `on_error` hook.** `RedactingWriter`'s constructor has gained an
   optional, keyword-only `on_error: Callable[[re.error], None] | None = None` parameter (mirrors
   `on_redaction`'s shape, fires only inside the existing fail-closed `except re.error` branch,
   receives only the caught exception — never the withheld payload). Changes no existing call site
   (default `None`, purely additive) — the repin **may** wire it, but nothing requires it to.
7. **NEW from Phase 8 — the hub now carries a pyright gate the consumer does not inherit.**
   `scripts/pyright_baseline.py` + `pyright-baseline.json` are dev-only,
   `[dependency-groups].dev`-scoped tooling; a consumer pinning the hub via `[tool.uv.sources]` does
   not install `pyright` and is not gated by this baseline — hub-internal hygiene, not a repin
   contract.

No version bump, tag, repin, `uv sync`, or deploy has been performed by any plan in Phase 8 or
earlier. `git status --porcelain` at the end of plan 08-05 showed no file outside `.planning/`
modified by that plan.

## Todos

- ~~Phase 7 discuss step must surface **LIFE-05** and **SURF-02** as explicit human decisions~~ —
  **DONE (Phase 7, 2026-08-04).** Both surfaced at discuss time and decided, never defaulted;
  reasoning recorded in `07-CONTEXT.md` (D-61/D-61a, D-62) and `07-DISCUSSION-LOG.md`.
  **LIFE-05 → keep-documented:** the bundled `-Om<module>` form stays deliberately undecoded, stated
  as a permanent limitation with reasoning in `EXTENSION-GUIDE.md` §4. D-61a exempts it from the
  GATE-02 RED-first rule (zero behavioral change — `identity.py`'s only diff is 5 docstring lines).
  **SURF-02 → narrow two of three:** `on_online` and `render` narrowed and pinned by `get_type_hints`
  regression tests; `SchedulerEngine.register`'s `callback` deliberately left `Callable[..., Any]`
  with the rationale in its docstring. The narrowing is a **public hub-surface change** — it ships to
  consumers only at the human-gated repin.

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
  **SETTLED (Phase 8, 2026-08-18).** REDACT-09 (plan 08-01) ratified this residual ACCEPT under
  D-02 — zero source-behavior change, held in place by a standing rationale-retention gate. Ancestry
  independently proven from git in plan 08-05. This todo stays annotated, not deleted, per the
  established record-what-was-believed-and-when convention.

## Blockers

None.
