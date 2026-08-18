# Phase 1: Reachable reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-22
**Phase:** 01-reachable-reliability
**Areas discussed:** Transient classification boundary, argv `-m` position rule, test substrate,
RED-first proof mechanism, regression test depth

**Mode:** advisor (`USER-PROFILE.md` present) · calibration tier `standard` (Vendor Philosophy =
`pragmatic-fast`, no project override) · `NON_TECHNICAL_OWNER` resolved `true` on the
`learning_style: guided` signal, applied as outcome-leading labels only — the underlying decisions
are internal library mechanics with no product surface.

**Deviation from advisor mode:** advisor mode normally fans out `gsd-advisor-researcher` subagents
per selected area. This session ran under a no-subagent directive, so the comparison tables were
built inline from local evidence instead — the installed `httpx 0.28.1` class tree, the actual
source at `retry.py:87` / `identity.py:130-149`, the actual `tests/` contents, and
`.planning/codebase/TESTING.md`. For these particular questions that is stronger evidence than web
research would have produced.

---

## Transient classification boundary (RELY-01 / H02)

| Option | Description | Selected |
|--------|-------------|----------|
| A1 | `(httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)` — the report's pick. Matches REQUIREMENTS.md RELY-01 verbatim. Deny-by-default; `ProxyError` and `UnsupportedProtocol` stay non-retryable | ✓ |
| A2 | `TransportError` minus a deny-list of `(LocalProtocolError, UnsupportedProtocol)`. Future-proof against another missed sibling, but allow-by-default | |
| A3 | A1 plus `ProxyError`. Closes the one plausible gap but adds unreachable code with no consumer that proxies | |

**User's choice:** A1

**Notes:** Presented with the `httpx 0.28.1` hierarchy dumped from the project's own `.venv` rather
than recalled. That dump corrected a detail worth recording: the current tuple's real misses are
`WriteError`, `CloseError`, and `RemoteProtocolError` — `PoolTimeout` was already covered via
`TimeoutException`. Deciding rationale for deny-by-default: a wrong retry burns ~75 minutes of a
delivery window silently, and a hub cannot see its consumers' failure modes. `ProxyError` was the
only genuinely debatable exclusion; deferred rather than rejected.

---

## argv `-m` position rule (LIFE-01 / H01)

| Option | Description | Selected |
|--------|-------------|----------|
| B1 | The report's literal fix: `argv[1] == b"-m" and argv[2] == marker` | |
| B2 | First-`-m` scan: lowest `i` with `argv[i] == b"-m"`, require `argv[i+1] == marker` | ✓ |
| B3 | B2 plus asserting `argv[0]` looks like a Python interpreter | |

**User's choice:** B2

**Notes:** B1 was presented as **rejected on evidence, not preference** — it demonstrably fails the
phase's own ROADMAP success criterion for `python -O -m <marker> run`, where `-O` occupies `argv[1]`.
This is a located correction to
`.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:92` and is recorded as D-05 in CONTEXT.md so the
planner implements the discussed rule rather than the report's text. B3 was declined because
hardcoding interpreter naming trades a vanishingly rare false positive for a worse false negative on
pypy / custom-named interpreters. The `python -m pytest -m <marker>` collision (pytest's own `-m`
marker selector) was noted as the sharpest proof that "**first** `-m`" is the correct rule.

---

## Test substrate

| Option | Description | Selected |
|--------|-------------|----------|
| C1 | Flat `tests/test_retry.py` + `tests/test_identity.py`, self-contained, no conftest — matches the existing precedent and the repo's build-in-consumer-then-promote discipline | |
| C2 | Same flat files plus a `tests/conftest.py` with shared fixtures now | ✓ |
| C3 | Package-mirroring tree (`tests/reliability/`, `tests/lifecycle/`) | |

**User's choice:** C2, scoped **minimal** on follow-up — only the fixtures Phase 1's two test files
actually need (instant-return fake `stop_event`, cmdline-bytes builder). Anticipatory seams for the
Phase 2–4 modules were declined.

**Notes:** Surfaced before finalizing that C2 is a **deliberate departure** from a documented
convention — `.planning/codebase/TESTING.md:36` states "No conftest.py" and `:142` "No
`@pytest.fixture` decorators in use". User confirmed after seeing this. Consequence recorded:
`TESTING.md` goes stale when Phase 1 lands. The decision was reached *after* discovering the hub has
no unit tests for `retry.py` or `identity.py` at all — `tests/` is only `test_gateway.py` (30 lines)
and `test_import_hygiene.py` (354 lines), and the `test_reload.py:561` the report cites as existing
decoy coverage is a **WeatherBot** file, not a hub file.

---

## RED-first proof mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Run-and-record | Write test, run against unmodified source, capture failure output as evidence, then one green commit per fix | |
| Two commits per fix | Commit the failing test, then commit the fix. Git history is the proof | ✓ |
| Retroactive | Write both, then prove RED by reverting the source hunk | |

**User's choice:** Two commits per fix, on a **phase branch merged at phase end** (follow-up
question). Alternatives offered were committing directly to `main` and a branch-per-fix with two
merges.

**Notes:** The branch follow-up was raised because `ECOSYSTEM.md` §3 makes tags the consumer
contract, so a deliberately-red commit landing twice on `main` affects bisect safety and
commit-pinning consumers. Also surfaced and recorded (D-15): **there is no CI** in this repo
(`TESTING.md:264` — no `.github/workflows`, no pre-commit hooks), so "green" means `uv run pytest`
run locally, and the branch decision is about history hygiene rather than build notifications.

---

## Regression test depth (RELY-01)

| Option | Description | Selected |
|--------|-------------|----------|
| D1 | Classifier unit asserts only | |
| D2 | D1 plus driving `build_retrying` to exhaustion, asserting the `RemoteProtocolError` escapes as itself rather than as a `tenacity.RetryError` | ✓ |
| D3 | D2 plus a test-local replica of `fire_slot`'s reason-picking so the literal string `"transient_exhausted"` is asserted | |

**User's choice:** D2

**Notes:** This area existed because the ROADMAP criterion — "reports `transient_exhausted` on
exhaustion instead of `internal_error`" — is **not literally assertable in this repo**.
`REASON_TRANSIENT_EXHAUSTED` is defined at `retry.py:75` but nothing in the hub assigns it;
`fire_slot`, which picks the reason, is consumer-side in WeatherBot. The hub-scoped restatement
(recorded as D-17) came from `retry.py:200-211`, whose `retry_error_callback` exists precisely
because a bare `reraise=True` yields `RetryError` — and `RetryError` is exactly what the consumer
mis-classifies as `internal_error`. D3 was declined as testing logic the hub does not own, and a
genericity smell in a repo carrying a standing litmus gate.

---

## Claude's Discretion

- Exact fixture names and signatures in `tests/conftest.py`, within the minimal bound.
- Whether the two fixes ship as one plan or two — disjoint files, no shared symbol.
- Exact test-function names, following the house style (module-level functions, docstring-first,
  no mocking library).
- Whether `pytest.raises()` is used for the escape assertion — would be the repo's first use;
  `try/except` + `assert isinstance` equally acceptable.
- Docstring wording for both fixed functions, provided the deny-by-default posture, the first-`-m`
  rule, and the `RetryError` restatement are stated.

## Deferred Ideas

- **`ProxyError` as transient** — arguable on the merits, but unreachable with no proxying consumer,
  so no honest RED-first test exists for it. Revisit on a real reproduction.
- **Injectable / per-consumer transient classifier** — a new capability, not a fix. Own phase, and
  only under the repo's rule-of-three promotion discipline.
- **Refresh `.planning/codebase/TESTING.md`** after Phase 1 invalidates its `:36` and `:142` claims.
  Housekeeping.

## Scope guardrail

No scope creep occurred. `LIFE-03` (H15, path-shaped `proc_marker`) touches the same function as
LIFE-01 and was explicitly *not* folded in — it is assigned to Phase 3, and this is noted in
CONTEXT.md's phase boundary so the planner does not absorb it opportunistically.
