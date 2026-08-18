---
phase: 05
slug: redaction-core-pattern-registration
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: 2026-08-05
---

# Phase 05 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register authored at plan time (`register_authored_at_plan_time: true`), sourced from the
`<threat_model>` blocks of `05-01-PLAN.md`, `05-02-PLAN.md` and `05-03-PLAN.md`. 12 unique
threats; `T-05-02` is declared twice against different components and is verified and recorded
here as two independent rows (`T-05-02a`, `T-05-02b`) so neither half can be closed by the
other's evidence. `T-05-SC` is declared identically in all three plans — verified once, covers
the whole phase.

Verification depth: **ASVS L1** (mitigation is PRESENT in the cited file). Where a named test
was cited as proof, the test BODY was read and the test RUN — a test's existence was never
accepted as evidence.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| rendered log / error text → `redact_secrets` | Arbitrary, partly attacker-influenced text (URLs, upstream API responses, user messages, formatted tracebacks) crosses into the substitution loop. | Untrusted `str`, possibly secret-bearing |
| consumer-held secret → `RedactionPattern.literal` | A plaintext secret VALUE is handed to a hub object and stored verbatim in that object's compiled pattern source. | Plaintext secret |
| `RedactionPattern` object → any consumer log / error sink | The hub object may be rendered by a consumer's own logging (`"registered %r"`) or a traceback frame dump. | Object representation of a secret-bearing pattern |
| consumer composition root → `register_patterns` | A consumer-authored regex is UNTRUSTED input to a library that must not let it hang the host process (the phase's live ASVS V5 control point). | Consumer-authored `re.Pattern` |
| rejected pattern → raised `ValueError` → consumer logs | Rejection text crosses from the hub into whatever sink the consumer's exception handling writes to. | Error message (must not carry pattern source) |
| new `redact/` source tree → standing import-hygiene gate | A new subpackage could slide outside the gate's coverage, silently dropping litmus/layering enforcement from the code most likely to name a secret. | Test-time coverage set |
| this repo → every consumer, via a human-gated repin | Hub changes ripple outward only when a consumer cuts a repin; an unaudited close would let an unproven redaction mechanism reach a real bot. | Version tag / dependency pin |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Denial of Service | `register_patterns` / `_looks_pathological` / `_blows_budget` | high | mitigate | Default-ON registration vetting: `redact/registry.py:39` `_NESTED_QUANTIFIER_RX`, `:96-99` `_looks_pathological`, `:102-133` `_blows_budget`, joined by `or` at `:183` and raising `ValueError` at `:195-204` before the pattern can reach any logging path. Default-ON confirmed by `redact/core.py:57` (`skip_redos_check: bool = False`). Both halves proven independently load-bearing: `tests/test_redact_registry.py:70-77` (structural pass sees it) and `:79-86` (structural pass returns `False`, timing probe still rejects). Re-run live: `(a\|a)*$` rejected in 0.40 s. | closed |
| T-05-02a | Information Disclosure | `RedactionPattern.literal` / `__repr__` / `redact_secrets` | high | mitigate | (a) Literal backstop — `redact/core.py:59-86`, `re.escape` + `re.compile` feeding the single scrubbing loop; proven by `tests/test_redact_core.py:174-189` (`test_literal_matches_inside_repr`, `_Carrier.__repr__` embeds the sentinel, sentinel absent from output). (b) Source-eliding `__repr__` — `redact/core.py:26` (`repr=False, slots=True`) + `:88-128`, returning only `len=` and `flags=`; proven by `:224-233` (`test_redaction_pattern_repr_does_not_leak_pattern_source`, asserts across `repr()`, `str()` and `!r`). Independently re-run: `repr` = `RedactionPattern(pattern=<compiled len=27 flags=32>, ...)`, sentinel absent. See UF-01 for the disclosed residual. | closed |
| T-05-02b | Information Disclosure | `register_patterns` rejection message | high | mitigate | `redact/registry.py:195-204` interpolates `index` and the source-eliding `{rp!r}` only — never `rp.pattern.pattern`. Proven by `tests/test_redact_registry.py:222-233` (plants `ZZSENTINELZZ` inside the rejected pattern's source, asserts absent from message, index present). Independently re-run: message = `RedactionPattern at index 1 rejected at registration — ... : RedactionPattern(pattern=<compiled len=…>` — sentinel absent. Second, post-plan rejection branch (`:165-180`, WR-01) audited separately: see UF-02. | closed |
| T-05-03 | Denial of Service (of diagnostics) | `redact_secrets` substitution loop / boundary style | medium | mitigate | 5-case boundary matrix present and green: `tests/test_redact_core.py:33-65` — following params survive, `&`-stop, URL-encoded value, quote termination, case-insensitivity, using the ported `(appid=)[^&\s\"'<>\\]+` negated-character-class boundary with the `r"\1***"` backreference template. Boundary rationale ported as load-bearing module prose at `redact/core.py:9-16`. **Scope note (residual, not a gap against the declared mitigation):** the hub is pattern-CONTENT-agnostic by design (D-48) — the boundary class lives in the consumer's injected pattern and in this regression fixture, not in hub source; `redact_secrets` (`:171-175`) carries no runtime over-redaction guard for a consumer pattern that consumes to end-of-line. | closed |
| T-05-04 | Denial of Service | `redact_secrets` public signature | low | mitigate | `redact/core.py:131` accepts only `Sequence[RedactionPattern]` (already-compiled); `RedactionPattern.pattern` is typed `re.Pattern[str]` (`:55`). Bytecode criterion re-run live: `redact_secrets.__code__.co_names == ('pattern', 'sub', 'replacement')` — no compilation reference. | closed |
| T-05-05 | Tampering | `redact_secrets` inputs | low | accept | Accepted risk ARISK-01. Non-mutation verified: `redact/core.py:171-175` rebinds only the local `text`; `RedactionPattern` frozen + slotted (`:26`); `tests/test_redact_core.py:123-143` asserts the original binding and element identities intact. Re-run live with a mutable `list` argument: input string and list unchanged. Residual (caller mutating its own list concurrently) documented below. | closed |
| T-05-06 | Denial of Service | `_blows_budget` probe itself | high | mitigate | Cumulative-elapsed check after EVERY individual `search` — `redact/registry.py:126-133`; bounded ladder `:61-62` (`_REDOS_LADDER_MAX_RATIO = 2.0`), enforced at IMPORT time by `_validate_ladder_growth_bound` (`:74-93`, called at `:93`, a real `raise` not a bare `assert`, so it survives `-O`). Measured live: max consecutive ladder ratio 1.50; catastrophic `(a\|aa)+$` registration returns in 0.443 s (ceiling 5 s). **Register-citation correction:** the register names `test_register_patterns_vetting_terminates_in_bounded_time` as the proof, but that test's own docstring (`tests/test_redact_registry.py:109-124`) states it exercises only the structural short-circuit and NOT the ladder. The ladder's termination property is actually pinned by `:127-141` (`test_register_patterns_catches_slow_ramping_pattern_before_coarse_tier_hangs`, structural check blind, 5 s ceiling) plus the import-time invariant. Property verified; the register's cited proof was mis-attributed. | closed |
| T-05-07 | Tampering | `register_patterns` return value / process-wide state | medium | mitigate | Pure function returning a NEW frozen tuple — `redact/registry.py:205` (`return tuple(patterns)`); no module-level mutable container. Runtime scan re-run live over `vars(registry_module)`: zero `list`/`dict`/`set`/`bytearray` public attributes. Behavioural non-accumulation proven by `tests/test_redact_registry.py:200-219`; immutability by `:160-164`; order/duplicate preservation by `:167-189`. | closed |
| T-05-08 | Elevation of Privilege | `skip_redos_check` opt-out | medium | accept | Accepted risk ARISK-03. PR-03's factual claim independently checked, BOTH halves present: module docstring `redact/registry.py:16-18` ("`skip_redos_check=True` is never the remedy for a rejection — a rejection means rewrite the pattern") AND the rejection message itself `:201-203` ("skip_redos_check=True is NOT a way to silence this rejection"). Opt-out proven genuinely load-bearing (not a no-op) by `tests/test_redact_registry.py:144-157`. Placement nuance recorded below. | closed |
| T-05-09 | Tampering | `tests/test_import_hygiene.py` litmus coverage | medium | mitigate | Path-scoped guard present at `tests/test_import_hygiene.py:292-298` inside `test_litmus_clean`, asserting a filename subset over `(_MODULE_ROOT / "redact").rglob("*.py")` — Phase 6 later widened the required set from `{core.py, registry.py}` to five filenames (a superset, so Phase 5's assertion still holds). Non-vacuity re-run live: the same subset check passes against `redact/` and FAILS against `reliability/` (`['__init__.py', 'retry.py']`). `uv run pytest tests/test_import_hygiene.py -q` green. | closed |
| T-05-10 | Repudiation | phase close / GATE-02 evidence | medium | mitigate | Re-derived from git directly, not read from the SUMMARY. Adjacency: `git rev-parse 104cdbe^` == `753f3d5ed7a0…` and `git rev-parse cad067e^` == `751cda9142c0…`. RED-ness from trees: `git ls-tree -r 753f3d5` contains `tests/test_redact_core.py` (1) and NOT `yahir_reusable_bot/redact/core.py` (0); same shape for `751cda9` vs `redact/registry.py`. Purity: RED commits touch only `tests/`, GREEN commits only `yahir_reusable_bot/`. | closed |
| T-05-11 | Elevation of Privilege | human-gated repin boundary (`ECOSYSTEM.md` §3) | medium | mitigate | Verified by inspection, not by the SUMMARY's attestation. `git tag --contains 753f3d5` → empty (every tag predates the phase: v0.1.2 = 2026-07-28, phase-5 commits = 2026-07-29). `pyproject.toml` version still `0.1.2`; `git diff 753f3d5~1 cad067e -- pyproject.toml uv.lock` is EMPTY. `git log --oneline -25 \| grep -iEc 'bump\|tag v\|repin\|uv sync\|deploy'` → 0. No repin, tag, version bump, lock change or deploy occurred. | closed |
| T-05-SC | Tampering | npm/pip/cargo installs | low | accept | Accepted risk ARISK-02. Zero new dependencies verified against the tree, not the research doc: `pyproject.toml` `dependencies` untouched across the whole phase range (empty diff, above); `redact/core.py` imports only `re`, `collections.abc`, `dataclasses`; `redact/registry.py` only `re`, `time`, `collections.abc` plus one absolute intra-package import of `RedactionPattern`. No `[ASSUMED]`/`[SUS]` package exists; nothing to vet. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Unregistered Flags (WARNING — new attack surface with no threat mapping)

No plan SUMMARY carries a `## Threat Flags` section (confirmed by grep across
`05-01-SUMMARY.md`, `05-02-SUMMARY.md`, `05-03-SUMMARY.md` — the heading is absent from all
three). Absence of the section is not evidence that no new surface appeared, so the following
were found by reading the implementation and the review artifacts. None is a blocker; all are
recorded so a later audit does not have to rediscover them.

| Flag ID | Surface | Where it appeared | Severity (assigned) | Assessment |
|---------|---------|-------------------|---------------------|------------|
| UF-01 | `dataclasses.asdict(rp)` / `astuple(rp)` / the public `rp.pattern.pattern` still return the RAW compiled pattern, whose own default `repr` prints a literal-constructed secret verbatim. | Surfaced by code review WR-02 (`05-REVIEW.md:200-209`), after the register was authored. Disclosed in source at `redact/core.py:102-122` and pinned by tripwire test `tests/test_redact_core.py:255-276`. The ACCIDENTAL half (`vars(rp)`, `rp.__dict__`) was CLOSED by `slots=True` (`core.py:26`), proven by `:236-252`. | medium | Residual of T-05-02a, not a failure of its declared mitigation (repr elision + literal backstop are both present and verified). Explicit-introspection-only; closing it requires an opaque wrapper around `pattern` — a public API shape change deliberately out of Phase-5 scope. Below the `high` block threshold; documented + tested + tripwired. **Non-blocking.** |
| UF-02 | A SECOND rejection message in `register_patterns` (`redact/registry.py:165-180`, WR-01 malformed-replacement-template branch) that interpolates `{exc}` — a path the register's T-05-02b proof (`test_register_patterns_error_does_not_echo_pattern_source`) does not exercise. | Added post-plan during the review-fix cycle. | high (same class as T-05-02b) | Audited independently rather than assumed: `str(re.error)` for a bad group reference is `"invalid group reference 2 at position 1"` — position only, no pattern source and no replacement template text (verified empirically; the source-carrying `exc.pattern` attribute is never interpolated). Live re-run of the branch with a planted sentinel in the pattern source: sentinel absent from the message. **Benign — no leak. Non-blocking.** |
| UF-03 | `redact_secrets` is public and accepts hand-built `RedactionPattern` objects directly, so a consumer can bypass `register_patterns` entirely — the T-05-01 ReDoS control is opt-in by call path, not structurally mandatory. | Inherent to the shipped API shape; stated in `redact/core.py:144-150` ("out of contract"). | medium | Same trust boundary and same reasoning as T-05-08: only the consumer's own composition root can take this path, and it already holds full process control, so no privilege is gained that was not already held. Below the `high` block threshold. **Non-blocking**; worth an explicit line in `EXTENSION-GUIDE.md` when the Phase-6 seam is documented. |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| ARISK-01 | T-05-05 | `redact_secrets` never mutates its `text` or `patterns` arguments (`redact/core.py:171-175` rebinds a local only), `RedactionPattern` is frozen and slotted, and `re.Pattern` is itself immutable — so a caller's inputs cannot be altered underneath it. Residual accepted: a caller may hand in a mutable `list` and mutate it concurrently. That is the caller's own state; `register_patterns` returns a frozen tuple (`registry.py:205`) precisely so a consumer need not. | Phase 05 plan (`05-01-PLAN.md` threat model) | 2026-07-29 |
| ARISK-02 | T-05-SC | No package-manager install occurs in this phase — zero new dependencies. Re-verified at audit against the tree (not the research doc): `pyproject.toml`/`uv.lock` diff across the phase commit range is empty, and both new modules import stdlib only (plus one intra-package import). No `[ASSUMED]`/`[SUS]` package exists, so no legitimacy checkpoint is warranted. | Phase 05 plans (all three threat models) | 2026-07-29 |
| ARISK-03 | T-05-08 | `skip_redos_check` is an explicit, per-pattern, consumer-set field that by design disables the ReDoS control (D-50 requires an escape hatch for a legitimately-slow pattern). It can only be set by the consumer's own composition root, which already has full control of the process, so it grants no privilege not already held. Residual (a consumer flipping it to silence a rejection) is addressed non-technically by prohibition PR-03, whose factual claim was verified at audit: the "not the remedy" statement is present in BOTH the module docstring (`registry.py:16-18`) and the rejection message (`registry.py:201-203`). **Placement nuance recorded:** it lives in the MODULE docstring, not in `register_patterns`'s own docstring nor beside the `skip_redos_check` field in `core.py:41-45` — a consumer reading only the field or the function docstring will not see it. Not a gap against PR-03 as written; noted for the Phase-6 `EXTENSION-GUIDE.md` seam write-up. | Phase 05 plan (`05-02-PLAN.md` threat model) | 2026-07-29 |

*Accepted risks do not resurface in future audit runs.*

---

## Verification Commands Re-Run At Audit

| Check | Command / probe | Result |
|-------|-----------------|--------|
| Full suite | `uv run pytest -q` | 191 passed in 1.42 s |
| Phase-5 suites | `uv run pytest tests/test_redact_core.py tests/test_redact_registry.py tests/test_import_hygiene.py -q` | 40 passed in 1.10 s |
| Lint | `uv run ruff check` | All checks passed |
| T-05-04 bytecode | `redact_secrets.__code__.co_names` | `('pattern', 'sub', 'replacement')` — no compilation reference |
| T-05-02a repr | `repr`/`str`/`!r` of `RedactionPattern.literal(SENTINEL)` | `pattern=<compiled len=27 flags=32>` — sentinel absent from all three |
| T-05-02b both branches | ReDoS branch + WR-01 malformed branch with planted sentinel | sentinel absent from both messages; index present |
| T-05-07 module state | scan of `vars(yahir_reusable_bot.redact.registry)` | zero public mutable containers |
| T-05-06 bounded probe | `(a\|aa)+$` and `(a\|a)*$` registration timing | 0.443 s / 0.401 s (ceiling 5 s); max ladder ratio 1.50 ≤ 2.0 |
| T-05-09 non-vacuity | subset check vs `redact/` and vs `reliability/` | passes / fails as required — guard has teeth |
| T-05-10 ancestry | `git rev-parse`, `git ls-tree -r`, `git show --name-only` on all four SHAs | adjacency, RED-ness and commit purity all confirmed |
| T-05-11 repin boundary | `git tag --contains 753f3d5`; `git diff 753f3d5~1 cad067e -- pyproject.toml uv.lock` | empty / empty; version still `0.1.2` |
| D-53 ambient state | `grep -rE 'os\.environ\|getenv\|^import os$\|^from os ' yahir_reusable_bot/redact/` | no hits |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-05 | 13 | 13 | 0 | gsd-security-auditor (ASVS L1, block_on: high) |

*13 = 12 unique register entries with `T-05-02` counted as its two independently-verified halves.*

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-05
