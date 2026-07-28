# Technology Stack

**Analysis Date:** 2026-07-08

## Languages

**Primary:**
- Python 3.12+ - Full codebase; async/await extensively used in Discord gateway, retry engine, and scheduler integration

**Secondary:**
- YAML - Configuration and systemd integration via environment variables

## Runtime

**Environment:**
- Python 3.12+ (specified in `pyproject.toml` via `requires-python = ">=3.12"`)

**Execution Model:**
- Async event loop: Primary via `asyncio` for Discord gateway communication
- Multithreading: Used for Discord bot thread isolation (`BotThread` in `yahir_reusable_bot/discord/gateway.py:204-279`)
- Sync/async interop: `asyncio.run_coroutine_threadsafe()` bridges bot's async loop to host's sync code

**Package Manager:**
- uv (0.11.x) - Lockfile: `uv.lock` (present and locked)
- Build backend: `hatchling` (specified in `pyproject.toml`)

## Frameworks

**Core:**
- discord.py 2.7.1 (EXACT PIN) - Bot gateway, intents, persistent-view registration, message handling
  - **Critical:** This is an exact version pin. The persistent-view `custom_id` wire contract (reconnect re-binding of buttons/selects after restart) is valid only against this exact version. See `yahir_reusable_bot/discord/gateway.py:26-27`
  - Intents used: `guilds`, `guild_messages`, `message_content` (privileged)

**Scheduler Integration:**
- APScheduler (host-provided, not a direct dependency) - The module owns only `SchedulerEngine` facade (`yahir_reusable_bot/scheduler/engine.py`), not the scheduler itself
  - The engine bakes three job-options: `misfire_grace_time=None`, `coalesce=True`, `max_instances=1`

**Testing:**
- pytest 9.0.3+ - Test framework and runner
- syrupy 5.3.4+ - Snapshot testing for output assertions

**Build/Dev:**
- ruff 0.15.16+ - Linting and code formatting (runs via `uv run ruff check`)
- grimp 3.14+ - Import-hygiene gate validation (one-way dependency check; runs via `uv run pytest tests/test_import_hygiene.py`)
- time-machine 2.16+ - Time mocking for scheduler/retry testing

## Key Dependencies

**Critical:**
- discord.py 2.7.1 - Exact version; do NOT loosen to range. The persistent-view custom_id routing contract is pinned to this version (D-05 in codebase)
- httpx 0.28.1+ - HTTP client for retries, timeout handling, status-code inspection
  - Used in retry engine (`yahir_reusable_bot/reliability/retry.py`) for `httpx.TimeoutException`, `ConnectError`, `ReadError`, `HTTPStatusError`

**Infrastructure & Logging:**
- structlog 26.1.0+ - Structured logging across gateway, config reload, panel kit
  - Used for: gateway startup diagnostics, retry attempt logging, panel summon operations
  - Never logs secrets (T-04-01 in retry.py)
- tenacity 9.1.4+ - Retry orchestration
  - Powers two-burst retry schedule with interruptible pauses (`yahir_reusable_bot/reliability/retry.py:145-248`)
  - Composes `retry_if_exception`, `retry_if_result`, `stop_after_attempt`

## Configuration

**Environment:**
- Environment-driven: Discord bot token passed at runtime (no .env file committed; host supplies via env var)
- systemd integration: `NOTIFY_SOCKET` env var for readiness signaling (optional; `SystemdNotifier` in `yahir_reusable_bot/lifecycle/sdnotify.py`)
- Configuration hot-reload via `ConfigHolder[T]` generic cell (injected config type at host composition root)

**Build:**
- `pyproject.toml`: Single source of truth for version, deps, build config, test paths
- Lockfile: `uv.lock` - Frozen dependency versions and resolved transitive closure
- Test config: pytest section in `pyproject.toml` specifies `testpaths = ["tests"]`, `pythonpath = ["."]`

## Platform Requirements

**Development:**
- Python 3.12 or higher (enforced by `requires-python` in `pyproject.toml`)
- uv package manager (0.11.x)
- Standard POSIX environment for systemd integration (optional fallback to no-op when not under systemd)

**Production:**
- Python 3.12+ runtime
- Discord bot token (environment variable, passed by consumer at startup)
- (Optional) systemd unit for readiness gating and watchdog integration (via `NOTIFY_SOCKET`)
- No external database or service dependencies in the hub itself (all integrations are host-injected via ports: `Channel`, `JobStore`, config `validate`/`desired_jobs` hooks)

**Deployment Target:**
- Linux/Unix (systemd integration assumes this; gracefully no-ops on non-systemd platforms)
- Host bots typically deploy as systemd services on dedicated hosts (e.g., `yahir-mint` for WeatherBot)

---

*Stack analysis: 2026-07-08*
