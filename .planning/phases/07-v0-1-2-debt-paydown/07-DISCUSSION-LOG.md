# Phase 7: v0.1.2 debt paydown - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-03
**Phase:** 7-v0.1.2 debt paydown
**Areas discussed:** LIFE-05 identity guard boundary, SURF-02 annotation narrowing, HYG-03 warning
fix location, DOCS-02/03 correction reach + verification

**Mode:** advisor (USER-PROFILE.md present), calibration tier `standard` (vendor_philosophy =
`pragmatic-fast`; no `preferences.vendor_philosophy` override in `.planning/config.json`).

---

## Process deviations (recorded for audit)

**1. Advisor research agents were not spawned.** The workflow's `advisor_research` step calls for
one parallel subagent per selected gray area. The session was configured not to invoke the Agent
tool unrequested, and by that point the orchestrator had already read every relevant source site,
verified the `discord` exception hierarchy at runtime, traced the identity-guard fix through git
history (`60698b1`), and checked the WeatherBot paths on disk. Comparison tables were synthesized
inline from that evidence instead. Disclosed to the user before the first table was presented.

**2. The non-technical-owner reframe was resolved TRUE but deliberately not applied.**
`USER-PROFILE.md` matches `learning_style: guided`, and no `technical_background: true` override
exists, so advisor mode's detection rules resolve `NON_TECHNICAL_OWNER = true`. It was not applied:
the phase is a Python library-internals debt sweep, the user's own planning artifacts are deeply
technical, and Phase 6's CONTEXT already recorded the binding framing rule ("highly technical in
this domain; plain language only where he has said he is not fluent"). Surfaced to the user at the
top of the discussion so the call could be audited.

---

## Premise corrections surfaced before any question was asked

Four requirement/audit claims were checked against live source and found stale or imprecise. All
four are recorded in CONTEXT.md's `<premise_corrections>` section.

| # | Claim as written | Verified reality |
|---|---|---|
| PC-A | LIFE-05: "the attached `-mmodule` form false negative" | Already fixed in v0.1.2 (`identity.py:226-227`, commit `60698b1`, 3 passing tests). The real residual is the **bundled** group `-Om<module>` |
| PC-B | HYG-03: "test-double artifact" | Production defect at `gateway.py:353` — the coroutine is constructed before `run_coroutine_threadsafe`, so it orphans on the live TOCTOU race |
| PC-C | DISC-07: retry-pin needs a `Forbidden` branch | `Forbidden` **is a subclass of** `HTTPException` — it is being swallowed by a broader `except` that runs first, not missing |
| PC-D | "11 planning artifacts" carry the drift | 9 files / 14 lines. The audit's 11 included `STATE.md:101`, since rewritten. **3 sites use the bare `ops/daemon.py` form** a fully-qualified grep would miss |

PC-D was itself a mid-discussion correction: the orchestrator's first count (9 lines / 8 files) was
wrong, having greped only `weatherbot/ops/daemon.py`. A prior session's recorded figure of 14
prompted the recount. This is the audit's own headline lesson recurring — *a check derived from a
narrower string than the error cannot catch the error* — and it changed the D-67 gate pattern from
`weatherbot/ops/daemon` to bare `ops/daemon`.

---

## Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| LIFE-05 — the `-m` guard boundary | Decode the bundled short-option group, or ratify the documented limitation? | ✓ |
| SURF-02 — `on_online` annotation | Narrow `Callable[..., None]` → `Callable[[HealthResult], None]`? | ✓ |
| HYG-03 — where the warning gets fixed | Test double (mask) vs production eager-coroutine construction | ✓ |
| DOCS-02/03 — correction reach + verification | Archive treatment + a gate that can't depend on a WeatherBot checkout | ✓ |

**User's choice:** all four.

---

## LIFE-05 — the identity guard `-m` boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A — ratify, record only | Keep behavior; correct the stale requirement text naming the already-fixed attached form. No consumer-facing doc surface | |
| B — decode bundled group | Whitelist-guarded short-option scan so `python -Omexamplebot` matches; accepts CPython-grammar coupling and false-positive risk on a whitelist gap | |
| C — ratify + consumer-visible | A, plus state the launch-form constraint in `EXTENSION-GUIDE.md` so consumers see it, not just hub maintainers | ✓ |

**User's choice:** C.

**Notes:** The deciding argument was failure-direction asymmetry, which the code's own docstring
(`identity.py:184-192`) had already worked out: a false negative reports a live daemon as dead
(recoverable); a false positive delivers SIGHUP — default disposition *terminate* — to an unrelated
recycled PID. Decoding `-Om` as `-O`+`-m` while `-Xmfoo` is `-X` consuming `mfoo` risks matching
the wrong token, so B would arguably **add** a footgun to a phase whose goal is removing them.
C over A because this is a hub: a limitation living only in a private docstring is invisible to the
consumer who trips it. → **D-61**, plus **D-61a** exempting LIFE-05 from an artificial RED test,
since its decided outcome is "no behavioral change" and the pinned boundary test at
`tests/test_identity.py:165` is GREEN both ways by design.

---

## SURF-02 — `on_online` annotation narrowing

| Option | Description | Selected |
|--------|-------------|----------|
| A — narrow `on_online` only | The literal requirement; smallest diff and repin blast radius | |
| B — narrow + sweep all three loose `Callable[...]` | `on_online` narrowed, `panelkit.render` narrowed to arity-accurate, `engine.callback` left variadic with the rationale recorded | ✓ |
| C — leave loose, document why | Zero risk; but the looseness is drift, not intent, so there is nothing to document | |

**User's choice:** B — via a mid-question challenge (see below).

**Notes:** Three verified facts reframed this from "risky public-surface change" to a low-risk
correction: `on_fail` at `ready_gate.py:92` is *already* narrow (so `on_online` is asymmetric, not
deliberate); the hub always invokes the hook with exactly one argument (`ready_gate.py:135`); and
the only live consumer already conforms (`WeatherBot/weatherbot/scheduler/wiring.py:442` —
`def _on_online(_result) -> None:`).

### Mid-question challenge: "lets then add pyright no?"

The user pushed back on being told the hub runs no type checker — correctly noting that an
annotation nothing checks is a comment with extra syntax. Rather than accept or dismiss, the
trade-off was laid out:

- **Against folding it into Phase 7:** it is a toolchain change every future phase then pays, and
  the first run will generate its own backlog, because the injection architecture is deliberately
  `Any`-heavy at every seam. Basic mode likely near-clean; strict mode a flood. Folding it in turns
  "close 9 audit items" into "close 9 audit items and adopt static typing" — and the debt phase,
  sequenced last precisely to absorb slip, would absorb that instead.
- **What Phase 7 can do without it:** assert the annotation directly via
  `typing.get_type_hints(ReadyGate.__init__)`. Fails against pre-fix source (RED-first satisfied)
  and keeps failing if anyone widens it back. Narrower than a type checker — guards these
  signatures, not all call sites — but real, in-suite, zero new tooling.

| Option | Description | Selected |
|--------|-------------|----------|
| Defer to backlog, do B now | Narrow all three with `get_type_hints` guards; file pyright for a future milestone | ✓ |
| Add pyright in Phase 7 | Adopt as a standing gate now; needs a mode decision, a baseline/triage pass, and becomes a GATE-02 obligation forever | |
| Defer pyright, do A now | File pyright; narrow only `on_online`, keeping the diff minimal | |

**User's choice:** defer pyright to backlog, do B now. → **D-62**, **D-63**.

---

## HYG-03 — where the unawaited-coroutine warning gets fixed

| Option | Description | Selected |
|--------|-------------|----------|
| A — fix the test double | Make `_FakeCloseableClient.close` synchronous. Suite instantly clean; production orphan survives unobserved | |
| B — fix production, one message | Reclaim the orphan on the scheduling-failure branch; keep the single existing log string | |
| C — fix production, split log by cause | Same fix, plus `"could not be scheduled (loop closed)"` vs `"did not complete cleanly"` become distinguishable | ✓ |

**User's choice:** C.

**Notes:** A was rejected as masking — it deletes the only signal for a live production race. The
constraint that shaped B/C: `coro.close()` cannot live in the shared `except`, because if
scheduling succeeded and only `future.result()` timed out, the coroutine is running on the loop and
closing it raises `RuntimeError: cannot close a running coroutine`. The `try` has to split
regardless, which makes C's second message free — and it matches the posture DISC-07 is already
taking in this same phase. "Don't conflate two causes behind one message" became the phase's
connecting thread. → **D-64**.

### Follow-up: enforce zero-warnings structurally

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — make it structural | `filterwarnings = ["error"]` in `[tool.pytest.ini_options]`; any future warning fails the suite | ✓ |
| No — just fix the warning | Close HYG-03 literally; leave the suite free to accumulate warnings again | |

**User's choice:** yes. **Notes:** HYG-03's wording is "the full suite emits zero warnings," which
today is true by accident. Baseline at discuss time: `158 passed, 1 warning` (the 1 being HYG-03
itself). Planner must verify green under the filter; a future dependency deprecation is handled by
a targeted commented `ignore::` entry, never by removing the filter. → **D-65**.

---

## DOCS-02/03 — correction reach and verification

### Archive treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Correct active, annotate archive | Fix the 2 active sites; add a drift banner atop each archived `04-*` file, bodies preserved | ✓ |
| Correct everything | Rewrite all drift sites including the archive. Cleanest grep state; rewrites history | |
| Correct active only | Fix the 2 active sites, leave the archive untouched and unwarned | |

**User's choice:** correct active, annotate archive.

**Notes:** The decisive artifact is `04-01-PLAN.md:257` — the `<automated>` grep check that *passed
by grepping the wrong string*. It is the primary evidence for the audit's headline lesson.
Rewriting erases the evidence; a banner preserves it while warning anyone landing there directly.
Corrected mid-discussion from 5 archived files to **7** once PC-D surfaced `04-RESEARCH.md` and
`04-VALIDATION.md`. Three sites (`REQUIREMENTS.md:217`, `v0.1.2-MILESTONE-AUDIT.md:21` and `:142`)
name the wrong path *as the error being described* and are exempt from any rewrite. → **D-66**.

### Verification mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| In-suite gate + recorded evidence | Always-runs test asserting the drifted string appears in no active artifact, with a commented exempt-list; plus one-time filesystem verification recorded in the phase SUMMARY | ✓ |
| Marker convention + gate | Same gate, but intentional mentions carry an inline marker instead of a file exempt-list | |
| Evidence only, no gate | One-time filesystem verification; no standing test | |

**User's choice:** in-suite gate + recorded evidence.

**Notes:** The framing problem was that the ROADMAP demands the check assert the path resolves on
disk *in WeatherBot*, while the hub's suite cannot hard-depend on a WeatherBot checkout. A
`skipif(weatherbot_missing)` guard was rejected as the **same failure class the audit warned
about** — a check that silently does not run is false assurance, exactly like one that greps the
string that produced the error. Splitting into an always-runs gate plus once-recorded evidence
avoids both. Filesystem verified 2026-08-03: `weatherbot/ops/daemon.py` does **not** exist;
`weatherbot/scheduler/daemon.py` and `weatherbot/ops/selfcheck.py` both do. → **D-67**, and
**D-68** for DOCS-03's third (producing) site plus the stale "11 artifacts" figure.

---

## Claude's Discretion

Presented with stated fix directions; the user reviewed and left them to the planner. Root causes
are pinned to exact lines — these are not open questions.

- **MATCH-03** — `seen: set[str]` in the existing D-34 loop at `registry/registry.py:53`, raising
  `ValueError`. Error type locked by the ROADMAP. Consumer-breaking; repin needs a WeatherBot sweep.
- **DISC-07** — `except discord.Forbidden` inserted *before* `except discord.HTTPException` on the
  retry pin (`gateway.py:218`), mirroring the idiom the first `msg.pin()` already uses at 196-200.
- **DISC-08** — drop the pre-delete `matches.pop(0)` (`gateway.py:208`); remove the stray from the
  cleanup list only on a successful delete, so a failed eviction is retried by the loop at 237.
- **HYG-02** — structured `label=` kwarg at `lifecycle/ready_gate.py:188` **and** the verbatim
  clone at `config/reload.py:326`. One fix, two sites.

## Deferred Ideas

- **Adopt pyright as a standing gate.** Raised by the user unprompted during SURF-02; deferred, not
  rejected. Sizing recorded in CONTEXT.md `<deferred>` — mode choice (`basic` vs `strict`),
  baseline-and-burn-down vs fix-all, `discord.py==2.7.1` stub quality, and annotating the
  intentional `Any`-at-seams sites. File to `.planning/backlog/` for a future milestone.
- **Decode CPython's bundled short-option group** (`python -Om<module>`) in the identity guard.
  D-61's rejected alternative. Revisit only if a consumer actually needs that launch form.

## Todos

`todo.match-phase 7` returned 0 matches — none folded, none reviewed.
