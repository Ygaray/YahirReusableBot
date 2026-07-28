# YahirReusableBot — Promotion Candidates (reusable mechanisms to pull up from consumers)

> Work that should be **built or promoted here in the hub**, surfaced from consumer repos.
> Distinct from `HUB-FINDINGS-HANDOFF.md` (that file = audit *bugs* in existing hub code).
> This file = *new reusable mechanisms* a consumer built app-local that belong in the hub.
>
> Per `ECOSYSTEM.md`, landing anything here is **human-gated**: build/promote in this repo,
> run the suite + import-hygiene/litmus/grimp gates, then **you** cut the tag and repin the
> consumer. Nothing below has been actioned yet.

---

## PC-01 — Log secret-redaction backstop (from WeatherBot Phase 30 "Secret Hygiene")

**Status:** deferred candidate — NOT yet built in the hub. WeatherBot ships it **app-local**
in Phase 30 (v1.2 audit milestone) to keep that phase "cheap, high-value" and avoid a
human-gated hub tag cut mid-phase.

**Source:** WeatherBot Phase 30 — `.planning/phases/30-secret-hygiene/30-CONTEXT.md`
(requirement HARD-SEC-01). Origin finding F12.

### What the hub should provide
A generic, renderer-agnostic logging backstop that scrubs secrets out of **all** rendered
log output — event fields AND formatted tracebacks — as defense-in-depth, independent of the
structlog processor chain. In WeatherBot the elegant seam is the shared stderr write choke
point (`_LiveStderr.write`, used by both `structlog.configure` sites); a hub version would
generalize that into a reusable secret-scrubbing sink/processor.

Shape to consider for the hub:
- A small `redact_secrets(text, patterns) -> text` core (regex-based, placeholder like `***`).
- A drop-in wrapper for a structlog `PrintLoggerFactory` file target (the `_LiveStderr`-style
  choke point) **and/or** a structlog processor, so consumers can pick their insertion point.
- Config-driven pattern list (each consumer registers its own secret patterns).

### Why it's a hub candidate (litmus)
"Could a different bot reuse this with zero domain assumptions?" — **Yes, if** the secret
patterns are injected by the consumer. The *mechanism* (scrub rendered log output) is fully
generic; only the *pattern* (`appid=<key>` for OpenWeather) is WeatherBot-specific. So the
hub owns the mechanism + pattern-registration API; the consumer owns its own patterns.

### Why deferred (not done now)
- The `appid` pattern is OpenWeather-specific → the immediate need is app-local.
- Cutting a hub tag (v0.1.x) + repinning WeatherBot is human-gated and would balloon a phase
  whose whole point is "cheap, high-value."

### When actioned here
1. Generalize WeatherBot's app-local redactor into a hub module (with the pattern-registration API).
2. Run this repo's suite + import-hygiene / litmus / grimp gates.
3. Cut the tag, repin WeatherBot, and replace WeatherBot's app-local copy with the hub import.

---
