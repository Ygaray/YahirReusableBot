# Phase 1: Reachable reliability - Research

**Researched:** 2026-07-22
**Domain:** httpx exception classification for a tenacity retry engine; `/proc/<pid>/cmdline` argv
matching for a process-identity guard; founding a pytest unit-test substrate with zero prior
coverage of either module.
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

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
- **D-04:** `_argv_matches_marker` uses a **first-`-m` scan**: find the lowest index `i` where
  `argv[i] == b"-m"`, then require `argv[i + 1] == proc_marker` (with a bounds check). The existing
  `argv0`-basename branch above it is unchanged.
- **D-05:** **The report's literal fix is rejected on evidence.**
  `.planning/backlog/HUB-HARDENING-REPORT-v0.1.2.md:92` prescribes
  `len(argv) >= 3 and argv[1] == b"-m" and argv[2] == proc_marker`. That **fails the phase's own
  ROADMAP success criterion**: in `python -O -m <marker> run`, `argv[1]` is `-O` and `-m` sits at
  `argv[2]`, so a live daemon would report not-running. The planner must implement D-04, not the
  report's text.
- **D-06:** "First `-m` wins" is load-bearing and must be stated in the docstring as the rule, not
  left as a heuristic — it mirrors Python's own CLI grammar (everything after `-m <mod>` is the
  module's argv), which is what makes the `python -m pytest -m <marker>` case (pytest's own `-m`
  marker selector) resolve correctly.
- **D-07:** Rejected: additionally asserting `argv[0]` looks like a Python interpreter. Closes a
  vanishingly rare false positive at the cost of breaking legitimate daemons on pypy / custom-named
  interpreters.

**Required truth table for D-04 (all four rows are acceptance criteria):**

| argv | required |
|---|---|
| `python -m pytest <marker>` | **no match** — recycled-PID decoy; a SIGHUP here hits an unrelated process |
| `python -O -m <marker> run` | **match** — real daemon behind an interpreter flag |
| `python -m <marker> run` | match |
| `<marker> run` | match — via the existing `argv0`-basename branch, not the `-m` branch |

- **D-08:** Flat files mirroring module names: `tests/test_retry.py`, `tests/test_identity.py`.
  No package-mirroring subdirectories.
- **D-09:** **Add `tests/conftest.py`** — a deliberate departure from the currently documented
  convention. Intentional convention change, not an oversight.
- **D-10:** The conftest stays **minimal — only what Phase 1's two test files actually need**: an
  instant-return fake `stop_event` (`.wait(timeout)` returns immediately) and a NUL-separated
  cmdline-bytes builder. Nothing speculative for Phases 2–4.
- **D-11:** Reuse the repo's existing RED-first idiom (`test_selfproof_*` in
  `tests/test_import_hygiene.py`) rather than inventing one.
- **D-12:** Both seams needed are already injectable in production code — no new test hooks:
  `is_running_process(..., cmdline_reader=...)` and
  `build_retrying(stop_event, attempts_per_burst=, burst_spread_s=, mid_pause_s=)`.
- **D-13:** **Two commits per fix** — commit 1 lands the failing regression test, commit 2 lands the
  fix. Git history is the proof. Four commits total.
- **D-14:** Work happens on a **phase branch, merged at phase end.** `main` only ever receives green
  commits.
- **D-15:** **State plainly in the plan that there is no CI.** "Green" is enforced by
  `uv run pytest` run locally by the executor.
- **D-16:** RELY-01 gets **both** levels: classifier truth-table asserts **and** driving
  `build_retrying` to exhaustion (`attempts_per_burst=2`, `burst_spread_s=0`, `mid_pause_s=0`, a
  callable that always raises `RemoteProtocolError`) — assert the attempt count and that the
  `RemoteProtocolError` escapes as itself.
- **D-17:** **The hub-side observable, restated.** "Reports `transient_exhausted` instead of
  `internal_error`" is not literally assertable in this repo (`fire_slot` is consumer-side). The
  hub-scoped equivalent the tests MUST assert instead:

  > an exhausted `RemoteProtocolError` propagates out of `Retrying.__call__` **as itself, not as a
  > `tenacity.RetryError`**

  Write `must_haves` truth against this restatement, not the literal string.
- **D-18:** Rejected: replicating `fire_slot`'s reason-picking in a hub test so the literal string
  `"transient_exhausted"` can be asserted.
- **D-19:** LIFE-01's regression tests cover all four rows of the D-04 truth table, including both
  adversarial cases — not just a new happy path.

### Claude's Discretion

- Exact fixture names and signatures in `tests/conftest.py` (within the D-10 minimal bound).
- Whether the two fixes ship as one plan or two — they touch disjoint files
  (`reliability/retry.py` vs `lifecycle/identity.py`) with no shared symbol, so either is defensible.
- Exact test-function names, though they should follow the `TESTING.md` module-level-function,
  docstring-first, no-mocking-library house style (D-11).
- Whether `pytest.raises()` is used for D-16's escape assertion — a `try/except` +
  `assert isinstance` is equally acceptable. *(Research note: this would NOT be the repo's literal
  first use — see Pitfall/Code Examples section; `pytest.raises` already appears once, in
  `tests/test_import_hygiene.py:243`. This does not affect the decision, just its stated novelty.)*
- Docstring wording for the two fixed functions, provided D-02, D-06, and D-17 are stated.

### Deferred Ideas (OUT OF SCOPE)

- **`ProxyError` as transient** (report option A3). Deferred because no current transport proxies
  (OpenWeather via httpx directly, Discord via `discord.py`), so it would be unreachable code with
  no honest RED-first test behind it.
- **Making the transient classifier injectable/configurable per consumer.** A new capability, not a
  fix — its own phase, and only under the repo's rule-of-three promotion discipline.
- **Refresh `.planning/codebase/TESTING.md`** after Phase 1 lands (D-09 invalidates its `:36` and
  `:142` claims). Housekeeping, not phase scope.
- **`LIFE-03` (H15, path-shaped `proc_marker`)** touches the same function as LIFE-01 but is
  explicitly Phase 3 — do not fold in.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RELY-01 (H02) | Broaden `is_transient` to classify `RemoteProtocolError`/`WriteError` as transient (deny-by-default, not blanket `TransportError`); exhausted transient errors must escape `Retrying.__call__` as themselves, not `RetryError`. | Verified installed `httpx 0.28.1` class tree; empirically reproduced the pre-fix miss (`is_transient` returns `False` for `RemoteProtocolError`/`WriteError`/`LocalProtocolError`); empirically confirmed the post-fix escape-as-itself mechanism via `retry_error_callback=lambda rs: rs.outcome.result()` against installed `tenacity 9.1.4`, including the RetryError-vs-reraise contrast. See Code Examples + Common Pitfalls. |
| LIFE-01 (H01) | Fix `_argv_matches_marker`'s overlapping-slice membership test so it matches program identity, not token position tolerance. | Verified all four D-04 truth-table rows empirically against the CURRENT production function — confirmed the false-positive decoy (`python -m pytest <marker>` → currently `True`, must become `False`) and found an additional false-negative form (`python -O -B -m <marker> run`, two flags before `-m`) that sharpens the D-04 rationale. See Common Pitfalls. |
</phase_requirements>

## Summary

Both defects are narrow, mechanical bugs in code the phase already has exact line ranges for, and
both were reproduced empirically against the installed dependency versions in this repo's own
`.venv` rather than reasoned about from memory — this research trades breadth for certainty on a
two-function phase.

For RELY-01, the installed `httpx 0.28.1` class tree was walked directly via `inspect`/`__bases__`
and matches CONTEXT.md's D-03 table exactly: `RemoteProtocolError` and `WriteError` inherit from
`ProtocolError`/`NetworkError` respectively, both under `TransportError`, and neither is currently
caught by `is_transient`'s tuple (`TimeoutException, ConnectError, ReadError`). Running the current
function against real exception instances confirms the miss directly: `is_transient` returns
`False` for `RemoteProtocolError`, `WriteError`, and (correctly, pre- and post-fix) `LocalProtocolError`.
The retry-exhaustion mechanism (D-17) was also reproduced against the installed `tenacity 9.1.4`:
with the D-01 classifier fix wired into a `Retrying` built exactly like `build_retrying`, an
exhausted `RemoteProtocolError` escapes `Retrying.__call__` as itself — because
`retry_error_callback=lambda rs: rs.outcome.result()` calls `.result()` on the final failed
`Future`, which re-raises the original exception. Removing that callback (bare default, or even
`reraise=True` in some code paths) instead raises `tenacity.RetryError` wrapping the original — this
is the exact bug class the consumer's `internal_error` misclassification traces to, verified by
running both variants side by side.

For LIFE-01, running the *actual current* `_argv_matches_marker` against all four D-04 truth-table
rows shows it returns `True` for **every** row, including the row that must be `False` (the
`python -m pytest <marker>` recycled-PID decoy) — the live false-positive bug, confirmed by
execution, not inference. A fifth, previously undocumented form —
`python -O -B -m <marker> run` (two interpreter flags before `-m`) — was found to return `False`
under current code (a genuine false negative the D-04 first-`-m`-scan rule fixes) and is worth
adding as a fifth regression case beyond the four locked rows. `python -m pytest -m <marker>` (the
CONTEXT.md-cited sharpest proof for "first `-m` wins") was also verified: it returns `False` under
both current code and the D-04 rule, so its value is as a discriminator against a *hypothetical*
naive "any `-m` token, any position" rule, not against current production behavior — worth stating
precisely in the plan so it isn't miscast as reproducing today's bug.

Both fixes are pure logic changes with zero new dependencies — `httpx`, `tenacity`, and `pytest`
are already pinned and installed at the versions checked here. The phase's second job, founding the
hub's first behavioral-test substrate for anything beyond `gateway.py`, has one concrete precedent
worth correcting: `TESTING.md:239` claims `pytest.raises()` is unused in the repo, but
`tests/test_import_hygiene.py:243` already uses it once (with an `exc_info` message assertion) —
a usable in-repo precedent for D-16's discretion point on the escape assertion.

**Primary recommendation:** Implement D-01 and D-04 exactly as locked; write both regression tests
FIRST against verified reproductions of the pre-fix behavior (the empirical outputs recorded in this
document), commit them RED, then commit the one-line-ish fixes GREEN — no exploration needed, the
defects and the fix shapes are already fully characterized.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Transient-failure classification (`is_transient`) | Hub library (`reliability/retry.py`) | — | Pure classification logic; no I/O, no consumer-specific knowledge. Owned entirely by the hub per D-02's "hub cannot see consumer failure modes" posture. |
| Retry scheduling + exhaustion escape semantics (`build_retrying`, `Retrying.__call__`) | Hub library (`reliability/retry.py`) | tenacity (3rd-party) | The hub composes `tenacity` primitives; the escape-as-itself contract is a hub-owned wiring decision (`retry_error_callback`), not a tenacity default. |
| Reason-taxonomy assignment (`transient_exhausted` vs `internal_error` string) | Consumer composition root (WeatherBot `fire_slot`) | — | Confirmed out of hub scope — `REASON_TRANSIENT_EXHAUSTED` is *defined* in the hub but never *assigned* here (D-17). Hub tests must stop at "escapes as itself," not the consumer's string. |
| Process-identity / argv matching (`_argv_matches_marker`, `is_running_process`) | Hub library (`lifecycle/identity.py`) | OS (`/proc` filesystem) | Hub owns the matching algorithm; the OS owns the ground truth (`/proc/<pid>/cmdline`) the hub reads via an injectable reader. |
| Signal delivery decision (whether to SIGHUP a PID) | Consumer composition root (daemon reload path) | Hub (`is_running_process` as the gate) | Not in this phase's fix surface — `is_running_process`'s boolean is the gate a consumer's reload logic acts on; the hub only answers "is this the right process," it doesn't send signals. |
| Test substrate conventions (fixtures, RED-first idiom, file layout) | Hub repo (`tests/`) | — | Founded in this phase; inherited by Phases 2–4 per CONTEXT.md's phase-boundary note. |

## Standard Stack

### Core

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 [VERIFIED: `uv run python -c "import httpx; print(httpx.__version__)"`] | HTTP client; source of the exception hierarchy `is_transient` classifies | Already the project's exclusive HTTP client (`pyproject.toml`); no alternative under consideration |
| `tenacity` | 9.1.4 [VERIFIED: `uv.lock`, `pyproject.toml: "tenacity>=9.1.4"`] | Retry/backoff engine (`Retrying`, `retry_if_exception`, `stop_after_attempt`) | Already the project's exclusive retry library; `build_retrying` is a thin composition over it |
| `pytest` | 9.0.3+ [VERIFIED: `pyproject.toml`, `TESTING.md`] | Test runner | Already the project's exclusive test framework; `[tool.pytest.ini_options]` already configured |

No new packages are introduced by this phase. All three above are pre-existing pinned dependencies;
research here is about their exact *installed behavior*, not about selecting or adding a library.

### Supporting

None — this phase adds zero new runtime or dev dependencies (D-10's `conftest.py` fixtures are
hand-written Python, not a fixture library).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `is_transient` deny-by-default tuple (D-01/D-02) | Blanket `httpx.TransportError` (with or without a deny-list) | Rejected by user (D-02) — allow-by-default silently retries an unrecognized future httpx exception for up to ~75 min; the hub can't see consumer failure modes to justify that risk |
| First-`-m`-scan argv matching (D-04) | `argv[1]`/`argv[2]` fixed-position check (the report's literal text) | Rejected by user (D-05) — empirically fails the `python -O -m <marker> run` ROADMAP criterion |
| `pytest.raises()` for the escape assertion | `try/except` + `assert isinstance` | Both acceptable (Claude's discretion); `pytest.raises` has one existing in-repo precedent (`test_import_hygiene.py:243`) worth citing but not decisive |

**Installation:** None required — no new packages.

**Version verification:** Confirmed directly against the project's `.venv`, not from training data:

```bash
uv run python -c "import httpx; print(httpx.__version__)"   # -> 0.28.1
grep -n 'name = "tenacity"' -A3 uv.lock                       # -> 9.1.4
grep -n 'requires-python\|pytest' pyproject.toml               # -> >=3.12, pytest>=9.0.3
```

## Package Legitimacy Audit

**Not applicable — this phase installs no new external packages.** `httpx`, `tenacity`, and
`pytest` are pre-existing pinned dependencies already present in `pyproject.toml` / `uv.lock`;
the phase only changes how the hub's own code calls them. The Package Legitimacy Gate is skipped
per its trigger condition ("whenever this phase installs external packages").

## Architecture Patterns

### System Architecture Diagram

```
                 ┌─────────────────────────────────────────────┐
                 │  Consumer (WeatherBot) composition root       │
                 │  - fire_slot(): picks REASON_* string          │
                 │  - reload sender: calls is_running_process()   │
                 │    then decides whether to SIGHUP a PID         │
                 └───────────────┬───────────────┬───────────────┘
                                 │ calls          │ calls
                                 ▼                ▼
   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
   │ Hub: reliability/retry.py         │   │ Hub: lifecycle/identity.py       │
   │                                    │   │                                    │
   │ is_transient(exc)  <── RELY-01 fix │   │ is_running_process(pid, marker)  │
   │   │ deny-by-default classify        │   │   │                                │
   │   ▼                                │   │   ▼                                │
   │ build_retrying(stop_event, ...)    │   │ _argv_matches_marker() <─ LIFE-01 │
   │   │ wraps tenacity.Retrying         │   │   fix (first-`-m` scan)           │
   │   ▼                                │   │   │                                │
   │ Retrying.__call__(fn)              │   │   ▼                                │
   │   │ on exhaustion:                  │   │ _read_proc_cmdline(pid) or        │
   │   │ retry_error_callback =          │   │ injected cmdline_reader (tests)   │
   │   │   rs.outcome.result()           │   └─────────────┬─────────────────────┘
   │   ▼                                │                 │ reads
   │ exhausted exc escapes AS ITSELF     │                 ▼
   │ (not tenacity.RetryError) ── D-17   │   ┌─────────────────────────────────┐
   └───────────────┬────────────────────┘   │ OS: /proc/<pid>/cmdline          │
                    │ caught by               │ (NUL-separated argv bytes)       │
                    ▼                         └─────────────────────────────────┘
   ┌─────────────────────────────────┐
   │ Consumer's except httpx.* handler │
   │ → REASON_TRANSIENT_EXHAUSTED       │
   │   (hub does not assign this string;│
   │    only makes the escape correct) │
   └─────────────────────────────────┘
```

### Recommended Project Structure

No structural changes — the phase adds files, not folders:

```
tests/
├── test_gateway.py       # existing — unchanged
├── test_import_hygiene.py  # existing — unchanged, must stay green (GATE-01)
├── conftest.py            # NEW (D-09) — minimal: fake stop_event + cmdline builder (D-10)
├── test_retry.py          # NEW (D-08) — RELY-01 regression tests
└── test_identity.py       # NEW (D-08) — LIFE-01 regression tests
```

### Pattern 1: Escape-as-itself via `retry_error_callback`

**What:** On exhaustion, `Retrying` calls `retry_error_callback(retry_state)` INSTEAD of raising
`RetryError`, when that callback is supplied. `build_retrying` supplies
`lambda rs: rs.outcome.result()`, and `Future.result()` re-raises the wrapped exception rather than
returning it, when the future's outcome was an exception.

**When to use:** Any time downstream code (here, `fire_slot`'s `except httpx.*` handlers) needs to
pattern-match on the ORIGINAL exception type after retries are exhausted, not a wrapper.

**Example (verified against installed tenacity 9.1.4):**
```python
# Source: reproduced locally against yahir_reusable_bot.reliability.retry.build_retrying
import httpx
from yahir_reusable_bot.reliability.retry import build_retrying

class FakeStopEvent:
    def wait(self, timeout=None):
        return False

attempts = {"n": 0}

def always_fails():
    attempts["n"] += 1
    raise httpx.RemoteProtocolError("server hung up mid-response")

retrying = build_retrying(FakeStopEvent(), attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0)
try:
    retrying(always_fails)
except httpx.RemoteProtocolError:
    pass  # AFTER the D-01 fix: escapes as itself, attempts == 4 (2 * attempts_per_burst)
# BEFORE the fix: is_transient(RemoteProtocolError) is False, so tenacity's `retry`
# predicate says "don't retry" and the exception escapes after attempts == 1 — the test
# distinguishing RED from GREEN is the attempt COUNT, not just the escaped type.
```

**Contrast — WITHOUT `retry_error_callback` (verified, do not use this shape):**
```python
# Source: reproduced locally; NOT what build_retrying does, shown to document the pitfall
from tenacity import Retrying, retry_if_exception, stop_after_attempt
r = Retrying(wait=lambda rs: 0, stop=stop_after_attempt(2),
             retry=retry_if_exception(is_transient_fixed), sleep=lambda t: None)
r(always_fails)
# -> raises tenacity.RetryError(...) wrapping the RemoteProtocolError, NOT the exception itself.
# This is the exact shape of bug that produces the consumer's internal_error misclassification.
```
[VERIFIED: local execution against installed tenacity 9.1.4 in project .venv]
[CITED: https://tenacity.readthedocs.io/en/latest/api.html — "When using retry_error_callback,
Tenacity will not reraise the exception" / reraise semantics]

### Pattern 2: First-`-m`-scan argv matching

**What:** Instead of checking fixed argv positions, scan for the lowest index where
`argv[i] == b"-m"` and require the very next token to equal `proc_marker`.

**When to use:** Any argv-shape match where an unknown number of interpreter flags (`-O`, `-B`,
`-X ...`) may precede the flag of interest — general Python CLI grammar, not `-m` specific.

**Example (locked shape, D-04):**
```python
# Source: derived from CONTEXT.md D-04; not yet in production code — this IS the fix to write
def _argv_matches_marker(cmdline: bytes, *, proc_marker: bytes) -> bool:
    argv = [part for part in cmdline.split(b"\x00") if part]
    if not argv:
        return False
    prog = Path(argv[0].decode("utf-8", "replace")).name
    if prog == proc_marker.decode("utf-8", "replace"):
        return True
    for i, tok in enumerate(argv[1:], start=1):
        if tok == b"-m":
            return i + 1 < len(argv) and argv[i + 1] == proc_marker
    return False
```
This is ONE valid shape satisfying D-04's "lowest index `i` where `argv[i] == b'-m'`, then require
`argv[i+1] == proc_marker`" rule; the planner/executor may implement equivalently (e.g. `.index(b"-m")`
inside a try/except `ValueError`). What's locked is the *semantics* (first `-m`, next token exact
match, bounds-checked), not this exact code shape.

### Anti-Patterns to Avoid

- **Membership-in-slice matching (the current bug):** `b"-m" in argv[1:3] and marker in argv[1:4]`
  checks *presence within a window*, not *adjacency at a specific position*. It's why the current
  code accepts `python -m pytest <marker>` (marker present in the window, but as pytest's
  positional test-selector arg, not the `-m` target) — verified empirically to return `True` when
  it must return `False`.
- **Blanket `TransportError` catch for `is_transient`:** Explicitly rejected (D-02). Would also
  silently start retrying `UnsupportedProtocol` and `ProxyError`, neither of which resolves by
  waiting.
- **Testing the consumer's reason string in the hub (D-18):** Do not replicate `fire_slot`'s
  string-picking logic in a hub test to literally assert `"transient_exhausted"` — that couples hub
  tests to consumer logic the hub doesn't own and can't see change.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP-layer transient-failure detection | A custom exception-message parser or status-code-only heuristic | `httpx`'s own exception hierarchy (`isinstance` checks against `TimeoutException`/`NetworkError`/`RemoteProtocolError`) | httpx already distinguishes transport-layer failures from protocol/client-side bugs; re-deriving that from `str(exc)` is fragile and exactly the kind of thing D-02's deny-by-default posture guards against |
| Retry scheduling / interruptible sleep | A custom `while` loop with `time.sleep` | `tenacity.Retrying` with `sleep=stop_event.wait` (already wired in `build_retrying`) | Already correctly composed; Phase 1 changes zero retry-scheduling code, only the classifier predicate |
| Process liveness / identity matching | `psutil` or a new third-party process-inspection dependency | The existing stdlib-only `/proc/<pid>/cmdline` read + injectable `cmdline_reader` | The module's own docstring states "stdlib ``os`` / ``tempfile`` / ``pathlib`` ONLY — zero new dependencies"; the bug is an argv-matching *algorithm* defect, not a missing capability that needs a new dependency |
| Mocking `/proc` reads or `tenacity` internals for tests | A mocking library (`pytest-mock`, `unittest.mock`) | Synthetic inline test doubles (a plain function passed as `cmdline_reader`; a plain `FakeStopEvent` class with `.wait()`) | Both seams are already parameter-injectable in production code (D-12) — no mocking framework is needed to reach them, and the repo has zero mocking-library usage today |

**Key insight:** Every seam this phase needs was already built with test-injection in mind
(`cmdline_reader=`, `stop_event`, keyword-overridable burst constants) — there is no missing
infrastructure to construct, only the two logic bugs to fix and the tests that prove them.

## Common Pitfalls

### Pitfall 1: Asserting only the exception TYPE escapes, not the attempt COUNT (RELY-01)

**What goes wrong:** A test that only checks `pytest.raises(httpx.RemoteProtocolError)` around
`retrying(always_fails)` passes both BEFORE and AFTER the fix — because even the unfixed
`is_transient` (returning `False`) causes tenacity to immediately give up and re-raise the original
exception on attempt 1 (verified: `attempts == 1` pre-fix). The type-only assertion is not RED
against pre-fix source, so it doesn't prove anything.

**Why it happens:** `retry_if_exception(predicate)` returning `False` doesn't produce a
`RetryError` — tenacity treats "predicate says don't retry" as "not retryable," and the original
exception propagates directly, same visible type as after the real fix drives it through full
exhaustion.

**How to avoid:** Assert the attempt count too — `attempts["n"] == 2 * attempts_per_burst` (4, with
`attempts_per_burst=2`) is only true when `is_transient` is actually returning `True` and the retry
loop actually ran to exhaustion (D-16 already locks this: "assert the attempt count and that the
`RemoteProtocolError` escapes as itself").

**Warning signs:** A regression test that passes without ever running `git stash` / reverting the
`is_transient` fix to confirm RED first (D-13's whole point).

### Pitfall 2: Miscounting rows in the LIFE-01 truth table against CURRENT vs FIXED behavior

**What goes wrong:** Assuming "false negative" in the phase description refers to current
production code's behavior on the `python -O -m <marker> run` row. Empirically, current code
already returns `True` for that row (its bug is a `False` **positive** on the decoy row, not a
false negative there). The false-negative failure mode described in CONTEXT.md/D-05 is about the
*report's proposed literal fix* (`argv[1]==-m and argv[2]==marker`), and about a form NOT in the
four locked rows: `python -O -B -m <marker> run` (two flags before `-m`) — verified to return
`False` under CURRENT code.

**Why it happens:** The overlapping-slice check (`argv[1:3]`, `argv[1:4]`) happens to have a wide
enough window to accidentally cover the 1-flag-before-`-m` case (`-O`) by coincidence of the slice
bounds, while both the true security concern (the positional decoy) and the 2-flag case break it.

**How to avoid:** Test all four LOCKED rows (D-19) AND consider adding the 2-flags-before-`-m` case
as a fifth regression test, since it's a genuine, currently-reproducible false negative that the
D-04 fix also happens to resolve, giving the phase stronger regression coverage than the ROADMAP's
literal four criteria.

**Warning signs:** A plan or PR description that says "fixes a false negative" while showing only
the `python -O -m <marker> run` case — that specific case is a false *positive* fix opportunity in
the sense that current code coincidentally gets it right; the real false-negative demonstration
needs the two-flags form or must be explicit that it demonstrates the REPORT's rejected fix, not
current code.

### Pitfall 3: `RetryError` masquerading as the fix already working

**What goes wrong:** After fixing `is_transient` but BEFORE verifying `build_retrying`'s
`retry_error_callback` wiring is untouched, a naive test using a bare `Retrying(..., reraise=True)`
(not `build_retrying`) could pass even though the actual production wiring might regress to
default `RetryError` behavior on some other code path.

**Why it happens:** `reraise=True` and `retry_error_callback=lambda rs: rs.outcome.result()` are
NOT equivalent tenacity configurations that happen to produce the same visible result in the
common case, but they ARE distinct — `retry_error_callback` bypasses reraise/RetryError entirely per
tenacity's docs ("When using `retry_error_callback`, Tenacity will not reraise the exception").
Testing against a hand-built `Retrying` instead of the real `build_retrying` risks testing the wrong
wiring.

**How to avoid:** D-16's exhaustion test MUST call `build_retrying(...)` itself (already locked),
not reconstruct a parallel `Retrying`. This is already the locked decision — flagged here as the
concrete reason it matters, verified via side-by-side reproduction (see Code Examples).

**Warning signs:** A test that imports `tenacity.Retrying` directly instead of
`yahir_reusable_bot.reliability.retry.build_retrying`.

## Code Examples

### Empirically confirmed pre-fix classifier gaps (RELY-01)

```python
# Source: reproduced locally against yahir_reusable_bot.reliability.retry.is_transient (pre-fix)
import httpx
from yahir_reusable_bot.reliability.retry import is_transient

is_transient(httpx.RemoteProtocolError("boom"))  # -> False (BUG: must be True after D-01)
is_transient(httpx.WriteError("boom"))            # -> False (BUG: must be True after D-01)
is_transient(httpx.LocalProtocolError("boom"))    # -> False (CORRECT — must STAY False, D-02)
```
[VERIFIED: local execution against installed httpx 0.28.1 in project .venv]

### Empirically confirmed pre-fix argv-matching bugs (LIFE-01)

```python
# Source: reproduced locally against yahir_reusable_bot.lifecycle.identity._argv_matches_marker
from yahir_reusable_bot.lifecycle.identity import _argv_matches_marker

def build(*parts: bytes) -> bytes:
    return b"\x00".join(parts) + b"\x00"

marker = b"weatherbot"

_argv_matches_marker(build(b"python", b"-m", b"pytest", marker), proc_marker=marker)
# -> True   (BUG: must be False — recycled-PID decoy, marker is pytest's positional arg)

_argv_matches_marker(build(b"python", b"-O", b"-m", marker, b"run"), proc_marker=marker)
# -> True   (already correct today, by coincidence of the slice window — must STAY True)

_argv_matches_marker(build(b"python", b"-O", b"-B", b"-m", marker, b"run"), proc_marker=marker)
# -> False  (BUG, not in the locked 4-row table: 2 flags before -m falls outside argv[1:3]/argv[1:4])

_argv_matches_marker(build(b"python", b"-m", b"pytest", b"-m", marker), proc_marker=marker)
# -> False  (already correct today AND under D-04 — see Pitfall 2's discriminator note)
```
[VERIFIED: local execution against installed source at `yahir_reusable_bot/lifecycle/identity.py:130-149`]

### In-repo `pytest.raises` precedent (for D-16's discretion point)

```python
# Source: tests/test_import_hygiene.py:243 (existing, unmodified by this phase)
with pytest.raises(ImportError) as exc_info:
    importlib.import_module(target)
assert "BLOCKED app import" in str(exc_info.value), (
    "the ImportError must come from the _AppBlocker (proving it bit), not from a "
    f"normal-finder ModuleNotFoundError: {exc_info.value}"
)
```
[VERIFIED: `grep -n "pytest\." tests/test_import_hygiene.py` → line 243]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `is_transient` misses `RemoteProtocolError`/`WriteError`/`CloseError` | D-01's deny-by-default tuple including `NetworkError` (covers `WriteError`/`CloseError`) and `RemoteProtocolError` explicitly | This phase | Server-hangup-mid-response failures now drive the two-burst retry instead of silently dropping a delivery |
| `_argv_matches_marker` overlapping-slice membership test | D-04's first-`-m`-scan | This phase | Closes both the false-positive (decoy) and false-negative (multi-flag) forms in one algorithmic change |
| `TESTING.md:36`/`:142` "no conftest.py / no fixtures" | D-09 adds a minimal `tests/conftest.py` | This phase | `TESTING.md` becomes stale on landing (tracked as a deferred housekeeping item, not phase scope) |

**Deprecated/outdated:**
- `TESTING.md:239` ("No `pytest.raises()` currently") is already inaccurate as of the CURRENT repo
  state (before this phase even lands) — `test_import_hygiene.py:243` already uses it. Worth
  flagging to whoever eventually refreshes `TESTING.md`, though out of this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `python -O -B -m <marker> run` and the two-flags-before-`-m` false negative are realistic enough to be worth a regression test, even though not in the ROADMAP's four locked criteria | Common Pitfalls / Pattern 2 | Low — this is an additive suggestion, not a locked requirement; if the planner declines it, D-19's four required rows still fully satisfy the phase's acceptance criteria |
| A2 | No other httpx exception besides the three in D-03's table needs consideration (e.g. no newer httpx 0.28.x point release changed the hierarchy) | Standard Stack | Low — the hierarchy was walked directly against the exact installed 0.28.1 wheel via `__bases__` introspection, not inferred; a `uv.lock` bump to a different 0.28.x patch is the only way this could drift, and patch releases rarely restructure exception hierarchies |

**This table is intentionally short.** Nearly every factual claim in this document was verified by
executing code against the actual installed dependencies and the actual pre-fix production source
in this repo's `.venv` — a stronger evidence tier than `[ASSUMED]` training-knowledge claims, and
tagged `[VERIFIED: local execution...]` throughout rather than left as assumptions.

## Open Questions

1. **Should the fifth (unlocked) argv form — two interpreter flags before `-m` — get its own
   regression test?**
   - What we know: it's a genuine, currently-reproducible false negative under the CURRENT
     production `_argv_matches_marker`, and D-04's first-`-m`-scan fixes it for free.
   - What's unclear: it's not one of the four ROADMAP-locked rows, so it's additive coverage, not a
     requirement.
   - Recommendation: planner includes it as a fifth test case in `test_identity.py` (cheap, and it's
     already-verified evidence of a real defect) but does not treat its absence as a phase-blocking
     gap if the planner descopes it — D-19 only mandates the four locked rows.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `httpx` | RELY-01 exception classification | ✓ | 0.28.1 | — |
| `tenacity` | RELY-01 retry engine (`build_retrying`) | ✓ | 9.1.4 | — |
| `pytest` | Test substrate (both fixes) | ✓ | 9.0.3+ | — |
| `/proc` filesystem | LIFE-01 (production path only — tests inject `cmdline_reader` and never touch real `/proc`) | ✓ (Linux host) | — | Not needed for tests; production-only, already documented to degrade to `True` on non-Linux |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None — all required tooling is already installed and
version-pinned in `uv.lock`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["."]`, `addopts="-ra"`) |
| Quick run command | `uv run pytest tests/test_retry.py tests/test_identity.py -v` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RELY-01 | `is_transient` classifies `RemoteProtocolError`/`WriteError` transient, `LocalProtocolError` non-transient | unit | `uv run pytest tests/test_retry.py -k classif -x` | ❌ Wave 0 |
| RELY-01 | Exhausted `RemoteProtocolError` escapes `build_retrying(...)` as itself (not `RetryError`), attempt count == `2 * attempts_per_burst` | unit (behavioral, `attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0`, fake `stop_event`) | `uv run pytest tests/test_retry.py -k exhaust -x` | ❌ Wave 0 |
| LIFE-01 | `_argv_matches_marker` rejects the recycled-PID decoy (`python -m pytest <marker>`) | unit | `uv run pytest tests/test_identity.py -k decoy -x` | ❌ Wave 0 |
| LIFE-01 | `_argv_matches_marker` accepts a daemon behind an interpreter flag (`python -O -m <marker> run`) | unit | `uv run pytest tests/test_identity.py -k interpreter_flag -x` | ❌ Wave 0 |
| LIFE-01 | `_argv_matches_marker` accepts the plain `python -m <marker> run` and `<marker> run` (argv0-basename branch) forms | unit | `uv run pytest tests/test_identity.py -k -"decoy or interpreter_flag" -x` | ❌ Wave 0 |
| GATE-01 (standing) | Import-hygiene / litmus / grimp gates stay green | unit (existing suite) | `uv run pytest tests/test_import_hygiene.py` | ✓ existing |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_retry.py tests/test_identity.py -v` (fast — no
  real sleeps; `mid_pause_s=0` and a fake `stop_event.wait()` returning immediately keep the
  exhaustion test sub-second despite the production 2700s default).
- **Per wave merge:** `uv run pytest` (full suite, includes `test_gateway.py` and
  `test_import_hygiene.py` — GATE-01 must stay green).
- **Phase gate:** Full suite green, on the phase branch (D-14), before merge to `main` and before
  `/gsd-verify-work`. No CI enforces this (D-15) — it is enforced by the executor running the
  commands above locally.

### Wave 0 Gaps

- [ ] `tests/conftest.py` — fake `stop_event` (instant `.wait(timeout)`) + NUL-separated
  cmdline-bytes builder (D-09/D-10). Both test files depend on it.
- [ ] `tests/test_retry.py` — new file (D-08); covers RELY-01.
- [ ] `tests/test_identity.py` — new file (D-08); covers LIFE-01.
- [ ] Framework install: none — `pytest`, `httpx`, `tenacity` are already installed and pinned.

**What would constitute an under-sampled (false-green) validation for these two fixes:**
- **RELY-01:** A test that asserts only the escaped exception TYPE (`pytest.raises(RemoteProtocolError)`)
  without also asserting the attempt COUNT reached `2 * attempts_per_burst`. Verified empirically
  (Pitfall 1): this assertion shape passes identically before AND after the fix, because pre-fix
  `is_transient` returning `False` also causes the original exception to propagate immediately
  (after 1 attempt) rather than through the retry-exhaustion path. This is the single highest-risk
  false-green in this phase — it would ship a test that looks like proof of D-17 but proves nothing.
- **RELY-01:** A test built against a hand-rolled `tenacity.Retrying(...)` instead of the real
  `build_retrying(...)` — would validate tenacity's general behavior, not the hub's specific
  `retry_error_callback` wiring, which is the actual load-bearing fix surface (Pitfall 3).
- **LIFE-01:** Testing fewer than all four D-19-locked truth-table rows — in particular, omitting
  the recycled-PID decoy row (`python -m pytest <marker>` → must be `False`) would leave the ACTUAL
  live defect (a false positive that can SIGHUP an unrelated process) unverified, since that row is
  the one CURRENT production code gets wrong while the other three rows already pass by coincidence
  of the slice-window bug (verified empirically — see Pattern 2 / Pitfall 2).
- **LIFE-01:** Asserting only that the fixed function COMPILES/imports without asserting its return
  value on each row — self-evidently false-green, called out because RED-first (D-13) specifically
  requires each test to demonstrably fail against pre-fix source; a docstring-only or import-only
  test would be RED for the wrong reason (or not RED at all).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | This phase touches no auth surface |
| V3 Session Management | no | N/A — no sessions in scope |
| V4 Access Control | partial | `_argv_matches_marker`'s false positive is a MISDIRECTED-SIGNAL risk, not a classic access-control bypass: a wrong match can cause `is_running_process` to report `True` for an unrelated process, and a consumer's reload path may then send it SIGHUP. The fix (D-04) is the standard control — match on program identity (argv0 basename or exact `-m` target adjacency), never substring/window presence. |
| V5 Input Validation | partial | `/proc/<pid>/cmdline` bytes are read from the OS, not network input, but are still untrusted in the sense that ANY process (including an attacker-controlled one, if PID recycling coincides with a malicious process) could construct argv content. The first-`-m`-scan rule is itself the validation control — treat argv as adversarial input to a matcher, not a trusted string to substring-search. |
| V6 Cryptography | no | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| PID-recycling signal misdirection (a stale/reused PID happens to have the marker string anywhere in its argv) | Spoofing / Tampering | Match program identity exactly (argv0 basename, or exact adjacency after the first `-m`), never `marker in argv` substring/window presence — this is precisely what D-04 implements and what the current bug fails to do (verified: `python -m pytest <marker>` currently matches when it must not) |
| Silent retry-budget exhaustion masking a real outage (an unclassified transient failure never retries, or an unrecognized failure retries when it shouldn't) | Denial of Service (of the delivery mechanism itself) | Deny-by-default classification (D-02) — an unrecognized future httpx exception fails closed (no retry) rather than retrying blindly for ~75 min; this phase narrows the true-negative set (adds `RemoteProtocolError`/`WriteError` as true-positive transient) without widening the retry surface to unknown exception types |

## Sources

### Primary (HIGH confidence — direct execution against installed packages / repo source)

- Installed `httpx 0.28.1` package (`.venv/lib/python3.12/site-packages/httpx`) — exception
  hierarchy walked via `__bases__` introspection for every class named in CONTEXT.md's D-03 table;
  matches exactly.
- Installed `tenacity 9.1.4` package (`.venv/lib/python3.12/site-packages/tenacity`) — `Retrying`
  behavior with/without `retry_error_callback` reproduced directly.
- `yahir_reusable_bot/reliability/retry.py:1-249` (full file read) — current `is_transient` (lines
  80-91) and `build_retrying` (lines 184-248) source, exercised directly.
- `yahir_reusable_bot/lifecycle/identity.py:1-164` (full file read) — current
  `_argv_matches_marker` (lines 130-149) source, exercised directly against all locked and
  additional truth-table rows.
- `tests/test_import_hygiene.py`, `tests/test_gateway.py` — read in full; grepped for
  `pytest\.` usage (corrects a `TESTING.md` staleness claim).
- `.planning/codebase/TESTING.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`,
  `ECOSYSTEM.md` §3 headings, `pyproject.toml`, `uv.lock` — read/grepped directly.

### Secondary (MEDIUM confidence — official docs, used to cite/corroborate empirical findings)

- [HTTPX Exceptions — python-httpx.org](https://www.python-httpx.org/exceptions/) — corroborates the
  locally-walked exception hierarchy.
- [Tenacity API Reference — tenacity.readthedocs.io](https://tenacity.readthedocs.io/en/latest/api.html)
  — corroborates the `retry_error_callback` / `reraise` / `RetryError` semantics reproduced locally.

### Tertiary (LOW confidence)

None used — every claim in this document is either verified by direct execution against installed
packages/repo source, or cited from official docs corroborating that execution.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; versions confirmed directly from `uv.lock`/`pyproject.toml`/runtime introspection.
- Architecture: HIGH — both fix sites read in full; both truth tables executed against real installed source, not inferred.
- Pitfalls: HIGH — all three pitfalls were discovered BY executing the pre-fix and candidate-fix code, not by reasoning about tenacity/httpx behavior from memory.

**Research date:** 2026-07-22
**Valid until:** Effectively pinned to this repo's `uv.lock` — revalidate only if `httpx` or
`tenacity` versions change before this phase executes (30-day estimate as a default ceiling).
