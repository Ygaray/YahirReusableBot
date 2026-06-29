# YahirReusableBot

**YahirReusableBot** is the reusable, app-agnostic bot core extracted from WeatherBot
(v2.0 "Bot Module Extraction" milestone). It is the clean module future bots import:
channel-agnostic delivery, retry/backoff reliability primitives, an in-process scheduler
engine, a generic command registry + dispatcher, a Discord adapter (gateway + panel kit +
selection), lifecycle/READY-gate plumbing, and host-supplied port Protocols.

**Core value:** A new bot starts from a clean, import-hygiene-proven core — channels,
scheduling, reliability, command dispatch, and a Discord adapter — and injects only its own
specifics at one composition root, instead of re-deriving the plumbing each time.

**Import root:** `yahir_reusable_bot` · **PyPI name:** `yahir-reusable-bot` · **No console
script** (library only). Build backend: hatchling. `requires-python >=3.12`.

## Origin

Extracted from `WeatherBot` over Phases 22–27 (in-place seam un-braiding), then physically
split into this standalone repo in Phase 28 (fresh `git init`, single clean import commit
tagged `v0.1.0`). The full extraction history lives durably in the WeatherBot repo. WeatherBot
is the first consumer, depending on this module via a uv git dependency tag-pinned for deploy.

## Distribution

The v2.0 distribution mechanism is a **uv git dependency** (`[tool.uv.sources]` git pin,
tag-pinned for deploy, reproducible `uv.lock`). Publishing to PyPI / a private index is
deferred — revisit only if a second consumer wants versioned releases.

## Constraints

- **One-way dependency:** no module file may import a host app; enforced by the standing
  import-hygiene gates (`tests/test_import_hygiene.py`: grimp graph + isolated-import +
  AST signature litmus).
- **`discord.py==2.7.1` is an EXACT pin** (the live-panel `custom_id` / persistent-view wire
  contract is valid only against the registered version) — never loosen to a range.
- **Generic public surface:** no weather noun in any `def`/`class`/param/annotation name
  (D-13 litmus) — the module reads as a generic bot core.

## Extension Discipline

Designed-but-deferred extension points follow **build-in-consumer-then-promote** (rule of
three): build a concrete impl in a consuming app first, prove it across consumers, then promote
the generalized form into this module. See `EXTENSION-GUIDE.md` and `REQUIREMENTS.md`.
