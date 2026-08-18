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

## Shipped: v0.2.0 Redaction promotion + hardening debt

**Status (2026-08-18): SHIPPED — milestone certified, Gate-2 signed off, tagged `v0.2.0`.**
All four phases executed and verified; Gate-1 agentic self-UAT all_pass on all four; human Gate-2
signed off (all four `signed-off-with-gap` — documented, accepted residuals, no blockers). Milestone
audit `tech_debt` (22/22 requirements satisfied, integration clean, Nyquist compliant). GATE-02
(milestone-standing) checked green at close. The granular history is frozen on keeper branch
`milestone/v0.2.0`; `main` carries one `feat: v0.2.0` squash. **Still human-gated (`ECOSYSTEM.md`
§3):** `git push` (main fast-forward + keeper + tag), the WeatherBot repin, and the deletion of
WeatherBot's app-local `_redact.py` in favor of the hub import — none performed.

**Next:** plan the next milestone via `/gsd-new-milestone`.

<details>
<summary>v0.2.0 goal + target features (archived detail)</summary>

Phase 5 (redaction core) ✓ · Phase 6 (insertion seams + provable backstop) ✓ · Phase 7 (v0.1.2 debt
paydown) ✓ · Phase 8 (redaction-hardening cleanup — REDACT-09, REDACT-10, DOCS-05, HYG-04) ✓. All 23
requirements are Complete except **GATE-02**, which is milestone-standing and is checked at
milestone close, not by any phase. Phase 8 additionally adopted a pyright `basic`-mode static gate
(dev-only, hand-rolled baseline) and gave `RedactingWriter` an optional `on_error` observability
hook (purely additive, no existing call site changes). Remaining work is the close-out sequence
below, which is deliberately **not** autonomous.

**Goal:** Promote the secret-redaction backstop into the hub as a generic mechanism, and clear
every open item the v0.1.2 audit surfaced — so the hub owns log scrubbing and carries forward no
known footgun or stale doc.

**Target features:**
- **PC-01 — secret-redaction backstop promotion.** A `redact_secrets(text, patterns) -> text`
  core, a pattern-registration API, and a structlog insertion seam (sink wrapper and/or
  processor) scrubbing event fields AND formatted tracebacks. Hub owns the mechanism; the
  consumer registers its own patterns. This is the hub's first **promotion** (not a defect fix).
- **WR-02 — duplicate `spec.name` rejected at registration.** The one real public-surface
  footgun left open by v0.1.2: a duplicate silently overwrites `by_name` while `match_command`
  can resolve a different `CommandSpec`.
- **Residual review nits** — Phase 4 IN-01/IN-02, Phase 2 IN-01/IN-02/IN-03, Phase 1 WR-01
  (attached `-mmodule` false negative).
- **Doc-drift corrections** — DOC-DRIFT-01 (a de-hack site documented at a path that does not
  exist, across 11 artifacts) and DOC-DRIFT-02 (a third de-hack site never named).

**Source of record:** `.planning/v0.1.2-MILESTONE-AUDIT.md` (the 9-item debt table + both drift
findings) and `.planning/backlog/PROMOTION-CANDIDATES.md` (PC-01 shape, litmus, and the
when-actioned sequence).

**Test posture:** unchanged from v0.1.2 — every fix ships a RED-first regression test that must
fail against current source before the fix lands. GATE-01 (full suite + import-hygiene / litmus /
grimp) stays green across every phase.

**PC-01 litmus constraint:** the mechanism must be fully generic. Only the *pattern* (e.g.
`appid=<key>`) is consumer-specific, and it is injected, never hardcoded. No domain noun may
enter the hub surface.

**Two items need an explicit human decision at discuss time, not a default:** Phase 1 WR-01
(behavioral fix vs. keep-documented — already deferred once) and Phase 4 IN-02 (`on_online`
annotation narrowing is a *public* hub-surface change).
**→ Both decided in Phase 7 (2026-08-04), reasoning recorded in `07-CONTEXT.md`:** WR-01/LIFE-05
resolved as **keep-documented** — the bundled `-Om<module>` form stays deliberately undecoded, stated
as a permanent limitation with reasoning in `EXTENSION-GUIDE.md` §4 (D-61; D-61a exempts it from the
RED-first-test rule since it ships no behavioral change). IN-02/SURF-02 resolved as **narrow** for
`on_online` and `render`, and **explicitly no-change** for `SchedulerEngine.register`'s variadic
`callback`, whose rationale is recorded in its docstring.

**Consumer-breaking note:** WR-02 makes a previously-silent duplicate registration raise
`ValueError`. The repin needs a WeatherBot sweep for duplicate `spec.name` values.

**Close-out is human-gated** (`ECOSYSTEM.md` §3): fixes plus green gates are autonomous; the
`pyproject.toml` bump `0.1.2 → 0.2.0`, the `v0.2.0` tag cut, the WeatherBot repin, and the
deletion of WeatherBot's app-local `_redact.py` in favor of the hub import are not.

**Out of milestone:** EXT-01 (durable `JobStore`) and EXT-02 (second `Channel` adapter) stay
parked. Both are deferred *by design* under build-in-consumer-then-promote (rule of three) — no
consumer needs either today, and building them now would mean designing against imagined
requirements.

</details>

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

_Last updated: 2026-08-18 after v0.2.0 milestone — SHIPPED. Certified (safety-net pass produced the
missing Phase 7/8 Gate-1 agentic self-UATs; integration clean, 218 pytest / 10 import-hygiene /
pyright 12-12), Gate-2 human UAT signed off for all four phases (all `signed-off-with-gap`), audit
`tech_debt` (22/22 requirements, no blockers). Granular history frozen on keeper `milestone/v0.2.0`;
`main` carries one `feat: v0.2.0` squash, tagged `v0.2.0`. Remaining human-gated close-out (per
`ECOSYSTEM.md` §3): `git push` (main FF + keeper + tag), WeatherBot repin `0.1.2 → 0.2.0`, and
deletion of WeatherBot's app-local `_redact.py` in favor of the hub import — none performed._

_Prior: 2026-08-18 — Phase 8 (redaction-hardening cleanup, Track C) complete: all 4 v0.2.0
phases executed and verified (215 tests passed, import-hygiene 10 passed, doc-drift 5 passed,
ruff clean, pyright gate green). REDACT-09 (WR-02 accept ratified with a rationale-retention gate),
REDACT-10 (`on_error` hook + guide contract), DOCS-05 (two prose gates), and HYG-04 (pyright `basic`
adopted, `get_type_hints` assertions kept as belt-and-suspenders — settled by observed experiment,
not reasoning) all closed on proven GATE-02 RED-first ancestry. Security audit: 31/31 threats
closed, 0 open. Nyquist-compliant._

_Prior: 2026-07-29 — Milestone v0.2.0 (Redaction promotion + hardening debt) started. v0.1.2 "Hub hardening" shipped: all 4 phases complete, 19/19 requirements satisfied, tagged `v0.1.2` (`60698b1`), repinned into WeatherBot and deployed live on `yahir-mint`. Retrospective audit (`.planning/v0.1.2-MILESTONE-AUDIT.md`) returned `tech_debt` — no blockers, 9 open items, which (minus the parked EXT points) are this milestone's scope alongside the PC-01 promotion. GATE-01 green at handoff: 80 passed, 8 import-hygiene, ruff clean._

_Prior: 2026-07-27 — Phase 3 (Reusable public-surface footguns) complete: 9 findings closed RED-first (H06 MATCH-01, H13 MATCH-02, H09 RELY-02, H10 RELY-03, H11 DISC-05, H12 DISC-06, H14 LIFE-02, H15 LIFE-03, H16 SCHED-01); full suite 71 passed + GATE-01 (import-hygiene/litmus/grimp) green; Nyquist-compliant. Two research corrections held (SCHED-01 `except KeyError` not apscheduler; DISC-05 falsy `not interaction.user` for the MISSING sentinel). One in-scope code-review regression fixed (WR-01 `write_pid_atomic` except-path close-safety); a duplicate-`spec.name` footgun (WR-02) logged for a scope decision. Phases 1–3 done; next: Phase 4 (cleanup + `ReadyGate` fatal outcome, H17/H18). Close-out (bump `0.1.1→0.1.2` / `v0.1.2` tag / WeatherBot repin) still human-gated._
