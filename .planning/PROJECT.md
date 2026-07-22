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

## Current Milestone: v0.1.2 Hub hardening

**Goal:** Close all 17 audit-surfaced hub defects and add a first-class `ReadyGate` fatal
outcome, so the live consumer stops silently dropping deliveries and the next consumer inherits
a footgun-free public surface.

**Target features:**
- Reachable reliability — the two defects live and unmitigated in a consumer today (H01, H02)
- Latent runtime robustness — real bugs behind narrow runtime conditions (H03, H04, H05, H07, H08)
- Reusable public-surface hardening — matcher, retry callable, panelkit, identity, scheduler
  footguns that are unreachable in the current consumer but will bite the next (H06, H09–H16)
- Public-surface cleanup + `ReadyGate` fatal outcome (H17, H18)

**Source of record:** `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` (fix direction per
finding), `.planning/backlog/HUB-FINDINGS-HANDOFF.md` (failure scenario + evidence per finding).
All 18 re-verified against source at HEAD `5da57b8` — no semantic drift; H07 is at `gateway.py:246`
(not `:244`) and H04 at `gateway.py:278` (not `:273`), both inside the same function as reported.

**Test posture:** every fix ships with a RED-first regression test. Several findings note the
existing tests cover only decoy cases (e.g. `test_reload.py:561` for H01) — the missing
adversarial case gets added, not just a new happy path.

**Close-out is human-gated** (`ECOSYSTEM.md` §3): fixes plus green gates are autonomous; the
`pyproject.toml` bump `0.1.1 → 0.1.2`, the `v0.1.2` tag cut, and the WeatherBot repin are not.

**Out of milestone:** PC-01 (log secret-redaction backstop promotion) stays in the backlog as
phase 999.5 — a promotion track, not a defect fix.

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

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---

_Last updated: 2026-07-22 — Milestone v0.1.2 (Hub hardening) started._
