# Phase 1: Reachable reliability - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 4 (2 modified, 2 created; conftest.py counted as a shared substrate file)
**Analogs found:** 4 / 4 (with an important caveat on the two NEW test files — see below)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `yahir_reusable_bot/reliability/retry.py` (modify `is_transient`) | service (pure classifier function) | transform | itself — surrounding module conventions (`parse_retry_after`, `is_auth_failure`) | exact (same file, same author's own idiom) |
| `yahir_reusable_bot/lifecycle/identity.py` (modify `_argv_matches_marker`) | utility (private guard/matcher) | transform | itself — surrounding module conventions (`is_running_process`, `_read_proc_cmdline`) | exact (same file, same author's own idiom) |
| `tests/test_retry.py` (NEW) | test | request-response / behavioral unit | `tests/test_gateway.py` (shape/imports/naming) **+ `tests/test_import_hygiene.py`** (RED-first `test_selfproof_*` idiom, `pytest.raises`) | role-match on shape; **no fixture-based analog exists anywhere in the repo** |
| `tests/test_identity.py` (NEW) | test | request-response / behavioral unit | `tests/test_gateway.py` + `tests/test_import_hygiene.py` (same as above) | role-match on shape; **no fixture-based analog exists anywhere in the repo** |
| `tests/conftest.py` (NEW) | config/fixture provider | transform (test-double construction) | **none** | no analog — first conftest.py in repo history |

**Explicit flag for the planner:** `tests/conftest.py` and the fixture-consuming style in
`test_retry.py`/`test_identity.py` have **zero in-repo precedent**. Do not treat the "no analog"
line below as a gap to paper over — CONTEXT.md D-09 confirms this is an intentional, locked
convention change (the hub has never had a `conftest.py` or a `@pytest.fixture`). What IS
inherited from the existing suite is everything else: file layout, import style, docstring-first
posture, assertion style, and the RED-first self-proof idiom. Those conventions are extracted
below and must still be followed even though the fixture mechanism itself is new.

## Pattern Assignments

### `yahir_reusable_bot/reliability/retry.py` — `is_transient` (RELY-01 fix)

**Analog:** the function itself + its sibling classifiers in the same file (`is_auth_failure`,
`parse_retry_after`) — read `yahir_reusable_bot/reliability/retry.py:1-249` in full for module
context.

**Current buggy code** (`retry.py:80-91`):
```python
def is_transient(exc: BaseException) -> bool:
    """True for retryable failures: network errors and transient HTTP statuses.

    Timeouts / connect / read errors and ``HTTPStatusError`` whose status is in
    :data:`TRANSIENT` (429 / 5xx) are retryable; everything else (incl. 4xx in
    :data:`PERMANENT`) is not (D-08, RELY-02).
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in TRANSIENT
    return False
```

**Module docstring-carries-rationale convention** (`retry.py:1-37`) — the module leads with a
long docstring stating WHY design decisions are load-bearing (e.g. "Interruptibility (D-07 /
Pitfall 1)"), citing decision IDs inline. Extend this same convention into the fixed function's
own docstring per CONTEXT.md D-02 (deny-by-default posture) and D-03 (installed httpx 0.28.1
class-tree table) — do not just fix the tuple silently, state the rejected alternative
(`TransportError` blanket) and why, mirroring how `two_burst_wait` and `build_retrying`'s
docstrings each state a rejected alternative inline (`retry.py:200-211`).

**Sibling classifier idiom to match exactly** (`is_auth_failure`, `retry.py:94-99`):
```python
def is_auth_failure(exc: BaseException) -> bool:
    """True only for an ``HTTPStatusError`` 401/403 (chooses ``reason=auth_failed``)."""
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {
        401,
        403,
    }
```
`is_transient` should keep this file's terse-`isinstance`-tuple, single-purpose-function shape —
no restructuring beyond broadening the tuple per D-01.

**Load-bearing exhaustion wiring — do not touch, but must be understood for D-16/D-17 tests**
(`retry.py:243-247`):
```python
        # On exhaustion, return the final outcome's .result(): a non-ok
        # DeliveryResult is returned (→ transient_exhausted), an exhausted
        # exception is re-raised (→ caught by fire_slot's httpx handlers). This
        # avoids a RetryError being mis-classified as internal_error (UAT Test 1).
        retry_error_callback=lambda rs: rs.outcome.result(),
```

**Imports pattern** (`retry.py:39-52`):
```python
from __future__ import annotations

import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import httpx
import structlog
from tenacity import (
    Retrying,
    retry_if_exception,
    retry_if_result,
    stop_after_attempt,
)
```

---

### `yahir_reusable_bot/lifecycle/identity.py` — `_argv_matches_marker` (LIFE-01 fix)

**Analog:** the function itself + its caller `is_running_process` in the same file — read
`yahir_reusable_bot/lifecycle/identity.py:1-164` in full for module context.

**Current buggy code** (`identity.py:130-149`):
```python
def _argv_matches_marker(cmdline: bytes, *, proc_marker: bytes) -> bool:
    """Return True only when NUL-separated ``cmdline`` names the marker PROGRAM.

    The PID-recycling defense (T-09-06) must key on program identity, NOT on the
    token appearing anywhere in argv (CR-02). A raw ``proc_marker in cmdline``
    substring test wrongly accepts unrelated recycled-PID processes whose argv
    merely *mentions* the path — ``vim .../bot/config.toml``,
    ``tail -f bot.log`` — and would deliver SIGHUP (default disposition:
    terminate) to them. So match ``argv0``'s basename, and for the
    ``python -m <module>`` form match the ``-m`` module target in the next two
    fields; never the whole buffer.
    """
    argv = [part for part in cmdline.split(b"\x00") if part]
    if not argv:
        return False
    prog = Path(argv[0].decode("utf-8", "replace")).name
    if prog == proc_marker.decode("utf-8", "replace"):
        return True
    # `python -m <module> [run]`: interpreter is argv0, `-m` then the module name.
    return b"-m" in argv[1:3] and proc_marker in argv[1:4]
```

**What must be preserved verbatim (unchanged branch, D-04):** the `argv0`-basename check
(`identity.py:145-147`, the `prog == proc_marker...` branch) — only the final `return` line
(the `-m`-window check) changes.

**Docstring-carries-decision convention to extend** (module header, `identity.py:1-25`, and the
function's own docstring above) — same posture as `retry.py`: state the locked rule explicitly.
CONTEXT.md D-06 requires "first `-m` wins" be stated as THE rule, not a heuristic. RESEARCH.md's
Pattern 2 gives one valid concrete shape (not mandatory verbatim, but matches this file's
loop/early-return style used elsewhere, e.g. `is_running_process`'s `try/except FileNotFoundError`
early-return at `identity.py:122-126`):
```python
    for i, tok in enumerate(argv[1:], start=1):
        if tok == b"-m":
            return i + 1 < len(argv) and argv[i + 1] == proc_marker
    return False
```

**Degrade-vs-raise split (must preserve — this function is a guard, not a writer):** contrast
`write_pid_atomic` (`identity.py:62-87`, re-raises on error — a writer) against
`is_running_process` (`identity.py:102-127`, degrades to `False`/`True` — a guard/reader). The
LIFE-01 fix lives inside the guard branch and must keep degrading (return `False`), never raise,
per CONTEXT.md's explicit note under "Established Patterns."

**Imports pattern** (`identity.py:27-33`):
```python
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
```

**Injectable seam already present — no new test hook needed** (`identity.py:102-127`,
`is_running_process`'s `cmdline_reader` parameter, D-12):
```python
def is_running_process(
    pid: int,
    *,
    proc_marker: bytes,
    cmdline_reader: Callable[[int], bytes] | None = None,
) -> bool:
    ...
    if cmdline_reader is None:
        cmdline_reader = lambda p: _read_proc_cmdline(p, proc_marker=proc_marker)
    try:
        cmdline = cmdline_reader(pid)
    except FileNotFoundError:
        return False
    return _argv_matches_marker(cmdline, proc_marker=proc_marker)
```

---

### `tests/test_retry.py` (NEW) and `tests/test_identity.py` (NEW)

**Analog for shape/imports/naming/assertions:** `tests/test_gateway.py` (full file, 31 lines —
the only prior behavioral test in the repo).

```python
"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: ...
"""
from __future__ import annotations

import asyncio

import discord

from yahir_reusable_bot.discord.gateway import build_client


def test_on_message_event_dispatches_to_injected_handler_not_itself():
    """The client's on_message event must call the INJECTED handler exactly once —
    never recurse into itself (the shadowed-name regression)."""
    seen: list[object] = []

    async def app_handler(message: object) -> None:
        seen.append(message)

    client = build_client(on_message=app_handler, view=discord.ui.View())

    sentinel = object()
    asyncio.run(client.on_message(sentinel))  # would RecursionError before the fix

    assert seen == [sentinel]
```
Conventions to copy exactly: module docstring stating what regression/finding the file covers;
`from __future__ import annotations`; flat module-level `test_*` functions (no classes); a
docstring on EACH test explaining *why*, not just what; synthetic inline doubles instead of a
mocking library (`app_handler`/`seen` here is the model for the fake `stop_event` /
`cmdline_reader` this phase needs); plain `assert` statements, no custom assertion helpers.

**Analog for the RED-first idiom:** `tests/test_import_hygiene.py` `test_selfproof_*` functions
(D-11) — `test_import_hygiene.py:183-199` and `:228-251`. Pattern: a "real" gate test
(`test_module_imports_with_app_blocked`) is paired with a `test_selfproof_*` sibling that proves
the gate is not a no-op by driving the SAME underlying mechanism against a synthetic
known-bad input and asserting it is caught. For Phase 1 this idiom maps onto D-13's two-commit
RED-first requirement (commit the test RED against pre-fix source, then commit the fix) rather
than a literal `test_selfproof_*` sibling function — CONTEXT.md is explicit that git history is
the proof mechanism here, not an in-file self-proof pair. Cite this idiom in the test docstrings
per D-11's "align naming and docstring posture with it," e.g. echo the "prove this is not a
no-op" framing when documenting why the attempt-COUNT assertion (not just the escaped-type
assertion) is required for RELY-01 (Pitfall 1 in RESEARCH.md).

**`pytest.raises` precedent** (`test_import_hygiene.py:243-247`):
```python
        with pytest.raises(ImportError) as exc_info:
            importlib.import_module(target)
        assert "BLOCKED app import" in str(exc_info.value), (
            "the ImportError must come from the _AppBlocker (proving it bit), not from a "
            f"normal-finder ModuleNotFoundError: {exc_info.value}"
        )
```
This is the repo's only prior `pytest.raises` usage — a usable precedent for the RELY-01
exhaustion test's escape assertion (D-16's discretion point). Note the message-carrying
`pytest.raises(...) as exc_info` + explanatory assertion message style — worth matching if
`pytest.raises` is chosen over `try/except`.

**No analog for:** fixture consumption (`def test_x(fake_stop_event):` style) or `conftest.py`
itself — none exists in this repo. Do not force-fit an analog; RESEARCH.md's Code Examples
section (the `FakeStopEvent` class and `build()` NUL-joiner shown at RESEARCH.md `retry.py`
Pattern 1 and `identity.py` Code Examples) is the closest available reference, since it was
empirically verified against the real production functions rather than invented.

---

### `tests/conftest.py` (NEW)

**No analog — first conftest.py in repo history (confirmed).** Build directly from D-10's
minimal-scope decision using the shapes already verified in RESEARCH.md's Code Examples:

Fake `stop_event` shape (verified working against `build_retrying`, RESEARCH.md Pattern 1 /
Code Examples):
```python
class FakeStopEvent:
    def wait(self, timeout=None):
        return False
```

NUL-separated cmdline-bytes builder shape (verified working against `_argv_matches_marker`,
RESEARCH.md Code Examples):
```python
def build(*parts: bytes) -> bytes:
    return b"\x00".join(parts) + b"\x00"
```

Exact fixture names/signatures are Claude's discretion (CONTEXT.md, "Claude's Discretion"
section) within this minimal bound — D-10 explicitly forbids adding anything speculative for
Phases 2-4.

## Shared Patterns

### Module docstrings carry decision rationale, not just what/how
**Source:** `yahir_reusable_bot/reliability/retry.py:1-37`, `yahir_reusable_bot/lifecycle/identity.py:1-25`
**Apply to:** both modified production files. Each fix's docstring must state the locked rule
(D-02 deny-by-default / D-06 first-`-m`-wins) and, where relevant, the rejected alternative and
why — this file's established habit, not new ceremony.

### Degrade vs. raise split
**Source:** `yahir_reusable_bot/lifecycle/identity.py` — contrast `write_pid_atomic` (raises,
`:62-87`) vs. `is_running_process`/`_argv_matches_marker` (degrade, `:102-149`)
**Apply to:** the LIFE-01 fix only — it is in the degrade half and must keep returning `False`,
never raise.

### Docstring-first, no-mocking-library, flat module-level test functions
**Source:** `tests/test_gateway.py` (whole file), corroborated by `.planning/codebase/TESTING.md`
**Apply to:** `tests/test_retry.py`, `tests/test_identity.py` — every convention except the
fixture mechanism itself.

### RED-first self-proof framing
**Source:** `tests/test_import_hygiene.py:183-199`, `:228-251` (`test_selfproof_*`)
**Apply to:** docstring language in `tests/test_retry.py`/`tests/test_identity.py` explaining why
each assertion is chosen (e.g. attempt-count, not just exception-type) — echoes this file's
"prove it's not a no-op" posture even though Phase 1's actual RED-first proof mechanism is git
history (D-13, two commits per fix), not an in-file self-proof pair.

### Injectable seams already exist — no new test hooks
**Source:** `yahir_reusable_bot/reliability/retry.py:184-190` (`build_retrying` keyword params),
`yahir_reusable_bot/lifecycle/identity.py:102-107` (`is_running_process`'s `cmdline_reader`)
**Apply to:** both new test files — D-12 confirms zero production-code seam additions are needed;
tests reach both fixes purely through existing keyword arguments.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/conftest.py` | config/fixture provider | transform | No `conftest.py` exists anywhere in repo history; this phase (D-09) is the first. Build from RESEARCH.md's verified Code Examples instead of an in-repo analog. |
| `tests/test_retry.py` / `tests/test_identity.py` fixture-consuming style | test | request-response | No file in the repo consumes a `@pytest.fixture`; `test_gateway.py` and `test_import_hygiene.py` are both fixture-free. Non-fixture conventions (imports, naming, docstrings, assertions) ARE inherited from those two files; only the fixture-consumption mechanics are new. |

## Stale Documentation Flag

`.planning/codebase/TESTING.md:36` ("No `conftest.py`") and `:142` ("No `@pytest.fixture`
decorators in use") will become **factually stale the moment this phase lands** — D-09 is a
deliberate, locked convention change, not an oversight. `.planning/codebase/TESTING.md:239` ("No
`pytest.raises()` currently") is *already* stale as of the phase start — `tests/test_import_hygiene.py:243`
uses it today. Per CONTEXT.md's Deferred Ideas, refreshing `TESTING.md` is explicitly out of this
phase's scope — housekeeping only. The planner should not attempt to update `TESTING.md` inside
this phase's plans.

## Metadata

**Analog search scope:** `yahir_reusable_bot/reliability/`, `yahir_reusable_bot/lifecycle/`,
`tests/` (entire directory — only 2 pre-existing test files in the whole repo)
**Files scanned:** `retry.py`, `identity.py`, `test_gateway.py`, `test_import_hygiene.py` (all
read in full or near-full; no file exceeded 2,000 lines, so no offset/limit chunking was needed)
**Pattern extraction date:** 2026-07-22
