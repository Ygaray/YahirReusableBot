# YahirReusableBot — Requirements

## Implemented (v0.1.0 — imported from WeatherBot extraction)

| ID | Requirement | Status |
|----|-------------|--------|
| CORE-01 | Channel-agnostic delivery surface (`Channel` ABC + `DeliveryResult`, `send(text)`) | done |
| CORE-02 | Retry/backoff reliability primitives (two-burst retry engine) | done |
| CORE-03 | In-process scheduler engine | done |
| CORE-04 | Generic command registry + dispatcher (`CommandSpec` / `DispatchContext` / `build_registry` / `match_command` / `dispatch_reply`) | done |
| CORE-05 | Discord adapter (gateway + panel kit + `SelectedContext[I]` + selection), `discord.py==2.7.1` exact pin | done |
| CORE-06 | Lifecycle: READY gate, systemd-notify, process-identity guard, `HealthResult` | done |
| CORE-07 | Host-supplied port Protocols: `AlertSink`, `OccurrenceStore`, `JobStore` (+ `MemoryJobStore`) | done |
| HYG-01 | Standing import-hygiene gates (grimp graph + isolated-import + AST signature litmus), green standalone | done |
| DOCS-01 | `EXTENSION-GUIDE.md` documents all six plug points with implemented-vs-deferred status | done |

## Milestone v0.1.2 — Hub hardening (SHIPPED 2026-07-28, tag `v0.1.2`)

> All 19 requirements satisfied and verified. Retrospective audit:
> `.planning/v0.1.2-MILESTONE-AUDIT.md` (status `tech_debt` — no blockers, 9 open items, which
> are carried into v0.2.0 below).

Source of record: `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` (fix direction per finding)
and `.planning/backlog/HUB-FINDINGS-HANDOFF.md` (failure scenario + evidence). One requirement per
audit finding, so every REQ traces back to an H-number. **Every requirement ships with a RED-first
regression test** — the test must fail against current source before the fix lands.

### Reliability (`reliability/retry.py`)

- [x] **RELY-01** (H02, high): A transient httpx network failure that arrives as
  `RemoteProtocolError` (server disconnected mid-response) or `WriteError` is classified transient,
  so the two-burst retry fires and exhaustion reports `transient_exhausted` — not `internal_error`.
  Broaden to `(TimeoutException, NetworkError, RemoteProtocolError)`; **not** a blanket
  `TransportError`, so client-side `LocalProtocolError` stays non-retryable. → Phase 1

- [x] **RELY-02** (H09, low): A caller configuring `burst_size == 1` gets a degraded wait rather
  than a `ZeroDivisionError` raised from inside the tenacity wait callable. → Phase 3

- [x] **RELY-03** (H10, low): A caller pairing standalone `two_burst_wait` with its own
  `stop_after_attempt(N)` cannot silently desync the mid-pause — `burst_size` is coupled to the
  stop bound, or the precondition is asserted loudly. → Phase 3

### Lifecycle (`lifecycle/identity.py`, `lifecycle/ready_gate.py`)

- [x] **LIFE-01** (H01, high): The process-identity guard matches `python -m <marker>` at the exact
  argv position, so a recycled PID running the marker as a *positional* arg is never signalled, and
  a genuine daemon started with an interpreter flag before `-m` is still detected as running. → Phase 1

- [x] **LIFE-02** (H14, low): `write_pid_atomic` never closes an fd twice, so a failing
  `os.replace` cannot silently close an unrelated descriptor that reused the integer. → Phase 3

- [x] **LIFE-03** (H15, low): The documented non-Linux "degrade to True" behavior holds even when
  the consumer supplies a path-shaped `proc_marker`. → Phase 3

- [x] **LIFE-04** (H18, enhancement): `ReadyGate.run` returns a distinct fatal outcome a consumer
  can branch on directly, instead of forcing consumers to overload the `stop` Event to escape a
  fatal probe result. → Phase 4

### Config reload (`config/reload.py`)

- [x] **CFG-01** (H03, medium): A PHASE-2 reconcile failure fires the `on_rejected` hook before
  re-raising — matching PHASE-1 — so the host's "reload rejected" alert is not silently skipped. → Phase 2

### Discord adapter (`discord/`)

- [x] **DISC-01** (H04, medium): A non-recoverable gateway disconnect does not leave the bot
  permanently dead with no operator signal — either a bounded supervised reconnect or liveness the
  host park-loop can act on. **Open design decision: the retry/backoff contract.** → Phase 2

- [x] **DISC-02** (H05, medium): Re-summoning a panel never leaves two live pinned panels or a
  fresh-but-unpinned panel — delete-then-pin ordering plus per-item handling of `HTTPException` /
  `NotFound`, not just `Forbidden`. → Phase 2

- [x] **DISC-03** (H07, low): `stop()` does not raise `RuntimeError` when the bot loop stops
  between the `is_running()` check and the cross-thread schedule. → Phase 2

- [x] **DISC-04** (H08, low): The `SelectedContext` concurrency contract is explicit about
  re-reading across an `await`, and the hub offers a snapshot-safe way to consume a selection.
  **Scope note: the observed defect's fix site is consumer-side** (`wiring.py` re-reads post-await);
  the hub side is contract + API only. → Phase 2

- [x] **DISC-05** (H11, low): `interaction_check` returns False cleanly when `interaction.user` is
  absent, instead of raising `AttributeError` outside `View.on_error`'s reach. → Phase 3

- [x] **DISC-06** (H12, low): An empty `marker` is rejected at construction, so `is_owned_panel`
  can never claim every bot-authored pinned message and have `summon_panel` delete unrelated pins. → Phase 3

- [x] **SURF-01** (H17, cleanup): `from yahir_reusable_bot.discord import summon_panel` works, or
  the package docstring stops advertising it — docstring, `gateway.__all__`, and the package
  `__init__` agree. → Phase 4

### Command registry (`registry/`)

- [x] **MATCH-01** (H06, medium): A command argument is extracted correctly when the keyword's
  casefold changes length (`ß`→`ss`, `ﬁ`→`fi`) — the arg is sliced from a string consistent with
  the string the prefix test matched. **Lands with MATCH-02.** → Phase 3

- [x] **MATCH-02** (H13, low): `spec.name` is validated at registration so an empty name cannot
  claim blank input, and an uppercase name cannot be permanently unmatchable against casefolded
  input. **Lands with MATCH-01.** → Phase 3

### Scheduler (`scheduler/engine.py`)

- [x] **SCHED-01** (H16, low): `SchedulerEngine.remove` has a stated contract for an already-gone
  job id — either idempotent swallow (symmetric with `register`) or a documented raise. → Phase 3

### Milestone-level

- [x] **GATE-01**: The full suite plus the standing import-hygiene gates (grimp graph +
  isolated-import + AST signature litmus, `tests/test_import_hygiene.py`) stay green across every
  phase — no fix may regress the one-way dependency or the generic-surface litmus.

### Human-gated close-out (NOT executed by the workflow)

Per `ECOSYSTEM.md` §3, these are surfaced for confirmation, never performed autonomously:
`pyproject.toml` version bump `0.1.1 → 0.1.2` · cut tag `v0.1.2` · repin WeatherBot
`[tool.uv.sources]` `v0.1.1 → v0.1.2` + `uv sync --frozen` · after LIFE-04 ships, WeatherBot
de-hacks its separate `fatal` Event at `weatherbot/scheduler/wiring.py:_on_fail` and the
gate-return check in `weatherbot/ops/daemon.py`.

## Milestone v0.2.0 — Redaction promotion + hardening debt (active)

Two tracks in one milestone. **Track A** is the hub's first *promotion* (PC-01, source of record
`.planning/backlog/PROMOTION-CANDIDATES.md`) — generalizing WeatherBot's production-proven
app-local secret redactor into a generic hub mechanism. **Track B** clears every open item the
v0.1.2 audit surfaced (`.planning/v0.1.2-MILESTONE-AUDIT.md`).

Research: `.planning/research/SUMMARY.md` (+ STACK / FEATURES / ARCHITECTURE / PITFALLS).
Verified verdict: **zero new dependencies** — `structlog` (already pinned, resolved 26.1.0) plus
stdlib `re` cover the whole mechanism.

**Test posture unchanged from v0.1.2:** every requirement ships a RED-first regression test that
must fail against pre-fix source before the fix lands.

**PC-01 litmus constraint:** the mechanism is fully generic; only the *pattern* is
consumer-specific and it is always injected, never hardcoded. No domain noun may enter the hub
surface — `redact_secrets(text, patterns)`, never `redact_appid` or an `appid` parameter.

### Redaction mechanism — new `yahir_reusable_bot/redact/` subpackage (Track A)

- [x] **REDACT-01** (PC-01): `redact_secrets(text, patterns) -> str` scrubs every configured
  secret from a rendered string in one pass — idempotent, tolerant of non-`str` input (never
  raises mid-exception-handling), and masks the *value* while preserving surrounding diagnostics
  (endpoint, HTTP status, neighbouring params). → Phase 5

- [x] **REDACT-02** (PC-01): A `RedactionPattern` type plus a stateless registration API —
  patterns compiled once and frozen into an immutable collection, with **zero process-wide
  mutable state**. A module-level singleton consumers mutate at import time is explicitly
  rejected (import-order dependence + cross-test pollution in a library). → Phase 5

- [x] **REDACT-03** (PC-01): A pattern that exceeds a wall-clock budget against adversarial input
  is **rejected at registration time**. Stdlib `re` has no timeout, hub logging is synchronous,
  and the Discord adapter runs an asyncio gateway loop — so a consumer's pathological regex would
  otherwise starve heartbeats and drop the live connection. → Phase 5

- [x] **REDACT-04** (PC-01): A `RedactingWriter` sink wrapper scrubs fully-rendered output —
  event text **and** formatted tracebacks — regardless of processor-chain order or renderer
  choice. **The load-bearing seam:** verified against installed `structlog`, `dev.ConsoleRenderer`
  renders tracebacks straight to the stream bypassing `event_dict`, so a processor alone cannot
  see them. → Phase 6

- [x] **REDACT-05** (PC-01): An optional structlog processor scrubs `event_dict` string values
  pre-render, with its chain-order precondition (must sit after the exception formatters) stated
  loudly in the docstring. Secondary and additive — never the sole backstop. → Phase 6

- [x] **REDACT-06** (PC-01): A literal-value redaction mode blocks an exact secret string wherever
  it appears, catching leak paths that pattern matching misses. → Phase 5

- [x] **REDACT-07** (PC-01): `assert_redaction_active` lets a consumer prove at wiring time that
  the backstop is actually installed — so a backstop silently dropped by a second
  `structlog.configure()` call fails loudly instead of looking identical to a working one. → Phase 6

- [x] **REDACT-08** (PC-01): Redaction-count telemetry exposes how many substitutions fired, so a
  consumer can observe the backstop working rather than assume it. → Phase 6

### Command registry (Track B)

- [ ] **MATCH-03** (v0.1.2 WR-02): A duplicate `spec.name` is rejected at registration, so
  `match_command` can never resolve to a different `CommandSpec` than `by_name` holds. The D-34
  validation loop checks non-empty + already-casefolded but not uniqueness; a duplicate silently
  overwrites in `by_name` while `by_keyword_len_desc` / `render_help` carry both.
  **Consumer-breaking** — needs a WeatherBot sweep at repin. → Phase 7

### Lifecycle (Track B)

- [ ] **LIFE-05** (v0.1.2 Phase 1 WR-01): The identity guard's attached `-mmodule` form behavior
  is resolved — either matched, or documented as a permanent limitation with reasoning.
  **Deliberately deferred once already; needs an explicit human decision at discuss time, not a
  default.** → Phase 7

### Public surface (Track B)

- [ ] **SURF-02** (v0.1.2 Phase 4 IN-02): `on_online`'s annotation is narrowed to
  `Callable[[HealthResult], None]`. **A public hub-surface change — needs an explicit human
  decision at discuss time.** → Phase 7

### Discord adapter (Track B)

- [ ] **DISC-07** (v0.1.2 Phase 2 IN-01): The retry-pin path distinguishes `discord.Forbidden`
  from a generic `HTTPException` in its log, so a permissions failure is not mislabeled as a
  pin-cap failure. **Lands with DISC-08.** → Phase 7

- [ ] **DISC-08** (v0.1.2 Phase 2 IN-02): A failed eviction-delete no longer drops that stray from
  the call's cleanup. **Lands with DISC-07** — both touch `summon_panel`. → Phase 7

### Hygiene (Track B)

- [ ] **HYG-02** (v0.1.2 Phase 4 IN-01): `_best_effort_hook` logs via a structured `label=` kwarg
  instead of an f-string — in both it and the shared site in `config/reload.py`. → Phase 7

- [ ] **HYG-03** (v0.1.2 Phase 2 IN-03): The full suite emits zero warnings — the
  unawaited-coroutine `RuntimeWarning` from the `test_gateway.py` fake client is eliminated. → Phase 7

### Documentation (Track B)

- [ ] **DOCS-02** (audit DOC-DRIFT-01): Every planning artifact naming a consumer de-hack site
  names a path that **exists**. `weatherbot/ops/daemon.py` appears across 11 artifacts; the real
  path is `weatherbot/scheduler/daemon.py`. → Phase 7

- [ ] **DOCS-03** (audit DOC-DRIFT-02): The documented de-hack site set is complete — including
  the *producing* site `weatherbot/ops/selfcheck.py`, without which the consumed outcome is
  unreachable. A deliverable enumerating consumer sites must name the site that produces the
  input, not only those that consume the outcome. → Phase 7

- [x] **DOCS-04** (PC-01): `EXTENSION-GUIDE.md` documents the redaction seam as **SEAM-08**,
  noting its architectural inversion — the hub provides a toolkit the consumer wires into its own
  `structlog.configure()`, rather than a Protocol the hub calls. (Note: `SEAM-02` is absent from
  the guide with no recorded explanation; 08 is the next free number.) → Phase 6

### Milestone-level

- [ ] **GATE-02**: The full suite plus the standing import-hygiene gates (grimp graph +
  isolated-import + AST signature litmus, `tests/test_import_hygiene.py`) stay green across every
  phase, and **every requirement ships a RED-first regression test** that fails against pre-fix
  source. No fix may regress the one-way dependency or the generic-surface litmus.
  → all phases (milestone-standing)

### Human-gated close-out (NOT executed by the workflow)

Per `ECOSYSTEM.md` §3, surfaced for confirmation, never performed autonomously:

1. `pyproject.toml` version bump `0.1.2 → 0.2.0` · cut tag `v0.2.0`.
2. Repin WeatherBot `[tool.uv.sources]` `v0.1.2 → v0.2.0` + `uv lock --upgrade` + `uv sync`.
3. **Prove parity before deleting anything:** run WeatherBot's existing, *unmodified*
   `tests/test_redact_hygiene.py` (6 tests) against the hub-backed replacement. All assertions
   must pass unchanged. Only then delete the app-local `weatherbot/_redact.py` in favour of the
   hub import.

4. **Sweep WeatherBot for duplicate `spec.name` values** — MATCH-03 turns a previously-silent
   overwrite into a `ValueError` at registration.

5. **Permanently out of PC-01 scope:** `weatherbot/weather/client.py`'s domain-specific redacted
   re-raise stays app-local forever — it is domain logic, not a generic backstop.

### Out of milestone (deliberately parked)

- **EXT-01** (durable `JobStore`) and **EXT-02** (second `Channel` adapter) — deferred *by design*
  under build-in-consumer-then-promote (rule of three). No consumer needs either today; building
  them now would mean designing against imagined requirements.

### Traceability

Phase numbering **continues from v0.1.2** (which ended at Phase 4). See `.planning/ROADMAP.md`.

| Requirement | Track | Phase | Status |
|-------------|-------|-------|--------|
| REDACT-01 | A (PC-01) | Phase 5 | Complete (2026-07-29) |
| REDACT-02 | A (PC-01) | Phase 5 | Complete (2026-07-29) |
| REDACT-03 | A (PC-01) | Phase 5 | Complete (2026-07-29) |
| REDACT-06 | A (PC-01) | Phase 5 | Complete (2026-07-29) |
| REDACT-04 | A (PC-01) | Phase 6 | Pending |
| REDACT-05 | A (PC-01) | Phase 6 | Pending |
| REDACT-07 | A (PC-01) | Phase 6 | Pending |
| REDACT-08 | A (PC-01) | Phase 6 | Pending |
| DOCS-04 | A (PC-01) | Phase 6 | Pending |
| MATCH-03 | B (debt) | Phase 7 | Pending |
| LIFE-05 | B (debt) | Phase 7 | Pending |
| SURF-02 | B (debt) | Phase 7 | Pending |
| DISC-07 | B (debt) | Phase 7 | Pending |
| DISC-08 | B (debt) | Phase 7 | Pending |
| HYG-02 | B (debt) | Phase 7 | Pending |
| HYG-03 | B (debt) | Phase 7 | Pending |
| DOCS-02 | B (debt) | Phase 7 | Pending |
| DOCS-03 | B (debt) | Phase 7 | Pending |
| GATE-02 | milestone | all phases (standing) | Pending |

**Coverage: 19/19 mapped — 18 phase-assigned + 1 milestone-standing. No orphans, no duplicates.**

GATE-02 is deliberately *not* a phase — same treatment GATE-01 received in v0.1.2. It stays
unchecked until green across all three phases.

## Future / Deferred Extension Points (designed in v2.0, built later)

Per build-in-consumer-then-promote / rule of three. See `EXTENSION-GUIDE.md`.

| ID | Extension point | Seam | Rationale |
|----|-----------------|------|-----------|
| EXT-01 | **Durable `JobStore` implementation + serialization contract** | SEAM-03 | Highest-value deferred entry. The serialization contract (importable callback, picklable identity-style args, per-fire keyword re-resolution) + the durable-store boundary (relocate non-picklable runtime handles into a process-level registry resolved by id at fire time) are **documented, not built**. v2.0 ships only `MemoryJobStore`. Build in a consumer that needs persistence, then promote. |
| EXT-02 | **Second `Channel` adapter** (Telegram / SMS / Slack) | SEAM-01 | One delivery adapter ships (Discord). The seam is built; a second adapter is designed-but-deferred. Implement `send(text) -> DeliveryResult` and wire at the host composition root — no module change. |

### Out of scope

- Publishing `yahir-reusable-bot` to PyPI / a private index (the git dependency is the v2.0
  distribution mechanism).

- Slash-command / non-text adapters; weather-pattern analysis (WeatherBot-app concerns).
