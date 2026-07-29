---
status: complete
result: all_pass
gate: 1
phase: 05-redaction-core-pattern-registration
source: [05-ROADMAP success criteria]
device: n/a — pure Python library, no runnable app (scratch venv, installed wheel)
apk: yahir_reusable_bot-0.1.2-py3-none-any.whl (md5 0c2fd03b79993bf65438f998b10cc3b8 @ 09dd075)
run: 2026-07-29T00:00:00Z
---

# Self-UAT Log — Phase 5 (Redaction core + pattern registration)

**Target:** No device/browser surface exists for this project (`yahir_reusable_bot` is a pure
library, "never run on its own" per its own `CLAUDE.md`). Per `AGENT-LIBRARY-TESTING.md` (authored
this run — no driver playbook previously existed; project config now points
`workflow.uat_driver_playbook` at it), the consumer-facing rung for this platform is: build the
wheel from HEAD, install it into a disposable scratch venv, and exercise the public API from a
Python process whose `cwd` is outside the repo (so the repo root is never on `sys.path` — the same
vantage point a real downstream consumer bot has).

**Build identity:** git sha `09dd075` (clean tree except an unrelated `.planning/config.json`
diff and this run's own new files). Wheel built via `uv build --out-dir <scratch>/dist` →
`yahir_reusable_bot-0.1.2-py3-none-any.whl`, md5 `0c2fd03b79993bf65438f998b10cc3b8`.
`unzip -l` confirmed the wheel contains `yahir_reusable_bot/redact/{__init__,core,registry}.py` —
the new subpackage is genuinely shipped, not just present in the source tree (the packaging risk
`uv run pytest` cannot see, since `pythonpath = ["."]` bypasses installed-package resolution
entirely).

**Scratch venv:** `uv venv <scratch>/venv --python 3.12` + `uv pip install --python
<scratch>/venv/bin/python <scratch>/dist/*.whl` (19 packages incl. `yahir-reusable-bot==0.1.2` from
the local wheel file). Project's own `.venv`/`uv.lock` were never touched.

**Preflight import check:** from `<scratch>/consumer_cwd` (a directory containing no copy of the
repo), `from yahir_reusable_bot.redact import RedactionPattern, redact_secrets, register_patterns`
succeeded, `module.__file__` resolved to the venv's `site-packages`, and the repo root was
confirmed absent from `sys.path`. This is the load-bearing precondition for every criterion below.

**Unit suite (inherited, code-level, not re-run by this gate):** `uv run pytest -q` → 109 passed;
`uv run pytest tests/test_import_hygiene.py -q` → 8 passed; `uv run ruff check` → clean (per
`05-VERIFICATION.md`, independently spot-confirmed via the gsd-verifier's own re-runs). This
Gate-1 pass adds the consumer-facing layer on top, not a re-run of that suite.

**Seed/fixture integrity:** no persistent fixture exists for a pure library; each criterion below
constructs (seeds) its own in-memory `RedactionPattern`/text fixtures directly in the probe script,
immediately before driving the SUT call — Arrange and Act are both visible in each script.

## Criteria

### 1. `redact_secrets(text, patterns)` masks the secret while diagnostics survive, idempotent under re-application (D-52: strict `str -> str`, non-`str` clause deliberately out of scope for Phase 5)
result: passed
- **Rung:** 3 (headless data check — installed-wheel process, return-value inspection)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** a labeled-secret pattern masks only the secret value; endpoint, HTTP status, and
  neighbouring params in the surrounding text survive; re-applying the same pattern to the already-
  redacted output is a no-op (fixed point).
- **Arranged (seeded):** an `api_key=<value>` `RedactionPattern` (boundary-stopping regex) and a
  realistic diagnostic string `'GET /v1/weather?api_key=SECRETVALUE123&city=Austin -> HTTP 503
  (next_param=foo)'` constructed in-script.
- **Did (drove):** called `redact_secrets(text, [pattern])` directly against the installed package,
  then re-called it against its own output (idempotence probe), then against an end-of-string
  variant with no trailing boundary char.
- **Observed:** `SECRETVALUE123` absent from output; `api_key=***`, `city=Austin`, `HTTP 503`,
  `next_param=foo`, `/v1/weather` all intact; second pass byte-identical to the first
  (`out2 == out`); end-of-string secret (`api_key=ANOTHERSECRET`, no trailing delimiter) also fully
  masked. First attempt used a naive test pattern that didn't stop at `&` and legitimately
  destroyed the neighbouring param — corrected the TEST pattern's own boundary set (this was a test
  authoring error, not a product defect — `redact_secrets` faithfully applied exactly the pattern
  handed to it, per its documented `str -> str` substitution-loop contract).
- **Evidence:** `/tmp/claude-1000/-home-yahir-Projects-Reusable-YahirReusableBot/88bbb10f-e9a2-418d-9d29-381d90aefb26/scratchpad/gate1-p05/c1_masking_idempotence.py` (script + inline output captured in this run's transcript: `OUT1: GET /v1/weather?api_key=***&city=Austin -> HTTP 503 (next_param=foo)`; `OUT2` identical; `CRITERION 1: PASS`).

### 2. Patterns compiled once at registration, frozen into an immutable collection; identical results in isolation and full-suite order — no cross-test pollution, no import-order dependence, no module-level mutable singleton
result: passed
- **Rung:** 3 (headless data check across independent processes)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** `register_patterns` returns a frozen, order-preserving tuple; repeated/interleaved
  calls never leak state into one another; a fresh process registering the same patterns in a
  DIFFERENT order gets the order it asked for, not a stale prior order.
- **Arranged (seeded):** two in-memory `RedactionPattern`s (`foo(\d+)`, `bar(\d+)`) built fresh
  per-script.
- **Did (drove):** in one process — `register_patterns([p1])`, then `register_patterns([p1, p2])`,
  then `register_patterns([p1])` again (to detect leakage from the intervening call); attempted
  item-assignment on the returned tuple and field-assignment on a returned `RedactionPattern`;
  scanned `vars(yahir_reusable_bot.redact.registry)` for any `list`/`dict`/`set` module attribute.
  In a SEPARATE fresh process — `register_patterns([p2, p1])` (reversed registration order).
- **Observed:** first and third calls to `register_patterns([p1])` produced byte-identical results
  (no pollution from the intervening `[p1, p2]` call); returned collection is a genuine `tuple`
  (item assignment raised `TypeError`); the `RedactionPattern` inside it raised
  `dataclasses.FrozenInstanceError` on field assignment; module-level mutable-state scan returned
  `[]`; the reversed-order fresh process returned `(p2, p1)` — order followed the caller's input,
  not any prior process's order; `register_patterns(())` returned `()`.
- **Evidence:** `/tmp/claude-1000/.../scratchpad/gate1-p05/c2_purity_and_frozen.py` and the inline
  fresh-process one-liner in this run's transcript (`reversed-order fresh-process result: (bar...,
  foo...)`; `CRITERION 2: PASS` both runs).

### 3. A nested/overlapping-quantifier pattern that blows a wall-clock budget is rejected at registration, never silently accepted to hang at log time
result: passed
- **Rung:** 3 (headless data check, run under a hard external `timeout` per the task's explicit
  ⚠ instruction — CR-01 regression class)
- **Target:** installed wheel, scratch venv, non-repo cwd; entire probe wrapped in `timeout 20`
- **Expected:** `register_patterns` raises `ValueError` for `(a|aa)+$` (the CR-01 alternation shape
  the structural pre-check is documented to MISS — only the wall-clock ladder catches it) and for
  `(a+)+$` (the textbook nested-quantifier shape the structural pre-check catches directly); a
  benign pattern and a `skip_redos_check=True` pathological pattern must still be ACCEPTED, proving
  rejection isn't a blanket "always raise" stub.
- **Arranged (seeded):** four `RedactionPattern`s built in-script: `(a|aa)+$`, `(a+)+$`, a benign
  `api_key=(\w+)`, and `(a+)+$` with `skip_redos_check=True`.
- **Did (drove):** called `register_patterns([...])` on each, timing each call, all inside
  `timeout 20 <venv-python> c3_redos_rejection.py`.
- **Observed:** `(a|aa)+$` rejected in **0.796s** (well under the 20s hard timeout — no hang);
  `(a+)+$` rejected in 0.000s (structural pre-check, instant); benign pattern accepted in 0.000s
  returning `(pattern,)`; `skip_redos_check=True` pattern accepted despite being pathological
  (explicit opt-out honored). Script exited 0 (no external timeout kill needed).
- **Evidence:** `/tmp/claude-1000/.../scratchpad/gate1-p05/c3_redos_rejection.py`; transcript:
  `(a|aa)+$ rejected in 0.796s: RedactionPattern at index 0 rejected at registration — it triggered
  the nested-quantifier structural check or exceeded the ReDoS wall-clock budget...`;
  `CRITERION 3: PASS`, `EXIT CODE: 0`.

### 4. A registered literal secret is blocked wherever it appears — including inside a `repr()` of an object that embeds it, not only `name=value`
result: passed
- **Rung:** 3 (headless data check — installed-wheel process)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** `RedactionPattern.literal(secret)` masks the exact secret string wherever it
  physically occurs in text, including inside a hand-written object `__repr__` that has no
  `name=value` shape adjacent to the secret, a URL path segment, a list-repr, and a value containing
  regex metacharacters (proving `re.escape` is genuinely applied, not just documented).
- **Arranged (seeded):** an `ApiClientConfig` class whose own `__repr__` embeds a secret verbatim
  (`api_key='sk_live_...'` inside `ApiClientConfig(base_url=..., api_key=..., timeout=30)`); a URL
  path with the secret as a path segment; a Python `list` containing the secret; a second secret
  containing `. + * ( )` metacharacters embedded in a `key=value;next=ok` string.
- **Did (drove):** built `RedactionPattern.literal(SECRET)`, ran `redact_secrets(repr(cfg),
  [pattern])` and the three falsification-shape variants above, each through the installed package.
- **Observed:** raw `repr(cfg)` confirmed to contain the secret verbatim (sanity check on the
  fixture); redacted output masked the secret while `ApiClientConfig(base_url='https://
  api.example.com'` and `timeout=30)` survived intact around it; URL-path, list-repr, and metachar
  shapes all masked the secret with `next=ok`/surrounding structure preserved; no metacharacter in
  the weird secret caused unintended regex interpretation (confirms `re.escape` inside
  `.literal()`).
- **Evidence:** `/tmp/claude-1000/.../scratchpad/gate1-p05/c4_literal_in_repr.py`; transcript:
  `REDACTED: ApiClientConfig(base_url='https://api.example.com', api_key='***', timeout=30)`;
  `URL-path shape: https://example.com/webhook/***/callback`; `list-repr shape: ['auth', '***',
  'retry=3']`; `metachar-secret shape: key=***;next=ok`; `CRITERION 4: PASS`.

### 5. Every `def`/`class`/param/annotation name under `redact/` passes the AST signature litmus, and `redact/` imports no sibling `yahir_reusable_bot` subpackage (pure leaf)
result: passed
- **Rung:** 3 (headless AST scan against the INSTALLED wheel copy, not the source tree — the
  in-repo `test_import_hygiene.py::test_litmus_clean` gate already proved this against
  `_MODULE_ROOT` = the source tree; this Gate-1 check independently re-derives it against
  `site-packages`, the one surface the source-tree test structurally cannot see)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** zero litmus hits (`weather|forecast|location|openweather|\buv\b|briefing`) across
  every `def`/`class`/param-name/annotation-name in the installed `redact/` copy; no
  `import`/`from ... import` statement in the installed copy names any sibling
  `yahir_reusable_bot.*` subpackage other than `yahir_reusable_bot.redact.*` itself.
- **Arranged (seeded):** none needed — the check reads the installed package's own files directly.
- **Did (drove):** `ast.parse` + `ast.walk` over `__init__.py`, `core.py`, `registry.py` as resolved
  from `yahir_reusable_bot.redact.__file__` inside the scratch venv; independently reimplemented
  the litmus regex and the sibling-import scan (not reusing the repo's test helper) to avoid
  trusting the same code path twice.
- **Observed:** confirmed exactly the three expected files present (`__init__.py`, `core.py`,
  `registry.py`); 0 litmus hits; 0 sibling-subpackage imports found (only
  `yahir_reusable_bot.redact.core` intra-package import present, matching the source-tree grimp
  result already recorded in `05-VERIFICATION.md`).
- **Evidence:** `/tmp/claude-1000/.../scratchpad/gate1-p05/c5_litmus_and_leaf.py`; transcript:
  `AST litmus: 0 hits across ['__init__.py', 'core.py', 'registry.py']`; `No sibling
  yahir_reusable_bot subpackage import found in installed copy.`; `CRITERION 5: PASS`.

## Summary

total: 5
passed: 5
partial: 0
failed: 0
infra: 0

## Notes / anomalies (for the Gate-2 reviewer)

- No UAT driver playbook existed for this project before this run (`workflow.uat_driver_playbook`
  was `null`). This project has no device/browser/server surface at all — it is a pure library.
  Authored `AGENT-LIBRARY-TESTING.md` at the project root this run (build wheel → scratch venv
  install → exercise public API from a non-repo `cwd`) and pointed
  `.planning/config.json:workflow.uat_driver_playbook` at it so future Gate-1 runs on this hub reuse
  it without re-bootstrapping.
- Criterion 1's first attempt used a test-authored pattern that didn't stop at `&`, and the neighbour
  param was legitimately destroyed by that pattern's own (test-code, not product) greediness — this
  was corrected and is called out above for transparency; it is not a product defect (the module's
  own docstring is explicit that value-boundary discipline is the CONSUMER pattern's responsibility,
  never `redact_secrets`'s).
- Per the task's explicit note (decision D-52), the non-`str` input clause of ROADMAP criterion 1 was
  deliberately NOT tested here — `redact_secrets` is strict `str -> str` by design in this phase, and
  that tolerance is relocated to the Phase-6 seam.
- The Phase-6 scope fence (`RedactingWriter`, structlog processor, `assert_redaction_active`,
  redaction-count telemetry, `EXTENSION-GUIDE.md` SEAM-08) was confirmed absent from `redact/` and
  correctly out of scope for this phase — not probed further here.
- No pre-existing `05-SELF-UAT.md` existed prior to this run (nothing to audit/correct).

## Findings routed to gap-closure (if any)

None — all 5 criteria PASS on the real, installed-wheel consumer-facing surface.

## Verdict

All 5 ROADMAP success criteria PASS → Gate-1 complete; human Gate-2 deferred to milestone
completion (registered in `.planning/HUMAN-UAT-PENDING.md`).
