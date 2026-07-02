# CLAUDE.md — `yahir_reusable_bot` (the shared hub)

You are working in the **hub** of a multi-repo bot ecosystem: generic, channel-agnostic bot
infrastructure that independent consumer bots (WeatherBot, and future bots like ReminderBot)
import via a uv git pin. This repo names **no domain concepts** — it is pure, reusable mechanism.

**Read `ECOSYSTEM.md` first.** It is the constitution for how the repos relate, cross-repo
jurisdiction, and where code goes. The essentials:

- **Changes here ripple to every consumer.** A hub change is not live in any consumer until that
  consumer cuts a repin (new tag → `[tool.uv.sources]` bump → `uv lock --upgrade` → `uv sync` →
  deploy). That repin/deploy step is **human-gated** — do the fix + tests autonomously, then
  surface the tag/repin/deploy for confirmation. See `ECOSYSTEM.md` §3.
- **Keep everything litmus-clean.** The one-way dependency (consumers import the hub; the hub
  imports no consumer) and the "no domain nouns" rule are enforced by the import-hygiene gate in
  `tests/test_import_hygiene.py` (`grimp` + litmus grep). Anything you add must pass it.
- **Plug points** are documented in `EXTENSION-GUIDE.md`; deferred impls (durable `JobStore`, a
  2nd `Channel`) are built in a consumer's `_promotable/` quarantine first, then promoted here via
  `git mv` (`ECOSYSTEM.md` §6).
- Public: `github.com/Ygaray/YahirReusableBot`, import root `yahir_reusable_bot`, PyPI name
  `yahir-reusable-bot`. Semver tags; tags are immutable. This repo is its own GSD project
  (`.planning/`).
- **Spinning up a new consumer bot? Run `python3 scripts/new_consumer.py <BotName>` — never
  hand-wire it.** The scaffolder pins the hub, writes the consumer's `CLAUDE.md` pointer + the
  `_promotable/` quarantine, and registers it in `ECOSYSTEM.md` §1 (see §8).

## Toolchain

- Python 3.12+, `uv` (0.11.x), `hatchling` build backend. Deps: `discord.py==2.7.1` (exact —
  the persistent-view `custom_id` wire contract), `httpx`, `structlog`, `tenacity`. Dev: `pytest`,
  `ruff`, `grimp`.
- Run tests: `uv run pytest`. Lint: `uv run ruff check`. Import-hygiene gate:
  `uv run pytest tests/test_import_hygiene.py`.
- Ships **no console script** — it is a library, imported and wired by the consumer's composition
  root, never run on its own.
