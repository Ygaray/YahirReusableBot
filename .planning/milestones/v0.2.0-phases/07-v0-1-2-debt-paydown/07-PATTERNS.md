# Phase 7: v0.1.2 debt paydown - Pattern Map

**Mapped:** 2026-08-03
**Files analyzed:** 13 modify targets (9 source/test files touched by 7 code requirements, 1 new
test file, 3 doc-drift correction/annotation site groups)
**Analogs found:** 13 / 13 — this is a debt-paydown phase, so almost every "analog" is the
existing convention in the SAME file the change lands in, or its direct sibling.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `yahir_reusable_bot/registry/registry.py` (MATCH-03) | model / construction-time validator | CRUD (build-once) | same file, D-34 loop (lines 52-57) | exact — in-place extension |
| `tests/test_registry.py` (MATCH-03) | test | request-response (raises) | same file's existing 5 tests | exact |
| `EXTENSION-GUIDE.md` (LIFE-05, D-61) | config/doc | — | its own existing plug-point doc sections | exact — doc-only |
| `yahir_reusable_bot/lifecycle/ready_gate.py` (SURF-02 `on_online`, HYG-02) | service | event-driven (hook dispatch) | same file — `on_fail`'s annotation (line 92) + `_best_effort_hook` (174-188) | exact |
| `yahir_reusable_bot/discord/panelkit.py` (SURF-02 `render`) | component | request-response | same file's `ItemContributor`/`DispatchCallable` typed-Callable style (lines 81, 109) | exact |
| `yahir_reusable_bot/scheduler/engine.py` (SURF-02 `callback`, recorded no-op) | service | event-driven | same file, `register`'s existing docstring style (lines 58-63) | exact — comment-only |
| `yahir_reusable_bot/discord/gateway.py` (DISC-07, DISC-08) | controller/adapter | event-driven (Discord API) | same function, `summon_panel`'s first `msg.pin()` (194-200) | exact — sibling code path in same function |
| `yahir_reusable_bot/discord/gateway.py` (HYG-03, `BotThread.stop`) | controller/adapter | event-driven | same file's own current `stop()` (339-358) | exact — restructure in place |
| `yahir_reusable_bot/config/reload.py` (HYG-02 clone) | service | event-driven | `ready_gate.py`'s `_best_effort_hook` (verbatim D-09 clone) | exact — byte-identical twin |
| `pyproject.toml` (D-65) | config | — | existing `[tool.pytest.ini_options]` table | exact |
| `tests/test_gateway.py` (DISC-07/08/HYG-03 new cases) | test | request-response | same file's `_FakeCloseableClient`/`_ClosedLoopFastPathProxy` doubles (260-284) | exact |
| `tests/test_ready_gate.py`, `tests/test_panelkit.py` (SURF-02 signature tests) | test | request-response | `typing.get_type_hints` pattern documented in RESEARCH.md Code Examples | exact (verified this session) |
| `tests/test_doc_drift.py` (DOCS-02, NEW) | test | batch/transform (file scan) | `tests/test_import_hygiene.py` (`_MODULE_ROOT`, gate + self-proof structure) | role-match — closest existing "standing planning-artifact scan" convention in repo |

## Pattern Assignments

### `yahir_reusable_bot/registry/registry.py` (MATCH-03)

**Analog:** itself — the existing D-34 loop, `registry.py:39-64`.

**Core pattern to extend** (lines 39-57, current live source):
```python
def __init__(self, specs: Iterable[CommandSpec]) -> None:
    self.commands: tuple[CommandSpec, ...] = tuple(specs)
    # D-34 (MATCH-02): validate every spec.name INSIDE this same pass, before any
    # view is derived from it — non-empty AND already-casefolded. ...
    for spec in self.commands:
        if not spec.name or spec.name != spec.name.casefold():
            raise ValueError(
                f"CommandSpec.name must be non-empty and already casefolded "
                f"(match_command folds input, never spec.name); got {spec.name!r}"
            )
    # MATCH-03 lands here: `seen: set[str]` check inside this same loop, raising
    # ValueError naming the duplicate, BEFORE `by_name` is derived below.
    self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
    ...
```
**Shape to copy:** a `seen: set[str]` added inside the existing `for spec in self.commands:` loop
(same loop, not a second pass), `raise ValueError(f"... duplicate ...; got {spec.name!r}")` in the
same f-string message style as the existing check — non-empty/casefold check first, duplicate
check second, both inside one loop body, both before `self.by_name` is derived.

**Error handling:** bare `raise ValueError(f"...")`, never a custom exception type — locked by the
existing convention and the ROADMAP.

### `tests/test_registry.py` (MATCH-03 tests)

**Analog:** itself — the file's existing 5 tests (full file read above).

**Conventions to copy exactly:**
- `_spec(name)` factory helper (lines 29-36) — plain construction, no mocking library.
- The "self-proof note" docstring pattern at module top (lines 7-14): explain WHY a naive
  "still constructs" assertion is not RED-proving.
- `with pytest.raises(ValueError): CommandRegistry([_spec(...), _spec(...)])` for the RED case.
- A `test_value_error_names_the_offending_*_value` test using
  `pytest.raises(ValueError, match=...)` to assert the message names the duplicate value —
  mirror `test_value_error_names_the_offending_uppercase_value` (lines 91-93).
- A `test_valid_*_still_construct_without_regression` guard (lines 70-81) exercising `by_name` /
  `by_keyword_len_desc` unaffected.
- New tests: two distinct `CommandSpec`s sharing the same `name`, asserting
  `pytest.raises(ValueError, match=<the shared name>)`.

### `yahir_reusable_bot/discord/gateway.py` — DISC-07 (retry-pin `Forbidden`/`HTTPException` split)

**Analog:** the SAME function's first `msg.pin()`, `gateway.py:194-200`.

**Pattern to mirror exactly** (already-correct idiom in the same function):
```python
try:
    await msg.pin()
except discord.Forbidden:
    # Re-raise to the outer TOCTOU backstop below — Forbidden is a distinct,
    # preflight-revoked-permission case, not the pin-cap case handled here.
    raise
except discord.HTTPException:
    ...
```

**Target site to change** (`gateway.py:216-222`, current buggy live source):
```python
                try:
                    await msg.pin()
                except discord.HTTPException:
                    _log.critical(
                        "panel pin failed at cap even after evicting a stray",
                        channel_id=getattr(channel, "id", None),
                    )
```
**Copy shape:** insert `except discord.Forbidden:` BEFORE the existing `except
discord.HTTPException:` at line 218 — order is load-bearing (`Forbidden` is a subclass of
`HTTPException`, confirmed at runtime; RESEARCH.md Pitfall 3). Give the `Forbidden` branch its
own distinct `_log.critical(...)` event string, structured `channel_id=` kwarg matching the
existing style (never an f-string).

### `yahir_reusable_bot/discord/gateway.py` — DISC-08 (cleanup-list bookkeeping)

**Analog:** same function, the per-item cleanup loop's success/failure split at `gateway.py:237-244`
(pattern to mirror), vs. the buggy unconditional pop at `gateway.py:207-215` (site to fix).

**Buggy current code** (lines 207-215):
```python
if len(matches) >= 1:
    stray = matches.pop(0)          # unconditional pop — DISC-08's bug
    try:
        await stray.delete()
    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
        _log.warning(
            "stray panel delete failed; continuing",
            channel_id=getattr(channel, "id", None),
        )
```
**Fix shape:** peek `matches[0]` (don't pop yet); `await stray.delete()`; only remove it from
`matches` on the SUCCESS path (inside `try`, after `delete()` returns without raising) — this
mirrors the per-item `except (discord.NotFound, discord.HTTPException, discord.Forbidden):` catch
tuple already used at line 240's loop, so a failed delete stays in `matches` and is retried by
`for old in matches:` at line 237.

### `yahir_reusable_bot/discord/gateway.py` — HYG-03 (`BotThread.stop`)

**Analog:** the SAME method's current shape, `gateway.py:339-358`.

**Current buggy source** (lines 350-357):
```python
loop = self._loop
if loop is not None and loop.is_running():
    try:
        future = asyncio.run_coroutine_threadsafe(self._client.close(), loop)
        future.result(timeout=timeout)
    except Exception:  # noqa: BLE001 — close best-effort (incl. "loop already
        # stopped" RuntimeError on the TOCTOU race); still join below
        _log.warning("bot client.close() did not complete cleanly")
self._thread.join(timeout=timeout)
```
**Shape to copy (per CONTEXT.md D-64, illustrative — planner owns final form):** bind
`coro = self._client.close()` to a name BEFORE scheduling; split into two `try` blocks — the
scheduling `try/except` reclaims via `coro.close()` ONLY on scheduling failure (never-scheduled
coroutine, safe to close); the await `try/except` (inside the scheduling `else:`) logs a distinct
message on `future.result()` timeout/failure and must NOT call `coro.close()` (it is live on the
loop; closing raises `RuntimeError: cannot close a running coroutine`). Invariants to preserve
from the current docstring at lines 342-349: `stop()` NEVER raises; `self._thread.join(...)`
below is ALWAYS reached — same `# noqa: BLE001` best-effort posture, same structured
`_log.warning("message")` calls (no kwargs needed here, matching current style), just split into
two distinct event strings per D-64.

### `tests/test_gateway.py` — DISC-07 / DISC-08 / HYG-03 new tests

**Analog:** same file's existing doubles, `test_gateway.py:260-293` (full excerpt read above).

**Conventions to copy:**
- Plain-construction fake classes, no mocking library: `_FakeCloseableClient`,
  `_ClosedLoopFastPathProxy`, `_FakeJoinableThread` (lines 262-284) — each a minimal class
  implementing only the methods exercised.
- For DISC-07/08, extend the existing `_FakeAtCapMessage`-style double already established
  elsewhere in this file's `summon_panel` test group (RESEARCH.md Code Examples references this
  by name) — construct fakes that raise `discord.Forbidden` vs `discord.HTTPException` on
  `.pin()`/`.delete()` to drive both branches.
- For HYG-03, extend `_FakeCloseableClient`/`_ClosedLoopFastPathProxy` to reproduce the
  scheduling-failure path (loop closed before schedule) vs. await-failure path (schedule
  succeeds, `future.result()` times out/raises) as two separate test cases, each asserting the
  distinct log message and that `bot.stop()` still does not raise and `fake_thread.joined ==
  [True]` (line 293 pattern).
- Use `structlog.testing.capture_logs()` (verified working this session, RESEARCH.md Code
  Examples) to assert on the `event=` string when a test needs to distinguish which branch fired
  — this repo has NO prior test asserting on structlog output, so this is genuinely new but the
  primitive is already available:
  ```python
  from structlog.testing import capture_logs
  with capture_logs() as cap:
      ...
  assert cap[0]["event"] == "..."
  ```

### `yahir_reusable_bot/lifecycle/ready_gate.py` (SURF-02 `on_online`)

**Analog:** the SAME file's already-correct sibling annotation, `on_fail` at line 92.

**Site to change** (line 91, current):
```python
on_online: Callable[..., None] | None = None,
```
**Analog it must match** (line 92, already correct):
```python
on_fail: Callable[[HealthResult], None] | None = None,
```
**Copy shape:** narrow `on_online` to `Callable[[HealthResult], None] | None` — identical shape
to its sibling three lines below. `HealthResult` is already imported at module scope (used by
`on_fail`'s existing annotation), so no new import needed.

### `yahir_reusable_bot/lifecycle/ready_gate.py` + `config/reload.py` (HYG-02)

**Analog:** the two files ARE each other's analog — a verbatim D-09 clone.

**Site 1** (`ready_gate.py:174-188`, current, f-string violation at line 188):
```python
    @staticmethod
    def _best_effort_hook(
        hook: Callable[[Any], None] | None, arg: Any, *, label: str
    ) -> None:
        """Invoke an optional hook best-effort: a None hook is a no-op; a raise is swallowed.
        ...
        """
        if hook is None:
            return
        try:
            hook(arg)
        except Exception:  # noqa: BLE001 — best-effort; never mask the engine result
            _log.warning(f"{label} hook failed; engine result unaffected")
```
**Site 2** (`config/reload.py:325-339`) — byte-identical structure, same f-string violation at
line 339.

**Copy shape:** replace `_log.warning(f"{label} hook failed; engine result unaffected")` with
`_log.warning("hook failed; engine result unaffected", label=label)` — structured kwarg form —
at BOTH sites. Do not let the clone drift: apply the identical edit to both files in the same
plan/commit.

**Test analog:** `structlog.testing.capture_logs()` (see gateway test section above) — assert
`cap[0]["label"] == "on_online"` (or `"on_fail"` / the reload-engine's label values) and
`cap[0]["event"] == "hook failed; engine result unaffected"` (no longer f-string-baked).

### `yahir_reusable_bot/discord/panelkit.py` (SURF-02 `render`)

**Analog:** same file's own typed-Callable convention already used for `ItemContributor` (line
81) and `DispatchCallable` (line 109).

**Site to change** (line 166, current):
```python
render: Callable[..., discord.Embed],
```
**Copy shape:** narrow to `Callable[[Any, Any], discord.Embed]` — arity-accurate (module docstring
+ RESEARCH.md confirm `render(reply, render_arg)` is always called with exactly two positional
args), type-vacuous by design (both params are legitimately `Any`, consistent with this file's own
`DispatchOutcome.render_arg: Any` field, line 105).

**Test pitfall (load-bearing):** `typing.get_type_hints(PanelKit.__init__)` raises `NameError`
without `localns={"SelectedContext": SelectedContext}` — `SelectedContext` is imported only under
`if TYPE_CHECKING:` at `panelkit.py:50-51`. The RED-first test in `tests/test_panelkit.py` MUST
import `SelectedContext` directly and pass it via `localns`:
```python
from yahir_reusable_bot.discord.selection import SelectedContext
hints = typing.get_type_hints(PanelKit.__init__, localns={"SelectedContext": SelectedContext})
assert hints["render"] == Callable[[Any, Any], discord.Embed]
```

### `yahir_reusable_bot/scheduler/engine.py` (SURF-02 `callback`, recorded no-op)

**Analog:** the same file's existing docstring-as-rationale convention, `register`'s docstring
(lines 58-63) which already explains WHY the three job-options are baked in.

**Copy shape:** no signature change to `callback: Callable[..., Any]` (line 52). Add an inline
comment or docstring addendum recording the D-62 verdict — "left variadic: `register` forwards
opaque `args`/`kwargs` straight through to `add_job`, so `Callable[..., Any]` is the accurate
contract, not an unexamined gap" — following the file's existing prose-rationale style rather
than a bare TODO.

### `tests/test_doc_drift.py` (DOCS-02, NEW FILE)

**Analog:** `tests/test_import_hygiene.py` — the repo's only existing "standing scan gate with
explicit exempt-list and a self-proof" convention (full excerpt read above, lines 1-178).

**Structural elements to copy:**
- Module docstring explaining the two-halves contract: (1) the real tree must pass, (2) a
  deliberately-injected violation must fail the SAME gate logic — mirror lines 12-16.
- `_MODULE_ROOT`-style path constant (line 64):
  ```python
  _MODULE_ROOT = Path(__file__).resolve().parent.parent / MODULE
  ```
  → for DOCS-02, the analogous constant is the `.planning/` directory:
  `_PLANNING_ROOT = Path(__file__).resolve().parent.parent / ".planning"`.
- A shared-helper-plus-self-proof split like `_scan_app_leaks` (lines 72-87): a pure function
  taking data in and returning violations, called BOTH by the real gate test and by a synthetic
  self-proof test that feeds it an injected temp-file match — mirror the pattern where
  `_scan_app_leaks` is called with a real graph in one test and a synthetic dict in another.
- Explicit, commented exempt-list — mirror the `APP = "weatherbot"` forbidden-literal-as-named-
  constant style (line 55) for readability: a `_EXEMPT: set[tuple[str, int]]` (relative path, line
  number) of the 3 intentional mentions + the 7 annotated-archive files, each entry commented with
  WHY it's exempt (per D-67).
- Regex: `re.compile(r"ops[/.]daemon")` — bare form per PC-D, NOT `weatherbot/ops/daemon`.
- Gate test walks `.planning/**/*.md`, greps each line for the bare regex, asserts every match's
  `(relative_path, line_number)` is in `_EXEMPT`; unexempted matches fail loudly (`assert
  unexempted == [], f"..."`) — mirror the `assert leaks == [], f"..."` shape at line 157.

## Shared Patterns

### Structured logging (`_log.warning`/`.critical(...)` with kwargs, never f-strings)

**Source:** `gateway.py:212-215`, `gateway.py:219-222`, `ready_gate.py:145-149`, `ready_gate.py:159-163`
**Apply to:** DISC-07's new log branch, HYG-03's two split messages, HYG-02's two fixed sites.
```python
_log.warning(
    "stray panel delete failed; continuing",
    channel_id=getattr(channel, "id", None),
)
```
Event string is a short, human-readable sentence; every dynamic value is a separate `key=value`
kwarg, never interpolated into the string.

### Plain-construction test doubles, no mocking library

**Source:** `tests/test_gateway.py:262-284`, `tests/test_registry.py:29-36`
**Apply to:** every new test in this phase (DISC-07/08, HYG-03, MATCH-03).
```python
class _FakeCloseableClient:
    async def close(self) -> None:
        pass
```
Minimal classes implementing only the methods exercised — never `unittest.mock`/`MagicMock`.

### RED-first self-proof note in test module docstrings

**Source:** `tests/test_registry.py:7-14`, `tests/test_import_hygiene.py:12-16`
**Apply to:** every new/extended test file — explain explicitly why a naive "still works"
assertion is NOT RED-proving, and which assertion genuinely fails pre-fix.

### `except <Subclass>:` before `except <BaseClass>:` ordering

**Source:** `gateway.py:196-200` (already correct)
**Apply to:** DISC-07's retry-pin fix — Python's `try/except` is first-match, not most-specific-
match; `discord.Forbidden` MUST be listed before `discord.HTTPException`.

## No Analog Found

None — every file in this phase is either a modify-in-place (analog = the file's own existing
convention or sibling line) or, for `tests/test_doc_drift.py`, a close role-match to
`tests/test_import_hygiene.py`'s standing-gate-with-self-proof structure.

## Metadata

**Analog search scope:** `yahir_reusable_bot/registry/`, `yahir_reusable_bot/discord/`,
`yahir_reusable_bot/lifecycle/`, `yahir_reusable_bot/scheduler/`, `yahir_reusable_bot/config/`,
`tests/` (whole directory)
**Files read directly this pass:** `registry/registry.py`, `discord/gateway.py` (180-360),
`lifecycle/ready_gate.py` (80-200), `config/reload.py` (310-350), `discord/panelkit.py` (30-170),
`scheduler/engine.py` (40-80), `tests/test_import_hygiene.py` (1-178), `tests/test_registry.py`
(full), `tests/test_gateway.py` (260-293)
**Pattern extraction date:** 2026-08-03
