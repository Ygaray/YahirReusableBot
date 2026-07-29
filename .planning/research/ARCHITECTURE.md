# Architecture Research: PC-01 Secret-Redaction Backstop Promotion

**Domain:** Internal integration design — promoting a proven consumer mechanism into the hub
**Researched:** 2026-07-29
**Confidence:** HIGH (based on direct read of the hub package tree, `EXTENSION-GUIDE.md`,
`ECOSYSTEM.md`, `tests/test_import_hygiene.py`, and the proven WeatherBot implementation —
no external ecosystem research needed for this question)

## Executive Summary

The hub already depends on `structlog>=26.1.0` and every existing subpackage that logs
(`lifecycle`, `scheduler`, `discord`, `config`, `reliability`) calls `structlog.get_logger(__name__)`
— **none of them call `structlog.configure(...)`**. That configuration call, including which
`logger_factory`/renderer/target stream is used, is 100% consumer composition-root territory
(`weatherbot/__init__.py` and `weatherbot/cli.py`, both calling `structlog.configure(...)`
directly). This is the load-bearing fact for the whole design: **the redaction mechanism must
be a toolkit the consumer wires into its own `structlog.configure()` call, never a hub-owned
configuration.** The hub must not call `structlog.configure()` itself.

The proven WeatherBot design is a single physical choke point — `_LiveStderr.write()` — used by
both of WeatherBot's `structlog.configure` sites, scrubbing the fully rendered text (event +
formatted traceback in one `write()` call) before it reaches `sys.stderr`. That single seam
already satisfies the milestone's stated requirement ("scrubs event fields AND formatted
tracebacks") in production. The recommended hub design generalizes exactly that shape as the
primary, load-bearing piece, and *additionally* offers a structlog processor as an optional,
narrower defense-in-depth layer — both built on one shared `redact_secrets()` core and one
shared pattern-registration API, in a new `redact/` subpackage.

## Q1 — Where does it live? New subpackage `redact/`

**Recommendation: a new top-level subpackage `yahir_reusable_bot/redact/`.** Not `logging/`
(shadows the stdlib module name and, more importantly, the hub does not own logging
*configuration* — see above — so a package named `logging/` would overclaim scope), not
`observability/` (implies metrics/tracing/structured-log-shipping the hub does not have and
should not invent for this milestone), not folded into an existing subpackage (`reliability/`,
`lifecycle/`, `config/` are all semantically unrelated — redaction is neither a retry primitive,
a startup-gate concern, nor config-schema plumbing). It is a narrow, self-contained,
zero-hub-internal-dependency mechanism — exactly the shape of `reliability/` (a flat subpackage
of pure functions/small classes with a re-exporting `__init__.py`), so it should be structured
the same way.

Naming: `redact` mirrors the proven module's own name (`weatherbot/_redact.py`), reads as a
generic noun (passes the litmus trivially — it is not in the forbidden-noun list and names no
domain concept), and is short enough that `yahir_reusable_bot.redact` reads cleanly at the
import site.

### Module tree after promotion

```
yahir_reusable_bot/
├── __init__.py                # unchanged
├── channels/                  # unchanged
├── config/                    # unchanged
├── discord/                   # unchanged
├── lifecycle/                 # unchanged
├── ports/                     # unchanged
├── redact/                    # NEW subpackage
│   ├── __init__.py            # NEW — re-exports the public surface (see below)
│   ├── core.py                # NEW — redact_secrets(text, patterns) -> str; RedactionPattern type
│   ├── registry.py            # NEW — pattern-registration API (register_pattern / registered_patterns)
│   ├── sink.py                # NEW — RedactingWriter: the generalized _LiveStderr choke point
│   └── processor.py           # NEW — redaction_processor: the optional structlog processor
├── registry/                  # unchanged (command registry — unrelated; do not confuse with redact/registry.py)
├── reliability/                # unchanged
└── scheduler/                  # unchanged
```

Everything under `redact/` is **NEW**. No existing file needs modification to add the
subpackage itself (modifications to `EXTENSION-GUIDE.md` and `pyproject.toml`'s version are
separate, covered in Q3 and the milestone's close-out).

Note the deliberate naming collision-avoidance: the hub already has a `registry/` subpackage
(the *command* registry — `spec.py`/`registry.py`/`match.py`/`dispatch.py`, SEAM-06). The new
`redact/registry.py` is a different, much smaller thing (a pattern list) living in a different
package path — no import collision (`yahir_reusable_bot.registry` vs.
`yahir_reusable_bot.redact.registry` are distinct dotted paths), but call it out explicitly in
the roadmap/plan so nobody merges the two registries by analogy-confusion.

## Q2 — Insertion seam: processor vs. sink — recommend BOTH, sink is primary

**Recommendation: ship both, as two composable pieces built on the same core — but they are
not equally load-bearing. The sink wrapper is the piece that structurally satisfies the stated
requirement on its own; the processor is an additive, narrower layer, not a substitute.**

### What each seam can and cannot catch

| | **Processor** (`redact/processor.py`) | **Sink** (`redact/sink.py`) |
|---|---|---|
| **Operates on** | The structured `event_dict` — individual field *values* as Python objects, before the renderer runs | The final rendered *text* (or bytes) — one `write()` call, after the renderer runs |
| **Catches event-field secrets** | Yes — sees `log.warning("fetch failed", url=url_with_key)`'s `url` value directly, can scrub or drop the field surgically | Yes, but only textually — it regex-matches the rendered string; it cannot distinguish "this is the `url` field" from prose, it just sees characters |
| **Catches formatted tracebacks** | **Conditional.** Only if placed in the chain *after* `structlog.processors.format_exc_info` (or `dict_tracebacks`) has already turned `exc_info` into a string field. If the renderer itself formats the traceback (e.g. some `ConsoleRenderer` configurations format exceptions internally, not via a prior processor), a processor **never sees that text at all** — it only ever saw the raw `exc_info` tuple, which by then has already been consumed by the renderer | **Unconditional.** The renderer has already turned everything — event message, fields, and any formatted traceback — into one string before it reaches `write()`. The sink sees the literal final text regardless of which processor or renderer produced it |
| **Catches secrets from non-structlog sources sharing the same stream** | No. If stdlib `logging`, a third-party library, or a bare `print()` writes to the same physical stream, a structlog processor never runs on that path | **Yes** — if the consumer routes that stream through the same wrapped target, the sink catches it too (this is exactly why WeatherBot's `_LiveStderr` is described as "the single, renderer-agnostic choke point") |
| **Depends on processor-chain ordering** | Yes — fragile. A later reorder of the chain (e.g. someone moves `format_exc_info` after the redaction processor, or swaps renderers) can silently stop catching tracebacks with zero visible failure | No — structurally independent of chain order and renderer choice by construction |
| **Precision** | Higher — can act on a named field (e.g. drop a `token` key entirely rather than leaving `***` inline), can be selective per field name | Lower — pure text pattern-matching; can only replace matched substrings, never "notices" a field boundary |
| **Reusable across a renderer swap** | Yes, structlog-internal, renderer-agnostic *within* structlog | Yes, and *also* agnostic to whether structlog is even the thing producing the write |

**Why the sink wins as the primary/required piece:** the milestone's explicit requirement is to
scrub "event fields AND formatted tracebacks," and the promotion candidate doc frames the
mechanism as "independent of the structlog processor chain." The processor's traceback coverage
is conditional on chain order and renderer internals that this codebase does not control (the
consumer's, or a future consumer's, structlog configuration) — that conditionality is exactly
the kind of footgun this hub's litmus-and-gate culture (see `test_import_hygiene.py`'s own
self-proof pattern: "a guard is only trustworthy if a deliberately-injected violation is PROVEN
to trip it") would flag as unacceptable for a security backstop. The sink has no such condition:
it is proven in production today, in exactly this shape, catching both requirements at once with
one `write()`.

**Recommended contract for each:**

- `redact.sink.RedactingWriter(target)` — a thin file-like decorator. Wraps *any* object with
  `.write()`/`.flush()` (not `sys.stderr` specifically — WeatherBot's `_LiveStderr` lazy-stream-
  resolution trick for `pytest capsys` compatibility is a **separate, orthogonal, still
  consumer-owned concern**; the hub sink should not presume `sys.stderr` at all). `write(data)`
  decodes `bytes` defensively (mirrors WR-02's tolerant-non-str handling already proven in
  `_LiveStderr`), calls `redact_secrets(data, registered_patterns())`, then forwards to
  `target.write(...)`. WeatherBot would compose it as
  `RedactingWriter(_LiveStderr())` — keeping its own capsys-safe stream-resolution proxy
  underneath the hub's generic redaction layer.
- `redact.processor.redaction_processor(logger, method_name, event_dict) -> event_dict` — the
  standard structlog processor signature. Walks the string-valued entries of `event_dict`
  (including an already-formatted `exception`/`exc_info` string field, if present at the point
  it runs) and scrubs each through `redact_secrets`. Ship it, document its chain-order caveat
  explicitly in its own docstring (a consumer who wants traceback coverage from the processor
  alone must place it after `format_exc_info`/`dict_tracebacks`), and be explicit in
  `EXTENSION-GUIDE.md` that it is a defense-in-depth *addition*, not a substitute for the sink.

Both pieces are pure additions the consumer opts into by injecting them into its own
`structlog.configure(...)` call (processor: append to the `processors=[...]` list; sink: wrap
the stream passed to `logger_factory=structlog.PrintLoggerFactory(file=...)`). The hub never
calls `structlog.configure` itself — that stays exactly where it is today, at the consumer's
composition root.

## Q3 — Yes, this warrants a new SEAM number: SEAM-08

`EXTENSION-GUIDE.md`'s table currently documents SEAM-01, 03, 04, 05, 06, 07 (SEAM-02 was
apparently assigned during the original v2.0 extraction phases but never surfaced as a
documented host-facing plug point — it is absent from every planning artifact searched; the
table's numbering is simply non-contiguous). **SEAM-08 is the next unused number** and should be
added as a new row + a new numbered section, following the guide's existing convention exactly
(a `**Source:**` line, an implemented/deferred split, explicit prose on what ships vs. what's
deferred).

One structural note for whoever writes the doc: SEAM-08 is architecturally **inverted** relative
to every other seam in the guide. SEAM-01/03/05/06/07 are all "the host implements a Protocol
the hub calls" (a `Channel`, a `JobStore`, a health callback, `CommandSpec`s, a `render`
function). SEAM-08 is "the hub provides callable mechanism + registration API that the host
calls into its own configuration" — closer in shape to SEAM-04 (config-schema hooks) than to a
Protocol-based port. Call this out explicitly in the new section so a future reader does not go
looking for a `Redactor` Protocol that doesn't exist.

**Suggested table row:**

| Plug point | Seam | Status | What ships today | Deferred |
|------------|------|--------|-------------------|----------|
| Secret redaction (`redact_secrets` core + pattern registry + sink/processor) | SEAM-08 (v0.2.0) | **implemented** (once this milestone lands) | `redact_secrets(text, patterns)`, a pattern-registration API, a `RedactingWriter` sink wrapper, and an optional `redaction_processor` | Config-driven pattern *sourcing* (e.g. loading patterns from a file/env) is host policy, not the hub's concern — out of scope |

**Suggested section shape (7. `redact` — secret-redaction backstop, SEAM-08):**

```markdown
## 7. `redact` — secret-redaction backstop (SEAM-08, implemented)

**Source:** `yahir_reusable_bot/redact/` (`core.py`, `registry.py`, `sink.py`, `processor.py`)

Unlike every other seam above, this is not a Protocol the host implements — it is a toolkit
the host wires into its OWN `structlog.configure(...)` call (the hub never calls
`structlog.configure` itself; see `ECOSYSTEM.md` — configuration stays host policy). The host
registers its own regex patterns (e.g. `appid=<key>`) via the registration API — no pattern is
hardcoded in the hub — then plugs the sink wrapper around its logger_factory's file target
and/or adds the processor to its own processor chain.

- **Implemented:** `redact_secrets(text, patterns) -> str` core; `register_pattern` /
  `registered_patterns()`; `RedactingWriter` (wraps any file-like write target — renderer- and
  stream-agnostic, catches fully-rendered text including formatted tracebacks); `redaction_processor`
  (structlog processor — catches structured event-dict fields pre-render; traceback coverage is
  chain-order-dependent, document accordingly).
- **Recommended usage:** wrap the sink around the `logger_factory`'s file target as the primary,
  required backstop; add the processor only as an additional layer, never as a substitute.
- **Deferred:** pattern *sourcing* (env/file-driven pattern lists) is host policy, not a hub concern.
```

## Q4 — Import-hygiene impact: no layering change; automatically covered by all three existing gates

Read `tests/test_import_hygiene.py` directly (all four assertions below are traced to specific
code in that file, not assumed):

1. **`test_module_imports_zero_app_code`** (Gate 1, grimp graph) — builds
   `grimp.build_graph(MODULE, cache_dir=None)` and filters
   `module == MODULE or module.startswith(MODULE + ".")`. `yahir_reusable_bot.redact.*` is
   **automatically in scope** — no code change to the test is needed. It will pass trivially as
   long as no file under `redact/` declares an import edge to `weatherbot`/`weatherbot.*`, which
   is guaranteed by construction: `redact/` needs only `re`, `dataclasses`/`typing`, and
   (for `processor.py` only) `structlog` — all stdlib or an already-declared hub dependency.

2. **`test_config_module_never_imports_pydantic`** — scoped explicitly to
   `module.startswith(MODULE + ".config")`. `redact/` does not match that prefix; this gate is
   **unaffected**, no action needed.

3. **`test_module_imports_with_app_blocked`** (Gate 2, isolated-import smoke) — walks every
   module via `pkgutil.walk_packages(pkg.__path__, prefix=MODULE + ".")` with a `weatherbot.*`
   import blocked at `sys.meta_path`. `redact/*.py` files are **automatically walked and
   imported** — no code change needed. Passes trivially since nothing in `redact/` imports the
   app namespace.

4. **`test_litmus_clean`** (Gate 3, AST signature litmus) — walks
   `_MODULE_ROOT.rglob("*.py")`, which **automatically includes** every file under `redact/`.
   This is the one gate that needs *design discipline*, not code change: no `def`/`class`/param/
   annotation name under `redact/` may match
   `weather|forecast|location|openweather|\buv\b|briefing` (case-insensitive, signature surface
   only — prose/docstrings are ignored by construction). Concretely: **do not name the public
   function `redact_appid`** (that is WeatherBot's domain-specific name, carried over verbatim it
   would still pass litmus since `appid` isn't in the forbidden list — but it is the wrong,
   consumer-shaped name for a generic hub function). Use `redact_secrets(text, patterns)` per
   the milestone's own stated shape. Avoid parameter names like `appid` in any signature; use
   `pattern`/`patterns`/`text`/`target` — all already litmus-clean and semantically correct for
   a generic mechanism.

   Note the file also asserts specific filenames are present in the scanned tree as a
   **coverage-gap self-check** for `lifecycle/`, `registry/`, and `discord/` (e.g.
   `assert {"ready_gate.py", ...} <= scanned`). This is a defensive pattern the codebase already
   uses to guarantee a future refactor can't silently drop a package from litmus coverage. It is
   not required for `redact/` (the `rglob("*.py")` scan already covers it unconditionally), but
   adding a matching assertion (`assert {"core.py", "registry.py", "sink.py", "processor.py"} <=
   redact_scanned`) would be consistent with the codebase's own diligence and is a cheap,
   worthwhile addition when this lands.

**Net conclusion: zero grimp layering-graph changes required.** `redact/` is a pure leaf
subpackage — it should import nothing from any other `yahir_reusable_bot.*` subpackage (no
architectural need to; it has zero dependency on `channels`, `registry`, `discord`, `config`,
`lifecycle`, `scheduler`, `ports`, or `reliability`). No existing module needs a new import edge
either — the consumer wires `redact/` in at its own composition root, exactly like every other
seam. **May import:** stdlib (`re`, `dataclasses` or `typing`, `collections.abc`) freely, plus
`structlog` (already an exact-version-unpinned `>=26.1.0` hub dependency) — but only inside
`processor.py`, since `structlog`'s processor calling convention is the only piece that actually
needs the library; `core.py`, `registry.py`, and `sink.py` can and should stay structlog-agnostic
(the sink wraps *any* file-like target, not specifically a structlog-configured one — this is
what makes it "renderer-agnostic" per the promotion candidate's own framing). **May not import:**
`weatherbot`/`weatherbot.*` (obviously — the standing gate), and, as an architectural
recommendation rather than a hard gate, should not import any sibling `yahir_reusable_bot`
subpackage — keeping it a leaf avoids ever becoming a hidden layering dependency for something
that is conceptually a cross-cutting utility.

## Q5 — Data flow: where a secret enters, and exactly where redaction intercepts it

### Today, in WeatherBot (the proven design being generalized)

```
1. weatherbot/weather/client.py builds an OpenWeather request URL containing appid=<key>
2. httpx.raise_for_status() raises with the URL (incl. appid=<key>) embedded in its message
     │
     ├── SOURCE-LEVEL FIX (D-01, primary control):
     │   client.py calls redact_appid(...) on the constructed message BEFORE it's ever
     │   raised/logged — this is the "primary control," entirely consumer-owned, out of
     │   the hub's scope (it's WHERE a secret is used, not a generic logging concern)
     │
3. weatherbot code calls log = structlog.get_logger(__name__); log.warning(event, **fields)
     (or an uncaught exception propagates with exc_info=True)
4. structlog's bound logger runs the configured processor chain
     (timestamp stamping, exc_info formatting, etc. — whatever WeatherBot configured)
5. The final processor (the renderer bound to PrintLoggerFactory) renders event + fields +
   any formatted traceback into ONE text blob
6. structlog.PrintLoggerFactory(file=_LiveStderr()) calls _LiveStderr().write(rendered_text)
     │
     └── BACKSTOP INTERCEPT (D-02, belt-and-suspenders):
         _LiveStderr.write() calls redact_appid(data) on the FULLY RENDERED text —
         event fields AND formatted traceback are in this one string — THEN forwards
         the scrubbed result to the real sys.stderr.write(...)
7. Scrubbed text reaches the terminal / systemd journal / log file
```

### After PC-01 lands (the generalized hub design)

```
1. Consumer's own domain code builds a request/response/exception that may embed a secret
     │
     ├── SOURCE-LEVEL FIX — still entirely consumer-owned; the hub does not (and should not)
     │   reach into where a consumer constructs its own strings. Out of hub scope, same as today.
     │
2. Consumer calls log = structlog.get_logger(__name__); log.warning(event, **fields)
     (or exc_info=True propagates an exception)
3. structlog runs the consumer's OWN processor chain
     │
     ├── OPTIONAL INTERCEPT #1 — redact.processor.redaction_processor, IF the consumer added
     │   it to processors=[...]: scrubs string-valued event_dict fields here, operating on
     │   individual field VALUES before the renderer runs. Catches a formatted traceback only
     │   if placed after format_exc_info/dict_tracebacks in the SAME chain (chain-order caveat)
     │
4. The renderer (whichever the consumer chose) renders event + fields + traceback into ONE
   text blob — same physically-fused shape as WeatherBot today
5. structlog.PrintLoggerFactory(file=<consumer's wrapped stream>) calls .write(rendered_text)
     │
     └── REQUIRED INTERCEPT #2 — redact.sink.RedactingWriter, wrapping whatever stream the
         consumer's PrintLoggerFactory targets: intercepts the FULLY RENDERED text — event
         fields AND formatted traceback are guaranteed to be in this one string, regardless
         of which processor/renderer produced it — scrubs it via redact_secrets(text,
         registered_patterns()), THEN forwards to the real underlying stream
6. Scrubbed text reaches wherever the consumer's stream ultimately writes
```

**The one non-negotiable intercept point is step 5/#2 (the sink)** — it is the only point in the
flow guaranteed, by construction, to see the same fused event+traceback text WeatherBot's proven
backstop already redacts today. The processor at step 3/#1 is a genuine, valuable *additional*
intercept — earlier, more surgical, field-aware — but its traceback coverage is conditional, so
it must never be the *only* seam wired in if the requirement includes tracebacks.

## Q6 — Suggested build order

Dependency chain, closest-to-furthest from the pure core outward:

1. **`redact/core.py`** — `redact_secrets(text, patterns) -> str` + the `RedactionPattern` type
   (a small dataclass/NamedTuple pairing a compiled `re.Pattern` with its replacement template,
   mirroring the proven `_APPID_RX.sub(r"\1***", text)` capture-group-preserving shape). Zero
   dependencies on anything else in this milestone — pure function, exhaustively unit-testable
   in isolation, RED-first per this repo's standing test posture. **Build and prove this first**
   — everything else is a thin wrapper around it.
2. **`redact/registry.py`** — the pattern-registration API (`register_pattern`,
   `registered_patterns()`). Depends only on (1)'s pattern type. Build second — it's the
   injection surface both seams below will call into, and it needs to exist (and be tested for
   the obvious footguns — duplicate registration, thread-safety-if-relevant) before either seam
   consumes it.
3. **`redact/sink.py`** — `RedactingWriter`, wrapping any file-like target. Depends on (1) + (2).
   **Build this before the processor.** It is the piece that alone satisfies the milestone's
   hard requirement (event fields *and* formatted tracebacks); proving it first means the
   requirement is met even if scope pressure later trims the processor.
4. **`redact/processor.py`** — `redaction_processor`, the structlog processor. Depends on (1) +
   (2). Independent of (3) — can be built in parallel with it, or after, but should not be built
   *before* the sink given the risk-ordering above.
5. **`redact/__init__.py`** — re-export the public surface once (1)–(4) exist:
   `redact_secrets`, `RedactionPattern`, `register_pattern`, `registered_patterns`,
   `RedactingWriter`, `redaction_processor`.
6. **Import-hygiene / litmus gates** — re-run the existing suite (auto-covers the new
   subpackage per Q4); optionally add the coverage-gap self-check assertion for `redact/`
   filenames matching the existing `lifecycle`/`registry`/`discord` pattern in
   `test_litmus_clean`.
7. **`EXTENSION-GUIDE.md`** — add the SEAM-08 table row + section (Q3 shape above). Documentation
   for a promoted mechanism is itself part of "done" per this repo's own promotion recipe
   (`ECOSYSTEM.md` §6, step 2: "document it in `EXTENSION-GUIDE.md`; flip its row to
   implemented").
8. **GATE-01** — full suite + import-hygiene/litmus/grimp green, per this milestone's standing
   test posture.
9. **[human-gated, out of the autonomous build]** — per `ECOSYSTEM.md` §3 and this milestone's
   own framing: bump `pyproject.toml` `0.1.2 → 0.2.0`, cut the `v0.2.0` tag, repin WeatherBot
   (`[tool.uv.sources]` → `uv lock --upgrade-package yahir-reusable-bot` → `uv sync --frozen`),
   then in WeatherBot: delete `weatherbot/_redact.py` and the redaction logic inside
   `_LiveStderr`, wire both `structlog.configure(...)` sites
   (`weatherbot/__init__.py`, `weatherbot/cli.py`) to
   `structlog.PrintLoggerFactory(file=RedactingWriter(_LiveStderr()))` (keeping WeatherBot's own
   lazy-`sys.stderr` capsys-safe proxy underneath the hub's generic redaction layer, per the Q2
   sink contract), and register the `appid=<key>` pattern via `redact.register_pattern(...)` at
   WeatherBot's own composition root.

Steps 1–8 are entirely autonomous within this milestone's stated authority (`ECOSYSTEM.md` §3:
"read/edit the hub source, add/adjust its tests, run the hub's own suite + the litmus gate ...
Fix it, prove it, keep it litmus-clean"). Step 9 is explicitly surfaced for human confirmation,
matching how this milestone's own `PROJECT.md` already frames close-out.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Hub calling `structlog.configure()`

**What people might do:** since the hub already depends on `structlog`, it would be tempting to
have the hub provide a one-call `setup_logging(...)` convenience that calls
`structlog.configure(...)` on the consumer's behalf.
**Why it's wrong:** every existing hub module currently only calls `structlog.get_logger(...)`;
configuration is 100% consumer composition-root policy today (two independent
`structlog.configure` sites in WeatherBot, tuned differently per entry path — see
`_configure_logging(level)` in `cli.py`). A hub-owned `configure()` call would silently override
consumer-specific tuning (verbosity flags, per-subcommand levels) the very first time a second
consumer's needs diverged from WeatherBot's — precisely the "designing a generic abstraction
against a single imagined consumer" trap `ECOSYSTEM.md` §6 warns against.
**Do this instead:** ship only composable pieces (`redact_secrets`, the registry, the sink class,
the processor function) that the consumer plugs into its own `structlog.configure(...)` call.

### Anti-Pattern 2: Shipping only the processor because it "feels more idiomatic structlog"

**What people might do:** structlog's own docs favor the processor-chain pattern, so it's
tempting to treat the processor as the canonical seam and the sink as a legacy compatibility
shim.
**Why it's wrong:** as detailed in Q2, the processor's traceback coverage is conditional on
chain order and renderer internals outside this repo's control. Treating it as sufficient alone
would silently regress the exact requirement (formatted-traceback scrubbing) that motivated this
promotion in the first place — with no test able to catch the regression short of a live
traceback-emitting integration test per consumer chain configuration.
**Do this instead:** treat the sink as the required, load-bearing piece; the processor as
optional, additive, explicitly documented as chain-order-sensitive.

## Sources

- `/home/yahir/Projects/Reusable/YahirReusableBot/.planning/PROJECT.md` (milestone framing, PC-01 shape)
- `/home/yahir/Projects/Reusable/YahirReusableBot/.planning/backlog/PROMOTION-CANDIDATES.md` (PC-01 origin, litmus, when-actioned sequence)
- `/home/yahir/Projects/Reusable/YahirReusableBot/EXTENSION-GUIDE.md` (seam documentation conventions, SEAM-01..07)
- `/home/yahir/Projects/Reusable/YahirReusableBot/ECOSYSTEM.md` (jurisdiction, promotion recipe, human-gating rules)
- `/home/yahir/Projects/Reusable/YahirReusableBot/tests/test_import_hygiene.py` (all three gates read directly, line-by-line)
- `/home/yahir/Projects/Reusable/YahirReusableBot/yahir_reusable_bot/__init__.py`, `reliability/`, `ports/__init__.py` (existing subpackage shape/conventions, confirmed no `structlog.configure` call anywhere in the hub)
- `/home/yahir/Projects/Reusable/YahirReusableBot/pyproject.toml` (confirms `structlog>=26.1.0` is already a hub dependency)
- `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` (the proven `redact_appid` core being generalized)
- `/home/yahir/Projects/WeatherBot/weatherbot/__init__.py`, `weatherbot/cli.py` (the two `structlog.configure` sites and the `_LiveStderr` sink choke point being generalized)
- `/home/yahir/Projects/Reusable/YahirReusableBot/.planning/v0.1.2-MILESTONE-AUDIT.md` (confirms no open items conflict with this design; confirms the milestone's own framing of human-gated close-out)

---
*Architecture research for: PC-01 secret-redaction backstop promotion*
*Researched: 2026-07-29*
