---
phase: 08
slug: redaction-hardening-cleanup
status: verified
threats_open: 0
asvs_level: 1
audited_head: 492cf7f339a653ceb69adbfe0c6c912d670147df
created: 2026-08-18
---

# Phase 08 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| `RedactionPattern` instance → any consumer serializer or logger | A `literal()`-built instance holds the secret verbatim inside its compiled pattern source | Secret pattern source (accepted-risk paths only: `asdict`/`astuple`/`rp.pattern.pattern`) |
| source docstring → the operator relying on it | The accepted-risk record is the only thing telling a consumer not to serialize a pattern | Rationale text, not secret data |
| arbitrary caller → `RedactingWriter.write` | Every log line, `print()`, stdlib logging record crosses here under recipe 2 | Untrusted, possibly secret-bearing text |
| `RedactingWriter` → consumer-supplied `on_error` callback | New outbound crossing this phase creates | The caught `re.error` exception ONLY — never the withheld payload |
| `RedactingWriter` → wrapped target | The fail-closed placeholder crosses here in place of the withheld payload | Fixed placeholder constant, never the secret |
| `EXTENSION-GUIDE.md` §7 → a consumer's composition root | Sole source of truth for wiring the redaction seam | Prose instructions a consumer acts on |
| PyPI → this repo's dev environment | `pyright` executes on the developer's machine at install and at every gate run, plus a transitive Node fetch | Package code, not secrets |
| dev dependency group → shipped wheel | Anything landing in the wrong `pyproject.toml` table reaches every consumer of the hub | Dependency metadata |
| the phase gate → the milestone audit | Whatever this plan records becomes the evidence the milestone close relies on | GATE-02 ancestry claims |
| this repo → the consumer repo | The close-out this phase surfaces would mutate a sibling repository and cut an immutable tag | Version/tag/repin actions (human-gated, none performed) |
| the narrowed public surface → consumers pinning against it | SURF-02's narrowing reaches consumers only at the imminent repin | Narrowed type annotations |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-08-01-01 | Information Disclosure | `dataclasses.asdict(rp)`/`astuple(rp)`/`rp.pattern.pattern` | medium | accept | Documented `core.py:110-130` docstring + `05-SECURITY.md` UF-01; accidental paths closed by `slots=True`; pinned `tests/test_redact_core.py:236-276` | closed |
| T-08-01-02 | Repudiation | the accepted-risk record itself | high | mitigate | Standing `_missing_wr02_anchors`/`test_wr02_accept_rationale_survives_on_the_live_repr_docstring` gate reads the live docstring; dated STATE.md line | closed |
| T-08-01-03 | Spoofing | the gate's own assurance | high | mitigate | Three-case synthetic self-proof + explicit None/short-docstring guard | closed |
| T-08-01-04 | Tampering | `RedactionPattern`'s public shape | high | mitigate | `916d4cd` — 8 insertions, 0 deletions; public shape unchanged | closed |
| T-08-01-SC | Tampering (supply chain) | npm/pip/cargo installs | low | accept | Zero installs in plan 08-01 | closed |
| T-08-02-01 | Information Disclosure | the `on_error` payload | high | mitigate | Callback receives only the exception (`sink.py:191-196`); pinned `test_on_error_payload_never_carries_the_secret_pattern_source` sweeping `dir(exc)` | closed |
| T-08-02-02 | Tampering / Information Disclosure | the `except re.error` branch | high | mitigate | Fail-closed placeholder unchanged; standing pin `tests/test_redact_sink.py:435-458` green | closed |
| T-08-02-03 | Denial of Service | the hot write path | high | mitigate | Swallow-and-continue guard copied verbatim (`grep -c 'except Exception:'` = 2); hook fires only after placeholder write returns | closed |
| T-08-02-04 | Repudiation | withheld log lines | medium | mitigate | Hook shipped and documented `EXTENSION-GUIDE.md:214-219` | closed |
| T-08-02-05 | Spoofing | the no-leak gate's own assurance | medium | mitigate | Non-vacuity guard + `dir(exc)` sweep (not hardcoded attr) | closed |
| T-08-02-SC | Tampering (supply chain) | npm/pip/cargo installs | low | accept | Zero installs/new imports in plan 08-02 | closed |
| T-08-03-01 | Information Disclosure | the section 7 reconfigure-discipline claim | high | mitigate | Dedicated content gate + non-vacuity self-proof observed failing against a broken copy | closed |
| T-08-03-02 | Spoofing | the doc gates' own assurance | high | mitigate | Marker-free anchors; non-vacuity guard; self-proof setup sanity assertions | closed |
| T-08-03-03 | Tampering | pre-existing gates loosened to accommodate new anchors | high | mitigate | Zero deleted lines across `4dc6f2c`/`aa59a1a`/`6900c42` | closed |
| T-08-03-04 | Repudiation | the anchor-collision constraint | medium | mitigate | `test_new_anchor_tokens_do_not_collide_...` reads incumbent substring from module's own source | closed |
| T-08-03-05 | Information Disclosure | the new guide paragraph itself | low | accept | Quotes no secret shape or pattern source | closed |
| T-08-03-SC | Tampering (supply chain) | npm/pip/cargo installs | low | accept | Zero installs in plan 08-03 | closed |
| T-08-04-SC | Tampering (supply chain) | `uv add --dev pyright` (+ transitive Node fetch) | high | mitigate | Blocking human checkpoint honored — operator approval `08-CONTEXT.md:95-102`, committed `cfa25d8` before install | closed |
| T-08-04-01 | Elevation of Privilege | dev dependency reaching a consumer | high | mitigate | `pyright` in `[dependency-groups].dev` only, absent from `[project].dependencies` | closed |
| T-08-04-02 | Spoofing | the gate's own assurance | high | mitigate | `_assert_run_was_not_vacuous` observed firing against mis-scoped include; scratch type error observed failing the gate | closed |
| T-08-04-03 | Tampering | `typeCheckingMode` omission | high | mitigate | Explicit `typeCheckingMode = "basic"` + 20-line rationale comment | closed |
| T-08-04-04 | Repudiation | the committed baseline | medium | mitigate | Diagnostic-count summary printed every run; count recorded at adoption | closed |
| T-08-04-05 | Denial of Service | test-suite feedback latency | medium | mitigate | Standalone script, not wired into pytest; diff logic unit-tested with synthetic dicts | closed |
| T-08-04-06 | Information Disclosure | `pyright-baseline.json` | low | accept | `_relativize_diagnostics` fix verified — `grep -c "/home/yahir"` on committed baseline = 0, all entries repo-relative; content is structural type-checker output only | closed |
| T-08-05-01 | Spoofing | the GATE-02 claim | high | mitigate | Adjacency + genuine RED-ness (scratch `git worktree`) + purity independently re-derived for all 4 pairs | closed |
| T-08-05-02 | Repudiation | DOCS-05's missing RED commit | high | mitigate | Disposition recorded with reason, Phase-6 precedent, and named contrasting case | closed |
| T-08-05-03 | Elevation of Privilege | the human-gated close-out | high | mitigate | No `v0.2.0` tag cut; `pyproject.toml` still `0.1.2`; `git diff HEAD -- . ':!.planning'` empty | closed |
| T-08-05-04 | Tampering | the SURF-02 runtime assertions | high | mitigate | Assertions intact; KEEP rationale recorded at all three sites, each citing the observed experiment | closed |
| T-08-05-05 | Tampering | the scratch experiment edit | medium | mitigate | `96b2168`'s `pyproject.toml` diff is comment-only; library-source diff empty | closed |
| T-08-05-06 | Repudiation | premature checkbox flips | medium | mitigate | Flips isolated to Task 3 (`d0b5698`); deviation disclosed and retroactively confirmed correct | closed |
| T-08-05-SC | Tampering (supply chain) | npm/pip/cargo installs | low | accept | Plan 08-05's only `pyproject.toml` touch is comment-only | closed |
| T-08-06-01 | Tampering / Denial of Service | `RedactingWriter._patterns` (mutation-during-iteration) | high | mitigate | `sink.py:125` snapshots `self._patterns = tuple(patterns)` at construction (was a bare reference pre-fix); all iteration sites (`write()`, `probe_redaction_path()`, `redact_secrets()`) read only the tuple, so no caller-side mutation — same-thread or cross-thread — can reach the iteration and raise `RuntimeError`, which would otherwise breach the "never raises" invariant. Pinned `tests/test_redact_sink.py:364-383`, RED-first per commit `5eea410`, confirmed GREEN at audited_head. | closed |
| T-08-06-02 | Information Disclosure / Repudiation | `scripts/pyright_baseline.py::_run_pyright` error path | low | mitigate | `_run_pyright` re-raises `RuntimeError(...) from exc` naming the exit code and carrying pyright's stderr instead of a bare `JSONDecodeError`; `from exc` preserves the original cause. Stderr originates from the dev-only `uv run pyright --outputjson` CLI invocation (bad flag/broken executable/Node failure) — consistent with the existing T-08-04-06 low/accept precedent for this gate's non-credential output. Pinned `tests/test_pyright_baseline.py:175-203`, confirmed GREEN. | closed |
| T-08-06-03 | Information Disclosure (documentation-only) | `sink.py` class docstring + `EXTENSION-GUIDE.md` §7 (WR-01 text-mode contract paragraph) | low | accept | Verified no runtime change: `git show 5eea410 -- yahir_reusable_bot/redact/sink.py` shows the only hunks are a new docstring paragraph plus the unrelated WR-03 tuple line; `write()`'s logic is byte-for-byte unchanged. Documentation accuracy independently verified by `tests/test_redact_sink.py:322-361` `test_sink_binary_only_target_raises_when_redaction_active_documented_limitation`, confirmed GREEN. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` (workflow.security_block_on) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-08-01 | T-08-01-01 | `dataclasses.asdict`/`astuple`/`rp.pattern.pattern` still expose the raw pattern source via explicit dataclass introspection — closing it needs an opaque wrapper around the public `pattern` field, breaking `redact_secrets`'s `.sub()` call and changing a public API shape immediately before a consumer repin. Companion record `05-SECURITY.md` UF-01. | gsd-security-auditor (Phase 8 audit) | 2026-08-18 |
| AR-08-03 | T-08-03-05 | The new §7 guide paragraph describes a fail-closed control using a self-describing, non-secret placeholder constant — consistent with the section's existing public disclosure posture. | gsd-security-auditor (Phase 8 audit) | 2026-08-18 |
| AR-08-SC-01 | T-08-01-SC / T-08-02-SC / T-08-03-SC / T-08-05-SC | Zero package-manager installs across plans 08-01/02/03/05. | gsd-security-auditor (Phase 8 audit) | 2026-08-18 |
| AR-08-04 | T-08-04-06 | `pyright-baseline.json` records file paths, rule names, and diagnostic messages from the library's own already-public source; the `_relativize_diagnostics` fix additionally strips any local filesystem prefix. No credentials or environment values are involved. | gsd-security-auditor (Phase 8 audit) | 2026-08-18 |
| AR-08-06 | T-08-06-03 | The new WR-01 docstring/`EXTENSION-GUIDE.md` paragraph documents a pre-existing, unchanged bytes→str behavior; introduces no new runtime code path and no secret-bearing content. | gsd-security-auditor (Phase 8 stale-audit re-verification) | 2026-08-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-18 | 31 | 31 | 0 | gsd-security-auditor (opus, ASVS L1, block_on=high) |
| 2026-08-18 | 34 | 34 | 0 | gsd-security-auditor (stale-audit re-verification, INC-2026-08-12-03 — audited_head advanced from `7ffa23d9` to `492cf7f3` after code-review gap-closure commits `5eea410`/`492cf7f`; all 31 prior threats re-verified live, not re-copied blind; 3 new threats constructed for the WR-01/02/03 delta) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-18 (re-audited 2026-08-18 against `audited_head: 492cf7f`)
