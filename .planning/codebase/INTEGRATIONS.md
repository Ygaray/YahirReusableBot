# External Integrations

**Analysis Date:** 2026-07-08

## APIs & External Services

**Discord Gateway:**
- Service: Discord bot gateway (websocket)
  - What it's used for: Inbound message handling, button/select interaction dispatch, panel creation/updates
  - SDK/Client: `discord.py==2.7.1` (exact version, see `yahir_reusable_bot/discord/gateway.py`)
  - Auth: Discord bot token (environment variable, passed by consumer at startup via `BotThread.__init__(token=...)`)
  - Entry: `BotThread` runs the client on its own thread (`yahir_reusable_bot/discord/gateway.py:191-279`)

**HTTP Requests (for consumer integrations):**
- Client: `httpx>=0.28.1`
  - What it's used for: Async HTTP calls with timeout, connection, and read error handling
  - Used by: Retry engine (`yahir_reusable_bot/reliability/retry.py`) for inspecting `HTTPStatusError`, parsing `Retry-After` headers
  - Connection timeouts: Handled via `httpx.TimeoutException`
  - Rate-limiting: Parsed via `Retry-After` header (capped at `RETRY_AFTER_CAP_S = 120s`)

## Data Storage

**Job Store (Scheduler persistence):**
- `MemoryJobStore` (in-memory, shipped in v2.0)
  - Location: `yahir_reusable_bot/ports/jobstore.py:61-72`
  - Persistence: None (in-memory only; job set re-derived from config on restart)
  - Serialization contract: Defined but NOT implemented in v2.0 (deferred, SEAM-03)
    - Constraints: importable callbacks, picklable positional args, per-fire keyword data re-resolved at runtime
    - Durable boundary: Non-picklable runtime handles (API client, delivery channel, stop signal, config holder) must be relocated to process-level registry in durable impl

**Configuration Storage:**
- `ConfigHolder[T]` (generic, in-memory, host-supplied config type)
  - Location: `yahir_reusable_bot/config/holder.py:43-73`
  - Mechanism: Lock-free read via single attribute load (atomic under GIL); locked swap via `replace(new_config)`
  - Refresh: Hot-reload engine polls and validates host's config, then swaps via holder
  - Validation: Injected at host's `ReloadEngine` (module never validates itself; see SEAM-04)

**File Storage:**
- None in the hub itself. Host apps may use:
  - Local filesystem (for config files, sent-log, etc.)
  - Cloud storage via consumer-provided `Channel` adapter

**Caching:**
- None built into the hub. Retry state is held transiently in `Retrying` object via tenacity

## Authentication & Identity

**Auth Provider:**
- Custom token-based
  - Implementation: Discord bot token only (passed as string to `BotThread`)
  - Location: `yahir_reusable_bot/discord/gateway.py:204-230` (BotThread start/stop)
  - Token validation: discord.py raises `discord.LoginFailure` if token is invalid; caught in `BotThread._run()` at `gateway.py:264-268`
  - Failure handling: Login failure is isolated to bot thread (never crashes host); `is_alive()` reports False asynchronously

**Process Identity:**
- systemd (optional)
  - Location: `yahir_reusable_bot/lifecycle/identity.py` (process identity guard), `sdnotify.py` (readiness signaling)
  - Mechanism: `NOTIFY_SOCKET` environment variable (standard sd_notify protocol)
  - Fallback: No-op when not running under systemd

## Monitoring & Observability

**Error Tracking:**
- None built-in. Errors are logged structurally via structlog:
  - Discord gateway: startup/ready logs, connection failures (`gateway.py:112-117`)
  - Retries: attempt logging with burst index, no secrets (`reliability/retry.py:222-232`)
  - Panel summon: permission failures logged with channel_id, never token (`gateway.py:184-187`)

**Logs:**
- Framework: `structlog>=26.1.0` (structured logging)
  - Configuration: No file written by hub; host configures output (stdout, files, etc.)
  - Formats: Events carry typed fields (attempt number, burst index, user identifiers)
  - Security: Never logs secrets (T-04-01 in `reliability/retry.py` docstring)
  - Used by:
    - `yahir_reusable_bot/discord/gateway.py` - Startup, ready, panel operations
    - `yahir_reusable_bot/config/reload.py` - Config reload events
    - `yahir_reusable_bot/lifecycle/ready_gate.py` - Health checks, readiness
    - `yahir_reusable_bot/reliability/retry.py` - Retry attempts

## CI/CD & Deployment

**Hosting:**
- Host-determined (not specified in hub)
  - Current consumer: WeatherBot deploys to `yahir-mint` (systemd service)
  - Mechanism: Hub ships as PyPI package (`yahir-reusable-bot`); consumer installs via uv git pin + tag

**CI Pipeline:**
- GitHub Actions (not present in hub repo)
- Local validation before tag:
  - Tests: `uv run pytest`
  - Lint: `uv run ruff check`
  - Import hygiene: `uv run pytest tests/test_import_hygiene.py` (grimp + AST litmus)

**Deployment Ritual (cross-repo, human-gated):**
- Steps (ECOSYSTEM.md §3, §6):
  1. Fix/test in hub source, verify against consumer via editable overlay (`uv pip install -e /path/to/hub`)
  2. Tag new hub version (semver, immutable)
  3. Consumer: update `[tool.uv.sources]` with new tag, `uv lock --upgrade`, `uv sync`
  4. Consumer: run tests, deploy/restart bot
  - Authority: Autonomous up to tag; tag + repin + deploy = human-gated

## Environment Configuration

**Required env vars:**
- `DISCORD_TOKEN` - Bot token (example; actual name is consumer-determined, passed to `BotThread`)

**Optional env vars:**
- `NOTIFY_SOCKET` - systemd readiness socket path (standard; set by systemd, read by `SystemdNotifier` in `lifecycle/sdnotify.py`)

**Secrets location:**
- Secrets stay behind the restart boundary (host's concern, not hub's)
- The hub's `ConfigHolder[T]` holds app config only; secrets never enter the holder
- `.env` files are consumer-provided; hub never reads them

## Webhooks & Callbacks

**Incoming (Discord):**
- Message events: `on_message` handler injected at `BotThread` composition root (`gateway.py:126-128`)
  - Captured in closure to avoid infinite recursion bug (D-06 in gateway.py docstring)
  - Runs async on bot's event loop
- Interaction events: Persistent-view button/select callbacks
  - Registered via `client.add_view()` in `setup_hook()` (`gateway.py:95-107`)
  - Dispatched by discord.py via `custom_id` static routing (no app import)
- Panel summon endpoint: `summon_panel()` async function (`gateway.py:133-188`)
  - Injected collaborators: channel resolution, idle embed, panel factory, is_owned predicate, callbacks

**Outgoing (consumer-provided):**
- Delivery channel: `Channel.send(text) -> DeliveryResult` (SEAM-01 in EXTENSION-GUIDE.md)
  - Abstract interface defined in `yahir_reusable_bot/channels/base.py`
  - Concrete implementation (Discord webhook, Telegram, etc.) provided by consumer
  - Used by: Scheduler job execution for briefing delivery, alert delivery
- Scheduler callbacks: Host-supplied job functions
  - Trigger: Time-based (cron, interval, date) via APScheduler (host-owned)
  - Callback: Importable module-level function (never closure/bound method)
  - Re-resolved at fire time via per-fire keyword data holder (config, channel, client, stop signal)

## Health Checks

**Mechanism:**
- `ReadyGate` + injected health callback (`lifecycle/ready_gate.py`)
- Fires once at startup after config init
- Host supplies: `Callable[[], Awaitable[HealthResult]]`
- Result: Passes/fails startup; failure prevents bot from marking `ready`
- Return value: `HealthResult` (success/failure + optional details)

**systemd Integration:**
- `SystemdNotifier.ready()` sends `READY=1` to systemd (activating → active)
- Readiness gating: Host fires after health check passes
- Watchdog: `watchdog()` method available (unused in v1; Pitfall 6 deferred)

---

*Integration audit: 2026-07-08*
