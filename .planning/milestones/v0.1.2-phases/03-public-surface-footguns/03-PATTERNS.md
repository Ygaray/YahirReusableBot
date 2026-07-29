# Phase 3: Reusable public-surface footguns - Pattern Map

**Mapped:** 2026-07-27
**Files analyzed:** 5 modified + 4 new test files (9 total)
**Analogs found:** 9 / 9 (all modified files have strong in-file/sibling precedent; all new test files have a clear house-style precedent to mirror)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `yahir_reusable_bot/registry/match.py` (MATCH-01) | utility (pure transform) | transform | in-file: `match_command`'s existing folded-prefix loop | exact (self-analog) |
| `yahir_reusable_bot/registry/registry.py` (MATCH-02) | model/registry (construction-time validation) | CRUD (build-once) | in-file: `CommandRegistry.__init__`'s existing derivation pass; cross-file: `panelkit.py:207` curated-command assert | exact (self-analog) + role-match |
| `yahir_reusable_bot/reliability/retry.py` (RELY-02/03) | utility (pure wait-callable) | transform | in-file: `is_transient`'s deny-by-default docstring; `_within_burst_wait`'s existing degrade branch (`attempt_number == burst_size`) | exact (self-analog) |
| `yahir_reusable_bot/discord/panelkit.py` (DISC-05/06) | controller (gateway event handler) | event-driven | in-file: `interaction_check`'s existing non-operator reject path; `_build_command_buttons`' positive-injection assert | exact (self-analog) |
| `yahir_reusable_bot/lifecycle/identity.py` (LIFE-02/03) | utility (OS process-lifecycle primitive) | file-I/O | in-file: `write_pid_atomic`'s existing except-path close; `_argv_matches_marker`'s existing `argv[0]` basenaming | exact (self-analog) |
| `yahir_reusable_bot/scheduler/engine.py` (SCHED-01) | service (thin facade) | CRUD (register/remove/list) | in-file: `register`'s tolerant/idempotent posture (same class) | exact (self-analog) |
| `tests/test_engine.py` (NEW) | test | request-response (unit) | `tests/test_reload.py` (`_FakeSchedulerEngine` shape, minimal fake-collaborator style) | role-match |
| `tests/test_match.py` (NEW) | test | transform (unit) | `tests/test_retry.py` (pure-function-driven, `test_selfproof_*`-style docstring justifying RED-ness) | role-match |
| `tests/test_registry.py` (NEW) | test | CRUD (unit, construction) | `tests/test_retry.py` / `tests/test_reload.py` (construction-time `pytest.raises` idiom) | role-match |
| `tests/test_panelkit.py` (NEW) | test | event-driven (unit, synthetic interaction) | `tests/test_identity.py` (synthetic inline double + docstring-first adversarial-row style); Code Example §4 in RESEARCH.md | role-match |

## Pattern Assignments

### `yahir_reusable_bot/registry/match.py` (MATCH-01, utility/transform)

**Analog:** itself — `match_command` (lines 45-68), no other file needed.

**Current buggy slice** (`match.py:56-61`):
```python
stripped = text.strip()
folded = stripped.casefold()
for spec in specs:
    if not folded.startswith(spec.name):
        continue
    rest = stripped[len(spec.name) :]   # BUG: slices ORIGINAL with FOLDED length
```

**Fix pattern** — add a private helper above `match_command`, call it instead of the raw `len(spec.name)` slice (verified O(n) algorithm, RESEARCH.md Code Examples §1):
```python
def _keyword_boundary(stripped: str, name: str) -> int | None:
    """Return the index into `stripped` just past the folded match of `name`."""
    target = len(name)
    acc = 0
    for i, ch in enumerate(stripped, start=1):
        acc += len(ch.casefold())
        if acc == target:
            return i
        if acc > target:
            return None
    return None

def match_command(text: str, specs: Iterable[CommandSpec]) -> ParsedCommand:
    stripped = text.strip()
    folded = stripped.casefold()
    for spec in specs:
        if not folded.startswith(spec.name):
            continue
        boundary = _keyword_boundary(stripped, spec.name)
        if boundary is None:
            continue
        rest = stripped[boundary:]
        if rest and not rest[0].isspace():
            continue
        arg = rest.strip() or None
        return ParsedCommand(spec=spec, arg=arg)
    return ParsedCommand(spec=None, arg=None)
```

**Docstring-contract idiom to preserve:** `ParsedCommand`'s existing docstring (lines 34-39) already states "`arg` is the RAW (case-preserved) argument substring" — do not touch that docstring's wording, only the slicing implementation beneath it must honor it.

**Error handling:** none — pure function, no exceptions; `None` boundary is folded into the existing `continue` control flow (no new branch semantics, matches Pitfall 4's guidance).

---

### `yahir_reusable_bot/registry/registry.py` (+ `spec.py`) (MATCH-02, model/registry construction validation)

**Analog:** itself — `CommandRegistry.__init__` (lines 39-48); cross-file idiom — `panelkit.py:207-210`'s curated-command assert (fail-LOUD-at-construction posture) and `retry.py:80-115`'s deny-by-default docstring shape (`is_transient`).

**Current single derivation pass** (`registry.py:39-48`):
```python
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    self.by_keyword_len_desc: tuple[CommandSpec, ...] = tuple(
        sorted(self.commands, key=lambda c: len(c.name), reverse=True)
    )
```

**Fix pattern** — validate inside the SAME loop that builds `commands`, before deriving `by_name`/`by_keyword_len_desc` (RESEARCH.md Pattern 1, verbatim-ready):
```python
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    for spec in self.commands:
        if not spec.name or spec.name != spec.name.casefold():
            raise ValueError(
                f"CommandSpec.name must be non-empty and already casefolded "
                f"(match_command folds input, never spec.name); got {spec.name!r}"
            )
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    self.by_keyword_len_desc: tuple[CommandSpec, ...] = tuple(
        sorted(self.commands, key=lambda c: len(c.name), reverse=True)
    )
```

**Fail-LOUD-at-construction idiom to cite** (`panelkit.py:206-210`):
```python
assert name in by_name, (  # noqa: S101 — build-time allow-list guard
    f"panel curated command {name!r} is not in the registry — a rename "
    f"broke the panel layout"
)
```
This phase's fix uses `raise ValueError` (not `assert`) because MATCH-02 is a genuine consumer-input validation the module must always enforce (asserts can be stripped with `-O`), whereas the panelkit assert guards an internal build-time invariant — note this distinction if the executor asks "assert vs raise" for D-34.

**Deny-by-default docstring idiom to mirror** (`retry.py:88-92`, `is_transient`):
```
**Deny-by-default is the LOCKED posture (D-02, RELY-01).** An httpx
exception type not explicitly named here classifies non-transient. ...
this library cannot see its consumers' failure modes, so an unrecognized
future exception type must fail closed rather than retry blind.
```
Adapt this rhetorical shape (name the rejected alternative, state the "why fail closed") for the new `ValueError` docstring/comment.

**`build_registry`** (registry.py:83-89) needs no code change — it forwards to `CommandRegistry(specs)`, so the `ValueError` propagates through it automatically; the D-43 test drives both `CommandRegistry(...)` directly and `build_registry(...)`.

**`spec.py`:** no change expected — `CommandSpec.name: str` (line 66) is already a plain field; MATCH-02 validates the VALUE at registry construction, not the spec's shape.

---

### `yahir_reusable_bot/reliability/retry.py` (RELY-02 + RELY-03)

**Analog:** itself — `_within_burst_wait` (lines 157-167), `two_burst_wait` (170-205), `is_transient`'s docstring (80-115) for the contract-in-docstring idiom.

**Current unguarded division** (`retry.py:157-167`):
```python
def _within_burst_wait(
    attempt_number: int, *, burst_spread_s: float, burst_size: int, mid_pause_s: float
) -> float:
    """Base two-burst wait (Pattern 1), independent of any Retry-After honoring."""
    if attempt_number == burst_size:
        return mid_pause_s
    step = burst_spread_s / (burst_size - 1)   # BUG: ZeroDivisionError when burst_size == 1
    jitter = random.uniform(0, step * 0.5)
    return step + jitter
```

**Fix pattern (D-36 guard-degrade)** — add a `burst_size <= 1` guard before the division, returning the spread base with no jitter computation dependent on it (Claude's Discretion covers exact degrade value — spread base is the RESEARCH-recommended shape):
```python
def _within_burst_wait(
    attempt_number: int, *, burst_spread_s: float, burst_size: int, mid_pause_s: float
) -> float:
    """Base two-burst wait (Pattern 1), independent of any Retry-After honoring.

    D-36 (RELY-02): burst_size <= 1 degrades to burst_spread_s (no jitter) rather
    than raising ZeroDivisionError; with burst_size == 1 each burst is a single
    attempt and stop_after_attempt bounds the schedule before this value is ever
    consumed, so the guard only has to not crash — see Pitfall 3 for why the
    wait callable still runs on the terminal attempt regardless.
    """
    if attempt_number == burst_size:
        return mid_pause_s
    if burst_size <= 1:
        return burst_spread_s
    step = burst_spread_s / (burst_size - 1)
    jitter = random.uniform(0, step * 0.5)
    return step + jitter
```

**`two_burst_wait` docstring precondition (D-37)** — extend the existing docstring (lines 177-185) with a loud MUST-pair statement; no code change to the function body:
```python
def two_burst_wait(
    retry_state,
    *,
    burst_spread_s: float = BURST_SPREAD_S,
    burst_size: int = BURST_SIZE,
    mid_pause_s: float = MID_PAUSE_S,
) -> float:
    """Two-burst wait that HONORS a capped ``Retry-After`` (Pattern 1 <-> Pattern 4).

    ...(existing 1./2. bullets unchanged)...

    PRECONDITION (D-37, RELY-03): this callable receives only
    ``retry_state.attempt_number`` and cannot see the stop bound. A caller
    wiring this into their OWN ``Retrying`` (bypassing ``build_retrying``)
    MUST pair it with ``stop=stop_after_attempt(2 * burst_size)`` — a
    mismatched stop desyncs the mid-pause (it fires at the wrong attempt, or
    never). ``build_retrying`` already couples these correctly
    (lines 258-260); this precondition only matters for a standalone caller.
    """
```

**Contract-in-docstring idiom to mirror** — `_argv_matches_marker`'s (identity.py:130-187) full-essay rationale style is the house precedent for "why this specific guard, what was rejected, what remains." Follow that density level, not a one-line comment.

---

### `yahir_reusable_bot/discord/panelkit.py` (DISC-05 + DISC-06)

**Analog:** itself — `interaction_check`'s existing reject-log paths (lines 299-331), `PanelKit.__init__`'s positive-injection assertion block (157-192).

**DISC-05 fix** — None/MISSING guard at the TOP of `interaction_check` (current code, lines 299-309):
```python
async def interaction_check(self, interaction: discord.Interaction) -> bool:
    """..."""
    if interaction.user.bot:   # AttributeError when interaction.user is MISSING/None
        _log.info(
            "panel reject (bot)",
            user_id=interaction.user.id,
            custom_id=(interaction.data or {}).get("custom_id"),
        )
        return False
    if interaction.user.id != self._operator_id:
        ...
```

**Fix pattern (D-40)** — falsy check (NOT `is None` — RESEARCH.md Pitfall 1: the real absence sentinel is `discord.utils.MISSING`, which is falsy but not `None`), inserted before the `.bot` dereference, reusing the exact reject-log shape every other path uses:
```python
async def interaction_check(self, interaction: discord.Interaction) -> bool:
    """...

    D-40 (DISC-05): interaction.user's absence sentinel is discord.utils.MISSING
    (not None) in discord.py 2.7.1 — the guard below is a falsy check, matching
    every other reject path's audit-log contract (no ephemeral ack: there is no
    user to ack).
    """
    if not interaction.user:
        _log.info(
            "panel reject (no user)",
            custom_id=(interaction.data or {}).get("custom_id"),
        )
        return False
    if interaction.user.bot:
        _log.info(
            "panel reject (bot)",
            user_id=interaction.user.id,
            custom_id=(interaction.data or {}).get("custom_id"),
        )
        return False
    if interaction.user.id != self._operator_id:
        ...
```

**DISC-06 fix** — reject empty/whitespace marker at `PanelKit.__init__`, alongside the existing required-injected-collaborator assignments (lines 172-185), BEFORE `_build_children()`/`_assert_layout()` run:
```python
def __init__(self, *, registry, command_names, marker, operator_id, ...) -> None:
    super().__init__(timeout=None)
    if not marker or not marker.strip():
        raise ValueError(
            f"PanelKit marker must be a non-empty, non-whitespace string "
            f"(an empty marker makes cid.startswith(marker) match every "
            f"bot-authored pin); got {marker!r}"
        )
    self._registry = registry
    ...
```

**Fail-LOUD-at-construction idiom to cite** — same `panelkit.py:207` assert cited for MATCH-02; here it is a `raise ValueError`, not an `assert`, matching the module's own docstring framing ("required, no default — the module bakes no marker literal of its own", lines 20-21) — this is a genuine consumer-input validation, not an internal invariant, so `ValueError` (survives `-O`) is correct, mirroring D-34's reasoning.

**Error handling:** neither fix introduces new exception types beyond `ValueError` (construction-time) — `interaction_check`'s return-False-never-raise contract is unchanged structurally (RESEARCH Pitfall 1: `on_error` DOES catch an escaping exception in 2.7.1, but the fix keeps the clean reject-log contract intact rather than relying on that backstop).

---

### `yahir_reusable_bot/lifecycle/identity.py` (LIFE-02 + LIFE-03)

**Analog:** itself — `write_pid_atomic`'s existing except-path close (lines 62-87), `_argv_matches_marker`'s existing `argv[0]` basenaming one line above the bug (line 191).

**LIFE-02 current double-close** (`identity.py:73-87`):
```python
fd, tmp = tempfile.mkstemp(dir=str(pid_file.parent), prefix=".wbpid-")
try:
    os.write(fd, f"{os.getpid()}\n".encode())
    os.close(fd)
    os.replace(tmp, pid_file)
except BaseException:
    try:
        os.close(fd)          # BUG: fd may already be closed; reused int -> wrong fd
    except OSError:
        pass
    Path(tmp).unlink(missing_ok=True)
    raise
```

**Fix pattern (D-42)** — set `fd = -1` (or an equivalent closed-flag) right after the first close; guard the except-path close on that flag:
```python
fd, tmp = tempfile.mkstemp(dir=str(pid_file.parent), prefix=".wbpid-")
try:
    os.write(fd, f"{os.getpid()}\n".encode())
    os.close(fd)
    fd = -1  # D-42: mark closed so the except-path never re-closes this int
    os.replace(tmp, pid_file)
except BaseException:
    if fd != -1:
        os.close(fd)
    Path(tmp).unlink(missing_ok=True)
    raise
```
**Re-raise posture to preserve exactly:** the bare `raise` at the end and the "WRITER deliberately re-raises" framing (module docstring lines 22-24) must not change — only the close-guard shape changes.

**LIFE-03 current mis-matched compare** (`identity.py:191-192`):
```python
prog = Path(argv[0].decode("utf-8", "replace")).name
if prog == proc_marker.decode("utf-8", "replace"):   # BUG: RHS not basenamed
    return True
```

**Fix pattern (D-39)** — basename both sides, symmetric with the LHS one line above:
```python
prog = Path(argv[0].decode("utf-8", "replace")).name
if prog == Path(proc_marker.decode("utf-8", "replace")).name:
    return True
```
Does not touch the `-m` module branch (lines 194-205) — module targets are never path-shaped, per D-39's rationale.

**LIFE-02's test double is a convention introduction — flag this explicitly:** `monkeypatch` (pytest's built-in fixture) has **zero prior uses in this repo** (verified in RESEARCH.md). This is the first monkeypatch-based test, analogous to how Phase 1 called out `conftest.py` (D-09) and `pytest.raises()` as deliberate house-style extensions. RESEARCH.md Code Examples §3 gives a ready-to-adapt double:
```python
def test_write_pid_atomic_closes_temp_fd_exactly_once_on_replace_failure(tmp_path, monkeypatch):
    import os as real_os
    from yahir_reusable_bot.lifecycle import identity

    close_calls: list[int] = []
    real_close = real_os.close

    def _counting_close(fd: int) -> None:
        close_calls.append(fd)
        real_close(fd)

    fake_os = types.SimpleNamespace(**vars(real_os))
    fake_os.close = _counting_close
    fake_os.replace = lambda *a, **kw: (_ for _ in ()).throw(OSError("simulated replace failure"))
    monkeypatch.setattr(identity, "os", fake_os)

    pid_file = tmp_path / "bot.pid"
    with pytest.raises(OSError, match="simulated replace failure"):
        identity.write_pid_atomic(pid_file)

    assert len(close_calls) == 1
```
(No pre-existing analog in `tests/test_identity.py` for this shape — it is genuinely new, unlike LIFE-03's test which extends the existing truth-table style below.)

**LIFE-03's test IS an existing precedent** — `tests/test_identity.py`'s truth-table style (module-level `test_*` functions, one `cmdline_bytes`-built argv per row, MARKER constant at module top, docstring stating RED/GREEN pre-fix and citing the specific defect) is the exact shape to extend; reuse the `cmdline_bytes` fixture (`conftest.py:49-63`) directly — it is explicitly called out as reusable for this finding.

---

### `yahir_reusable_bot/scheduler/engine.py` (SCHED-01)

**Analog:** itself — `register`'s already-tolerant posture (baking invariant options so call sites can't drift, lines 44-70); `Path.unlink(missing_ok=True)` semantics (stdlib, cited in D-38 rationale).

**Current non-idempotent forward** (`engine.py:72-74`):
```python
def remove(self, job_id: str) -> None:
    """Drop the job with this id from the host scheduler."""
    self._scheduler.remove_job(job_id)
```

**Fix pattern (D-38, RESEARCH.md Code Examples §2 — verbatim-ready)** — catch `KeyError`, NOT an imported `JobLookupError` (apscheduler is not and must not become a hub dependency; `JobLookupError` IS a `KeyError` subclass, verified against apscheduler 3.x source):
```python
def remove(self, job_id: str) -> None:
    """Drop the job with this id; a no-op success if it is already gone.

    Idempotent by design (D-38, SCHED-01): a host scheduler's "job not found"
    signal (e.g. APScheduler's JobLookupError, which IS a KeyError — verified
    against apscheduler 3.x source) is caught and swallowed with a debug log,
    mirroring Path.unlink(missing_ok=True). This module never imports a
    specific scheduler package (host-agnostic by design, D-05); a bare
    `except KeyError:` catches the real signal without adding a dependency
    this facade has never needed.
    """
    try:
        self._scheduler.remove_job(job_id)
    except KeyError:
        _log.debug("scheduler remove: id already absent", job_id=job_id)
```
**NOTE — module currently has no `_log`/`structlog` import** (`engine.py` imports only `from typing import Any, Callable`). The fix must ADD `import structlog` and `_log = structlog.get_logger(__name__)` at module level — mirror the exact shape used in `retry.py:46,54` (`import structlog` / `_log = structlog.get_logger(__name__)`) and `panelkit.py:48,60`.

**Test double (dependency-free, RESEARCH.md Code Examples §2):**
```python
class _FakeRawScheduler:
    """A minimal double for the host-injected scheduler SchedulerEngine wraps."""
    def __init__(self, raise_on_remove: bool = False) -> None:
        self.raise_on_remove = raise_on_remove
        self.removed: list[str] = []

    def remove_job(self, job_id: str) -> None:
        if self.raise_on_remove:
            raise KeyError(f"No job by the id of {job_id} was found")
        self.removed.append(job_id)
```

---

## Shared Patterns

### Fail-LOUD-at-construction (deny-by-default validation)
**Source:** `panelkit.py:207-210` (curated-command assert), `panelkit.py`'s "no module default" framing (module docstring lines 16-27)
**Apply to:** `registry.py` (MATCH-02, D-34) and `panelkit.py` (DISC-06, D-41) — both use `raise ValueError` (not `assert`, since these are genuine untrusted-input validations that must survive `-O`), stated in the docstring alongside the rejected alternative.
```python
assert name in by_name, (  # noqa: S101 — build-time allow-list guard
    f"panel curated command {name!r} is not in the registry — a rename "
    f"broke the panel layout"
)
```

### Deny-by-default / degrade-vs-raise split (contract-in-docstring)
**Source:** `retry.py:88-92` (`is_transient` deny-by-default docstring); module docstring split in `identity.py:22-24` ("WRITER deliberately re-raises... guard/reader degrade cleanly")
**Apply to:** all six fixes — D-34/D-41 sit on the raise side (build-time wiring bugs); D-36/D-38/D-40 sit on the degrade side (runtime/portability conditions); state which side explicitly in each new/extended docstring, matching this codebase's "essay" density (see `_argv_matches_marker`, `identity.py:130-187`, as the ceiling example).

### structlog logging idiom
**Source:** `retry.py:46,54` / `panelkit.py:48,60` — `import structlog` then `_log = structlog.get_logger(__name__)`; call sites use `_log.info(...)` / `_log.debug(...)` / `_log.exception(...)` with keyword-only outcome fields (never secrets/domain nouns).
**Apply to:** `scheduler/engine.py` (SCHED-01 — needs this import added fresh), and the existing `_log.info` reject-log calls in `panelkit.py` (DISC-05 — reuse verbatim, do not invent a new log shape).

### No-mocking-library house style + synthetic inline doubles
**Source:** `tests/conftest.py` module docstring (lines 16-19): "this repo uses no mocking library (no `pytest-mock`, no `unittest.mock`)"; every existing fake (`_FakeSchedulerEngine` in `test_reload.py`, `_InstantStopEvent` in `conftest.py`) is a hand-written class with only the methods the code under test actually calls.
**Apply to:** all four new test files — `_FakeRawScheduler` (test_engine.py), `_FakeInteraction` (test_panelkit.py), plain `CommandSpec(...)` construction (test_match.py/test_registry.py) — and LIFE-02's `monkeypatch`-based delegating fake (flagged separately below as a convention EXTENSION, not a violation: `monkeypatch` is pytest core, not a mocking library, per RESEARCH.md's explicit clarification).

### `test_<module_basename>.py` naming convention (unbroken across every existing file)
**Source:** `test_retry.py`↔`retry.py`, `test_identity.py`↔`identity.py`, `test_reload.py`↔`reload.py`, `test_selection.py`↔`selection.py`
**Apply to:** the four new files — `test_match.py`, `test_registry.py` (kept SEPARATE per module, not merged, per RESEARCH.md's explicit recommendation), `test_panelkit.py`, `test_engine.py`.

### Docstring-first, `test_selfproof_*`-style self-proof note
**Source:** `test_retry.py:1-13` and `test_identity.py:1-22` module docstrings — both explain WHY a naive assertion would pass identically pre/post-fix and name the ONE assertion that is genuinely RED.
**Apply to:** all four new test files' module docstrings — each must name the specific assertion shape that is RED pre-fix (per RESEARCH.md's Common Pitfalls warnings: DISC-05's test must call `interaction_check` directly, NOT assert `on_error` isn't invoked; RELY-02's test must exercise `attempt_number != burst_size` with `burst_size <= 1`, not just the branch that already worked).

## No Analog Found

None. Every one of the nine fixes has an in-file or same-class precedent (all are one-file changes with existing surrounding code to pattern-match), and every one of the four new test files has a clear house-style precedent (`test_retry.py`, `test_identity.py`, `test_reload.py`, `conftest.py`) to mirror for structure/tone even though the specific test FILES themselves are new (RESEARCH.md Pitfall 5 — do not mistake "no test file yet" for "no pattern to follow").

**Convention-introduction flagged (not a missing-analog gap, but worth calling out to the executor):** LIFE-02's `monkeypatch`-based close-counting double is the first use of pytest's `monkeypatch` fixture anywhere in this repo. It is not a new dependency (pytest core, not a mocking library) and does not violate the no-mocking-library house style, but the plan/executor should state this explicitly the same way Phase 1 called out `conftest.py` (D-09) and `pytest.raises()` as deliberate house-style extensions.

## Metadata

**Analog search scope:** `yahir_reusable_bot/registry/`, `yahir_reusable_bot/reliability/`, `yahir_reusable_bot/discord/`, `yahir_reusable_bot/lifecycle/`, `yahir_reusable_bot/scheduler/`, `tests/`
**Files scanned:** 6 source files (`match.py`, `registry.py`, `spec.py`, `retry.py`, `panelkit.py`, `identity.py`, `engine.py`) + 4 existing test files (`test_retry.py`, `test_identity.py`, `test_reload.py`, `conftest.py`)
**Pattern extraction date:** 2026-07-27
