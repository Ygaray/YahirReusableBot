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

## Milestone v0.1.2 — Hub hardening (active)

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

- [ ] **RELY-02** (H09, low): A caller configuring `burst_size == 1` gets a degraded wait rather
  than a `ZeroDivisionError` raised from inside the tenacity wait callable. → Phase 3

- [ ] **RELY-03** (H10, low): A caller pairing standalone `two_burst_wait` with its own
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

- [ ] **LIFE-04** (H18, enhancement): `ReadyGate.run` returns a distinct fatal outcome a consumer
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

- [ ] **DISC-05** (H11, low): `interaction_check` returns False cleanly when `interaction.user` is
  absent, instead of raising `AttributeError` outside `View.on_error`'s reach. → Phase 3

- [ ] **DISC-06** (H12, low): An empty `marker` is rejected at construction, so `is_owned_panel`
  can never claim every bot-authored pinned message and have `summon_panel` delete unrelated pins. → Phase 3

- [ ] **SURF-01** (H17, cleanup): `from yahir_reusable_bot.discord import summon_panel` works, or
  the package docstring stops advertising it — docstring, `gateway.__all__`, and the package
  `__init__` agree. → Phase 4

### Command registry (`registry/`)

- [ ] **MATCH-01** (H06, medium): A command argument is extracted correctly when the keyword's
  casefold changes length (`ß`→`ss`, `ﬁ`→`fi`) — the arg is sliced from a string consistent with
  the string the prefix test matched. **Lands with MATCH-02.** → Phase 3

- [ ] **MATCH-02** (H13, low): `spec.name` is validated at registration so an empty name cannot
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
