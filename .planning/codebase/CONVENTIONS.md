# Coding Conventions

**Analysis Date:** 2026-07-08

## Naming Patterns

**Files:**
- Module files: `snake_case.py` (e.g., `gateway.py`, `panelkit.py`, `ready_gate.py`)
- Packages: `snake_case` directories with `__init__.py` (e.g., `yahir_reusable_bot/discord/`, `yahir_reusable_bot/registry/`)

**Functions:**
- Public functions: `snake_case` (e.g., `build_client`, `summon_panel`, `match_command`)
- Private functions: `_snake_case` (e.g., `_dispatch_message`, `_amain`, `_best_effort_hook`)
- Async functions: same convention with `async def` prefix (e.g., `async def summon_panel(...)`)

**Classes:**
- Classes: `PascalCase` (e.g., `BotThread`, `CommandRegistry`, `HealthResult`, `ReadyGate`)
- Private classes: `_PascalCase` (e.g., `_AppBlocker` in tests)

**Type Aliases:**
- Type aliases: `PascalCase` (e.g., `OnMessage`, `OwnedPredicate`, `PanelFactory`, `ItemContributor`)
- Defined at module level for reusability

**Variables:**
- Instance attributes: `_snake_case` for private (e.g., `self._token`, `self._scheduler`, `self._loop`)
- Local variables: `snake_case` (e.g., `stripped`, `folded`, `matches`)
- Loop variables: short but descriptive (e.g., `c` for command spec, `m` for message, `job` for scheduler job)

**Constants:**
- Module-level constants: `UPPERCASE` (e.g., `REQUIRED_PANEL_PERMS`, `RE_PROBE_INTERVAL_S`)
- Discord constants: `_UPPERCASE` when private (e.g., `_MAX_CUSTOM_ID`, `_MAX_LABEL`, `_FETCHING_CUE`, `_ERROR_REPLY`)

**Enums:**
- Enum members: `UPPERCASE` (e.g., `Severity.WARNING`, `Severity.CRITICAL`)

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc` or Ruff format config)
- String quotes: double quotes `"` preferred (observed in all source files)
- Line length: no configured limit (pyproject.toml has no limit setting)
- Indentation: 4 spaces (Python standard)

**Linting:**
- Tool: `ruff` (configured in `pyproject.toml` dependencies)
- Config: default Ruff rules (no custom `[tool.ruff]` in `pyproject.toml`)
- Key pattern: `noqa: BLE001` used to suppress broad `except Exception` warnings when intentional (e.g., in `BotThread._run()` failure isolation, panelkit error handler)
- No `.ruff.toml` or separate config file; all settings via `pyproject.toml`

**Type Hints:**
- Required throughout: all function parameters and return types must have type hints
- Complex types: use `Callable[[Type], ReturnType]`, `Awaitable[Type]`, `Iterable[Type]`
- Optional types: use `Type | None` (requires `from __future__ import annotations`)
- `Any` used for opaque collaborators (e.g., `scheduler: Any`, `cache: Any`, `config: Any`)
- `TYPE_CHECKING` blocks for forward references (e.g., in `panelkit.py` to import `SelectedContext`)

## Import Organization

**Order:**
1. `from __future__ import annotations` (always first)
2. Standard library imports (e.g., `asyncio`, `threading`, `dataclasses`)
3. Third-party imports (e.g., `discord`, `structlog`, `httpx`, `tenacity`)
4. Local/package imports (e.g., `from yahir_reusable_bot.registry.spec import CommandSpec`)

**Style:**
- Group related imports (stdlib together, third-party together)
- Blank line between import groups
- Use `from module import Name` for clarity
- Module-level imports use `__all__` to declare public surface (e.g., in `gateway.py`, `panelkit.py`)
- Avoid wildcard imports (`from module import *`)

**Example:** (`yahir_reusable_bot/discord/gateway.py`)
```python
from __future__ import annotations

import asyncio
import threading
from typing import Awaitable, Callable

import discord
import structlog

__all__ = [
    "BotThread",
    "build_client",
    "summon_panel",
    "REQUIRED_PANEL_PERMS",
]
```

## Error Handling

**Patterns:**
- **Expected failures return Result types** — functions that can fail return a DTO (e.g., `DeliveryResult`, `DispatchOutcome`) instead of raising
  - Example: `Channel.send() -> DeliveryResult` with `ok: bool` and `detail: str`
  - Caller decides whether to retry, alert, or suppress
  
- **Exceptions propagate** — utility functions let exceptions bubble (domain errors not caught at utility layer)
  - Example: `dispatch_spec()` lets `parse_flags`, `cache_suffix`, and `bind` exceptions bubble to caller
  - Comment: `"Exceptions from the injected hooks or the bind closure BUBBLE — never caught here."`

- **Critical failures logged + swallowed (failure isolation)** — for cross-thread/cross-process boundaries
  - Example: `BotThread._run()` catches `LoginFailure` and broad `Exception`, logs at CRITICAL, sets `_failed=True`, never re-raises
  - Reason: prevent dead gateway thread from crashing the host scheduler

- **Best-effort hook pattern** — optional callbacks that fail quietly
  - Example: `ReadyGate.run()` calls `self._best_effort_hook()` which logs + swallows hook exceptions
  - Pattern: `try/except Exception` with log, then continue

- **TOCTOU backstop** — for time-of-check / time-of-use race conditions
  - Example: `summon_panel()` catches `discord.Forbidden` (permission revoked between preflight and write)
  - Behavior: log CRITICAL, return cleanly, never re-raise

- **noqa suppression:**
  - `# noqa: BLE001` — suppresses broad `except Exception` warnings when failure isolation is intentional
  - Used in: `BotThread._run()`, `panelkit.py` error handler, `gateway.py` stop() close handler
  - Never skip the noqa; if using broad except, must justify with this comment

## Logging

**Framework:** `structlog`

**Patterns:**
- Module-level logger: `_log = structlog.get_logger(__name__)` in every module that logs
- Structured logging: `_log.info("event name", field1=value1, field2=value2)`
- Log levels: `info()`, `warning()`, `critical()` (no `debug()` or `error()` in current codebase)
- Sensitive data: never logged (e.g., webhook URLs, tokens, API keys)
  - Example: `channel_id` OK to log, but not the webhook URL

**Examples from codebase:**
```python
_log.info(
    "persistent view registered",
    custom_ids=[getattr(c, "custom_id", None) for c in view.children],
)
_log.critical(
    "invalid Discord token; inbound bot disabled, scheduler unaffected"
)
_log.info("bot online")
```

## Comments

**When to Comment:**
- **Design decisions** — explain WHY the code is written this way, not WHAT it does
  - Example: "Capture the injected app handler BEFORE the @client.event below rebinds the name..."
  - Example: "Create-before-delete (no-orphan ordering): post the fresh panel..."

- **Non-obvious control flow** — explain the reason for branches
  - Example: "Word-boundary guard: anything other than whitespace right after the keyword..."

- **Design document references** — pin to architectural decisions with codes like D-01, SEAM-06, A4
  - Example: "The exact channel permissions a panel summon preflights BEFORE any write (A4 — names Discord permissions, not any app concept)."

- **Invariants and contracts** — document load-bearing assumptions
  - Example: "The persistent-view `custom_id` routing contract is valid only against the exact discord.py version..."

- **Avoid:** Comments that restate what the code obviously does
  - Bad: `i = 0  # Initialize i to 0`
  - Good: `self._failed = False  # Set in the _run except handlers when the thread dies.`

**Docstrings:**
- **Module level:** Always present; explains the relocated code, seam name, and load-bearing invariants
  - Example: `"""The reusable Discord gateway: ``BotThread`` + ``build_client`` + summon orchestration (D-06)..."`
  
- **Class level:** Explains construction, ownership, and key invariants
  - Example: `"""Thin, non-owning registrar over a host-supplied background scheduler..."`

- **Function level:** Explains parameters, return value, and behavior edge cases
  - Example: `"""Gate systemd ``READY=1`` on an injected health-check, re-probing until it passes..."`

- **Docstring style:** Plain text (no specific formatter like Google/Numpy style)
  - Uses backticks for code references: `` `HealthResult` ``
  - Uses colons to introduce sections: `Intents:`, `Persistent-view registration:`, etc.

## Dataclasses

**Pattern:**
- Use `@dataclass(frozen=True)` for immutable DTOs (data transfer objects)
  - Example: `HealthResult`, `DispatchOutcome`, `DeliveryResult`, `CommandSpec`, `DispatchContext`, `ParsedCommand`
  - Frozen prevents accidental mutation: raises `FrozenInstanceError` on mutation attempt

- Default values only on trailing fields
  - Example: `ok: bool` required, `detail: str = ""` optional with default
  - Example: `severity: Severity = Severity.WARNING` optional with enum default

## Function Design

**Size:** No explicit limit; functions range from 1 line (`dispatch_reply`) to ~40 lines (`summon_panel`)

**Parameters:**
- Type hints required on all parameters and return type
- Keyword-only arguments after `*` for optional/configuration parameters
  - Example: `def build_client(*, on_message: OnMessage, view: discord.ui.View) -> discord.Client:`
  - Example: `def register(self, job_id: str, trigger: Any, callback: Callable[..., Any], *, args: Any = None, ...)`
  - Reason: makes call sites explicit and prevents accidental positional argument mistakes

- Default values for optional params
- No *args or **kwargs except for opaque pass-through (marked with `# noqa: ANN001` for parameter type)

**Return Values:**
- Explicit return type hint (including `-> None` for functions with no return)
- Single return per function (no implicit None)
- Use Result types (`DeliveryResult`) for fallible operations, not exceptions

**Async functions:**
- Prefix with `async def`
- Type hint returns `-> Awaitable[Type]` or `async def -> Type`
- Example: `async def summon_panel(...) -> None:` (async function returning nothing when awaited)

## Module Design

**Exports:**
- Public surface declared via `__all__ = [...]` at module level
  - Example: `yahir_reusable_bot/discord/gateway.py`
  ```python
  __all__ = [
      "BotThread",
      "build_client",
      "summon_panel",
      "REQUIRED_PANEL_PERMS",
  ]
  ```

- Underscore prefix (`_`) for private (functions, classes, module-level variables)
  - Example: `_log`, `_dispatch_message`, `_AppBlocker`, `_MAX_CUSTOM_ID`

- No re-exports of third-party names (keep package boundary clean)

**Barrel Files:**
- `__init__.py` files are minimal; define no logic
  - Example: `yahir_reusable_bot/__init__.py` contains only a docstring and `from __future__ import annotations`
  - Package submodules (`registry.registry`, `discord.gateway`) are imported directly, not re-exported

## Special Patterns

**Constructor Injection:**
- Collaborators (scheduler, cache, config) passed as parameters, never module-level singletons
  - Example: `SchedulerEngine(scheduler)` takes the scheduler instance
  - Example: `CommandRegistry(specs)` takes app-supplied specs tuple
  - Reason: keeps module reusable and testable; app controls lifetime

**Opaque Callables:**
- Functions/closures stored as parameters and invoked without inspecting their bodies
  - Example: `callback` in `SchedulerEngine.register(...)` — module never names it, inspects it, or decides its args
  - Reason: app's domain logic stays outside the module
  - Type hint: `Callable[[Type], ReturnType]` for clarity

**Design Document References:**
- Design decisions pinned with codes like `D-01`, `D-02`, `SEAM-06`, `A4`
- These map to external architecture documents (not in this repo)
- Example: `"(D-06)."`, `"(SEAM-05, D-01)"`, `"A4 — names Discord permissions..."`

---

*Convention analysis: 2026-07-08*
