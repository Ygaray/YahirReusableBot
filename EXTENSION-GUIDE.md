# YahirReusableBot — Extension Guide

`yahir_reusable_bot` is the clean, app-agnostic bot core a host application imports
(import root `yahir_reusable_bot`, PyPI name `yahir-reusable-bot`). Its contract is a
**one-way dependency**: the host may import from the module, but no module file imports
the host. Everything app-specific is **injected** at the host's composition root — the
module assembles nothing of its own.

This guide enumerates every documented plug point (the seams established across the
v2.0 extraction, Phases 22–27), each marked **implemented** or **deferred**. Deferred
points are designed-but-unbuilt: build them in a consumer first, then promote to the
module under the rule of three (build-in-consumer-then-promote).

## Plug-Point Summary

| Plug point | Seam | Status | What ships today | Deferred |
|------------|------|--------|------------------|----------|
| `Channel` | SEAM-01 (P22) | **partial** | one delivery adapter | 2nd adapter (Telegram / SMS / Slack) |
| `JobStore` Protocol | SEAM-03 (P23) | **partial** | in-memory `MemoryJobStore` | **durable impl + serialization contract** (see below) |
| Config-schema extension (`validate` / `desired_jobs`) | SEAM-04 (P24) | **implemented** | injected over the host's schema | — |
| Health-check (READY-gate callback) | SEAM-05 (P25) | **implemented** | host-provided callback | — |
| Command registration (`registry` / `bind`) | SEAM-06 (P26) | **implemented** | host registers specs; CLI / Discord / help derive | — |
| Panel `SelectedContext[I]` | SEAM-07 (P27) | **implemented** | generic holder + injected `render` | — |

---

## 1. `Channel` — delivery surface (SEAM-01, partial)

**Source:** `yahir_reusable_bot/channels/__init__.py`, `channels/base.py`

The channel-agnostic delivery surface: the text-only `Channel` ABC + `DeliveryResult`,
the canonical `send(text) -> DeliveryResult` seam every provider implements. This is a
SUBSET surface by design — the concrete channel implementations and the `build_channel`
factory stay host-side; the host wires them at its composition root.

- **Implemented:** one delivery adapter (the v1 Discord webhook delivery channel, host-side).
- **Deferred:** a **second `Channel` adapter** (Telegram / SMS / Slack). The seam is built;
  no second adapter ships in v2.0. Add one by implementing `send(text) -> DeliveryResult`
  and wiring it at the host composition root — no module change required.

## 2. `JobStore` — the scheduler's job store (SEAM-03, partial)

**Source:** `yahir_reusable_bot/ports/jobstore.py` (the serialization contract is the file's
payload docstring), `ports/__init__.py`

Where a host's scheduled jobs live is HOST policy. The module owns only the *contract* for
what a durable job store would require, plus the trivial in-memory implementation that ships.

- **Implemented:** `MemoryJobStore` — holds each registered job as a live object, never
  serializes. The job set is re-derived from config on each restart, so there is nothing to
  deserialize and no durable-store boundary to cross.
- **Deferred (highest-value extension point):** a **durable `JobStore`** that serializes
  (pickles) each job.

### Durable-`JobStore` serialization contract

A durable backend must satisfy three constraints — all already true of today's jobs, so a
durable backend could be slotted in without changing host registration:

1. **Importable callback.** Every job's callable is a module-level function referenceable by
   import path — never a closure or a bound method on a transient object — so a serializer can
   re-resolve it by reference.
2. **Picklable identity-style positional args.** Positional `args` are plain data (a plain id
   plus plain-data records), never a live client, socket, channel, or threading primitive — so
   the args round-trip through a pickle unchanged.
3. **Per-fire keyword data re-resolved at fire time.** Per-fire keyword data carries a
   holder/registry the job re-reads when it fires, never a baked-in snapshot of mutable state —
   so a later reconfigure changes what an unchanged job does.

**Durable-store boundary (named, not built):** today's jobs additionally thread
**non-picklable runtime handles** through their per-fire keyword data — a live API client, an
open delivery channel, a process stop signal, a config holder. These cannot survive a pickle. A
durable implementation must **relocate these handles out of the job payload into a
process-level registry resolved BY ID at fire time**, leaving only the picklable id in the
stored job. v2.0 ships only the in-memory store, which sidesteps this boundary entirely.

## 3. Config-schema extension — `validate` / `desired_jobs` hooks (SEAM-04, implemented)

**Source:** `yahir_reusable_bot/config/` (`reload.py`, `holder.py`, `__init__.py`)

The config hot-reload seam routes ALL validation through the host's injected concrete
validator — the module never parses/validates the config itself (enforced by the
`test_config_module_never_imports_pydantic` import-hygiene gate). The host injects its
`validate` and `desired_jobs` hooks over its own config schema; the module owns only the
holder + reload plumbing.

## 4. Health-check — READY-gate callback (SEAM-05, implemented)

**Source:** `yahir_reusable_bot/lifecycle/` (`ready_gate.py`, `sdnotify.py`, `health.py`, `identity.py`)

The lifecycle package owns the generic READY gate, the systemd-notify integration, the
generic process-identity guard, and the `HealthResult` type. The host supplies the concrete
health-check callback the READY gate fires once at startup self-check. Generic seam names
(`health` / `ready` / `identity`) are exactly what the module exposes — no host nouns.

## 5. Command registration — `registry` / `bind` (SEAM-06, implemented)

**Source:** `yahir_reusable_bot/registry/` (`spec.py`, `registry.py`, `match.py`, `dispatch.py`, `__init__.py`)

The generic command-registry + dispatcher mechanism. A host registers its own commands into
the generic `CommandSpec` + `DispatchContext`, builds a `CommandRegistry` via `build_registry`,
matches text with the opt-in `match_command`, and dispatches via `dispatch_spec` /
`dispatch_reply`. Every app-specific — command names, handler closures, the flag grammar — is
injected; the module assembles nothing of its own. A different bot registers its own specs into
the same mechanism, and the CLI / Discord / help surfaces all derive from the registry.

## 6. Panel `SelectedContext[I]` — interactive panel state (SEAM-07, implemented)

**Source:** `yahir_reusable_bot/discord/` (`panelkit.py`, `gateway.py`, `selection.py`)

The Discord adapter owns the generic interactive panel mechanism: a generic
`SelectedContext[I]` holder for the current selection, the panel kit, and the gateway. The
host injects its `render` function (the panel's app-specific embed rendering stays host-side
and is injected at the composition root — the render cycle was resolved by **ownership**, not a
deferred import). The `discord.py==2.7.1` pin lives in this module's `pyproject.toml`; the
panel's persistent-view `custom_id` routing contract is valid only against that exact version —
do NOT loosen it.

---

## How a host wires the module

The host imports the module's generic mechanisms and injects all of its specifics at a single
**composition root** (the only crossing point — a stable, public-name boundary). The host
supplies the concrete `Channel`, the `JobStore` (today `MemoryJobStore`), the config
`validate` / `desired_jobs` hooks, the health-check callback, the command specs, and the panel
`render` function. None of these require subclassing — the ports are structural Protocols.
