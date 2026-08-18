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
| `RedactingWriter` / `redaction_processor` | SEAM-08 (P06) | **implemented** | the rendered-text sink, its redaction counter, the wiring self-check, and the optional event-mapping processor | a safe pattern-builder helper, per-pattern replacement beyond the template mechanism and partial masking, config-driven pattern loading, a chain-builder helper for processor ordering, and an unwrap convention for a consumer proxy nested around the writer |

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

**Launch-form constraint on the process-identity guard (D-61):** the identity guard
recognizes a daemon launched as `python -m yourmodule` and its attached twin
`python -myourmodule`, but it deliberately does NOT recognize the bundled short-option
group form, where `-m` is fused onto a preceding single-letter flag (`python -Omyourmodule`,
`python -Imyourmodule`). **Do not launch your daemon that way** — the guard will report a
live daemon as not-running. This is a permanent, deliberate limitation, not an unfixed bug:
the guard's two failure directions are asymmetric. A false negative (this case) merely
reports a live daemon as dead — annoying, but recoverable. A false positive delivers SIGHUP
— whose default disposition is *terminate* — to an unrelated, recycled PID. Partially
reconstructing CPython's short-option-bundling grammar to decode the bundled form risks
exactly that trade in the wrong direction, so the boundary stays where it is. See
`_argv_matches_marker`'s docstring in `yahir_reusable_bot/lifecycle/identity.py` for the
full argument.

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

## 7. Secret redaction — insertion seams into a consumer's own logging (SEAM-08, implemented)

**Source:** `yahir_reusable_bot/redact/` (`core.py`, `registry.py`, `sink.py`, `verify.py`,
`processor.py`, `__init__.py`)

Every other seam in this guide is the host implementing a Protocol the module calls. SEAM-08
**inverts** that shape: the module supplies callable mechanism — `RedactingWriter`,
`assert_redaction_active`, `REDACTION_PROCESSOR_MARKER`, `redaction_processor` — plus a
registration entry point (`register_patterns`, Phase 5), and the HOST wires that mechanism into
its OWN `structlog.configure()` call. There is no redaction Protocol here and none to go looking
for — this is the single most useful sentence in this section for a future reader.

**What the module owns versus what the host injects.** The module owns the pattern-pair type and
its literal mode (`RedactionPattern`, Phase 5), the substitution loop (`redact_secrets`), the
vetting registration call (`register_patterns`), the sink (`RedactingWriter`), its redaction
counter, the wiring self-check (`assert_redaction_active`), and the optional processor
(`redaction_processor`). The host owns every pattern's CONTENT (what a secret shape looks like),
the decision to wire redaction at all, the wiring itself, and the disablement value. The module
hardcodes no pattern and never configures logging on its own initiative — it never calls
`structlog.configure()` and never assigns to `sys.stderr` by itself.

**Recipe 1 — required.** Pass `RedactingWriter` as the render target of the host's own logger
factory, in the host's own composition root:

```python
import sys
import structlog
from yahir_reusable_bot.redact import RedactingWriter

structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(
        file=RedactingWriter(sys.stderr, patterns)
    ),
)
```

**Recipe 2 — optional, broader.** The host assigns `RedactingWriter` over the process's own
`sys.stderr` in its own composition root:

```python
sys.stderr = RedactingWriter(sys.stderr, patterns)
```

This additionally covers stdlib `logging` records, bare `print()` calls, and third-party library
output the structlog-only recipe never sees. The ordering constraint is a hard requirement, not a
tip: this assignment must happen **before any** stdlib `logging` handler is constructed, because a
handler resolves its stream at construction time — an already-bound handler keeps writing to the
original stream even after the swap. The module never performs this assignment itself; the host's
own visible line of code does, which is what keeps a security-relevant process-wide mutation
auditable.

**Proving it is on.** `assert_redaction_active(*, deep=False)` raises rather than returns a status
— call it once at boot AND again after any reconfiguration, because `structlog`'s configuration is
global mutable state and a second `structlog.configure()` call can drop the wiring with no error of
its own. The opt-in `deep=True` option proves the scrub code path executes against a non-secret
probe entirely in memory, and catches an empty pattern set and a disabled writer; it does NOT prove
that any particular secret shape is covered, and it deliberately does not require a canary pattern.

**The optional processor.** `redaction_processor(patterns)` is additive defense-in-depth for
field-level `event_dict` scrubbing before serialization. It has a chain-order precondition — place
it after the exception formatters (`structlog.processors.format_exc_info` /
`structlog.processors.dict_tracebacks`) in the processors chain, or it never sees traceback text —
and, stated at least as prominently as its benefit: it is **NOT** a substitute for the sink, because
some renderers (`structlog.dev.ConsoleRenderer`) format exception output directly into their own
output buffer regardless of where the processor sits in the chain. The self-check warns, never
raises, about ordering; a host's own hand-written redaction processor can opt into that same check
by setting `REDACTION_PROCESSOR_MARKER` truthy on its own callable.

**Telemetry, described accurately.** `RedactingWriter.redaction_count` is readable off the live
writer instance, and an optional `on_redaction` push hook can be supplied at construction. It
counts **changed writes**, not individual substitutions, and is monotonic for process lifetime — a
rate is obtained by diffing two point-in-time reads, never by treating it as a per-substitution
total.

**When a pattern is malformed.** `register_patterns` vets every pattern at registration; a
hand-built, unregistered `RedactionPattern` sits outside that contract, and its substitution can
raise. When it does, the writer fails closed: it withholds the original payload and forwards a
fixed, non-secret, self-describing placeholder in its place. It does NOT forward the original — an
unproven payload might carry the very secret redaction exists to catch — and it does NOT raise,
because an exception inside a logging call would break the caller and can mask the very error being
logged. The optional `on_error` hook, supplied at construction alongside `on_redaction`, fires once
the placeholder has already reached the target, receiving only the caught error: it deliberately
does not receive the withheld payload, and `redaction_count` does not move on this path, because no
substitution occurred — only a withholding. Wire the hook if a silently-withheld log line would
matter, and prefer `register_patterns` over hand-building a `RedactionPattern`, which is what keeps
this branch unreachable in the first place.

**Known limitations.**

- The self-check cannot see a writer nested inside the host's own proxy and will raise — wrap the
  stream with `RedactingWriter` FIRST, then wrap that in any additional proxy.
- The self-check reads a private attribute of the logging library's shipped factories, and the
  dependency is pinned with a lower bound only — a future release can break it; it fails loudly
  with a distinct message naming the installed version rather than silently passing.
- Recipe 2 is a Python-level stream proxy and therefore cannot intercept a write made through the
  stream's raw byte buffer or a direct file-descriptor write.
- A `name=value`-shaped pattern whose value boundary excludes a quote or backslash can under-redact
  a secret whose own value contains one of those characters inside already-escaped text —
  literal-value mode (`RedactionPattern.literal`) matches verbatim and sidesteps it.

**Implemented:** `RedactingWriter` (rendered-text sink, both recipes, redaction counter,
`probe_redaction_path`), `assert_redaction_active` (wiring proof, opt-in deep check, ordering
warning), `redaction_processor` (optional event-mapping scrub). **Deferred:** a safe
pattern-builder helper, per-pattern replacement beyond the template mechanism and partial masking,
config-driven pattern loading, a chain-builder helper for processor ordering, and an unwrap
convention for a consumer proxy nested around the writer.

---

## How a host wires the module

The host imports the module's generic mechanisms and injects all of its specifics at a single
**composition root** (the only crossing point — a stable, public-name boundary). The host
supplies the concrete `Channel`, the `JobStore` (today `MemoryJobStore`), the config
`validate` / `desired_jobs` hooks, the health-check callback, the command specs, and the panel
`render` function. None of these require subclassing — the ports are structural Protocols.
