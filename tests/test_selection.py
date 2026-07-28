"""Regression tests for SelectedContext's await-safety contract
(yahir_reusable_bot.discord.selection).

Covers DISC-04 (H08): a value re-read via ``.value`` after an ``await`` can observe a
concurrent ``.set()`` that ran during the yield (a ``Select`` tap on the gateway loop
rebinding the cell during an off-loop ``await``), yielding a mismatched render label. A
value captured via ``.snapshot()`` BEFORE the ``await`` is stable across that same
interleaved ``.set()`` (D-29/D-30).

No discord.py import needed (Pitfall 4, RESEARCH.md): the hazard is a pure single-threaded
event-loop interleaving reproducible with two plain coroutines and an ``asyncio.sleep(0)``
yield point — no gateway, no ``discord.ui.Select``, no real interaction required.
"""
from __future__ import annotations

import asyncio

from yahir_reusable_bot.discord.selection import SelectedContext


def test_snapshot_is_stable_across_interleaved_set_but_value_reflects_it():
    """Both halves of D-33's assertion live in the SAME test (RESEARCH.md's DISC-04
    under-sampling risk): a snapshot() taken before an await is UNCHANGED after a
    concurrent set() runs during the yield, while a plain .value re-read after the same
    yield DOES reflect the write. Sampling only the first half would false-green an
    over-fix that also freezes .value after first read; sampling only the second half
    would not prove snapshot() is load-bearing at all."""
    cell = SelectedContext("A")

    async def reader_via_snapshot() -> str:
        snap = cell.snapshot()
        await asyncio.sleep(0)  # yield point; writer interleaves here
        return snap

    async def reader_via_value() -> str:
        await asyncio.sleep(0)  # yield point; writer interleaves here
        return cell.value

    async def writer() -> None:
        await asyncio.sleep(0)
        cell.set("B")

    async def run() -> tuple[str, str]:
        snap_result, _, value_result = await asyncio.gather(
            reader_via_snapshot(), writer(), reader_via_value()
        )
        return snap_result, value_result

    snap_result, value_result = asyncio.run(run())

    assert snap_result == "A", (
        "snapshot() captured before the await must be STABLE across the interleaved "
        "set() that ran during the yield — this is the DISC-04 fix (D-29)"
    )
    assert value_result == "B", (
        ".value re-read after the same interleaved set() must reflect the write — "
        "proving the snapshot() idiom is load-bearing and that .value is NOT frozen "
        "after first read (guards against an over-fix, D-33 under-sampling risk)"
    )
