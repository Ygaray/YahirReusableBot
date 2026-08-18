# YahirReusableBot — Roadmap

## Milestones

- ✅ **v0.1.0 Initial extraction** — Phase 0 (shipped 2026, tag `v0.1.0`)
- ✅ **v0.1.2 Hub hardening** — Phases 1–4 (shipped 2026-07-28, tag `v0.1.2`)
- ✅ **v0.2.0 Redaction promotion + hardening debt** — Phases 5–8 (shipped 2026-08-18, tag `v0.2.0`)

## Phases

<details>
<summary>✅ v0.1.0 Initial extraction (Phase 0) — SHIPPED, tag v0.1.0</summary>

- [x] Phase 0: Initial import (module tree, pyproject, re-scoped import-hygiene suite, EXTENSION-GUIDE, GSD init)

v0.1.0 was the single clean import commit; the hardening that followed is archived under
`milestones/v0.1.2-ROADMAP.md`.

</details>

<details>
<summary>✅ v0.1.2 Hub hardening (Phases 1–4) — SHIPPED 2026-07-28, tag v0.1.2</summary>

- [x] Phase 1: Reachable reliability (4/4 plans)
- [x] Phase 2: Latent runtime robustness (3/3 plans)
- [x] Phase 3: Reusable public-surface footguns (5/5 plans)
- [x] Phase 4: Cleanup + ReadyGate fatal outcome (2/2 plans)

Full detail: `milestones/v0.1.2-ROADMAP.md` · requirements: `milestones/v0.1.2-REQUIREMENTS.md`

</details>

<details>
<summary>✅ v0.2.0 Redaction promotion + hardening debt (Phases 5–8) — SHIPPED 2026-08-18, tag v0.2.0</summary>

- [x] Phase 5: Redaction core + pattern registration (3/3 plans) — completed 2026-07-29
- [x] Phase 6: Insertion seams + provable backstop (4/4 plans) — completed 2026-08-04
- [x] Phase 7: v0.1.2 debt paydown (7/7 plans) — completed 2026-08-04
- [x] Phase 8: Redaction-hardening cleanup (5/5 plans) — completed 2026-08-18

Milestone audit: `tech_debt` (22/22 requirements satisfied, integration clean, no blockers — four
phases signed off at Gate-2 `signed-off-with-gap`; the one deferred action is the P7 MATCH-03/SURF-02
live-WeatherBot check at repin). Full detail: `milestones/v0.2.0-ROADMAP.md` · requirements:
`milestones/v0.2.0-REQUIREMENTS.md` · audit: `milestones/v0.2.0-MILESTONE-AUDIT.md`

</details>

## Deferred Extension Points (future milestones)

Built under build-in-consumer-then-promote / rule of three when a consumer needs them.

| Phase (future) | Scope | Tracks |
|----------------|-------|--------|
| EXT-A | Durable `JobStore` impl + serialization contract (promote from a consumer that needs persistence) | EXT-01 |
| EXT-B | Second `Channel` adapter (Telegram / SMS / Slack) | EXT-02 |

**Out of Milestone v0.2.0 — deliberately parked.** EXT-01 and EXT-02 stay deferred *by design*
under rule of three. No consumer needs either today; building them now would mean designing
against imagined requirements.

## Backlog

Unsequenced parking lot. Source of record for every item below lives in `.planning/backlog/`:

- `HUB-HARDENING-REPORT-v0.1.2.md` — **the planning document.** 17 audit defects (H01–H17) +
  1 enhancement (H18), each with a fix direction verified against hub HEAD `50e8f09`, plus a
  consumer-impact triage. Supersedes the raw handoff for planning.

- `HUB-FINDINGS-HANDOFF.md` — evidence appendix: full failure scenario + evidence per finding.
- `PROMOTION-CANDIDATES.md` — new reusable mechanisms to pull up from consumers (not bugs).

The H01–H18 defect items that once lived here were grouped per the report's §3 sequencing and
have since been promoted. Anything landed from this parking lot is **human-gated** at close-out
(`ECOSYSTEM.md` §3): fixes + green gates are autonomous; the tag cut, the `pyproject.toml`
version bump, and the consumer repin are yours.

> **999.1–999.4 promoted to Milestone v0.1.2 on 2026-07-22** — they are now Phases 1–4 above.
> Their phase directories were renumbered `999.N-*` → `0N-*`.
>
> **999.5 promoted to Milestone v0.2.0 on 2026-07-29** — PC-01 is now Phases 5–6 above
> (REDACT-01..08 + DOCS-04). The parked section below is **superseded** and kept only as the
> origin record; the empty `.planning/phases/999.5-secret-redaction-promotion/` directory is
> retired in favour of the real phase directories. Nothing remains parked in this section.

### Phase 999.5: PC-01 — log secret-redaction backstop promotion (SUPERSEDED — promoted to Phases 5–6)

**Goal:** Promote WeatherBot's app-local secret redactor into a generic hub mechanism.
**Requirements:** REDACT-01..08, DOCS-04 (assigned at v0.2.0 roadmapping)
**Plans:** 7/7 plans complete

**Separate track — a promotion, not a fix.** WeatherBot ships this app-local in its Phase 30
(`HARD-SEC-01`, origin finding F12) to keep that phase cheap and avoid a mid-phase hub tag cut.

The hub should own a renderer-agnostic backstop that scrubs secrets from **all** rendered log
output — event fields *and* formatted tracebacks — independent of the structlog processor chain:
a `redact_secrets(text, patterns) -> text` core, a drop-in wrapper for a structlog
`PrintLoggerFactory` file target (WeatherBot's seam is the shared `_LiveStderr.write` choke point)
and/or a processor, plus a config-driven pattern list.

**Litmus:** the *mechanism* is fully generic; only the *pattern* (`appid=<key>` for OpenWeather) is
domain-specific. Hub owns mechanism + pattern-registration API; the consumer registers its patterns.
Landing it replaces WeatherBot's app-local copy with a hub import.

## Notes

- The first consumer is **WeatherBot**, depending on this module via a uv git dependency
  tag-pinned for deploy (currently `tag = "v0.1.2"`, reproducible `uv.lock`).

- A real GitHub remote for this repo is a deploy prerequisite for pinning from a host
  (the local `file://` git URL is sufficient for development / Gate-1 verification only).
