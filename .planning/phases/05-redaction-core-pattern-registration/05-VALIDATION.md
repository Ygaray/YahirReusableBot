---
phase: 05
slug: redaction-core-pattern-registration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-29
validated: 2026-07-29
---

# Phase 05 — Validation Strategy

> **Finalized post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`, auto
> mode) after Gate-1 passed: every phase requirement has a passing automated test — zero coverage
> gaps — so `nyquist_compliant: true`.
>
> Originally derived from `05-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest>=9.0.3`, per `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~1.3 seconds (measured post-execution: 109 passed in 1.23s; the ReDoS vetting probes are the added cost, well under the plan's 10s ceiling) |

---

## Sampling Rate

- **After every task commit:** `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py -q`
- **After every plan wave:** `uv run pytest -q` (full suite) **and** `uv run pytest tests/test_import_hygiene.py -q` (grimp layering + isolated-import blocker + AST signature litmus — the standing gate a new `redact/` tree must keep green)
- **Before `/gsd-verify-work`:** Full suite green, import-hygiene green
- **Max feedback latency:** <1 second

---

## Per-Task Verification Map

> Finalized against the executed phase. Every row's test now exists and passes (the two new
> modules: 29 passed; full suite: 109 passed). Each requirement was **RED-first** — the RED test
> commit precedes its GREEN fix commit (`753f3d5`→`104cdbe`, `751cda9`→`cad067e`), independently
> re-derived from git by the phase verifier.

| Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|------|--------|
| 05-01 | 1 | REDACT-01 | — | `redact_secrets` masks the value while surrounding diagnostics (endpoint, status, neighbouring params) survive intact | unit | `uv run pytest tests/test_redact_core.py::test_redact_helper_boundaries -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-01 | T-05-03 | Ported WeatherBot boundary-case matrix: neighbouring params preserved, `&`-stop, URL-encoded value, quote-terminated, case-insensitivity | unit | `uv run pytest tests/test_redact_core.py -k boundary -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-01 | — | Idempotence — re-applying `redact_secrets` to already-redacted text is a no-op | unit | `uv run pytest tests/test_redact_core.py::test_redact_secrets_idempotent -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-01 | — | Zero patterns (`redact_secrets(text, ())`) returns `text` unchanged, silently (D-49) | unit | `uv run pytest tests/test_redact_core.py::test_redact_secrets_zero_patterns_is_identity -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-01 | — | Sequential application in registration order; input and pattern collection never mutated | unit | `uv run pytest tests/test_redact_core.py -k "registration_order or does_not_mutate" -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-02 | — | `RedactionPattern` is frozen — mutating a field raises `FrozenInstanceError` | unit | `uv run pytest tests/test_redact_core.py::test_redaction_pattern_is_frozen -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-02 | — | `register_patterns` returns an immutable collection; identical results in isolation and in full-suite order (no module-level mutable singleton, no import-order dependence) | unit + suite-order regression | `uv run pytest tests/test_redact_registry.py -x` (isolation) **and** `uv run pytest -q` (full-suite order) | ✅ | ✅ green |
| 05-02 | 2 | REDACT-02 | — | No module-level state; order and duplicates preserved | unit | `uv run pytest tests/test_redact_registry.py -k "holds_no_module_level_state or preserves_input_order or keeps_duplicate" -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-03 | T-05-01 | A pattern with `(a+)+$`-shaped nested quantifiers is **rejected at registration** with `ValueError` naming the offending entry (by INDEX — never by pattern source, which may be the secret) | unit (adversarial) | `uv run pytest tests/test_redact_registry.py::test_register_patterns_rejects_catastrophic_pattern -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-03 | T-05-06 | **CR-01 regression:** an overlapping-alternation pattern the structural check cannot see (`(a\|aa)+$`) is rejected via the timing path, under a wall-clock ceiling — the ladder never hands a single uninterruptible `re.search` an input large enough to hang | unit (adversarial, bounded) | `uv run pytest tests/test_redact_registry.py -k "structural_check_misses or slow_ramping" -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-03 | — | No false-reject: WeatherBot's proven boundary pattern shape passes vetting | unit (regression) | `uv run pytest tests/test_redact_registry.py::test_register_patterns_accepts_proven_boundary_pattern -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-03 | — | Explicit opt-out parameter bypasses vetting for a knowingly-slow pattern (D-50) | unit | `uv run pytest tests/test_redact_registry.py::test_register_patterns_honors_skip_redos_check -x` | ✅ | ✅ green |
| 05-02 | 2 | REDACT-03 | — | **WR-01:** a malformed replacement template is rejected at registration, so `redact_secrets` cannot raise `re.error` mid-log | unit | `uv run pytest tests/test_redact_registry.py::test_register_patterns_rejects_malformed_replacement_template -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-06 | T-05-02 | `RedactionPattern.literal(value)` blocks the exact value wherever it appears — including inside a `repr()` of an object embedding it, not only in a `name=value` shape | unit | `uv run pytest tests/test_redact_core.py::test_literal_matches_inside_repr -x` | ✅ | ✅ green |
| 05-01 | 1 | REDACT-06 | T-05-02 | Literal escapes regex metacharacters; empty/blank literal rejected (a zero-width pattern would shred the whole string) | unit | `uv run pytest tests/test_redact_core.py -k "escapes_regex_metacharacters or rejects_empty_or_blank" -x` | ✅ | ✅ green |
| post-review | — | REDACT-06 | T-05-02 | **WR-02 (accidental paths closed):** `slots=True` removes the instance `__dict__`, so `vars(rp)` raises `TypeError` and `rp.__dict__` raises `AttributeError` rather than exposing the raw `re.Pattern` — the paths a generic serializer/logger hits unintentionally | unit | `uv run pytest tests/test_redact_core.py::test_redaction_pattern_has_no_instance_dict_so_generic_serializers_cannot_leak -x` | ✅ | ✅ green |
| post-review | — | REDACT-06 | T-05-02 | **WR-02 (explicit residual, pinned):** `asdict()`/`astuple()` still expose the raw pattern — deliberate, no worse than the public `rp.pattern.pattern`; closing it needs an opaque wrapper (API shape change) | unit (tripwire) | `uv run pytest tests/test_redact_core.py::test_redaction_pattern_asdict_still_exposes_raw_pattern_source -x` | ✅ | ✅ green |
| 05-03 | 3 | GATE-01 (standing) | — | Full suite + grimp layering + isolated-import blocker + AST signature litmus stay green; `redact/` names are domain-noun-free and it imports no sibling subpackage; new `redact_scanned` coverage guard added | standing gate | `uv run pytest -q` (109) · `uv run pytest tests/test_import_hygiene.py -q` (8) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_redact_core.py` — created; covers REDACT-01 and REDACT-06 (core function, `RedactionPattern`, literal mode)
- [x] `tests/test_redact_registry.py` — created; covers REDACT-02 and REDACT-03 (registration + ReDoS vetting)
- [x] No new fixtures added to `tests/conftest.py` — the hand-written-doubles / minimal-conftest convention (D-10) held; each redaction test constructs its own `RedactionPattern` and text literals
- [x] Framework install: **none** — pytest was already a dev dependency

*Both files exist and pass: 29 tests across the two modules.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| WeatherBot parity gate — **4 of 6** assertions are reachable after Phase 5 | REDACT-01/02/03/06 close-out | Cross-repo — belongs to the human-gated repin step (`ECOSYSTEM.md` §3), not to this phase's workflow. Written now so it is not improvised at repin time (PITFALLS 10). | Run `/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py` unmodified with only the import swapped. **Phase-5-reachable (4):** `test_redact_helper_boundaries`, `test_onecall_failure_redacts_key_and_keeps_status`, `test_geocode_failure_redacts_key`, `test_reraised_exception_request_carries_no_key`. **Phase-6-gated (2) — cannot fully re-pass until the sink/backstop seam ships:** `test_discord_on_message_does_not_dump_key`, `test_livestderr_write_tolerates_and_scrubs_bytes`. |
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

> **Finalized post-execution** by the Nyquist finalizer (`verify:post` → `validate-phase`, auto
> mode) after Gate-1 passed. Zero coverage gaps → `nyquist_compliant: true` (INC-2026-07-27-01:
> this flag is set ONLY here, never at plan time).

- [x] All tasks have `<automated>` verify (29 dedicated tests + the standing full-suite/import-hygiene gate)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covered all MISSING references (`tests/test_redact_core.py`, `tests/test_redact_registry.py` both created)
- [x] No watch-mode flags
- [x] Feedback latency ~1.2s (full suite)
- [x] `nyquist_compliant` — set `true`: gap analysis found zero gaps (every phase requirement has a passing automated test)

**Approval:** approved 2026-07-29 — Nyquist finalizer (auto), zero gaps

---

## Validation Audit 2026-07-29

| Metric | Count |
|--------|-------|
| Requirements audited | 4 (REDACT-01, 02, 03, 06) + standing GATE-01 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Coverage | REDACT-01 COVERED · REDACT-02 COVERED · REDACT-03 COVERED · REDACT-06 COVERED · GATE-01 COVERED |

Every phase requirement maps to a passing automated test (29 dedicated tests across
`tests/test_redact_core.py` and `tests/test_redact_registry.py`; full suite 109 passed;
import-hygiene 8 passed). No MISSING or PARTIAL rows → `nyquist_compliant: true`. No auditor spawn
was needed (zero gaps; auto mode).

**Two corrections applied to this document during finalization** — the plan-time draft was wrong on
both, and both were caught by execution rather than by planning:

1. **Test name.** The draft named `test_register_patterns_accepts_proven_appid_pattern`. That
   embeds a consumer domain noun; the planner renamed it to
   `..._accepts_proven_boundary_pattern`. The row now cites the real name.
2. **WeatherBot parity scope.** The draft's manual-only row claimed all **6** assertions re-pass at
   repin. Plan 05-03's executor read the actual WeatherBot test file and found only **4** are
   Phase-5-core-only; `test_discord_on_message_does_not_dump_key` and
   `test_livestderr_write_tolerates_and_scrubs_bytes` depend on the Phase-6 sink/backstop seam.
   Corrected above so the repin step is not set up against a false expectation.

**Rows added post-execution** for coverage that did not exist at plan time: the CR-01 ReDoS
regression (T-05-06) and the WR-01 malformed-replacement-template rejection, both products of the
code-review gate.

---

## Addendum 2026-07-29 — WR-02 residual narrowed

After phase close, the WR-02 residual was revisited rather than carried into Phase 6 (where
redaction gets wired into the logging path, making an accidental serialization most likely).
`RedactionPattern` is now `slots=True` (RED `17fe469` → GREEN `eaab73a`), closing `vars(rp)` and
`rp.__dict__` — the paths a generic serializer or logging helper reaches for without intending to
introspect a dataclass. No public API change: field names/types, `redact_secrets`'s
`rp.pattern.sub(...)` call path, and frozen semantics are all unchanged, so the pending WeatherBot
repin is unaffected.

`asdict()`/`astuple()` remain open **by design** and are now pinned by an explicit tripwire. The
`__repr__` docstring previously claimed the gap "cannot be closed here"; that was overstated and is
corrected in source. Suite 109 → 110 (the old single tripwire split in two, one per leak class).

Coverage verdict unchanged: zero gaps, `nyquist_compliant: true`.
