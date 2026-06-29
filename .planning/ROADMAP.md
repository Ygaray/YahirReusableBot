# YahirReusableBot — Roadmap

## Milestone v0.1.0 — Initial extraction (DONE)

Imported from the WeatherBot v2.0 "Bot Module Extraction" milestone (Phases 22–28). The module
core, the standing import-hygiene suite, and the `EXTENSION-GUIDE` ship in the single clean
import commit tagged `v0.1.0`.

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Initial import (module tree, pyproject, re-scoped import-hygiene suite, EXTENSION-GUIDE, GSD init) | done |

## Deferred Extension Points (future milestones)

Built under build-in-consumer-then-promote / rule of three when a consumer needs them.

| Phase (future) | Scope | Tracks |
|----------------|-------|--------|
| EXT-A | Durable `JobStore` impl + serialization contract (promote from a consumer that needs persistence) | EXT-01 |
| EXT-B | Second `Channel` adapter (Telegram / SMS / Slack) | EXT-02 |

## Notes

- The first consumer is **WeatherBot**, depending on this module via a uv git dependency
  tag-pinned for deploy (`tag = "v0.1.0"`, reproducible `uv.lock`).
- A real GitHub remote for this repo is a deploy prerequisite for pinning from a host
  (the local `file://` git URL is sufficient for development / Gate-1 verification only).
