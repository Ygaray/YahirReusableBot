> **Archival note (added 2026-08-04, Phase 7 DOCS-02/DOCS-03):** this is an archived v0.1.2 record; the consumer gate-return de-hack path this record names does not exist as spelled — the correct path is `weatherbot/scheduler/daemon.py`, and the enumeration is also incomplete without the producing site `weatherbot/ops/selfcheck.py`. The body below is preserved unrevised as the historical record. See `.planning/v0.1.2-MILESTONE-AUDIT.md` DOC-DRIFT-01 / DOC-DRIFT-02.

# Phase 4: Cleanup + ReadyGate fatal outcome - Context

**Gathered:** 2026-07-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Two independent, low-risk changes closing the last two milestone findings (ROADMAP §"Phase 4"):

1. **SURF-01 (H17)** — public-surface drift. `discord/__init__.py`'s docstring advertises "the
   create-before-delete summon orchestration" and `gateway.py.__all__` lists `summon_panel`, but
   the package `__init__` never re-exports it, so `from yahir_reusable_bot.discord import
   summon_panel` raises `ImportError`. Fix direction is **locked by the success criterion**: make
   docstring ↔ `gateway.__all__` ↔ package `__init__` agree by adding the missing re-export.

2. **LIFE-04 (H18)** — `ReadyGate.run` enhancement. `run(stop)` returns `bool` (True=online,
   False=clean-shutdown) and loops until ok-or-`stop`. A **fatal** probe is only logged louder and
   **re-probed forever** — consumers must overload the `stop` Event to break out. Give the gate a
   first-class fatal outcome a consumer branches on directly, without breaking the ok / clean-shutdown
   paths' current semantics or emit ordering (`on_online` → log → `READY=1`).

**Standing gate (GATE-01):** full pytest suite + import-hygiene / litmus / grimp layering stay
green. **Every fix ships a RED-first regression test** that fails against pre-fix source.

**Not in this phase:** the human-gated close-out (pyproject bump `0.1.1→0.1.2`, `v0.1.2` tag cut,
WeatherBot repin + de-hack) — surfaced at phase end, never performed autonomously (ECOSYSTEM.md §3).

</domain>

<decisions>
## Implementation Decisions

> Decision numbering continues the milestone-wide sequence. Phase 3's last **fix** decision was
> **D-42** (D-43 in the Phase-3 CONTEXT is a cross-cutting test-posture note, not a fix), so
> Phase 4 fix decisions start at **D-44**. Distinct namespace from the module docstrings' own
> extraction decisions (`D-01..D-09` inside the source files).
>
> **The user reviewed the gray areas and accepted the recommended default for each** ("your recs
> are fine") — every decision below is a locked default, recorded with its rejected alternatives so
> the planner sees the reasoning, not just the verdict. This mirrors the Phase-3 pattern.

### ReadyGate fatal outcome (LIFE-04)

- **D-44 (outcome shape — return type):** **Replace the `bool` return of `ReadyGate.run` with a
  three-member `ReadyOutcome` enum (`ONLINE`, `SHUTDOWN`, `FATAL`), and override `__bool__` so ONLY
  `ONLINE` is truthy.** New/updated callers branch on identity (`outcome is ReadyOutcome.FATAL`);
  every existing `if gate.run(stop):` caller (WeatherBot's `ops/daemon.py` gate-return check for the
  non-fatal case) stays byte-compatible because ONLINE remains truthy and both non-online outcomes
  remain falsy. Export `ReadyOutcome` from `lifecycle/__init__.py`'s `__all__` alongside `ReadyGate`.
  - **Why the `__bool__` override is the safe choice, not a magic trick:** a *plain* enum (no
    override) makes ALL members truthy (non-zero) — so an un-updated `if run():` would treat both
    SHUTDOWN and FATAL as "online" and start work on shutdown. That silent behavior reversal is
    exactly the regression class the project guards against. Constraining truthiness to ONLINE
    preserves the ROADMAP-locked "ok / clean-shutdown paths keep their current semantics."
  - **Rejected — plain enum, force every caller to `run() is ReadyOutcome.ONLINE`:** crisper on
    paper but churns every call site and risks the silent "un-updated `if run():` → treats non-ONLINE
    as truthy" bug above.
  - **Rejected — keep `bool`, signal fatal via exception / separate attribute:** that *is* the
    stop-overload-class hack the enhancement exists to remove; it keeps fatal off the return channel
    consumers already branch on.

- **D-45 (fatal trigger — what makes a probe fatal):** **Add a new explicit `fatal: bool = False`
  field to `HealthResult`, app-authored at the boundary; leave `Severity.CRITICAL` re-probe
  semantics UNCHANGED.** The gate branches on `result.fatal` exactly as it already branches on the
  neutral `result.severity` rung — opaque passthrough, weather-noun-free, "app classifies, gate
  branches" (the D-02 lifecycle litmus). `fatal` is additive (defaults False), so every existing
  `HealthResult(...)` construction and all current tests keep compiling and behaving identically.
  - **Rejected — reuse `Severity.CRITICAL` as the fatal trigger:** needs no new field but *reverses*
    `Severity`'s documented stay-alive contract (health.py: "CRITICAL... still keeps re-probing — a
    dead process can answer no future status query"). It also conflates two orthogonal axes: "how
    loudly do I log this" vs "is this recoverable." An app must be able to log a critical-but-
    recoverable failure without triggering death.
  - **Rejected — new `Severity.FATAL` rung above CRITICAL:** keeps everything on one ordered field
    but forces fatalness onto the log-level axis; a fatal failure and its log level are independent
    concerns → two fields, not one overloaded rung.

- **D-46 (fatal-path semantics — hooks, ordering, re-probe):** **On a failing probe, `on_fail`
  fires first (unchanged — the app's durable health-row stamp, D-02a); then if `result.fatal` is
  True, log the fatal event at `critical` and `return ReadyOutcome.FATAL` immediately — no
  `stop.wait()` re-probe.** `on_online` does NOT fire (the gate never went online). This mirrors the
  online path's locked "hook → log → return" ordering. The non-fatal failing path is byte-identical
  to today (existing severity-branch log + interruptible re-probe wait). Concretely: the `fatal`
  short-circuit sits *after* the `on_fail` invocation and *before/at* the severity-branch log.
  - **Rejected — skip `on_fail` on the fatal path:** would drop the app's durable-row stamp for the
    single most important (terminal) failure — precisely when the app most needs the row written.
  - **Rejected — return FATAL but still do one `stop.wait()` first:** pointless latency; fatal means
    stop gating now.

### Public-surface drift (SURF-01)

- **D-47 (export scope):** **Add `summon_panel` to `discord/__init__.py`'s imports + `__all__`,
  re-exported ONLY from the `discord` subpackage — NOT surfaced at the top-level
  `yahir_reusable_bot` package.** The docstring is already correct and `gateway.__all__` already
  lists it, so the fix is purely the missing re-export leg (no docstring edit). `summon_panel` is
  Discord-adapter vocabulary; the top-level package stays minimal. RED test: `from
  yahir_reusable_bot.discord import summon_panel` (currently `ImportError`).
  - **Rejected — "fix the docstring" (delete the claim instead of exporting):** the success
    criterion explicitly wants the import to *succeed*, so alignment is toward exporting, not
    retracting.
  - **Rejected — also re-export at top-level `yahir_reusable_bot`:** unnecessary surface widening
    for an adapter-specific symbol.

### Claude's Discretion
- Exact `ReadyOutcome` member ordering / values and whether it subclasses `Enum` vs a plain class
  with `__bool__` — any impl satisfying "only ONLINE truthy, three distinct identities" is fine.
- Exact fatal-log message wording (structured, weather-noun-free, `reason`/`detail` opaque
  passthrough like the existing critical branch).
- Test file placement: a new `tests/test_ready_gate.py` for LIFE-04; SURF-01's import assertion may
  live in a small new test or extend the import-surface coverage — planner's call, provided it's
  RED-first against current source.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of record — the two findings
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` §4 — H17 (SURF-01) and H18 (LIFE-04) fix
  direction + the H18 consumer de-hack site names, verified against hub source.
- `.planning/backlog/HUB-FINDINGS-HANDOFF.md` — full failure scenario + evidence per finding.
- `.planning/ROADMAP.md` §"Phase 4" — success criteria (three-way `summon_panel` agreement; distinct
  fatal outcome; de-hack sites named in the phase summary) and the human-gated close-out checklist.

### Governance
- `ECOSYSTEM.md` §3 — human-gated close-out: fixes + green gates are autonomous; the `pyproject.toml`
  bump, `v0.1.2` tag cut, and WeatherBot repin are surfaced, never performed.

### Source files touched
- `yahir_reusable_bot/lifecycle/ready_gate.py` — `ReadyGate.run` (the `while not stop.is_set()`
  loop, the online-return, the severity-branch log, the `stop.wait()` re-probe) — D-44/D-46 site.
- `yahir_reusable_bot/lifecycle/health.py` — `HealthResult` frozen dataclass + `Severity` IntEnum —
  D-45 adds `fatal: bool = False`; `Severity` left unchanged.
- `yahir_reusable_bot/lifecycle/__init__.py` — `__all__` — export `ReadyOutcome` (D-44).
- `yahir_reusable_bot/discord/__init__.py` — imports + `__all__` — D-47 re-export leg.
- `yahir_reusable_bot/discord/gateway.py` — `__all__` already lists `summon_panel` (line 42);
  reference only, no change.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`HealthResult` (frozen dataclass, health.py):** additive `fatal: bool = False` field — mirrors
  how `severity: Severity = Severity.WARNING` was added as a neutral, app-authored, defaulted field.
- **`Severity` IntEnum (health.py):** the precedent for a neutral gate-branch field; D-45
  deliberately does NOT extend it (keeps log-level and fatalness orthogonal).
- **`ReadyGate._best_effort_hook` (ready_gate.py):** the None-safe hook invoker `on_fail`/`on_online`
  already ride — the fatal path reuses it verbatim for the `on_fail` stamp.
- **`discord/__init__.py` `__all__` re-export idiom:** `BotThread`, `build_client`, `PanelKit`,
  `SelectedContext` are already re-exported the exact way `summon_panel` needs to be.

### Established Patterns
- **"App classifies at the boundary, gate branches on a neutral field, never inspects `reason`"**
  (D-02 lifecycle litmus) — `fatal` obeys it; the gate reads `result.fatal` opaquely, never a string.
- **Locked emit ordering** `on_online` → `_log.info("bot online")` → `notifier.ready()` on the
  online path — D-46's fatal path mirrors it (`on_fail` → critical log → return FATAL).
- **RED-first regression per fix** against a hub-assertable observable — the milestone GATE-01
  posture (D-43, Phase-3 CONTEXT).
- **No domain nouns / one-way dependency** — `ReadyOutcome`, `fatal`, and the `summon_panel` export
  must pass `tests/test_import_hygiene.py` (grimp + litmus grep) with zero weather vocabulary.

### Integration Points
- `ReadyGate.run`'s return type is the consumer contract WeatherBot's daemon branches on — D-44's
  truthy-ONLINE preserves that seam for the non-fatal case.
- `lifecycle/__init__.py` `__all__` is the public import surface — `ReadyOutcome` must join it so a
  consumer can `from yahir_reusable_bot.lifecycle import ReadyOutcome`.

</code_context>

<specifics>
## Specific Ideas

**H18 consumer de-hack — must be named in the phase summary (ROADMAP success criterion).** After
ship + repin, WeatherBot collapses its app-side `fatal` `threading.Event` workaround onto the hub's
`ReadyOutcome.FATAL` at two sites (per HUB-HARDENING-REPORT §4):
- `weatherbot/scheduler/wiring.py` `_on_fail` (fatal branch) — deletes the separate `fatal` Event.
- `weatherbot/ops/daemon.py` — the gate-return exit-code check consumes `ReadyOutcome.FATAL`
  directly instead of inspecting the overloaded stop/fatal Event.

These live in the WeatherBot repo (cross-repo) — this phase only *documents* them for the repin;
it does not touch WeatherBot.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (PC-01 log secret-redaction promotion remains parked as
backlog Phase 999.5, out of this milestone.)

</deferred>

---

*Phase: 4-cleanup-readygate-fatal*
*Context gathered: 2026-07-28*
