---
phase: 05
slug: redaction-core-pattern-registration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-29
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. **This is a plan-time
> DRAFT** — `status`, `nyquist_compliant`, and `wave_0_complete` are finalized post-execution by the
> Nyquist finalizer (`verify:post` → `validate-phase`), never here (INC-2026-07-27-01).
>
> Derived from `05-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest>=9.0.3`, per `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~0.55 seconds (verified: 80 passed in 0.55s on unmodified HEAD this session) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q`
- **After every plan wave:** `uv run pytest -q` (full suite) **and** `uv run pytest tests/test_import_hygiene.py -q` (grimp layering + isolated-import blocker + AST signature litmus — the standing gate a new `redact/` tree must keep green)
- **Before `/gsd-verify-work`:** Full suite green, import-hygiene green
- **Max feedback latency:** <1 second

---

## Per-Task Verification Map

> Plan IDs are assigned by the planner; rows are keyed by requirement + behavior and the planner
> must map each to a task. `❌ W0` marks a file Wave 0 must create.

| Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | 1 | REDACT-01 | — | `redact_secrets` masks the value while surrounding diagnostics (endpoint, status, neighbouring params) survive intact | unit | `uv run pytest tests/test_redact_core.py::test_redact_helper_boundaries -x` | ❌ W0 | ⬜ pending |
| TBD | 1 | REDACT-01 | T-05-03 | Ported WeatherBot boundary-case matrix: neighbouring params preserved, `&`-stop, URL-encoded value, quote-terminated, case-insensitivity | unit | `uv run pytest tests/test_redact_core.py -k boundary -x` | ❌ W0 | ⬜ pending |
| TBD | 1 | REDACT-01 | — | Idempotence — re-applying `redact_secrets` to already-redacted text is a no-op | unit | `uv run pytest tests/test_redact_core.py::test_redact_secrets_idempotent -x` | ❌ W0 | ⬜ pending |
| TBD | 1 | REDACT-01 | — | Zero patterns (`redact_secrets(text, ())`) returns `text` unchanged, silently (D-49) | unit | `uv run pytest tests/test_redact_core.py -k zero_patterns -x` | ❌ W0 | ⬜ pending |
| TBD | 1 | REDACT-02 | — | `RedactionPattern` is frozen — mutating a field raises `FrozenInstanceError` | unit | `uv run pytest tests/test_redact_core.py::test_redaction_pattern_is_frozen -x` | ❌ W0 | ⬜ pending |
| TBD | 2 | REDACT-02 | — | `register_patterns` returns an immutable collection; identical results in isolation and in full-suite order (no module-level mutable singleton, no import-order dependence) | unit + suite-order regression | `uv run pytest tests/test_redact_registry.py -x` (isolation) **and** `uv run pytest -q` (full-suite order) | ❌ W0 | ⬜ pending |
| TBD | 2 | REDACT-03 | T-05-01 | A pattern with `(a+)+$`-shaped nested quantifiers is **rejected at registration** with `ValueError` naming the offending pattern | unit (adversarial) | `uv run pytest tests/test_redact_registry.py::test_register_patterns_rejects_catastrophic_pattern -x` | ❌ W0 | ⬜ pending |
| TBD | 2 | REDACT-03 | — | No false-reject: WeatherBot's proven `_APPID_RX` passes vetting | unit (regression) | `uv run pytest tests/test_redact_registry.py::test_register_patterns_accepts_proven_appid_pattern -x` | ❌ W0 | ⬜ pending |
| TBD | 2 | REDACT-03 | — | Explicit opt-out parameter bypasses vetting for a knowingly-slow pattern (D-50) | unit | `uv run pytest tests/test_redact_registry.py::test_register_patterns_honors_skip_redos_check -x` | ❌ W0 | ⬜ pending |
| TBD | 1 | REDACT-06 | T-05-02 | `RedactionPattern.literal(value)` blocks the exact value wherever it appears — including inside a `repr()` of an object embedding it, not only in a `name=value` shape | unit | `uv run pytest tests/test_redact_core.py::test_literal_matches_inside_repr -x` | ❌ W0 | ⬜ pending |
| all | all | GATE-01 (standing) | — | Full suite + grimp layering + isolated-import blocker + AST signature litmus stay green; `redact/` names are domain-noun-free and it imports no sibling subpackage | standing gate | `uv run pytest -q` · `uv run pytest tests/test_import_hygiene.py -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_redact_core.py` — covers REDACT-01 and REDACT-06 (core function, `RedactionPattern`, literal mode). Does not exist yet.
- [ ] `tests/test_redact_registry.py` — covers REDACT-02 and REDACT-03 (registration + ReDoS vetting). Does not exist yet.
- [ ] No new fixtures in `tests/conftest.py` — per this repo's hand-written-doubles / minimal-conftest convention (D-10), each redaction test constructs its own `RedactionPattern` and text literals. A `SENTINEL` constant (mirroring WeatherBot `test_redact_hygiene.py:29`) belongs at the top of each new test module, not in `conftest.py` — it is a constant, not a fixture.
- [ ] Framework install: **none** — pytest is already a dev dependency and the suite is green (80 passed).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WeatherBot parity gate (6 tests run unmodified against the hub-backed replacement) | REDACT-01/02/03/06 close-out | Cross-repo — belongs to the human-gated repin step (`ECOSYSTEM.md` §3), not to this phase's workflow. Written now so it is not improvised at repin time (PITFALLS 10). | Run `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` unmodified with only the import swapped. All 6 must pass: `test_redact_helper_boundaries`, `test_onecall_failure_redacts_key_and_keeps_status`, `test_geocode_failure_redacts_key`, `test_discord_on_message_does_not_dump_key`, `test_reraised_exception_request_carries_no_key`, `test_livestderr_write_tolerates_and_scrubs_bytes`. |
| `client.py` scope boundary confirmed untouched | REDACT close-out item 5 | `weatherbot/weather/client.py`'s domain-specific redacted re-raise is permanently out of PC-01 scope (domain logic, stays app-local forever) | At repin, confirm `client.py` is untouched by the swap and re-run `test_reraised_exception_request_carries_no_key` as the scope-boundary check |
| PC-01 verified independently of WR-02/MATCH-03 | milestone close-out | This milestone bundles the redaction promotion with an unrelated breaking change (duplicate `spec.name` rejection); one green CI run does not attribute a failure to the right change | Verify the redaction repin and the `spec.name` change in separate runs before treating a combined repin as ready |

*All in-repo Phase 5 behaviors have automated verification. The manual rows are cross-repo repin deliverables owned by the human-gated close-out, not by this phase.*

---

## Note on REDACT-01's non-`str` clause (D-52)

`REDACT-01` is worded as *the core* being "tolerant of non-`str` input (never raises
mid-exception-handling)". **D-52 relocates that clause's implementation to the Phase 6 seam**
(REDACT-04), matching the proven `_LiveStderr.write` design. Phase 5 verification must **not** report
a gap because `redact_secrets` is strict `str -> str`; that is the locked contract. Phase 6
verification owns the tolerance assertion (`test_livestderr_write_tolerates_and_scrubs_bytes`).

---

## Validation Sign-Off

> **Plan-time state is a DRAFT.** `status: draft` and `nyquist_compliant: false` stay as-is here.
> They are finalized ONLY post-execution by the Nyquist finalizer (`verify:post` →
> `validate-phase`, invoked by execute-phase `finalize_nyquist_validation` after Gate-1).

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`tests/test_redact_core.py`, `tests/test_redact_registry.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] _(finalizer-only, post-execution)_ `nyquist_compliant` — leave `false` at plan time; the finalizer sets `true` iff its gap analysis finds zero gaps

**Approval:** pending — finalizer-owned, not set at plan time
