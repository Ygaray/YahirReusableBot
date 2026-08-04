---
status: complete
result: all_pass
gate: 1
phase: 06-insertion-seams-provable-backstop
source: [06-ROADMAP success criteria]
device: n/a — pure Python library, no runnable app (scratch venv, installed wheel)
apk: yahir_reusable_bot-0.1.2-py3-none-any.whl (md5 2c65563912514c856bd1ce03e2a500c7 @ fa8a9ac)
run: 2026-08-03T00:00:00Z
---

# Self-UAT Log — Phase 6 (Insertion seams + provable backstop)

**Target:** No device/browser surface exists for this project (`yahir_reusable_bot` is a pure
library, "never run on its own" per its own `CLAUDE.md`). Per
`.planning/AGENT-LIBRARY-TESTING.md` (D1-D8), the consumer-facing rung is: build the wheel from
HEAD, install it into a disposable scratch venv, and drive the public API exactly as
`EXTENSION-GUIDE.md` §7 (SEAM-08) documents it — a real `structlog.configure()` call made by this
run, real `logger.exception(...)`/`logger.info(...)` emissions carrying a real sentinel secret
(never one of the hub's own test fixtures), and inspection of the actual captured stream output.
This is deliberately distinct from `uv run pytest` (hand-written capture doubles, `pythonpath =
["."]` bypasses packaging).

**Build identity:** git sha `fa8a9ac` (clean tree; only `.planning/phases/06-.../06-VERIFICATION.md`
untracked, pre-existing from the code-level gate, not touched by this run). Wheel built via
`uv build --out-dir <scratch>/dist` → `yahir_reusable_bot-0.1.2-py3-none-any.whl`, md5
`2c65563912514c856bd1ce03e2a500c7`. `unzip -l` confirmed the wheel ships all 6
`yahir_reusable_bot/redact/{__init__,core,registry,sink,verify,processor}.py` files — the Phase-6
seams are genuinely shipped, not just present in the source tree.

**Scratch venv:** `uv venv <scratch>/venv --python 3.12` + `uv pip install --python
<scratch>/venv/bin/python <scratch>/dist/*.whl` + `uv pip install ... "structlog>=26.1.0"` (19
packages incl. `yahir-reusable-bot==0.1.2` from the local wheel, `structlog==26.1.0`). Project's
own `.venv`/`uv.lock` were never touched.

**Preflight:** from `<scratch>/consumer_cwd` (a directory containing no copy of the repo), every
probe script below imports `yahir_reusable_bot.redact` successfully and resolves through
`site-packages`, never the repo tree.

**Unit suite (inherited, code-level, not re-run by this gate):** `06-VERIFICATION.md` records
`uv run pytest -q` → 158 passed; import-hygiene → 10 passed; `ruff check` → clean. This Gate-1 pass
adds the real-`structlog`, real-process consumer layer on top — it does not re-run that suite.

**Seed/fixture integrity:** no persistent fixture exists for a pure library. Each criterion below
constructs (seeds) its own `RedactionPattern`s and sentinel-secret text in-script, immediately
before driving the SUT — the sentinel secrets (`ZZTOPSECRET-4711`, `-9182`, `-3355`, `-AAAA`,
`-BBBB`) are self-describing and never appear anywhere in the hub's own source/test fixtures, so a
leak in this run's output is unambiguous.

## Criteria

### 1. `logger.exception(...)` through `dev.ConsoleRenderer` (bypasses `event_dict`) comes out of the wrapped sink masked, asserted against the FULL captured output; a `JSONRenderer` line with an escaped secret still round-trips through `json.loads`
result: passed
- **Rung:** 3 (installed-wheel process, real `structlog.configure()`, captured-stream inspection — the ceiling rung for this platform per D6)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** a real `logger.exception()` call, rendered by `dev.ConsoleRenderer` with NO
  `format_exc_info` in the chain (so the renderer formats the traceback straight to its own output
  buffer, never through `event_dict`), comes out of the `RedactingWriter`-wrapped sink with the
  secret masked in the full multi-line captured text, not merely in `str(exc)`. A `JSONRenderer`
  line whose `exception` field contains the secret inside an escaped-quote/backslash/newline
  context still parses via `json.loads` after redaction.
- **Arranged (seeded):** `RedactionPattern.literal("ZZTOPSECRET-4711", "***REDACTED***")` via
  `register_patterns`; a `ValueError` raised with the secret embedded in its message (SC1a) and a
  second `ValueError` with the secret embedded inside quotes/backslash/newline text (SC1b).
- **Did (drove):** `structlog.configure(processors=[dev.ConsoleRenderer(colors=False)],
  logger_factory=PrintLoggerFactory(file=RedactingWriter(stream, patterns)))`, then
  `try/except ValueError: logger.exception("boom")` — the real documented Recipe 1 wiring, driven
  live. Separately, `structlog.configure(processors=[format_exc_info, JSONRenderer()], ...)` +
  `logger.exception("boom json")`.
- **Observed:** SC1a full captured output contained `Traceback (most recent call last):` +
  `ValueError: connection failed secret=***REDACTED***` — the raw secret string absent from the
  ENTIRE captured buffer (asserted with `SECRET not in full_output`, not `str(exc)` alone);
  `writer.redaction_count == 1`. SC1b's raw JSON line parsed successfully via `json.loads` (proving
  JSON structure survived redaction of escaped content), and `***REDACTED***` present / secret
  absent from the round-tripped object.
- **Evidence:** `/tmp/.../scratchpad/06-uat/probe_sc1.py`; run transcript:
  ```
  ValueError: connection failed secret=***REDACTED***
  SC1a PASS — redaction_count=1
  {"event": "boom json", "exception": "...ValueError: quoted \"secret=***REDACTED***\" value..."}
  SC1b PASS — round-tripped keys: ['event', 'exception'], redaction_count=1
  ```

### 2. The optional structlog processor scrubs `event_dict` string values pre-render, its chain-order precondition is stated loudly in its own docstring, shipped as additive defense-in-depth never the sole backstop
result: passed
- **Rung:** 3 (installed-wheel process, real `structlog.configure()`, adversarial falsification)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** `redaction_processor.__doc__` states both the chain-order precondition and the
  not-sufficient-alone caveat; a correctly-ordered processor (after `format_exc_info`) scrubs the
  `exception` field; a MIS-ordered processor (before `format_exc_info`) leaks, live, proving the
  precondition is real and not decorative; a processor-only configuration (no `RedactingWriter`
  sink) against `dev.ConsoleRenderer` leaks the traceback, live, proving "never the sole backstop."
- **Arranged (seeded):** `RedactionPattern.literal("ZZTOPSECRET-9182", "***REDACTED***")`.
- **Did (drove):** four real `structlog.configure()` calls: (a) doc inspection only; (b)
  `processors=[format_exc_info, redaction_processor(patterns), JSONRenderer()]` +
  `logger.exception()`; (c) same processors REORDERED (`redaction_processor` first — the wrong
  order); (d) `processors=[redaction_processor(patterns), dev.ConsoleRenderer()]` with no sink at
  all, `logger_factory=PrintLoggerFactory(file=stream)` (plain `io.StringIO`, not wrapped).
- **Observed:** doc contains `CHAIN-ORDER PRECONDITION` and `NOT SUFFICIENT ALONE` verbatim.
  (b) scrubbed — secret absent, `***REDACTED***` present. (c) **leaked** — raw
  `ZZTOPSECRET-9182` present in the JSON `exception` field, confirming the mis-ordered case
  genuinely fails as documented (this is a deliberate falsification, not a bug: correctly asserts
  the precondition is load-bearing). (d) **leaked** — raw secret present in `dev.ConsoleRenderer`'s
  own traceback buffer even though the processor ran and was correctly ordered, confirming the
  processor structurally cannot see a renderer-formatted traceback and the sink remains load-
  bearing.
- **Evidence:** `/tmp/.../scratchpad/06-uat/probe_sc2.py`; run transcript shows SC2a scrubbed,
  SC2b and SC2c genuinely leak the raw sentinel (`ZZTOPSECRET-9182`) as the falsifying proof.

### 3. `assert_redaction_active` fails loudly when the backstop is not actually installed (e.g. after a second `structlog.configure()` call drops it), and passes when it is
result: passed
- **Rung:** 3 (installed-wheel process, real reconfigure sequence)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected:** `assert_redaction_active()` returns `None` silently when a `RedactingWriter` is the
  live logger factory's file target (both shallow and `deep=True`); raises `ValueError` naming
  `RedactingWriter` specifically after a SECOND `structlog.configure()` call replaces the factory's
  file with a plain stream (the exact documented reconfigure-drop scenario); raises a DISTINCT
  message for a wholly unrecognised factory type.
- **Arranged (seeded):** `RedactionPattern.literal("ZZTOPSECRET-3355", "***REDACTED***")`.
- **Did (drove):** `structlog.configure(..., logger_factory=PrintLoggerFactory(file=RedactingWriter(...)))`
  then `assert_redaction_active()` / `assert_redaction_active(deep=True)`; then a SECOND real
  `structlog.configure()` call with `logger_factory=PrintLoggerFactory(file=io.StringIO())` (no
  wrapper — the drop) then `assert_redaction_active()` again; then a THIRD `structlog.configure()`
  with a wholly unrecognised `logger_factory` callable.
- **Observed:** first call passed silently (both shallow and deep). Second call raised
  `ValueError: assert_redaction_active: the configured logger_factory's file target is StringIO,
  not RedactingWriter...` — caught, message names the missing type. Third call raised a distinct
  `ValueError: ...the configured logger_factory is function, not PrintLoggerFactory or
  WriteLoggerFactory...`.
- **Evidence:** `/tmp/.../scratchpad/06-uat/probe_sc3.py`; run transcript:
  ```
  SC3a PASS — assert_redaction_active() and deep=True both pass when correctly wired
  SC3b PASS — raised as expected: "...file target is StringIO, not RedactingWriter..."
  SC3c PASS — distinct message for unrecognised factory: "...is function, not PrintLoggerFactory..."
  ```

### 4. Redaction-count telemetry reports how many substitutions fired (locked D-58 reading: CHANGED WRITES, not individual substitutions)
result: passed
- **Rung:** 3 (installed-wheel process, real `structlog.configure()` + real logger calls)
- **Target:** installed wheel, scratch venv, non-repo cwd
- **Expected, against the D-58 contract (not the literal wording):** a write with no secret does
  not increment the counter; a write with one secret increments by 1; a write with TWO distinct
  secrets in the SAME line increments by exactly 1 (one changed WRITE, not two substitutions) —
  this is the specific behavior that falsifies a naive "count substitutions" implementation; the
  optional `on_redaction` hook fires exactly once per changed write with the running count;
  monotonic — later clean writes never decrement or leave it unchanged from a wrong direction.
- **Arranged (seeded):** two literal patterns (`ZZTOPSECRET-AAAA`, `ZZTOPSECRET-BBBB`);
  `on_redaction=hook_calls.append` push hook at construction.
- **Did (drove):** real `structlog.configure()` + `logger.info(...)` four times through the wrapped
  sink: clean / one-secret / two-secrets-same-line / clean; then five direct `writer.write()` calls
  with the secret plus three clean writes on a second instance.
- **Observed:** `redaction_count == 2` after the four `logger.info` calls (not 3, not 4) — the
  two-secrets-in-one-line write counted ONCE, confirmed against the locked D-58 "changed writes"
  contract, not the literal "substitutions" wording. `hook_calls == [1, 2]` — fires exactly on
  changed writes, receives the running count. Second instance: `redaction_count == 5` after 5 dirty
  + 3 clean writes, unaffected by the clean writes (monotonic, no false increment).
- **Evidence:** `/tmp/.../scratchpad/06-uat/probe_sc4.py`; run transcript:
  ```
  redaction_count = 2
  SC4a PASS — counts CHANGED WRITES (2), hook fires exactly with running count, no leak
  SC4b PASS — monotonic, unaffected by subsequent clean writes: 5 -> 5
  ```

### 5. `EXTENSION-GUIDE.md` carries SEAM-08 flipped to **implemented**, naming the architectural inversion explicitly — no `Redactor` Protocol exists to go looking for
result: passed
- **Rung:** 0 (direct source read + grep — the criterion is a doc-content + code-absence claim,
  no process needed)
- **Target:** repo tree at `fa8a9ac`
- **Expected:** the SEAM-08 summary-table row reads `implemented`; the `## 7.` section opens with
  the inversion statement naming that every other seam is the host implementing a module-supplied
  Protocol, SEAM-08 inverts that; and a grep for a `Redactor` Protocol/class anywhere under
  `yahir_reusable_bot/` finds nothing (falsifying check — a stray `Redactor` class would directly
  contradict the criterion).
- **Arranged (seeded):** none — direct read of the artifact under test.
- **Did (drove):** `Read EXTENSION-GUIDE.md` (full file); `grep -rn "class Redactor\|Redactor(Protocol)\|Protocol.*[Rr]edact" yahir_reusable_bot/`.
- **Observed:** `EXTENSION-GUIDE.md:24` table row reads `SEAM-08 (P06) | **implemented**`.
  `EXTENSION-GUIDE.md:120` section header: `## 7. Secret redaction — insertion seams into a
  consumer's own logging (SEAM-08, implemented)`. Line 125: "Every other seam in this guide is the
  host implementing a Protocol the module calls. SEAM-08 **inverts** that shape..." Line ~129:
  "There is no redaction Protocol here and none to go looking for..." Grep for a `Redactor`
  Protocol/class returned zero matches (exit code 1) — the doc's claim is not merely asserted, it
  is true of the actual source tree.
- **Evidence:** `EXTENSION-GUIDE.md:24,120-212`; grep exit 1 (no matches) captured in this run's
  transcript.

## Summary

total: 5
passed: 5
partial: 0
failed: 0
infra: 0

## Notes / anomalies (for the Gate-2 reviewer)

- This run deliberately drove two ADVERSARIAL/falsifying configurations for SC2 (a mis-ordered
  processor, and a processor-only configuration with no sink) and confirmed they genuinely LEAK the
  sentinel secret live — that is the correct, expected outcome per the criterion's own wording
  ("never as the sole backstop") and per D-60's warn-only design; it is not a defect in the shipped
  code. Do not read the "leaked" lines in the SC2 evidence as a phase failure — they are the
  intended falsification proving the documented limitation is real, not merely claimed.
- No prior `06-SELF-UAT.md` existed for this phase — this is an initial Gate-1 run, not an audit of
  a prior verdict.
- `06-VERIFICATION.md` (the code-level gate) had already independently re-run the unit suite and
  confirmed all 5 criteria via the hand-written test doubles; this Gate-1 run adds the real-
  `structlog`, real-process, installed-wheel layer those tests do not exercise (per this task's
  `<target_surface>` framing) and reaches the same PASS verdict via entirely independent evidence.

## Findings routed to gap-closure (if any)

None.

## Verdict

All 5 criteria PASS → Gate-1 complete; human Gate-2 deferred to milestone completion (registered in
HUMAN-UAT-PENDING.md).
