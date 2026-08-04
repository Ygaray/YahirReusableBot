---
phase: 06-insertion-seams-provable-backstop
plan: 04
subsystem: logging
tags: [structlog, redaction, documentation, import-hygiene, phase-gate]

# Dependency graph
requires:
  - phase: 06-insertion-seams-provable-backstop (plan 06-01)
    provides: "RedactingWriter — the load-bearing sink; RED/GREEN SHAs re-derived by this plan's ancestry audit"
  - phase: 06-insertion-seams-provable-backstop (plan 06-02)
    provides: "assert_redaction_active / REDACTION_PROCESSOR_MARKER; RED/GREEN SHAs re-derived by this plan's ancestry audit"
  - phase: 06-insertion-seams-provable-backstop (plan 06-03)
    provides: "redaction_processor — completes the PC-01 public surface; RED/GREEN SHAs re-derived by this plan's ancestry audit"
provides:
  - "EXTENSION-GUIDE.md SEAM-08 row (implemented) and its own ## 7. section (DOCS-04) — the promotion is now hub-side done per ECOSYSTEM.md §6"
  - "test_redact_sink_never_imports_structlog + self-proof — executable proof the load-bearing sink stays framework-agnostic"
  - "Extended redact_scanned litmus coverage guard covering all five redact/ modules"
  - "GATE-02 RED-first ancestry independently re-derived from git trees for REDACT-04/05/07/08"
  - "Human-gated close-out record: updated WeatherBot parity status, httpx-gap flag, unperformed repin checklist"
affects: ["Phase 7 (open items: nested-proxy unwrap convention, unbounded structlog pin, WR-02 residual status)", "the human-gated WeatherBot repin (ECOSYSTEM.md §3)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Phase-gate audit task: no source/test change, only evidence (commands + output) recorded into the SUMMARY, mirroring the 05-03 precedent"
    - "grimp include_external_packages=True required for a THIRD-PARTY-coupling gate (structlog) — the two pre-existing grimp gates in this file only ever check internal-package-prefixed edges and never needed the flag"

key-files:
  created: []
  modified:
    - EXTENSION-GUIDE.md
    - tests/test_import_hygiene.py

key-decisions:
  - "[Rule 1/3 deviation, Task 2] The plan's own acceptance-criteria grimp snippet omitted include_external_packages=True. Verified live (grimp 3.14): the default False drops every third-party edge from the graph entirely, not just offending ones — structlog never appears in ANY module's edge set under that default, including verify.py's genuine `import structlog`. Without the flag the new gate would be permanently vacuous regardless of what sink.py imports. Fixed by building the gate's own graph with include_external_packages=True."
  - "[Discovery, Task 2] processor.py, despite its own docstring's 'permitted to import structlog' framing (carried from 06-03's docstring voice), does NOT declare a direct `import structlog` edge — it imports only REDACTION_PROCESSOR_MARKER (a string constant) from verify.py. It stays in the gate's allowlist (matching the package docstring's stated permission), but the non-vacuity proof asserts the real structlog edge only for verify.py (the module whose introspection genuinely needs structlog.get_config()) rather than asserting a false edge for processor.py that the real source does not have."
  - "[Parity-status finding, Task 3] Both Phase-6-gated WeatherBot parity assertions are now satisfiable by RedactingWriter, but 05-VALIDATION.md's 'unmodified, only the import swapped' framing understates the repin work: RedactingWriter's constructor is (target, patterns, *, enabled, on_redaction), not _LiveStderr()'s parameterless constructor, so the two tests need a signature-level update at repin, not merely an import swap. Flagged in the close-out record below so the repin is not set up against a false expectation."

patterns-established: []

requirements-completed: [DOCS-04, REDACT-04, REDACT-05, REDACT-07, REDACT-08]

coverage:
  - id: D1
    description: "EXTENSION-GUIDE.md SEAM-08 row flipped to implemented plus its own ## 7. section, naming the architectural inversion, both D-54 recipes with the ordering constraint, the self-check discipline, the optional processor's non-substitutability, the counter's changed-writes semantics, and four known limitations — DOCS-04's literal ask"
    requirement: "DOCS-04"
    verification:
      - kind: other
        ref: "grep/python acceptance criteria run against EXTENSION-GUIDE.md (see Task 1 evidence below)"
        status: pass
    human_judgment: false
  - id: D2
    description: "test_redact_sink_never_imports_structlog proves the load-bearing sink/core/registry/barrel declare zero structlog edges while the allowlisted verify.py genuinely does, with its own self-proof against a synthetic injected edge (T-06-17)"
    requirement: "REDACT-04"
    verification:
      - kind: unit
        ref: "tests/test_import_hygiene.py#test_redact_sink_never_imports_structlog"
        status: pass
      - kind: unit
        ref: "tests/test_import_hygiene.py#test_selfproof_sink_framework_gate_catches_injected_edge"
        status: pass
    human_judgment: false
  - id: D3
    description: "redact_scanned litmus coverage guard extended to require all five redact/ module filenames (T-06-18)"
    requirement: "REDACT-05"
    verification:
      - kind: unit
        ref: "tests/test_import_hygiene.py#test_litmus_clean"
        status: pass
    human_judgment: false
  - id: D4
    description: "GATE-02 RED-first ancestry (adjacency, RED-ness, commit purity) independently re-derived from git trees for all three requirement plans (06-01, 06-02, 06-03), not asserted in prose (T-06-19)"
    requirement: "REDACT-07"
    verification:
      - kind: other
        ref: "git rev-parse / git ls-tree / git show commands, output recorded in this SUMMARY's GATE-02 Ancestry Proof section"
        status: pass
    human_judgment: false
  - id: D5
    description: "Standing gates green at phase close: full suite (153 passed, up from the 110-test milestone baseline), import-hygiene gate (10 passed), ruff clean, AST proof of zero structlog.configure() call sites in hub source, complete PC-01 surface imports"
    requirement: "REDACT-08"
    verification:
      - kind: other
        ref: "uv run pytest -q; uv run pytest tests/test_import_hygiene.py -q; uv run ruff check; AST scan (see Task 3 evidence below)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Human-gated close-out record: updated WeatherBot parity status (now 6/6 mechanically satisfiable, still requiring the human-gated repin to execute), the permanent client.py scope boundary, the unmissable httpx-gap flag, and the unperformed repin ritual checklist"
    requirement: "DOCS-04"
    verification: []
    human_judgment: true
    rationale: "This is a cross-repo, human-gated deliverable (ECOSYSTEM.md §3) — the record itself is complete and mechanically checkable for presence, but the repin it describes is explicitly NOT performed by this workflow and requires a human decision to execute."

duration: ~10min
completed: 2026-08-04
status: complete
---

# Phase 6 Plan 4: Phase gate — SEAM-08 documentation, sink framework-agnosticism gate, GATE-02 ancestry audit Summary

**`EXTENSION-GUIDE.md` SEAM-08 flipped to implemented (both table row and its own `## 7.` section), a new `test_redact_sink_never_imports_structlog` grimp gate proving the sink stays framework-agnostic, and GATE-02's RED-first ancestry independently re-derived from git trees for all three of this phase's requirement plans — closing Phase 6 with the full suite at 153 passed (up from the 110-test milestone baseline).**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-08-04T00:36Z
- **Tasks:** 3 (docs, test, audit-and-record)
- **Files modified:** 2 source-of-record files (`EXTENSION-GUIDE.md`, `tests/test_import_hygiene.py`) + this SUMMARY

## Accomplishments

- `EXTENSION-GUIDE.md`'s Plug-Point Summary table gained one new row (`RedactingWriter` /
  `redaction_processor` — SEAM-08 (P06) — **implemented**), and a new `## 7.` section
  follows the SEAM-04..07 layout: it states the architectural inversion first and
  unmissably (the module supplies mechanism; the HOST wires it into its OWN
  `structlog.configure()` — no redaction Protocol exists to go looking for), documents
  both of D-54's wiring recipes with the hard ordering constraint on recipe 2, the
  `assert_redaction_active` self-check discipline (call at boot AND after any
  reconfiguration), the optional processor's non-substitutability, the redaction
  counter's changed-writes semantics, and four known limitations stated plainly. The
  diff to the file is purely additive — zero lines removed, no other row or section
  touched.
- `tests/test_import_hygiene.py` gained a new, self-proved gate
  (`test_redact_sink_never_imports_structlog` +
  `test_selfproof_sink_framework_gate_catches_injected_edge`) encoding the phase's
  promote decision as an executable invariant: `sink.py`/`core.py`/`registry.py`/the
  package barrel declare zero `structlog` import edges, while `verify.py` — the module
  whose introspection genuinely needs `structlog.get_config()` — demonstrably does.
  Building this gate surfaced and fixed a real vacuity risk in the plan's own sketch
  (see Deviations).
- The `redact_scanned` litmus coverage guard was extended from `{core.py, registry.py}`
  to all five shipped module filenames (`core.py`, `registry.py`, `sink.py`, `verify.py`,
  `processor.py`), matching the standing lifecycle/registry/discord guard-shape
  convention, so a future relocation cannot silently drop `redact/` from litmus
  coverage.
- GATE-02's RED-first ancestry was independently re-derived from git trees — not
  asserted in prose — for all three of this phase's requirement plans (06-01, 06-02,
  06-03): adjacency via `git rev-parse`, RED-ness via `git ls-tree` (the test file
  present, the source module absent), and commit purity via `git show --name-only`. All
  three pairs verified clean on the first pass; no discrepancy to record.
- The full suite closed the phase at **153 passed** (110 → 151 across 06-01/02/03 → 153
  after this plan's two new tests), `uv run pytest tests/test_import_hygiene.py -q` at
  **10 passed**, `uv run ruff check` clean, and an AST-level scan confirms zero
  `*.configure()` call sites anywhere under `yahir_reusable_bot/` — the hub still never
  calls `structlog.configure()`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Flip SEAM-08 to implemented in EXTENSION-GUIDE.md (DOCS-04)** - `117a4be` (docs)
2. **Task 2: Extend the standing import-hygiene gate for the phase's new modules** - `656b30b` (test)

**Plan metadata / Task 3 (this commit, docs):** phase gate — GATE-02 ancestry proof and human-gated close-out record.

## Files Created/Modified

- `EXTENSION-GUIDE.md` — one new Plug-Point Summary row + `## 7.` SEAM-08 section (95
  lines added, 0 removed)
- `tests/test_import_hygiene.py` — extended `redact_scanned` coverage guard; added
  `_scan_framework_leaks`, `test_redact_sink_never_imports_structlog`,
  `test_selfproof_sink_framework_gate_catches_injected_edge` (111 lines added, 2
  removed)
- `.planning/phases/06-insertion-seams-provable-backstop/06-04-SUMMARY.md` — this file

## Decisions Made

See `key-decisions` in the frontmatter for the two Task-2 deviations and the Task-3
parity-status finding, expanded in full in **Deviations from Plan** and the **Close-Out
Record** below.

---

## Task 1 — EXTENSION-GUIDE.md SEAM-08 evidence

All acceptance criteria run and green:

```
$ grep -c 'SEAM-08' EXTENSION-GUIDE.md
3
$ grep -E '^\|.*SEAM-08.*\|' EXTENSION-GUIDE.md | grep -qi 'implemented' && echo OK
OK
$ grep -cE '^\|.*SEAM-08 \(P06\)' EXTENSION-GUIDE.md
1
$ grep -qE '^## 7\..*SEAM-08.*implemented' EXTENSION-GUIDE.md && echo OK
OK
$ grep -q 'yahir_reusable_bot/redact/' EXTENSION-GUIDE.md && echo OK
OK
# inversion tokens (invert, protocol) present after the first "seam-08" hit: OK
# all four public mechanisms (RedactingWriter, assert_redaction_active,
#   redaction_processor, REDACTION_PROCESSOR_MARKER) present: OK
# all seven concept tokens (limitation, proxy, buffer, boundary, "before any",
#   "changed writes", reconfigur) present: OK
$ git diff HEAD~1 -- EXTENSION-GUIDE.md | grep -cE '^-[^-]'
0
$ git show --name-only --pretty=format: HEAD | grep -vc 'EXTENSION-GUIDE.md'
0
```

## Task 2 — import-hygiene gate extension evidence

```
$ uv run pytest tests/test_import_hygiene.py -q
..........
10 passed in 0.29s
$ uv run pytest -q
153 passed, 1 warning in 2.14s
$ uv run ruff check
All checks passed!
$ uv run pytest tests/test_import_hygiene.py --collect-only -q | \
    grep -c 'test_redact_sink_never_imports_structlog\|test_selfproof_sink_framework_gate_catches_injected_edge'
2
$ grep -c '_scan_framework_leaks' tests/test_import_hygiene.py
5
$ git show --name-only --pretty=format: HEAD | grep -c 'yahir_reusable_bot/'
0
$ git show --name-only --pretty=format: HEAD | grep -c 'tests/conftest.py'
0
$ uv run pytest tests/test_import_hygiene.py --collect-only -q | \
    grep -c 'test_module_imports_zero_app_code\|test_config_module_never_imports_pydantic\|test_selfproof_import_gate_catches_injected_app_edge\|test_litmus_clean\|test_selfproof_litmus_catches_weather_noun'
5
```

## Task 3 — standing-gates evidence at phase close

```
$ uv run pytest -q
153 passed, 1 warning in 1.70s
$ uv run pytest tests/test_import_hygiene.py -q
..........
10 passed in 0.45s
$ uv run ruff check
All checks passed!
$ uv run python -c "
import ast, pathlib
bad=[str(p) for p in pathlib.Path('yahir_reusable_bot').rglob('*.py')
     for n in ast.walk(ast.parse(p.read_text(encoding='utf-8')))
     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr=='configure']
assert bad==[], bad"
OK — no configure() call sites
$ uv run python -c "
from yahir_reusable_bot.redact import (RedactionPattern, redact_secrets, register_patterns,
    RedactingWriter, assert_redaction_active, REDACTION_PROCESSOR_MARKER, redaction_processor)"
OK
$ for p in 06-01 06-02 06-03; do echo "$p: $(git log --oneline --pretty=%s | grep -c "($p)")"; done
06-01: 4
06-02: 3
06-03: 4
$ git diff --name-only HEAD~1 | grep -cE 'pyproject.toml|uv.lock'
0
```

Suite growth across the phase: **110** (milestone baseline, Phase 5 close) → **151**
(after 06-01/06-02/06-03) → **153** (after this plan's two new hygiene tests). Well past
baseline; matches the `1[5-9][0-9] passed` acceptance regex.

---

## GATE-02 Ancestry Proof (re-derived from git trees, not asserted in prose)

For each of the three requirement plans, three things are proven independently: **adjacency**
(the GREEN commit's parent is the RED commit), **RED-ness** (the RED commit's tree contains the
new test file and does NOT contain the source module it exercises), and **purity** (the RED
commit's changed paths are all under `tests/`; the GREEN commit's are all under
`yahir_reusable_bot/`).

### Plan 06-01 (`RedactingWriter`, REDACT-04 + REDACT-08)

- **RED:** `96ebefd8f0665570ff73e138b982d4e869b07807` — `test(06-01): RED — redacting sink, both wiring recipes, telemetry counter, dry-run probe`
- **GREEN:** `5cf35d633472e2df092467ec5222fb9220d836a3` — `feat(06-01): RedactingWriter sink — rendered-text backstop, counter, dry-run probe`

```
$ git rev-parse 5cf35d633472e2df092467ec5222fb9220d836a3^
96ebefd8f0665570ff73e138b982d4e869b07807          # == RED sha — ADJACENT

$ git ls-tree -r 96ebefd8f0665570ff73e138b982d4e869b07807 --name-only | grep -c 'tests/test_redact_sink.py'
1
$ git ls-tree -r 96ebefd8f0665570ff73e138b982d4e869b07807 --name-only | grep -c 'yahir_reusable_bot/redact/sink.py'
0                                                  # test present, source absent — GENUINELY RED

$ git show --name-only --pretty=format: 96ebefd8f0665570ff73e138b982d4e869b07807 | grep -vc '^tests/'
0                                                  # RED touches only tests/ — PURE
$ git show --name-only --pretty=format: 5cf35d633472e2df092467ec5222fb9220d836a3 | grep -vc '^yahir_reusable_bot/'
0                                                  # GREEN touches only yahir_reusable_bot/ — PURE
```

**Verdict:** ADJACENT, GENUINELY RED, PURE.

### Plan 06-02 (`assert_redaction_active`, REDACT-07)

- **RED:** `17ef1757598a10d927004ec6750047d7e54e8412` — `test(06-02): RED — assert_redaction_active introspection, deep probe, ordering warning`
- **GREEN:** `c13a9b941e06473afe895cc680a62577ab4aab87` — `feat(06-02): assert_redaction_active — wiring proof, deep probe, ordering warning`

```
$ git rev-parse c13a9b941e06473afe895cc680a62577ab4aab87^
17ef1757598a10d927004ec6750047d7e54e8412          # == RED sha — ADJACENT

$ git ls-tree -r 17ef1757598a10d927004ec6750047d7e54e8412 --name-only | grep -c 'tests/test_redact_verify.py'
1
$ git ls-tree -r 17ef1757598a10d927004ec6750047d7e54e8412 --name-only | grep -c 'yahir_reusable_bot/redact/verify.py'
0                                                  # test present, source absent — GENUINELY RED

$ git show --name-only --pretty=format: 17ef1757598a10d927004ec6750047d7e54e8412 | grep -vc '^tests/'
0
$ git show --name-only --pretty=format: c13a9b941e06473afe895cc680a62577ab4aab87 | grep -vc '^yahir_reusable_bot/'
0                                                  # both PURE
```

**Verdict:** ADJACENT, GENUINELY RED, PURE.

### Plan 06-03 (`redaction_processor`, REDACT-05)

- **RED:** `2ce4cd1beb752dd09599c592b0a187f67ffd1963` — `test(06-03): RED — optional redaction processor, ordering marker, pinned sink-necessity limitation`
- **GREEN:** `6bb4241b681c5c66bb4c696ff607144c776c98ba` — `feat(06-03): optional redaction processor — additive event-mapping scrubbing`

```
$ git rev-parse 6bb4241b681c5c66bb4c696ff607144c776c98ba^
2ce4cd1beb752dd09599c592b0a187f67ffd1963          # == RED sha — ADJACENT

$ git ls-tree -r 2ce4cd1beb752dd09599c592b0a187f67ffd1963 --name-only | grep -c 'tests/test_redact_processor.py'
1
$ git ls-tree -r 2ce4cd1beb752dd09599c592b0a187f67ffd1963 --name-only | grep -c 'yahir_reusable_bot/redact/processor.py'
0                                                  # test present, source absent — GENUINELY RED

$ git show --name-only --pretty=format: 2ce4cd1beb752dd09599c592b0a187f67ffd1963 | grep -vc '^tests/'
0
$ git show --name-only --pretty=format: 6bb4241b681c5c66bb4c696ff607144c776c98ba | grep -vc '^yahir_reusable_bot/'
0                                                  # both PURE
```

A third, immediately-following commit `67a4f42` (`test(06-03): fix RED test's formatter
choice for the positive scrub case`, a Rule 1 auto-fix documented in `06-03-SUMMARY.md`)
postdates this RED→GREEN pair and does not disturb its adjacency or purity — verified
directly above by resolving `GREEN^` to the RED sha, not by eyeballing `git log`.

**Verdict:** ADJACENT, GENUINELY RED, PURE.

**GATE-02 holds for REDACT-04, REDACT-05, REDACT-07 and REDACT-08.** All three pairs
passed independent re-derivation on the first check; no discrepancy was found, so
nothing was rationalised.

---

## Human-Gated Close-Out Record

Per `ECOSYSTEM.md` §3, everything below is **recorded for the human who performs the
repin**, and **none of it was performed by this workflow**.

### 1. WeatherBot parity status — updated now that the seam has shipped

`STATE.md` recorded that only 4 of 6 `test_redact_hygiene.py` assertions were reachable
after Phase 5. The two Phase-6-gated assertions and their satisfiability, read from the
actual WeatherBot test source
(`/home/yahir/Projects/WeatherBot/tests/test_redact_hygiene.py`) against what this phase
actually shipped:

| Assertion | Phase-5 status | Now (Phase 6 shipped) | Satisfied by |
|-----------|-----------------|------------------------|--------------|
| `test_discord_on_message_does_not_dump_key` | gated — needs the sink | **satisfiable** | `RedactingWriter` wrapping the `PrintLoggerFactory` render target (recipe 1, REDACT-04) — scrubs the FULL rendered traceback regardless of processor chain, exactly the property this assertion needs. |
| `test_livestderr_write_tolerates_and_scrubs_bytes` | gated — needs D-52 bytes tolerance at the seam | **satisfiable** | `RedactingWriter.write`'s D-52 triage (bytes decode-with-replace, then scrub) — the exact behavior `_LiveStderr.write` proved and this phase relocated into the hub sink. |

Both are now mechanically satisfiable by shipped hub mechanism — **6 of 6** assertions
are satisfiable in principle. **This does not mean the repin is a drop-in.**
`05-VALIDATION.md`'s framing ("re-pass unmodified... only the import swapped") is
**overstated** for these two: `RedactingWriter.__init__(target, patterns, *, enabled,
on_redaction)` is not a parameterless constructor like `_LiveStderr()` — WeatherBot's
test bodies will need a signature-level update (constructing `RedactingWriter(sys.stderr,
patterns)` with WeatherBot's own registered pattern set), not merely an import swap. Flag
this explicitly at repin time so the repin is not planned against a false "zero-touch"
expectation.

### 2. The scope boundary that does not move

`weatherbot/weather/client.py`'s domain-specific redacted re-raise stays app-local
**permanently** and is **not in scope** for the repin. `test_reraised_exception_request_carries_no_key`
(one of the four Phase-5-reachable assertions) is the scope-boundary check to re-run
untouched at repin — confirming `client.py` itself was not touched by the swap.

### 3. The httpx-class gap — flagged, not closed by this phase

**The hub upgrade does NOT by itself close WeatherBot's stdlib-logging bypass.**
`weatherbot/weather/client.py:48-54` documents that httpx's stdlib-`logging` INFO line
(carrying the API key in the request URL) bypasses a structlog-only backstop entirely.
D-54 recipe 2 (`sys.stderr = RedactingWriter(sys.stderr, patterns)`) is the hub-side
answer and **ships in this phase** — but *adopting* recipe 2 in WeatherBot's own
composition root is a **consumer decision at repin time**, not something the hub upgrade
performs on its own. **The repin must not silently assume the hub upgrade closes this
gap** — it closes it only if the human wiring the repin explicitly adopts recipe 2.

### 4. Wiring-order warning for the consumer (if recipe 2 is adopted)

If the repin adopts D-54 recipe 2, the `sys.stderr = RedactingWriter(sys.stderr,
patterns)` assignment **must** happen before any stdlib `logging` handler is
constructed (before `logging.basicConfig()`, and before importing any third-party
library that constructs its own handler at import time) — an already-bound handler
resolves its stream at construction time and keeps writing to the original,
un-redacted `sys.stderr` even after the swap (RESEARCH Pitfall 6).

### 5. The repin ritual steps — unperformed, all human-gated (`ECOSYSTEM.md` §3/§7)

None of the following was performed by this workflow:

- [ ] **NOT DONE** — version bump (`pyproject.toml` `0.1.2 → 0.2.0` per `PROJECT.md`)
- [ ] **NOT DONE** — cut the `v0.2.0` git tag
- [ ] **NOT DONE** — bump WeatherBot's `[tool.uv.sources]` pin to the new tag
- [ ] **NOT DONE** — `uv lock --upgrade-package yahir-reusable-bot` in WeatherBot
- [ ] **NOT DONE** — `uv sync --frozen` in WeatherBot
- [ ] **NOT DONE** — run WeatherBot's own test suite against the repinned hub, including
      the updated 6-assertion parity gate above (with the signature-update caveat)
- [ ] **NOT DONE** — delete WeatherBot's local `_redact.py` / `_LiveStderr` in favor of
      `from yahir_reusable_bot.redact import RedactingWriter, ...`
- [ ] **NOT DONE** — deploy / restart on `yahir-mint`
- [ ] **NOT DONE** — verify PC-01's repin independently of WR-02/MATCH-03 (a separate,
      unrelated breaking change bundled in the same milestone) rather than in one
      combined run, per `05-VALIDATION.md`'s Manual-Only row

`git diff --name-only HEAD~1 | grep -cE 'pyproject.toml|uv.lock'` returned `0` for this
plan's own commit, confirming no dependency manifest or lock file was touched by this
workflow.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1/3 - Bug/Blocking] The plan's own acceptance-criteria grimp snippet made the
new gate permanently vacuous**

- **Found during:** Task 2's implementation of `test_redact_sink_never_imports_structlog`.
- **Issue:** The plan's `<action>` instructed building the graph identically to the two
  existing grimp gates (`grimp.build_graph(MODULE, cache_dir=None)`, no
  `include_external_packages` argument). Verified live (grimp 3.14): with the default
  `include_external_packages=False`, grimp drops **every** third-party edge from the
  graph entirely — `structlog` never appears in ANY module's edge set under that
  default, including `verify.py`'s genuine `import structlog`. Running the plan's own
  acceptance-criteria python snippet verbatim against the real (correct, unmodified)
  source **failed** at the `assert 'structlog' in edges('...verify')` line — proving
  this was a defect in the plan's verification script, not in the shipped code.
- **Fix:** Built the new gate's own grimp graph with `include_external_packages=True`.
  This is a deliberate, necessary deviation from the two pre-existing grimp gates in
  this file, which only ever check internal-package-prefixed edges (`weatherbot.*`,
  which — being unresolvable and never installed — behaves identically either way for
  their purposes) and never needed the flag.
- **Files modified:** `tests/test_import_hygiene.py` (the new gate's `grimp.build_graph`
  call).
- **Verification:** `uv run pytest tests/test_import_hygiene.py -q` — 10 passed,
  including the new gate genuinely detecting `verify.py`'s real `structlog` edge (not a
  false pass from a permanently-empty external-edge set).
- **Commit:** `656b30b` (Task 2 commit).

**2. [Rule 1 - Discovery, documented not "fixed"] `processor.py` does not declare a
direct `structlog` import edge, despite its own docstring's "permitted to import
structlog" framing**

- **Found during:** Task 2, while designing the non-vacuity half of the new gate
  (proving the allowlisted modules genuinely couple to `structlog`).
- **Issue:** `processor.py`'s docstring (06-03) states it is "the second and last
  module under `redact/` permitted to import `structlog`," implying — and 06-03's own
  SUMMARY restates — a real import edge symmetric with `verify.py`'s. Live grimp
  inspection (`include_external_packages=True`) shows `processor.py`'s actual edges are
  `{__future__, collections, yahir_reusable_bot.redact.core, yahir_reusable_bot.redact.verify}`
  — **no `structlog` edge at all**. It imports only `REDACTION_PROCESSOR_MARKER` (a
  string constant) from `verify.py`; nothing in `processor.py`'s function bodies or
  type annotations requires importing `structlog` itself.
- **Resolution:** This is not a bug to fix (Task 2 explicitly forbids modifying any file
  under `yahir_reusable_bot/`, and adding a needless `import structlog` purely to
  satisfy a documentation claim would be worse — a manufactured edge with no functional
  purpose). It is a genuinely **stronger purity property** than the docstring implies:
  `processor.py` stays in the gate's allowlist (matching the documented *permission*,
  and future-proofing against a later version that does add the import), but the
  non-vacuity assertion is written honestly — it proves the real edge only for
  `verify.py`, the module whose introspection genuinely needs
  `structlog.get_config()`/`PrintLoggerFactory`/`WriteLoggerFactory`, rather than
  asserting a false universal claim the actual source does not support.
- **Files modified:** `tests/test_import_hygiene.py` (test docstring and assertion
  design only — no source file touched).
- **Commit:** `656b30b` (Task 2 commit).

---

**Total deviations:** 2 (1 blocking-bug fix in the new gate's own construction, 1
documented discovery about `processor.py`'s actual coupling that changed how the
non-vacuity proof was worded).
**Impact on plan:** Both were necessary for the new gate to actually prove what T-06-17
claims it proves. No scope creep — no source file was touched by either.

## Issues Encountered

None beyond the two deviations above, both caught and resolved within Task 2's own
verification loop before that commit landed.

## User Setup Required

None - no external service configuration required. The human-gated repin (see Close-Out
Record above) is a separate, cross-repo action for a human to perform on their own
schedule.

## Next Phase Readiness — open items for Phase 7 and beyond

- **The nested-proxy unwrap convention** (RESEARCH Open Question 2, assumption A1) —
  `assert_redaction_active` hard-raises for a writer nested inside a consumer's own
  proxy, with no unwrap convention built. Revisit only if the repin hits real friction
  from this in practice (rule of three) — do not build it speculatively.
- **The unbounded `structlog` dependency version pin** (`structlog>=26.1.0`, no upper
  bound) — the private-attribute coupling (`PrintLoggerFactory._file` /
  `WriteLoggerFactory._file`) `assert_redaction_active` reads rides on this pin. A
  future `structlog` release renaming/removing that attribute will surface as a loud,
  distinct `ValueError` naming the installed version (by design, RESEARCH Pitfall 5) —
  not a silent pass — but the underlying fragility remains standing, unresolved by this
  phase.
- **The Phase-5 WR-02 residual** — re-checked by 06-03 per `CONTEXT.md`'s
  deferred-ideas instruction and confirmed it stays correctly closed:
  `redaction_processor` never places a `RedactionPattern` instance into an
  `event_dict` (it reads patterns from its closure and writes only scrubbed strings
  back). `RedactionPattern.asdict()`/`astuple()` still expose the raw pattern source —
  deliberately left open per the Phase-5 addendum (`05-VALIDATION.md`), unchanged by
  this phase, no new trigger surfaced.
- Phase 6 is now closed. Phase 7 (Track B — debt closure: MATCH-03, LIFE-05, SURF-02,
  DISC-07/08, HYG-02/03, DOCS-02/03) is next per `ROADMAP.md`. Its discuss step must
  surface **LIFE-05** and **SURF-02** as explicit human decisions per `STATE.md` §Todos
  — both deliberately deferred once already; neither may be defaulted.
- No blockers.

---
*Phase: 06-insertion-seams-provable-backstop*
*Completed: 2026-08-04*
