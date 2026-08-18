---
status: complete
result: all_pass
gate: 1
phase: 08-redaction-hardening-cleanup
source: [08-ROADMAP success criteria]
device: n/a — pure Python library, no runnable app (scratch venv, installed wheel)
apk: yahir_reusable_bot-0.1.2-py3-none-any.whl (md5 399e28a462f3447237a728353123a09f @ d97d866)
run: 2026-08-18T00:00:00Z
---

# Self-UAT Log — Phase 8 (Redaction-hardening cleanup)

**Target:** No device/browser surface exists for this project (`yahir_reusable_bot` is a pure
library, "never run on its own" per its own `CLAUDE.md`). Per `.planning/AGENT-LIBRARY-TESTING.md`
(D1–D8), the consumer-facing rung for this platform is: build the wheel from HEAD, install it into a
disposable scratch venv, and exercise the public API from a Python process whose `cwd` is outside
the repo (so the repo root is never on `sys.path` — the same vantage point a real downstream
consumer bot has). This phase closes 4 actionable v0.2.0 audit residuals: two are runnable
public-API behaviors driven against the installed wheel (REDACT-09, REDACT-10); two are a
documentation gate (DOCS-05) and a dev-only tooling gate (HYG-04) verified at the layer their claim
lives at.

**Build identity:** git sha `d97d866` (clean tree — `git status --short` empty before and after the
run; this run touched only the disposable scratch venv and this log). Wheel built via `uv build
--out-dir <scratch>/dist` → `yahir_reusable_bot-0.1.2-py3-none-any.whl`, md5
`399e28a462f3447237a728353123a09f`. `unzip -l` confirmed the wheel ships all 6
`yahir_reusable_bot/redact/{__init__,core,registry,sink,verify,processor}.py` files — the REDACT-09
`__repr__` ratification and the REDACT-10 `on_error` hook are genuinely shipped, not just present in
the source tree. Critically, the wheel ships **no** `scripts/pyright_baseline.py` and **no**
`pyright-baseline.json` — HYG-04's gate is dev-only tooling and is correctly absent from the shipped
wheel surface (see criterion 4).

**Scratch venv:** `uv venv <scratch>/venv --python 3.12` (CPython 3.12.3) + `uv pip install --python
<scratch>/venv/bin/python <scratch>/dist/*.whl "structlog>=26.1.0"` — installed
`yahir-reusable-bot==0.1.2` from the local wheel file. Project's own `.venv`/`uv.lock` were never
touched (git tree confirmed clean after the run; the two `uv run` gate invocations below used
`--no-sync`).

**Preflight import check:** from `<scratch>/consumer_cwd` (a directory containing no copy of the
repo), `from yahir_reusable_bot.redact import RedactionPattern, RedactingWriter, redact_secrets,
register_patterns` succeeded; `redact.__file__` resolved to the venv's `site-packages`; the repo-root
`sys.path` filter returned `[]` (repo root absent). This is the load-bearing precondition for the two
installed-wheel criteria below.

**Unit suite (inherited, code-level, not re-run wholesale by this gate):** `08-VERIFICATION.md`
records `uv run pytest -q` → 218 passed; import-hygiene → 10 passed; `ruff check` → clean; pyright
baseline gate → exit 0, 12/12. This Gate-1 pass adds the real-process, installed-wheel consumer layer
on top for the runnable criteria, plus a targeted re-run of the two gate suites (DOCS-05, HYG-04)
whose subject is the gate itself.

**Seed/fixture integrity:** no persistent fixture exists for a pure library. Each criterion below
constructs (seeds) its own `RedactionPattern`s and sentinel-secret text in-script, immediately before
driving the SUT — the sentinels (`sk_live_ZZUAT8SECRET_4711`, `ZZUAT10SECRET-BADPAT`) are
self-describing and never appear anywhere in the hub's own source/test fixtures, so a leak in this
run's output would be unambiguous.

## Criteria

### 1. REDACT-09 — the raw-pattern-source reflection residual is formally ACCEPTED (D-02) with a documented rationale + pinning tests; a `RedactionPattern` built via `literal(...)` closes the accidental paths and leaves the explicit paths open exactly as recorded
result: passed
- **Rung:** 3 (headless data check — installed-wheel process, return-value/exception inspection; the ceiling rung for this platform per D6)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected, against the recorded ACCEPT decision (D-02):** the ACCIDENTAL reflection paths are
  CLOSED by `slots=True` (`vars(rp)` raises `TypeError`, `rp.__dict__` raises `AttributeError`);
  `repr(rp)`/`str(rp)` never leak the secret; the EXPLICIT paths (`dataclasses.asdict`, `astuple`,
  `rp.pattern.pattern`) STILL return the raw secret **by design** — the accepted residual — so the
  shipped behavior must match the recorded rationale rather than silently having closed them; and the
  live `RedactionPattern.__repr__` docstring carries the "Scope (WR-02)" block naming REDACT-09, the
  ACCEPTED disposition, and the `asdict`/`astuple`/`slots` specifics.
- **Arranged (seeded):** `RedactionPattern.literal("sk_live_ZZUAT8SECRET_4711")` constructed
  in-script from the installed package.
- **Did (drove):** called `vars(rp)`, `rp.__dict__`, `repr(rp)`, `str(rp)`,
  `dataclasses.asdict(rp)`, `dataclasses.astuple(rp)`, `rp.pattern.pattern` directly against the
  installed object; read `RedactionPattern.__repr__.__doc__` off the imported class (live docstring,
  not a source grep) and checked the anchors.
- **Observed:** `vars(rp)` → `TypeError: vars() argument must have __dict__ attribute`; `rp.__dict__`
  → `AttributeError: 'RedactionPattern' object has no attribute '__dict__'` (accidental paths CLOSED);
  `repr(rp)` = `RedactionPattern(pattern=<compiled len=25 flags=32>, replacement='***',
  skip_redos_check=False)` — secret absent from both `repr` and `str`; `asdict`/`astuple`/
  `.pattern.pattern` all returned the raw secret (`True/True/True`), matching the documented
  still-open explicit paths; live docstring contained all anchors
  `['Scope (WR-02)', 'REDACT-09', 'ACCEPTED', 'asdict', 'astuple', 'slots']`. Zero FAILS.
- **Evidence:** `<scratch>/gate1-p08/c1_redact09.py`; transcript: `vars(rp) -> TypeError (CLOSED)`,
  `rp.__dict__ -> AttributeError (CLOSED)`, `repr/str SAFE: secret absent from both`,
  `asdict/astuple/.pattern.pattern leaks secret (documented-open): True`,
  `docstring anchors present: [...all 6...]`, `CRITERION 1 (REDACT-09): PASS`.

### 2. REDACT-10 — `RedactingWriter.write`'s malformed-pattern behavior, plus the new keyword-only `on_error` hook (D-01), driven live from the installed wheel
result: passed
- **Rung:** 3 (installed-wheel process, real `RedactingWriter.write` driven through the fail-closed `except re.error` branch; run under a hard `timeout 30` per D7's ReDoS/uninterruptible-`re` guard)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** a hand-built, unregistered `RedactionPattern` whose replacement references an
  out-of-range group (`\9` against a single-group pattern) makes `redact_secrets` raise `re.error` at
  `.sub()` time — the exact out-of-contract path. On it, `write` must fail **CLOSED**: the fixed
  non-secret placeholder reaches the target, the original secret-bearing payload is withheld, the
  `on_error` hook fires exactly once receiving **only** the `re.error` (never the withheld payload),
  `redaction_count` does not move, and `on_redaction` does not fire. Additionally: a RAISING
  `on_error` must never propagate to the caller's `write`; `on_error` must be keyword-only; and it
  must NOT fire on a well-formed redaction (no cross-firing).
- **Arranged (seeded):** a malformed `RedactionPattern(pattern=re.compile(r"(secret=\w+)"),
  replacement=r"\9REDACTED")` and a well-formed `RedactionPattern.literal("ZZUAT10SECRET-BADPAT")`,
  plus `io.StringIO` capture targets and list-append `on_error`/`on_redaction` hooks, all
  constructed in-script from the installed package.
- **Did (drove):** SC10a — `RedactingWriter(stream, [bad], on_redaction=..., on_error=...)` then
  `.write("line with secret=ZZUAT10SECRET-BADPAT embedded")`, inspecting the captured stream and both
  hook lists and `redaction_count`. SC10b — a `RedactingWriter` with an `on_error` that `raise`s, then
  `.write(payload)`. SC10c — attempted positional `RedactingWriter(stream, [bad], None, None, boom)`.
  SC10d — a well-formed writer with an `on_error`, then `.write(payload)`.
- **Observed:** SC10a — placeholder present in output, `secret` absent (fails CLOSED), `on_error`
  fired once with `re.error("invalid group reference 9 at position 1")`, no secret in the error,
  `redaction_count == 0`, `on_redaction` did not fire. SC10b — the raising `on_error` did NOT
  propagate; placeholder still present. SC10c — `TypeError` (`__init__()` takes 3 positional
  arguments) confirms `on_error` is keyword-only. SC10d — `on_error` did NOT fire on the clean
  redaction, `redaction_count == 1`, output redacted. Script exited 0 under the hard timeout; zero
  FAILS.
- **Evidence:** `<scratch>/gate1-p08/c2_redact10.py`; transcript: `SC10a placeholder written: True`,
  `SC10a on_error got re.error only: True | msg: invalid group reference 9...`, `SC10a secret
  withheld: True | count: 0 | on_redaction fired: False`, `SC10b raising on_error survived`,
  `SC10c on_error is keyword-only (positional rejected)`, `SC10d clean-path on_error fired: False |
  count: 1 | output redacted: True`, `CRITERION 2 (REDACT-10): PASS`, `EXIT: 0`.

### 3. DOCS-05 — `EXTENSION-GUIDE.md` §7 carries the changed-writes telemetry semantics and the reconfigure-discipline claim, each regression-gated by a non-vacuous self-proof; mutating either turns the suite red
result: passed
- **Rung:** 0/1 (documentation-content + gate-existence claim — source read + grep for the prose;
  gate suite executed to confirm it is real and its self-proofs are non-vacuous. `EXTENSION-GUIDE.md`
  is a doc artifact, not shipped in the wheel, so there is no installed-wheel surface to exercise —
  the criterion's claim lives at the doc + test-gate layer.)
- **Target:** repo tree at `d97d866`
- **Expected:** §7 states the telemetry counts **changed writes** (not substitutions) and is
  monotonic, AND states the reconfigure discipline (call `assert_redaction_active` again after any
  reconfiguration because a second `structlog.configure()` can drop the wiring); `tests/
  test_extension_guide.py` carries a primary gate for each plus a self-proof that EXCISES the target
  paragraph from a temp copy, monkeypatches `GUIDE_PATH`, re-invokes the primary gate, and asserts it
  raises — a genuine non-vacuity proof, not an assertion on static text — plus an anchor-collision
  guard; and the full suite is green.
- **Arranged (seeded):** none — direct read of the artifact and gate under test.
- **Did (drove):** `grep` for the §7 telemetry ("changed writes", "monotonic") and reconfigure
  ("again after any reconfiguration", "a second `structlog.configure()` call can drop the wiring")
  prose; located the four gate functions + collision guard by name in `tests/test_extension_guide.py`;
  read the `test_selfproof_telemetry_semantics_gate_catches_a_deleted_paragraph` body directly
  (lines 475–525) to confirm it `re.sub`-excises the paragraph, swaps `GUIDE_PATH` to the temp copy,
  re-runs the primary gate, and asserts it raises; ran the suite via `uv run --no-sync pytest
  tests/test_extension_guide.py -q`.
- **Observed:** §7 line 204 — "counts **changed writes**, not individual substitutions, and is
  monotonic for process lifetime"; §7 line 186 — "call it once at boot AND again after any
  reconfiguration, because `structlog`'s configuration is global mutable state and a second
  `structlog.configure()` call can drop the wiring". All four gate functions
  (`..._pins_the_changed_writes_telemetry_semantics`,
  `test_selfproof_telemetry_semantics_gate_catches_a_deleted_paragraph`,
  `..._pins_the_reconfiguration_recheck_discipline`,
  `test_selfproof_reconfigure_discipline_gate_catches_a_deleted_paragraph`) plus
  `test_new_anchor_tokens_do_not_collide_with_the_recipe_2_ordering_assertion` present; the inspected
  self-proof genuinely excises-and-reasserts (not vacuous); `16 passed in 0.03s`.
- **Evidence:** `EXTENSION-GUIDE.md:186,204`; `tests/test_extension_guide.py:441,475,528,564,621` and
  the self-proof body at 475–525; suite run `16 passed`.

### 4. HYG-04 — a static type checker runs clean as a standing dev-only gate (pyright `basic`, source-scoped); it is dev tooling, correctly absent from the shipped wheel surface
result: passed
- **Rung:** 0/3 (dev-tooling gate — pyproject config inspection at rung 0; standing gate executed to
  confirm it runs clean; wheel-content inspection to prove it is NOT part of the shipped surface. As
  dev-only tooling it is not exercised through the installed wheel — the point of the criterion is
  precisely that distinction.)
- **Target:** repo tree at `d97d866`; wheel `399e28a4...` for the dev-only-distinction check
- **Expected:** pyright is a dev dependency only — in `[dependency-groups].dev`, NOT in
  `[project].dependencies` (so zero consumer blast radius; `version` still `0.1.2`);
  `[tool.pyright].typeCheckingMode` is EXPLICITLY `basic`; `uv run python scripts/pyright_baseline.py`
  runs clean (exit 0, gate passed, diagnostics == committed baseline); and neither
  `scripts/pyright_baseline.py` nor `pyright-baseline.json` appears in the shipped wheel — confirming
  the gate is dev-only tooling, not part of the library's public surface.
- **Arranged (seeded):** none — inspects the standing gate + config + built wheel directly.
- **Did (drove):** parsed `pyproject.toml` via `tomllib` (checked `pyright` membership in
  `[project].dependencies` vs `[dependency-groups].dev`, `typeCheckingMode`, `version`); ran the
  standing gate `uv run --no-sync python scripts/pyright_baseline.py`; ran `unzip -l` over the built
  wheel grepping for `scripts`/`pyright`.
- **Observed:** `pyright in [project].dependencies: False`; `pyright in [dependency-groups].dev:
  True`; `typeCheckingMode: basic`; `project version: 0.1.2`. Gate run: `pyright: 12 diagnostic(s)
  this run, 12 in the committed baseline.` → `Gate PASSED — no diagnostics outside the committed
  baseline.`, exit 0. Wheel `unzip -l` grep for `scripts`/`pyright` returned nothing (only the 6
  `redact/*.py` files matched the broader `redact/` grep) — the gate ships in neither the wheel's
  `scripts/` (none) nor its metadata. The dev-only distinction holds.
- **Evidence:** `pyproject.toml` (`[dependency-groups].dev` pyright, `[tool.pyright]
  typeCheckingMode = "basic"`, `version = "0.1.2"`); `scripts/pyright_baseline.py` run → `Gate
  PASSED`, exit 0; `unzip -l <wheel>` — no `scripts/`/`pyright*` entries shipped.

## Summary

total: 4
passed: 4
partial: 0
failed: 0
infra: 0

## Notes / anomalies (for the Gate-2 reviewer)

- Two of the four residuals are runnable public-API behaviors (REDACT-09, REDACT-10) and were driven
  against the installed wheel from a non-repo cwd at rung 3 — the ceiling rung for this pure-library
  platform per `.planning/AGENT-LIBRARY-TESTING.md`. The other two are a documentation gate (DOCS-05)
  and a dev-only tooling gate (HYG-04); each was verified at the layer its claim actually lives at
  (doc prose + non-vacuous test gate for DOCS-05; config + standing-gate run + wheel-absence for
  HYG-04), not force-fit onto an installed-wheel probe where no such surface exists.
- REDACT-09 is an ACCEPT (not a close): the explicit reflection paths
  (`asdict`/`astuple`/`.pattern.pattern`) DELIBERATELY still return the raw secret, and this run
  confirmed they do — that is the recorded, documented decision, NOT a leak defect. The check was
  written adversarially to FAIL if any explicit path had silently been closed (which would contradict
  the recorded rationale) — all three remained open as documented, and the accidental
  (`vars`/`__dict__`) paths are closed by `slots=True`. `repr`/`str`, the paths a consumer actually
  reaches when logging a pattern, never leak.
- HYG-04's dev-only distinction was verified positively: the built wheel ships neither
  `scripts/pyright_baseline.py` nor `pyright-baseline.json`, and pyright is confined to
  `[dependency-groups].dev`. The library's public `version` remains `0.1.2` — no consumer blast
  radius from adopting the type checker.
- No prior `08-SELF-UAT.md` existed for this phase — this is an initial Gate-1 run, not an audit of a
  prior verdict. `08-VERIFICATION.md` (the code-level gate) had already re-run the full suite and
  independently re-derived RED-first ancestry; this Gate-1 run adds the real-process, installed-wheel
  consumer layer for the two runnable criteria and independently re-exercised the two gate suites.
- The project's own `.venv`/`uv.lock` were never mutated; `git status --short` was empty both before
  and after the run (the two `uv run` gate invocations used `--no-sync`). All wheel probes ran in a
  disposable scratch venv under the session scratchpad.

## Findings routed to gap-closure (if any)

None — all 4 ROADMAP success criteria PASS on the real, installed-wheel (REDACT-09/REDACT-10) and
doc/dev-tooling (DOCS-05/HYG-04) surfaces.

## Verdict

All 4 ROADMAP success criteria PASS → Gate-1 complete; human Gate-2 deferred to milestone completion
(registered in `.planning/HUMAN-UAT-PENDING.md`).
