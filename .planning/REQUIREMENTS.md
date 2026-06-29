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
