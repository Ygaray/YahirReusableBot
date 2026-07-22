# Phase 1: Reachable reliability - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the two hub defects that are live and unmitigated in WeatherBot **today**, each with a
RED-first regression test:

- **RELY-01 (H02)** — `reliability/retry.py:87` `is_transient` misses common httpx network/protocol
  failures, so the two-burst retry never fires and a routine mid-response hangup silently drops a
  delivery.
- **LIFE-01 (H01)** — `lifecycle/identity.py:149` `_argv_matches_marker` tests `-m` and the marker
  by membership in overlapping slices, producing both a false positive (recycled PID running the
  marker as a positional arg can be SIGHUP'd) and a false negative (a daemon started with an
  interpreter flag before `-m` is reported not running).

Phase 1 is also, unavoidably, the phase that **founds the hub's unit-test substrate** — there are
currently no tests for any module except `gateway` and the import-hygiene gate. Conventions set
here are inherited by the 13 remaining findings in Phases 2–4.

**Not in this phase:** every other H-number. Notably `LIFE-03` (H15, path-shaped `proc_marker`)
touches the same function as LIFE-01 but is explicitly Phase 3 — do not fold it in.

</domain>

<decisions>
## Implementation Decisions

### Transient classification (RELY-01)

- **D-01:** `is_transient` broadens to
  `isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError))`.
  The `httpx.HTTPStatusError` / `TRANSIENT` status branch below it is unchanged.
- **D-02:** **Deny-by-default is the locked posture.** `LocalProtocolError` (client-side bug),
  `ProxyError`, and `UnsupportedProtocol` all stay **non**-transient. Explicitly rejected:
  a `TransportError`-shaped rule (blanket or minus-a-deny-list). Rationale: a wrong retry burns
  ~75 min of a delivery window silently, and the hub cannot see its consumers' failure modes, so
  an unrecognized future httpx exception must fail closed rather than retry 16 times.
- **D-03:** Verified against the **installed `httpx 0.28.1`** class tree (not from memory):
  `TransportError` → `NetworkError` (`CloseError`, `ConnectError`, `ReadError`, `WriteError`),
  `ProtocolError` (`LocalProtocolError`, `RemoteProtocolError`), `ProxyError`,
  `TimeoutException` (`ConnectTimeout`, `PoolTimeout`, `ReadTimeout`, `WriteTimeout`),
  `UnsupportedProtocol`. Consequence worth stating in the fix's docstring: the current tuple's real
  misses are `WriteError`, `CloseError`, and `RemoteProtocolError` — `PoolTimeout` was already
  covered via `TimeoutException`.

### argv position rule (LIFE-01)

- **D-04:** `_argv_matches_marker` uses a **first-`-m` scan**: find the lowest index `i` where
  `argv[i] == b"-m"`, then require `argv[i + 1] == proc_marker` (with a bounds check). The existing
  `argv0`-basename branch above it is unchanged.
- **D-05:** **The report's literal fix is rejected on evidence.**
  `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:92` prescribes
  `len(argv) >= 3 and argv[1] == b"-m" and argv[2] == proc_marker`. That **fails the phase's own
  ROADMAP success criterion**: in `python -O -m <marker> run`, `argv[1]` is `-O` and `-m` sits at
  `argv[2]`, so a live daemon would report not-running — H01's false-negative half, uncorrected.
  The planner must implement D-04, not the report's text. *(The report is otherwise authoritative;
  this is a single located correction, not a reason to distrust it.)*
- **D-06:** "First `-m` wins" is load-bearing and must be stated in the docstring as the rule, not
  left as a heuristic: it mirrors Python's own CLI grammar (everything after `-m <mod>` is the
  module's argv), which is what makes the `python -m pytest -m <marker>` case — pytest's own `-m`
  marker selector — resolve correctly.
- **D-07:** Rejected: additionally asserting `argv[0]` looks like a Python interpreter. It closes a
  vanishingly rare false positive (a non-Python program taking `-m <marker>`) at the cost of
  breaking legitimate daemons on pypy / custom-named interpreters — a worse failure in a hub that
  must not assume its consumer's runtime.

**Required truth table for D-04 (all four rows are acceptance criteria):**

| argv | required |
|---|---|
| `python -m pytest <marker>` | **no match** — recycled-PID decoy; a SIGHUP here hits an unrelated process |
| `python -O -m <marker> run` | **match** — real daemon behind an interpreter flag |
| `python -m <marker> run` | match |
| `<marker> run` | match — via the existing `argv0`-basename branch, not the `-m` branch |

### Test substrate (founds the convention for Phases 2–4)

- **D-08:** Flat files mirroring module names: `tests/test_retry.py`, `tests/test_identity.py`.
  No package-mirroring subdirectories.
- **D-09:** **Add `tests/conftest.py`** — a deliberate departure from the currently documented
  convention (`.planning/codebase/TESTING.md:36` "No conftest.py"; `:142` "No `@pytest.fixture`
  decorators in use"). This is an intentional convention change, not an oversight.
- **D-10:** The conftest stays **minimal — only what Phase 1's two test files actually need**:
  an instant-return fake `stop_event` (a `.wait(timeout)` that returns immediately, so the 2700s
  mid-pause can never run for real) and a NUL-separated cmdline-bytes builder. Nothing speculative
  for Phases 2–4; it grows when a real second caller appears, matching the repo's own
  build-in-consumer-then-promote discipline.
- **D-11:** Reuse the repo's existing RED-first idiom rather than inventing one. `test_selfproof_*`
  in `tests/test_import_hygiene.py` already encodes "prove this test is not a no-op"
  (`TESTING.md:209-234`) — align naming and docstring posture with it.
- **D-12:** Both seams needed are already injectable in production code — no new test hooks:
  `is_running_process(..., cmdline_reader=...)` and
  `build_retrying(stop_event, attempts_per_burst=, burst_spread_s=, mid_pause_s=)`.

### RED-first proof

- **D-13:** **Two commits per fix** — commit 1 lands the failing regression test, commit 2 lands the
  fix. Git history is the proof that the test was RED against pre-fix source. Four commits total.
- **D-14:** Work happens on a **phase branch, merged at phase end.** `main` only ever receives green
  commits. Driven by `ECOSYSTEM.md` §3 making tags the consumer contract plus bisect safety.
- **D-15:** **State plainly in the plan that there is no CI** (`TESTING.md:264` — no
  `.github/workflows`, no pre-commit hooks). "Green" is enforced by `uv run pytest` run locally by
  the executor. The plan must not imply a pipeline gate that does not exist; the branch decision is
  about history hygiene, not build notifications.

### Regression test depth

- **D-16:** RELY-01 gets **both** levels: classifier truth-table asserts **and** driving
  `build_retrying` to exhaustion (`attempts_per_burst=2`, `burst_spread_s=0`, `mid_pause_s=0`, a
  callable that always raises `RemoteProtocolError`) — assert the attempt count and that the
  `RemoteProtocolError` escapes as itself.
- **D-17:** **The hub-side observable, restated.** The ROADMAP criterion "reports
  `transient_exhausted` on exhaustion instead of `internal_error`" is **not literally assertable in
  this repo** — `REASON_TRANSIENT_EXHAUSTED` is *defined* at `retry.py:75` but nothing here assigns
  it; `fire_slot`, which picks the reason, is consumer-side in WeatherBot. The hub-scoped equivalent
  the tests MUST assert instead:

  > an exhausted `RemoteProtocolError` propagates out of `Retrying.__call__` **as itself, not as a
  > `tenacity.RetryError`**

  This is the exact mechanism behind the consumer symptom — see `retry.py:200-211`, where
  `retry_error_callback=lambda rs: rs.outcome.result()` exists precisely because a bare
  `reraise=True` yields `RetryError`, and `RetryError` is what the consumer mis-classifies as
  `internal_error`. Planner: write the `must_haves` truth against this restatement, not the
  literal string.
- **D-18:** Rejected: replicating `fire_slot`'s reason-picking in a hub test so the literal string
  `"transient_exhausted"` can be asserted. The hub would be testing logic it does not own, and
  encoding consumer behavior in hub tests is a genericity smell in a repo with a standing litmus
  gate.
- **D-19:** LIFE-01's regression tests cover all four rows of the D-04 truth table, including both
  adversarial cases (the positional-arg decoy and the flag-before-`-m` daemon) — not just a new
  happy path.

### Claude's Discretion

- Exact fixture names and signatures in `tests/conftest.py` (within the D-10 minimal bound).
- Whether the two fixes ship as one plan or two — they touch disjoint files
  (`reliability/retry.py` vs `lifecycle/identity.py`) with no shared symbol, so either is defensible.
- Exact test-function names, though they should follow the `TESTING.md` module-level-function,
  docstring-first, no-mocking-library house style (D-11).
- Whether `pytest.raises()` is used for D-16's escape assertion — it would be the repo's first use
  (`TESTING.md:239`); a `try/except` + `assert isinstance` is equally acceptable.
- Docstring wording for the two fixed functions, provided D-02, D-06, and D-17 are stated.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source of record for the findings
- `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md` — fix direction per finding. **H01 is at :87-94,
  H02 at :96-107.** Note D-05: the H01 fix text at `:92` is superseded by D-04 in this document.
- `.planning/backlog/HUB-FINDINGS-HANDOFF.md` — full failure scenario and evidence per finding.
- `.planning/REQUIREMENTS.md` — RELY-01 at `:26-30`, LIFE-01 at `:39-41`, GATE-01 at `:93-95`.
- `.planning/ROADMAP.md` §"Phase 1: Reachable reliability" (`:27-41`) — the four success criteria.

### Files being modified
- `yahir_reusable_bot/reliability/retry.py` — `is_transient` at `:80-91`; read `:184-248`
  (`build_retrying`) for why the `RetryError`-vs-real-exception distinction is load-bearing (D-17).
- `yahir_reusable_bot/lifecycle/identity.py` — `_argv_matches_marker` at `:130-149`; the
  `argv0`-basename branch at `:145-147` is unchanged.

### Test conventions and standing gates
- `.planning/codebase/TESTING.md` — house style. **Will be stale after this phase** (D-09 adds the
  conftest its `:36` and `:142` say does not exist). Key live conventions: flat `tests/`,
  module-level `test_*()` functions, docstring-first, no mocking library, synthetic inline test
  doubles, `test_selfproof_*` naming (`:209-234`), no CI (`:264`).
- `tests/test_gateway.py` — the only behavioral-test precedent (30 lines); match its shape.
- `tests/test_import_hygiene.py` — the standing GATE-01 gate. Must stay green; also the source of
  the `test_selfproof_*` idiom (D-11).

### Project constitution
- `ECOSYSTEM.md` §3 — human-gated close-out; why tags are the consumer contract (D-14).
- `CLAUDE.md` (repo root) — hub rules: one-way dependency, `discord.py==2.7.1` exact pin, no domain
  nouns in the public surface.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `is_running_process(pid, *, proc_marker, cmdline_reader=None)` — `cmdline_reader` is an
  already-parameterized injection point for stubbing the `/proc` read. No new seam needed for
  LIFE-01's tests.
- `build_retrying(stop_event, *, attempts_per_burst, burst_spread_s, mid_pause_s)` — all three
  schedule constants are already keyword-overridable, so D-16's exhaustion test runs instantly
  instead of sleeping through the 2700s mid-pause.
- `tests/test_import_hygiene.py` `test_selfproof_*` pattern — a working, in-repo precedent for
  "prove the test is not a no-op" that the RED-first requirement should inherit (D-11).

### Established Patterns
- Tests are flat, self-contained, module-level functions with a docstring explaining *why*; no
  fixtures, no mocking library, synthetic inline doubles. D-09 changes only the fixtures part.
- The module's docstrings carry decision rationale inline (see `retry.py:1-37` and
  `identity.py:1-25`). Both fixes should extend that habit — D-02's deny-by-default posture and
  D-06's first-`-m` rule belong in the docstrings, not just the commit message.
- Deliberate degrade-vs-raise split in `identity.py`: the writer re-raises, the guard/reader degrade
  cleanly. LIFE-01 is in the *guard*, so it must keep degrading (return `False`), never raise.

### Integration Points
- `is_transient` is consumed by `build_retrying`'s `retry_if_exception(is_transient)` predicate
  (`retry.py:239`) and is public surface a consumer can call directly. Broadening it is a silent
  behavior change for every consumer at repin — the change belongs in the phase summary handed to
  the human-gated close-out.
- `_argv_matches_marker` is private, reached only via `is_running_process`. Its blast radius is the
  reload/SIGHUP path.

### Discovered during scouting (not previously recorded)
- **The hub has no unit tests for `retry.py` or `identity.py` — or for `reload.py`, `registry/`,
  `scheduler/`, or `panelkit`.** `tests/` is exactly `test_gateway.py` (30 lines) and
  `test_import_hygiene.py` (354 lines). The `test_reload.py:561` that the report cites as existing
  decoy coverage lives in **WeatherBot**, not in this repo — so Phase 1 is not adding a case to an
  existing suite, it is creating the first one.
- No `conftest.py` and no `pytest.raises()` usage anywhere in the repo today.

</code_context>

<specifics>
## Specific Ideas

- The `python -m pytest -m <marker>` case (pytest's own `-m` marker-selector flag colliding with the
  interpreter's `-m`) is the sharpest available proof that "**first** `-m`" is the right rule and
  not merely a convenient one. Worth an explicit test case even though it is not in the ROADMAP's
  four criteria.
- D-17's restatement is the single most important thing to carry into `must_haves`. Written
  literally from the ROADMAP, the criterion is unprovable in this repo and would either produce a
  test that asserts nothing or push a consumer-logic replica into the hub (D-18).

</specifics>

<deferred>
## Deferred Ideas

- **`ProxyError` as transient** (report option A3). Genuinely arguable — a proxy hiccup is transient
  in the same sense `RemoteProtocolError` is. Deferred because neither current transport proxies
  (OpenWeather via httpx directly, Discord via `discord.py`), so it would be unreachable code with
  no honest RED-first test behind it. Revisit as a one-line change the first time a consumer runs
  behind a proxy and has a real reproduction.
- **Making the transient classifier injectable/configurable per consumer.** Raised implicitly by
  D-02's "the hub cannot see its consumers' failure modes." That is a new capability, not a fix —
  belongs in its own phase, and only under the repo's rule-of-three promotion discipline once a
  second consumer actually wants a different boundary.
- **Refresh `.planning/codebase/TESTING.md`** after Phase 1 lands, since D-09 invalidates its `:36`
  and `:142` claims. Housekeeping, not phase scope.

</deferred>

---

*Phase: 1-reachable-reliability*
*Context gathered: 2026-07-22*
