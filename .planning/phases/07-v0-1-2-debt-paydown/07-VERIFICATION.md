---
phase: 07-v0-1-2-debt-paydown
verified: 2026-08-04T05:53:25Z
status: passed
score: 11/11 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 7: v0.1.2 debt paydown Verification Report

**Phase Goal:** The hub carries forward no known footgun and no stale planning doc from v0.1.2 —
every open item from the retrospective audit is closed or explicitly decided.
**Verified:** 2026-08-04T05:53:25Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | MATCH-03 — duplicate `CommandSpec.name` raises `ValueError` at construction, before `by_name` is derived | ✓ VERIFIED | `yahir_reusable_bot/registry/registry.py:52-64`: `seen: set[str]` check inside the existing D-34 loop; message interpolates only `spec.name`. `uv run pytest tests/test_registry.py -k "duplicate or empty_and_single or normalization" -q` → 5 passed. Ancestry: `git rev-parse 7da4568^` == `d92351d` (RED test is direct parent of GREEN fix); RED commit touches only `tests/test_registry.py`. |
| 2 | DISC-07 — retry-pin `discord.Forbidden` logged distinctly from generic `HTTPException`, ordered before it so it is reachable, logged-and-swallowed (not re-raised) | ✓ VERIFIED | `gateway.py:224-236`: `except discord.Forbidden:` precedes `except discord.HTTPException:` on the retry pin, distinct critical message, no `raise`. `git rev-parse 802ac85^` == `c42e90f`. `tests/test_gateway.py` retry-pin tests pass (15 passed in file). |
| 3 | DISC-08 — a failed eviction-delete leaves the stray in `matches` for the cleanup loop to retry; a successful delete removes it | ✓ VERIFIED | `gateway.py:214-222`: peek (`matches[0]`) + conditional `matches.pop(0)` inside `else:` on the delete `try`. Same RED/GREEN pair as DISC-07 (paired plan, verified above). |
| 4 | HYG-02 — `_best_effort_hook` logs via a fixed event string + structured `label=` kwarg at BOTH sites (`ready_gate.py` and its `config/reload.py` clone), never an f-string | ✓ VERIFIED | `grep -n 'label=label' ready_gate.py config/reload.py` → one hit each, both reading `_log.warning("hook failed; engine result unaffected", label=label)`. No `_log.warning(f"` remains. `git rev-parse d2e9ca3^` == `b44e555`. AST-normalized anti-drift guard (`test_reload_best_effort_hook_clone_matches_ready_gate_byte_for_byte`) passes, proving the clone did not drift. |
| 5 | HYG-03 — the never-scheduled `client.close()` coroutine is bound before scheduling and reclaimed only on the scheduling-failure branch; the two failure causes log distinct messages; `stop()` never raises | ✓ VERIFIED | `gateway.py:361-402`: `coro = self._client.close()` bound before the `try`; `coro.close()` appears exactly once, inside the scheduling-`except`; two distinct `_log.warning` strings. `git rev-parse b6ba940^` == `b5cbe36`. |
| 6 | HYG-03 / D-65 — the full suite runs clean under the REAL warning filter, structurally enforced | ✓ VERIFIED | `pyproject.toml:48` `filterwarnings = ["error"]` inside `[tool.pytest.ini_options]`; re-ran live: `uv run pytest -q -o 'filterwarnings=error'` → `184 passed`, zero warnings. |
| 7 | LIFE-05 — the bundled `-Om<module>` short-option-group form is an explicitly decided, documented, consumer-visible limitation, with ZERO behavioral change to `identity.py` | ✓ VERIFIED | `identity.py` diff (`b44e555~1..2e97b64`) is 5 added lines, entirely inside a docstring paragraph — re-verified live, zero executable lines touched. `tests/test_identity.py -k bundled_short_option` → 1 passed (pinned GREEN-both-ways, D-61a's recorded RED-first exemption — correctly NOT a gap per phase instructions). `EXTENSION-GUIDE.md` §4 states the constraint and the SIGHUP/false-positive asymmetric-risk reasoning (`grep -c SIGHUP` → 1, and full paragraph read confirms quality). |
| 8 | SURF-02 — `on_online` narrowed to `Callable[[HealthResult], None] \| None`; `panelkit.render` arity-narrowed to `Callable[[Any, Any], discord.Embed]`; `scheduler.engine.register`'s `callback` deliberately left `Callable[..., Any]` with the reason recorded in its own docstring | ✓ VERIFIED | Grepped all three sites directly — annotations match exactly. `register`'s docstring read in full: contains the "variadic form IS the accurate contract... injection-by-`Any` at a seam... not sloppiness" rationale (D-62/D-63). Two of the three sites pinned by `get_type_hints` regression tests; `git rev-parse 94e14d9^` == `7f60a90`. |
| 9 | DOCS-02 — every ACTIVE planning artifact naming a consumer de-hack site names a path that exists on disk, enforced by a standing gate (not a one-time check) | ✓ VERIFIED | `tests/test_doc_drift.py` exists, bare `ops[/.]daemon` regex confirmed (not consumer-prefixed), `uv run pytest tests/test_doc_drift.py -q` → 5 passed. `git rev-parse 824702e^` == `2793076` (gate committed RED against the two real active drift sites, then GREEN with zero exemptions added — `git diff HEAD~1 -- tests/test_doc_drift.py` empty at Task 2). Filesystem re-checked live against `/home/yahir/Projects/WeatherBot`: `weatherbot/ops/daemon.py` ABSENT, `weatherbot/scheduler/daemon.py` and `weatherbot/ops/selfcheck.py` EXIST. Seven archived v0.1.2 phase-4 files carry the drift banner and are otherwise byte-unchanged (verified `git diff --stat` insertions-only pattern is consistent with the SUMMARY's claim). |
| 10 | DOCS-03 — the de-hack enumeration is complete: it names the PRODUCING site (`weatherbot/ops/selfcheck.py:to_health_result`), not only the consuming sites | ✓ VERIFIED | `.planning/REQUIREMENTS.md` (Human-gated close-out block) and `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` both read directly: each names all three sites (`wiring.py:_on_fail`, `scheduler/daemon.py`, `ops/selfcheck.py:to_health_result`) with the producing-site reasoning stated. Manual-only by design (07-VALIDATION.md) — confirmed here by direct read, not merely by trusting the SUMMARY. |
| 11 | GATE-02 — full suite + standing gates green; every behavioral requirement's RED-first ancestry provably holds from git; the human-gated close-out is surfaced, nothing performed | ✓ VERIFIED | Re-ran all four standing gates live (see Requirements Coverage below) — all green. Spot-checked 2 of 6 documented RED/GREEN adjacency pairs directly (MATCH-03, DOCS-02) plus the LIFE-05 docstring-only diff — all held. `git tag --list v0.2.0` empty; `pyproject.toml` still `0.1.2`; hub `git status --short` clean; WeatherBot's dirty status is pre-existing/unrelated (`.planning/config.json`, `.planning/REQUIREMENTS.md` — its own concurrent session, untouched by this phase). GATE-02 correctly remains unchecked `[ ]` in REQUIREMENTS.md (milestone-standing, per phase instructions — not a gap). |

**Score:** 11/11 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `yahir_reusable_bot/registry/registry.py` | `seen` uniqueness check | ✓ VERIFIED | Present, wired, tested |
| `tests/test_registry.py` | MATCH-03 RED-first + boundary tests | ✓ VERIFIED | 5 new tests present and passing |
| `yahir_reusable_bot/discord/gateway.py` | Forbidden discrimination + success-tied eviction + HYG-03 restructure | ✓ VERIFIED | All three edits present, correct ordering |
| `tests/test_gateway.py` | DISC-07/08 + HYG-03 regression tests | ✓ VERIFIED | 15 tests in file, all passing |
| `yahir_reusable_bot/lifecycle/ready_gate.py` | Narrowed `on_online`; structured `label=` | ✓ VERIFIED | Both present |
| `yahir_reusable_bot/discord/panelkit.py` | Arity-narrowed `render` | ✓ VERIFIED | Present |
| `yahir_reusable_bot/scheduler/engine.py` | Recorded leave-variadic verdict | ✓ VERIFIED | Docstring rationale present, read in full |
| `yahir_reusable_bot/config/reload.py` | HYG-02 clone fix | ✓ VERIFIED | `label=label` present, AST-drift-guard green |
| `yahir_reusable_bot/lifecycle/identity.py` | Docstring-only LIFE-05 ratification | ✓ VERIFIED | Diff confirmed docstring-only |
| `EXTENSION-GUIDE.md` | Consumer-facing `-m` boundary constraint | ✓ VERIFIED | §4 read in full, SIGHUP reasoning present |
| `pyproject.toml` | `filterwarnings = ["error"]` | ✓ VERIFIED | Present under `[tool.pytest.ini_options]`, no `ignore::` added |
| `tests/test_doc_drift.py` | Standing DOCS-02 gate | ✓ VERIFIED | 5 tests, all passing, bare regex confirmed |
| `.planning/REQUIREMENTS.md` | Corrected LIFE-05/DOCS-02/DOCS-03 text | ✓ VERIFIED | All corrections present and read |
| `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` | Corrected origin line | ✓ VERIFIED | Three-site enumeration present |
| `.planning/v0.1.2-MILESTONE-AUDIT.md` | Correction blockquote (annotated, not rewritten) | ✓ VERIFIED | Annotation present |
| 7 archived `04-cleanup-readygate-fatal/*.md` files | Drift banner, byte-unchanged bodies | ✓ VERIFIED | Banner present in all 7 (per SUMMARY's `git diff --stat` evidence, consistent with `git log` for `824702e`/`058ff75`) |
| `.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md` | Pickup-ready deferred backlog entry | ✓ VERIFIED | Exists, contains SURF-02 citation + sizing decisions |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `tests/test_registry.py` | `registry.py` | `pytest.raises(ValueError)` around duplicate specs | ✓ WIRED | Confirmed by passing test run |
| `tests/test_gateway.py` | `gateway.py` | `capture_logs()` around `summon_panel`/`stop()` | ✓ WIRED | Confirmed by passing test run |
| `tests/test_ready_gate.py` / `tests/test_panelkit.py` | `ready_gate.py` / `panelkit.py` | `typing.get_type_hints` equality assertions | ✓ WIRED | Confirmed by passing test run |
| `tests/test_reload.py` | `config/reload.py` | AST-normalized clone-drift comparison | ✓ WIRED | Confirmed by passing test run |
| `tests/test_doc_drift.py` | `.planning/**/*.md` | `_scan_drift` over `_collect_planning_lines()` | ✓ WIRED | Confirmed by passing test run against the live tree |
| `EXTENSION-GUIDE.md` §4 | `identity.py`'s `_argv_matches_marker` docstring | restates the same reasoning for a consumer audience | ✓ WIRED | Both read directly; content consistent |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite, real warning filter | `uv run pytest -q -o 'filterwarnings=error'` | `184 passed` | ✓ PASS |
| Import-hygiene standing gate | `uv run pytest tests/test_import_hygiene.py -q` | `10 passed` | ✓ PASS |
| Doc-drift standing gate | `uv run pytest tests/test_doc_drift.py -q` | `5 passed` | ✓ PASS |
| Lint | `uv run ruff check` | `All checks passed!` | ✓ PASS |
| MATCH-03 ancestry adjacency | `git rev-parse 7da4568^` vs `d92351d` | match | ✓ PASS |
| DOCS-02 ancestry adjacency | `git rev-parse 824702e^` vs `2793076` | match | ✓ PASS |
| LIFE-05 no-behavior-change | `git diff b44e555~1..2e97b64 -- identity.py` | docstring-only, 5 lines added | ✓ PASS |
| WR-01 docstring drift fix (code-review follow-up) | `git show 6ca3ad3 --stat` + docstring read | `>=1` threshold now correctly documented | ✓ PASS |
| Registry probes (empty/single/Unicode-NFC-NFD) | `pytest tests/test_registry.py -k "duplicate or empty_and_single or normalization"` | `5 passed` | ✓ PASS |
| Consumer repo untouched | `git -C WeatherBot status --porcelain` | pre-existing unrelated dirty state only | ✓ PASS |
| No tag / version bump | `git tag --list v0.2.0`; `grep version pyproject.toml` | empty; `0.1.2` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MATCH-03 | 07-01 | Duplicate `spec.name` rejected at registration | ✓ SATISFIED | `registry.py`, tests pass, ancestry confirmed |
| DISC-07 | 07-02 | Retry-pin `Forbidden` logged distinctly | ✓ SATISFIED | `gateway.py`, tests pass, ancestry confirmed |
| DISC-08 | 07-02 | Failed eviction-delete retried, not dropped | ✓ SATISFIED | `gateway.py`, tests pass |
| HYG-03 | 07-03 | Coroutine leak fixed at root; zero warnings structural | ✓ SATISFIED | `gateway.py`, `pyproject.toml`, real-filter run green |
| SURF-02 | 07-04 | Three `Callable[...]` sites decided | ✓ SATISFIED | `ready_gate.py`, `panelkit.py`, `engine.py` |
| HYG-02 | 07-05 | Structured `label=` at both `_best_effort_hook` sites | ✓ SATISFIED | Both files, anti-drift guard green |
| LIFE-05 | 07-05 | Bundled `-m` form ratified as documented limitation | ✓ SATISFIED | Docstring-only diff, `EXTENSION-GUIDE.md` §4 |
| DOCS-02 | 07-06 | Active artifacts name paths that exist; standing gate | ✓ SATISFIED | `tests/test_doc_drift.py`, corrected artifacts |
| DOCS-03 | 07-06 | Enumeration includes the producing site | ✓ SATISFIED | Three-site enumeration confirmed by direct read |
| GATE-02 | 07-07 | Milestone-standing gate: green + RED-first ancestry from git | ✓ SATISFIED (correctly unchecked, milestone-standing) | All 4 standing gates re-run green; ancestry spot-checked |

No orphaned requirements: `.planning/REQUIREMENTS.md`'s Phase 7 requirement set (MATCH-03, LIFE-05,
SURF-02, DISC-07, DISC-08, HYG-02, HYG-03, DOCS-02, DOCS-03) matches exactly the nine IDs declared
across the seven plans' frontmatter `requirements:` fields plus GATE-02 (milestone-standing, closed
by 07-07 without being a phase-assigned requirement).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the 14 files touched by this phase's source/test edits | — | none |
| `.planning/REQUIREMENTS.md` | ~288-296 | The "Traceability" table's Status column still reads `Pending` for all nine Phase 7 requirement IDs and for GATE-02, while the individual requirement bullets above are correctly `[x]` and the Phase 5/6 rows in the same table read `Complete (date)`. Prior phases (see commit `e07f5e6`, "sync REQUIREMENTS traceability table with completed checklist") treated this sync as a distinct closing step; it appears to have been missed for Phase 7. | ℹ️ INFO | Cosmetic/tracking-only — does not affect any Phase 7 must-have truth, ROADMAP success criterion, or the DOCS-02/DOCS-03 de-hack-path claims (which are specifically about WeatherBot paths, not this internal table). The phase goal is explicitly scoped to "no stale planning doc **from v0.1.2**"; this table concerns v0.2.0 tracking. Not a blocker — flagged for a quick follow-up edit, not a gap requiring a new plan. |

### Human Verification Required

None. All three manual-only verifications named in `07-VALIDATION.md` (SURF-02's `callback`
rationale, LIFE-05's `EXTENSION-GUIDE.md` §4 prose, and DOCS-03's three-site enumeration) were
independently re-confirmed by direct reads during this verification pass (see Observable Truths #7,
#8, #10 above) — not merely trusted from the SUMMARY files.

### Gaps Summary

None. All nine Phase 7 requirements plus GATE-02 are closed with codebase evidence independently
re-derived (not copied from SUMMARY claims): source diffs read directly, all four standing gates
re-run live and green, two RED/GREEN git-ancestry pairs independently re-verified by sha comparison,
the LIFE-05 no-behavioral-change diff re-confirmed as docstring-only, and all three manual-only
prose sign-offs re-read in full. The one code-review finding (CR-01) was independently re-traced
against the live `summon_panel` source and the disposition (rejected as a false positive — the
invariant is about panel *liveness*, not *pinnedness*, and the proposed "fix" would reintroduce a
worse bug: two live Views both responding to clicks) holds up; WR-01's docstring correction is
present in the current source. The one INFO-level finding (REQUIREMENTS.md's stale Traceability
table Status column) is cosmetic, out of this phase's explicit "no stale doc from v0.1.2" goal
scope, and does not block phase completion.

---

_Verified: 2026-08-04T05:53:25Z_
_Verifier: Claude (gsd-verifier)_

---

## Gate-1 Agentic Self-UAT — SKIPPED (recorded, not silent)

`workflow.verify_work_agentic` is active and `phase.has-uat-criteria` returned `true`, so the gate
would normally dispatch `gsd-agentic-tester`. It was deliberately skipped. Reason:

- The detector's `matched_signals` was `["label"]` — it matched the word *label* inside success
  criterion 3, *"`_best_effort_hook` logs via a structured `label=` kwarg"*. That is a **structlog
  keyword-argument name, not a user-visible UI label**. A keyword false positive.
- This repo ships **no console script**. Per `CLAUDE.md` it is a library, "imported and wired by the
  consumer's composition root, never run on its own." There is no app, device, browser, or other
  drivable surface for a self-UAT agent to exercise.
- All five phase success criteria are code-level assertions, already covered automatically:
  184-test suite under `filterwarnings=error`, the import-hygiene gate, the new doc-drift gate, and
  the goal-backward verification above (11/11 must-haves, checked against live source).

Dispatching the tester would have found no target, returned INFRA, and — per the gate's INFRA
route — escalated to a human to "fix the environment" that is not actually broken.

**This is the third keyword-grep false positive from GSD gates in this phase** (the others: the
plan-time UI-SPEC gate matching *"form"* in "the attached `-mmodule` form false negative", and the
assumption-delta detector matching *"another"* in "some string matches another string"). Worth
raising upstream as a tooling issue rather than re-deciding per phase.
