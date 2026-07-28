"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: build_client's `@client.event on_message`
shadowed the injected `on_message` handler, so the event dispatched to ITSELF
(infinite recursion → RecursionError) instead of the app handler. The mocked-Discord
behavioral suites never dispatched a real message, so only a live `!panel` surfaced it.
"""
from __future__ import annotations

import asyncio

import discord

from yahir_reusable_bot.discord.gateway import BotThread, build_client, summon_panel


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


def test_bot_thread_records_login_failure_death_reason():
    """DISC-01 (H04): a LoginFailure death must leave a programmatic signal, not just
    a silently-dead bot. After ``_run()`` swallows a ``discord.LoginFailure`` raised
    from ``client.start()``, ``is_alive()`` reads False AND ``death_reason()`` reads
    the ``login_failure`` reason constant (D-22) — purely additive alongside the
    unchanged ``is_alive()`` semantics (D-23)."""

    class _FakeLoginFailureClient:
        async def __aenter__(self) -> "_FakeLoginFailureClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def start(self, token: str) -> None:
            raise discord.LoginFailure()

    bot = BotThread("fake-token", client=_FakeLoginFailureClient())
    bot._run()  # plain sync method; runs asyncio.run(_amain()) — no real thread needed

    assert bot.is_alive() is False
    assert bot.death_reason() == "login_failure"


def test_bot_thread_records_crashed_death_reason_on_generic_exception():
    """DISC-01 (H04), the second branch (under-sampling defense — both branches must
    be sampled, RESEARCH.md): a generic crash out of ``client.start()`` sets
    ``death_reason() == "crashed"`` (D-22's minimal two-reason bound). ``_run`` still
    never raises (failure isolation preserved)."""

    class _FakeCrashingClient:
        async def __aenter__(self) -> "_FakeCrashingClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def start(self, token: str) -> None:
            raise Exception("boom")

    bot = BotThread("fake-token", client=_FakeCrashingClient())
    bot._run()  # must not raise — die alone, never crash the process

    assert bot.death_reason() == "crashed"


class _Resp:
    """Minimal ``response``-shaped stub for constructing discord.py HTTPException
    subclasses (``NotFound``/``HTTPException`` read ``.status``/``.reason`` off it)."""

    status = 404
    reason = "stub"


class _FakeOwnedMessage:
    """A synthetic owned-panel message double: tracks whether delete()/pin() ran."""

    def __init__(self, *, delete_raises: BaseException | None = None) -> None:
        self.deleted = False
        self.pinned = False
        self._delete_raises = delete_raises

    async def delete(self) -> None:
        if self._delete_raises is not None:
            raise self._delete_raises
        self.deleted = True

    async def pin(self) -> None:
        self.pinned = True


class _FakeChannel:
    """A synthetic channel double: ``pins()`` yields injected owned matches;
    ``send()`` returns the injected fresh message."""

    id = 424242

    def __init__(self, *, owned_matches: list, fresh_message) -> None:
        self._owned_matches = owned_matches
        self._fresh_message = fresh_message
        self.sent_count = 0

    async def pins(self):
        for m in self._owned_matches:
            yield m

    async def send(self, *, embed, view):
        self.sent_count += 1
        return self._fresh_message


async def _noop() -> None:
    pass


async def _noop_int(_: int) -> None:
    pass


def test_summon_panel_continues_deleting_after_notfound_mid_delete():
    """DISC-02 (H05), half (a): a NotFound on the FIRST owned stray's delete() must
    not abort the remaining deletes (D-25's per-item catch) — net state is exactly
    ONE live pinned panel (the fresh one), not the 2+-live-panels CONFIRMED bug."""
    old1 = _FakeOwnedMessage(delete_raises=discord.NotFound(_Resp(), "gone"))
    old2 = _FakeOwnedMessage()
    old3 = _FakeOwnedMessage()
    fresh = _FakeOwnedMessage()
    channel = _FakeChannel(owned_matches=[old1, old2, old3], fresh_message=fresh)

    asyncio.run(
        summon_panel(
            channel=channel,
            bot_user=object(),
            idle_embed=object(),
            panel_factory=lambda: object(),
            is_owned=lambda m: True,
            on_created=_noop,
            on_resummoned=_noop,
            on_strays_cleaned=_noop_int,
        )
    )

    # old1's delete() raised NotFound (never marked deleted) — the remaining two
    # owned strays STILL got deleted despite it, and the fresh panel is pinned.
    assert old1.deleted is False
    assert old2.deleted is True
    assert old3.deleted is True
    assert fresh.pinned is True


class _FakeAtCapMessage:
    """A synthetic message double whose ``pin()`` fails with ``HTTPException`` UNLESS
    at least one owned stray has already been evicted (``freed_count >= 1``) — proving
    the fix reserves pin headroom rather than merely retrying blindly."""

    def __init__(self, *, cap_state: dict, is_fresh: bool = False) -> None:
        self.deleted = False
        self.pinned = False
        self._cap_state = cap_state
        self._is_fresh = is_fresh

    async def delete(self) -> None:
        self.deleted = True
        if not self._is_fresh:
            self._cap_state["freed_count"] += 1

    async def pin(self) -> None:
        if self._is_fresh and self._cap_state["freed_count"] < 1:
            raise discord.HTTPException(_Resp(), "at cap")
        self.pinned = True


def test_summon_panel_reserves_pin_headroom_at_cap_so_fresh_panel_ends_up_pinned():
    """DISC-02 (H05), half (b) — an INDEPENDENT fixture from half (a) (different code
    path, D-26): at the pin cap with >=2 owned panels, one owned stray is deleted
    BEFORE the fresh panel's pin succeeds (headroom-reserve). The fresh panel ends up
    PINNED and >=1 owned panel is live at every step (no-zero-panel-window, D-24)."""
    cap_state = {"freed_count": 0}
    old1 = _FakeAtCapMessage(cap_state=cap_state)
    old2 = _FakeAtCapMessage(cap_state=cap_state)
    fresh = _FakeAtCapMessage(cap_state=cap_state, is_fresh=True)
    channel = _FakeChannel(owned_matches=[old1, old2], fresh_message=fresh)

    asyncio.run(
        summon_panel(
            channel=channel,
            bot_user=object(),
            idle_embed=object(),
            panel_factory=lambda: object(),
            is_owned=lambda m: True,
            on_created=_noop,
            on_resummoned=_noop,
            on_strays_cleaned=_noop_int,
        )
    )

    assert fresh.pinned is True
    # At least one owned stray was live/evicted en route (no-zero-panel-window):
    # the eviction happened, but it never dropped the owned-panel count to zero
    # mid-flight (only one of the two owned matches needed evicting).
    assert cap_state["freed_count"] >= 1


def test_summon_panel_reserves_pin_headroom_at_cap_with_a_single_owned_panel():
    """DISC-02 (H05), half (b) boundary — the COMMON re-summon case is exactly ONE
    existing owned panel (the one being replaced). At the pin cap with a single owned
    stray, that stray must STILL be evicted to free a slot: create-before-delete already
    made the fresh panel live, so no-zero-window holds even when the last owned stray
    goes. The fresh panel must end up PINNED — never left fresh-but-unpinned (the ROADMAP
    success criterion). WR-01 regression guard: the >=2 eviction threshold skipped this
    single-stray case, dropping to the D-27 residual and leaving the fresh panel unpinned."""
    cap_state = {"freed_count": 0}
    old1 = _FakeAtCapMessage(cap_state=cap_state)
    fresh = _FakeAtCapMessage(cap_state=cap_state, is_fresh=True)
    channel = _FakeChannel(owned_matches=[old1], fresh_message=fresh)

    asyncio.run(
        summon_panel(
            channel=channel,
            bot_user=object(),
            idle_embed=object(),
            panel_factory=lambda: object(),
            is_owned=lambda m: True,
            on_created=_noop,
            on_resummoned=_noop,
            on_strays_cleaned=_noop_int,
        )
    )

    assert fresh.pinned is True
    assert cap_state["freed_count"] >= 1


def test_stop_does_not_raise_and_still_joins_when_loop_closes_mid_call():
    """DISC-03 (H07): a loop that closes between the ``is_running()`` fast-path check
    and the ``run_coroutine_threadsafe`` schedule (the TOCTOU boundary) must not let a
    ``RuntimeError`` escape ``stop()`` — it degrades (logs WARNING, falls through) AND
    still joins the thread (D-28). The success criterion is 'cannot raise AND still
    joins', not just 'cannot raise' (RESEARCH under-sampling risk).

    Per RESEARCH.md Pitfall 3: a REAL closed loop (``asyncio.new_event_loop()`` then
    ``.close()``) makes ``run_coroutine_threadsafe`` raise ``RuntimeError("Event loop
    is closed")`` deterministically, with zero timing/flakiness. A thin proxy reports
    ``is_running() == True`` (satisfying the fast-path) while delegating everything
    else (incl. ``call_soon_threadsafe``) to the real closed loop.
    """
    real_closed_loop = asyncio.new_event_loop()
    real_closed_loop.close()

    class _ClosedLoopFastPathProxy:
        def __init__(self, real_loop) -> None:
            self._real_loop = real_loop

        def is_running(self) -> bool:
            return True

        def __getattr__(self, name):
            return getattr(self._real_loop, name)

    class _FakeCloseableClient:
        async def close(self) -> None:
            pass

    class _FakeJoinableThread:
        def __init__(self) -> None:
            self.joined: list[bool] = []

        def join(self, timeout: float | None = None) -> None:
            self.joined.append(True)

        def is_alive(self) -> bool:
            return False

    bot = BotThread("fake-token", client=_FakeCloseableClient())
    bot._loop = _ClosedLoopFastPathProxy(real_closed_loop)
    fake_thread = _FakeJoinableThread()
    bot._thread = fake_thread

    bot.stop()  # must NOT raise RuntimeError

    assert fake_thread.joined == [True]
