---
status: complete
result: all_pass
gate: 1
phase: 07-v0-1-2-debt-paydown
source: [07-ROADMAP success criteria]
device: n/a — pure Python library, no runnable app (scratch venv, installed wheel)
apk: yahir_reusable_bot-0.1.2-py3-none-any.whl (md5 399e28a462f3447237a728353123a09f @ d97d866)
run: 2026-08-18T00:00:00Z
---

# Self-UAT Log — Phase 7 (v0.1.2 debt paydown)

**Target:** No device/browser surface exists for this project (`yahir_reusable_bot` is a pure
library, "never run on its own" per its own `CLAUDE.md`). Per `.planning/AGENT-LIBRARY-TESTING.md`
(D1–D8, authored at Phase 5 and reused unchanged at Phase 6), the consumer-facing rung for this
platform is: build the wheel from HEAD, install it into a disposable scratch venv, and exercise the
public API from a Python process whose `cwd` is outside the repo (so the repo root is never on
`sys.path` — the same vantage point a real downstream consumer bot has). All behavioral criteria
below are driven against that installed wheel with the REAL runtime deps (`discord.py==2.7.1`,
`structlog==26.1.0`) — never the hub's own `.venv`.

**Note on the prior SKIP verdict (audited, not trusted):** `07-VERIFICATION.md` recorded the
agentic Gate-1 as *SKIPPED — "no console script … no app, device, browser, or other drivable
surface for a self-UAT agent to exercise."* That premise is **falsified by this run**: the exact
scratch-venv consumer-probe driver already used for Phases 5 and 6 (documented in the same
`HUMAN-UAT-PENDING.md` ledger that called Phase 7 un-driveable) drives every Phase-7 public behavior
cleanly. The "drivable surface" for a library is the installed package's public API, not a UI. The
keyword false-positive that triggered the SKIP (the detector matching *label* inside SC3) was a real
tooling misfire, but the conclusion drawn from it — that nothing could be behaviorally verified —
was wrong. This log supersedes that SKIP with first-hand, installed-wheel evidence for all five
ROADMAP success criteria. The code-level gate's 11/11 goal-backward verification remains valid and
complementary; this run adds the consumer-facing, real-`discord.py`/real-`structlog`, installed-wheel
layer on top of it.

**Build identity:** git sha `d97d866` (clean tree — `git status --short` empty). Wheel built via
`uv build --wheel --out-dir <scratch>/dist` → `yahir_reusable_bot-0.1.2-py3-none-any.whl`, md5
`399e28a462f3447237a728353123a09f`. `unzip -l` confirmed the wheel ships every Phase-7-touched
module: `registry/{registry,spec,match}.py`, `discord/{gateway,panelkit}.py`,
`lifecycle/{ready_gate,identity}.py`, `config/reload.py`, `scheduler/engine.py` — the fixes are
genuinely packaged, not merely present in the source tree (the packaging risk `uv run pytest` cannot
see, since `pythonpath = ["."]` bypasses installed-package resolution entirely).

**Scratch venv:** `uv venv <scratch>/venv --python 3.12` + `uv pip install --python
<scratch>/venv/bin/python <scratch>/dist/*.whl` (pulled `discord.py==2.7.1`, `structlog==26.1.0`,
`tenacity==9.1.4`, `httpx`/`yarl`/`propcache` transitives, and `yahir-reusable-bot==0.1.2` from the
local wheel file). Project's own `.venv`/`uv.lock` were never touched.

**Preflight import check:** from `<scratch>/consumer_cwd` (a directory containing no copy of the
repo), `import yahir_reusable_bot` resolved to the venv's `site-packages`, and the repo root was
confirmed absent from `sys.path` (repo-derived `sys.path` entries: `[]`). `discord 2.7.1` and
`structlog 26.1.0` importable. This is the load-bearing precondition for every criterion below.

**Unit suite (inherited, code-level, not re-run by this gate):** `07-VERIFICATION.md` records
`uv run pytest -q -o 'filterwarnings=error'` → `184 passed` (zero warnings), import-hygiene → 10
passed, doc-drift gate → 5 passed, `ruff check` → clean. This Gate-1 pass adds the real-process,
installed-wheel consumer layer those suites do not exercise; it does not re-run them.

**Seed/fixture integrity:** no persistent fixture exists for a pure library. Each criterion
constructs (seeds) its own in-memory `CommandSpec`s, fake `discord` channel/message doubles (whose
`pin()`/`delete()` raise REAL `discord.Forbidden`/`discord.HTTPException` instances), and NUL-joined
`argv` byte strings directly in each probe script, immediately before driving the SUT.

## Criteria

### 1. Registering two `CommandSpec`s with the same `name` raises `ValueError` at registration, so `match_command` can never resolve a different `CommandSpec` than `by_name` holds (MATCH-03)
result: passed
- **Rung:** 3 (headless data check — installed-wheel process, return-value + raised-exception inspection)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** two specs sharing a `name` raise `ValueError` at `CommandRegistry` construction AND
  through `build_registry`, the message naming the duplicate, BEFORE `by_name` is derived; a valid
  registry stays internally consistent (`by_name` and `by_keyword_len_desc` carry the same spec set,
  so `match_command` — which reads those views — can never disagree with `by_name`); empty and
  single-spec registries never trip the guard; NFC vs NFD name variants are distinct registrations.
- **Arranged (seeded):** in-script `CommandSpec` factory; a duplicate-`status` pair; a valid
  `now`/`next`/`next-cloudy` trio; empty and single-spec lists; NFC and NFD forms of `café`.
- **Did (drove):** `CommandRegistry([dup, dup])` and `build_registry([dup, dup])` (expect raise);
  `build_registry(trio)` then compared `set(reg.by_name.values())` against
  `set(reg.by_keyword_len_desc)` and drove `match_command("next-cloudy today", reg.by_keyword_len_desc)`
  asserting `.spec is reg.by_name["next-cloudy"]`; constructed empty/single/NFC-NFD registries.
- **Observed:** `ValueError: CommandSpec.name must be unique per registry (a duplicate silently
  overwrites in by_name while by_keyword_len_desc and render_help still carry both entries); got
  duplicate 'status'` from BOTH construction paths, message names the duplicate; valid registry
  `by_name`/`by_keyword_len_desc` spec sets equal and `match_command` resolved to exactly the spec
  `by_name` holds; empty → `()`, single → 1 command (guard not over-eager); NFC/NFD café → 2 distinct
  commands, not a duplicate.
- **Evidence:** `<scratch>/gate1-p07/c1_match03_duplicate.py`; transcript `CRITERION 1: PASS`.

### 2. The retry-pin path distinguishes `discord.Forbidden` from a generic `HTTPException` (a permissions failure is never mislabeled as a pin-cap failure); a failed eviction-delete leaves that stray in the call's cleanup instead of dropping it (DISC-07 + DISC-08)
result: passed
- **Rung:** 3 (installed-wheel process, real `discord.Forbidden`/`discord.HTTPException` types + real `structlog.testing.capture_logs`)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** driving `summon_panel` into the pin-cap retry branch where the retry `pin()` raises
  `discord.Forbidden` logs the distinct `"panel pin forbidden on retry …"` event and NOT the generic
  cap message, leaving the fresh panel unpinned (logged-and-swallowed, not re-raised); a generic
  `discord.HTTPException` on the retry still logs the cap message and NOT the forbidden one
  (falsifies an over-broad `Forbidden` catch); a stray whose `delete()` raises is retried by the
  cleanup loop on the SAME call (`delete_attempts == 2`); a stray whose `delete()` succeeds is not
  re-deleted (`delete_attempts == 1`).
- **Arranged (seeded):** fake `_FakeChannel`/`_FakeOwnedMessage`/`_FakeRetryPinMessage`/`_FakeStubbornStray`
  doubles whose `pin()`/`delete()` raise REAL `discord.Forbidden(_Resp(), …)` /
  `discord.HTTPException(_Resp(), …)` instances (the actual exception classes from the installed
  discord.py, not stand-ins).
- **Did (drove):** four `asyncio.run(summon_panel(...))` invocations under `capture_logs()` — retry
  Forbidden; retry generic HTTPException; stubborn-stray (delete always raises); cooperative-stray
  (delete succeeds).
- **Observed:** DISC-07a — forbidden event present, cap event absent, `fresh.pinned is False`.
  DISC-07b — cap event present, forbidden event absent. DISC-08a — `delete_attempts == 2`
  (two `"stray panel delete failed; continuing"` warnings emitted, corroborating the retry),
  `fresh.pinned is True`. DISC-08b — `delete_attempts == 1`, `fresh.pinned is True`.
- **Evidence:** `<scratch>/gate1-p07/c2_disc0708.py`; transcript `CRITERION 2: PASS`.

### 3. `_best_effort_hook` logs via a structured `label=` kwarg (not an f-string) at both its sites; and the never-scheduled `client.close()` coroutine no longer leaks an unawaited-coroutine `RuntimeWarning` (HYG-02 + HYG-03)
result: passed
- **Rung:** 3 (installed-wheel process, real `capture_logs` event-dict inspection + real `warnings` filter)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected (HYG-02):** invoking `_best_effort_hook` with a raising hook, at BOTH the
  `ready_gate.ReadyGate` site and the `config.reload.ReloadEngine` clone, emits the event `"hook
  failed; engine result unaffected"` carrying `label` as a SEPARATE structured key equal to the
  passed value — NOT folded into the event string (the falsification: an f-string would leave no
  `label` key and put the value inside `event`). **Expected (HYG-03):** driving `BotThread.stop()`
  into the TOCTOU closed-loop scheduling-failure branch reclaims the never-scheduled coroutine
  (`inspect.getcoroutinestate` → `CORO_CLOSED`) so `gc.collect()` under `warnings.simplefilter("error")`
  raises NO `RuntimeWarning`, `stop()` never raises, the thread still joins; the scheduling-failure
  and await-failure branches log DISTINCT messages.
- **Arranged (seeded):** a raising `boom` hook; `_CoroCapturingClient` (plain `close()` returning an
  inspectable coroutine), `_RaisingCloseClient`, a closed-loop fast-path proxy, and a joinable-thread
  double — all constructed in-script.
- **Did (drove):** called `ReadyGate._best_effort_hook` and `ReloadEngine._best_effort_hook` under
  `capture_logs()`; drove `BotThread.stop()` on a proxied closed loop under
  `warnings.catch_warnings()/simplefilter("error")` + `gc.collect()`, then under `capture_logs()`;
  drove `stop()` on a genuinely running loop whose client `close()` raises.
- **Observed:** HYG-02 both sites — one matching event, `label == "probe-label"` as a distinct key,
  value absent from `event`. HYG-03a — coroutine state `CORO_CLOSED`, no warning raised, thread
  joined `[True]`. HYG-03b — `"bot client.close() could not be scheduled (bot loop already closed)"`
  present, await-failure message absent. HYG-03c — `"bot client.close() did not complete cleanly"`
  present, scheduling message absent, thread joined.
- **Evidence:** `<scratch>/gate1-p07/c3_hyg02_hyg03.py`; transcript `CRITERION 3: PASS`.

### 4. The identity guard's attached `-mmodule` behavior and `on_online`'s annotation each land as an explicitly decided outcome with the reasoning recorded (LIFE-05 + SURF-02)
result: passed
- **Rung:** 3 (installed-wheel process — `typing.get_type_hints`/`inspect.signature` introspection + real behavioral drive of `_argv_matches_marker` + shipped-docstring inspection)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected (SURF-02):** `ReadyGate.__init__`'s `on_online` hint is exactly
  `Callable[[HealthResult], None] | None`; `panelkit`'s build-time `render` param is
  `Callable[[Any, Any], discord.Embed]` (arity-narrowed); `SchedulerEngine.register`'s `callback`
  is DELIBERATELY left `Callable[..., Any]` with the reason recorded in its own docstring (naming
  SURF-02). **Expected (LIFE-05):** the documented, decided limitation holds behaviorally — standalone
  `-m examplebot` and attached `-mexamplebot` argv forms MATCH the marker, while the bundled
  `-Omexamplebot` short-option group is intentionally NOT decoded (returns `False`); and the shipped
  `_argv_matches_marker` docstring records the reasoning (bundled-group boundary, SIGHUP asymmetric
  risk, cross-reference to `EXTENSION-GUIDE.md`).
- **Arranged (seeded):** NUL-joined `argv` byte strings for the three `-m` forms; marker
  `b"examplebot"`.
- **Did (drove):** `typing.get_type_hints(ReadyGate.__init__)` and `inspect.signature(...)` on the
  three SURF-02 sites; `identity._argv_matches_marker(argv, proc_marker=…)` for standalone/attached/
  bundled; `inspect.getdoc` on `SchedulerEngine.register` and `_argv_matches_marker`.
- **Observed:** SURF-02a — `on_online == Callable[[HealthResult], None] | None` (Optional of Callable
  with a single `HealthResult` param, `None` return). SURF-02b — `render == Callable[[Any, Any],
  discord.Embed]`. SURF-02c — `callback == Callable[..., Any]`, docstring contains `SURF-02` +
  variadic rationale. LIFE-05 — `standalone=True attached=True bundled(-Om)=False`; docstring
  contains the bundled/SIGHUP/EXTENSION-GUIDE reasoning.
- **Evidence:** `<scratch>/gate1-p07/c4_surf02_life05.py`; transcript `CRITERION 4: PASS`.

### 5. Every active planning artifact naming a consumer de-hack site names a path that **exists** in WeatherBot, and the enumeration includes the *producing* site (`weatherbot/ops/selfcheck.py`), not only the consuming sites — verified against the filesystem (DOCS-02 + DOCS-03)
result: passed
- **Rung:** 0 (direct source/doc read + WeatherBot filesystem check — the criterion is a
  doc-content-vs-filesystem claim; the `.planning/` docs it concerns are not shipped in the wheel,
  and the standing gate that enforces it is a source-tree test, so no installed-process drive applies)
- **Target:** repo `.planning/` tree at `d97d866` + the live WeatherBot filesystem at `/home/yahir/Projects/WeatherBot`
- **Expected:** the de-hack site enumerations in the two ACTIVE artifacts (`.planning/REQUIREMENTS.md`,
  `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md`) name only paths that resolve on the WeatherBot
  filesystem; the enumeration includes the PRODUCING site `weatherbot/ops/selfcheck.py:to_health_result`;
  the stale `weatherbot/ops/daemon.py` path (the original drift) does NOT exist on disk; any residual
  mention of the stale spelling in an active artifact is a line-scoped exempted meta-mention describing
  the drift, not a de-hack site reference. Verified against the filesystem, not against the string that
  produced the drift.
- **Arranged (seeded):** none — direct read of the artifacts under test + filesystem stat.
- **Did (drove):** grepped the two active artifacts for `weatherbot/…\.py` references; `test -f`
  against WeatherBot for `scheduler/wiring.py`, `scheduler/daemon.py`, `ops/selfcheck.py`, and the
  stale `ops/daemon.py`; read `weatherbot/ops/selfcheck.py:149` (`def to_health_result(...) ->
  HealthResult`); swept all active (non-archive) `.planning/**` for the bare `ops/daemon` spelling
  and classified each hit.
- **Observed:** `weatherbot/scheduler/wiring.py`, `weatherbot/scheduler/daemon.py`,
  `weatherbot/ops/selfcheck.py` all EXIST; stale `weatherbot/ops/daemon.py` ABSENT; producing site
  named in the enumeration (`REQUIREMENTS.md:122`, `:233`) and genuinely produces `HealthResult`
  (`to_health_result` at `selfcheck.py:149`). The only active-artifact mentions of the stale spelling
  are the DOCS-02 requirement block itself (`REQUIREMENTS.md:225-230` — the line-scoped exempt window,
  narrating "the real path is `weatherbot/scheduler/daemon.py`"), the annotated
  `v0.1.2-MILESTONE-AUDIT.md` audit record, and the Phase-7 planning subtree describing the
  drift-fix work — none are de-hack site references to a non-existent path. The standing gate
  `tests/test_doc_drift.py` (bare `ops[/.]daemon` regex, 5 tests) exists and per `07-VERIFICATION.md`
  passes live.
- **Evidence:** `07-VERIFICATION.md` truths #9/#10; live filesystem checks captured in this run's
  transcript (`EXISTS weatherbot/scheduler/wiring.py` … `ABSENT weatherbot/ops/daemon.py`).

## Summary

total: 5
passed: 5
partial: 0
failed: 0
infra: 0

## Notes / anomalies (for the Gate-2 reviewer)

- **This log supersedes the prior SKIP.** `07-VERIFICATION.md` (and the pre-existing
  `HUMAN-UAT-PENDING.md` Phase-7 entry) recorded the agentic Gate-1 as SKIPPED on a "no drivable
  surface" premise. That premise was incorrect for a library: the drivable surface is the installed
  package's public API, and the very same `.planning/AGENT-LIBRARY-TESTING.md` scratch-venv driver
  used for Phases 5 and 6 drove all five Phase-7 criteria here with first-hand evidence. The
  keyword-grep false positive that triggered the SKIP (matching *label* in SC3) was real, but the
  inference "therefore nothing is verifiable" was the actual error this run corrects. The Phase-7
  ledger entry has been updated from SKIPPED to a Gate-1 PASS pointing at this log.
- Criterion 2 deliberately raises REAL `discord.Forbidden` and `discord.HTTPException` instances from
  the installed discord.py (constructed with a synthetic `_Resp`) and drives the async `summon_panel`
  coroutine via `asyncio.run` — the two `"stray panel delete failed; continuing"` warnings printed
  during DISC-08a are the expected, correct signal of the retry (two delete attempts), not a defect.
- Criterion 5 is inherently a rung-0 doc-vs-filesystem claim (planning docs are not in the wheel);
  it was settled by direct filesystem verification of the enumerated de-hack sites against the live
  WeatherBot tree, exactly as the criterion demands ("verified against the filesystem, not against
  the string that produced the drift").
- Two SC probes hit an authoring bug in the PROBE (not the product) on first run — a
  `match_command` return-value access in C1 and a space-stripped-needle mismatch in C4's SURF-02b
  string check — both corrected in-script; the underlying product annotations/return types were
  correct throughout. Called out for transparency.
- The INFO-level finding from `07-VERIFICATION.md` (the stale `Pending` Status column in
  `REQUIREMENTS.md`'s Traceability table) is cosmetic/tracking-only, out of this phase's "no stale
  doc from v0.1.2" goal scope, and does not affect any of the five behavioral criteria above.

## Findings routed to gap-closure (if any)

None — all 5 ROADMAP success criteria PASS on the real, installed-wheel consumer-facing surface.

## Verdict

All 5 ROADMAP success criteria PASS → Gate-1 complete; human Gate-2 deferred to milestone
completion (registered in `.planning/HUMAN-UAT-PENDING.md`).
