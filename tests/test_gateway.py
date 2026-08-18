"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: build_client's `@client.event on_message`
shadowed the injected `on_message` handler, so the event dispatched to ITSELF
(infinite recursion → RecursionError) instead of the app handler. The mocked-Discord
behavioral suites never dispatched a real message, so only a live `!panel` surfaced it.
"""
from __future__ import annotations

import asyncio
import inspect
import threading

import discord
from structlog.testing import capture_logs

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


class _FakeRetryPinMessage:
    """A fresh-message double whose ``pin()`` fails with ``discord.HTTPException``
    on the FIRST call — driving ``summon_panel`` into the pin-cap branch — and,
    on the SECOND call (the retry pin), raises whichever exception instance the
    constructor was given, or succeeds and sets ``self.pinned = True`` when that
    is ``None``."""

    def __init__(self, *, retry_raises: BaseException | None) -> None:
        self.pinned = False
        self._retry_raises = retry_raises
        self._pin_calls = 0

    async def pin(self) -> None:
        self._pin_calls += 1
        if self._pin_calls == 1:
            raise discord.HTTPException(_Resp(), "at cap")
        if self._retry_raises is not None:
            raise self._retry_raises
        self.pinned = True


class _FakeStubbornStray:
    """An owned-stray double that counts ``delete()`` attempts and raises the
    injected exception for the first ``fail_count`` attempts — ``None`` (the
    default) means EVERY attempt raises, ``0`` means every attempt succeeds —
    so a test can distinguish 'attempted once' from 'attempted twice'."""

    def __init__(
        self, *, raises: BaseException | None, fail_count: int | None = None
    ) -> None:
        self.delete_attempts = 0
        self.deleted = False
        self._raises = raises
        self._fail_count = fail_count

    async def delete(self) -> None:
        self.delete_attempts += 1
        should_fail = self._fail_count is None or self.delete_attempts <= self._fail_count
        if should_fail:
            raise self._raises
        self.deleted = True


def test_retry_pin_forbidden_logs_a_distinct_event_not_the_cap_message():
    """DISC-07 — RED pre-fix: ``discord.Forbidden`` is a subclass of
    ``discord.HTTPException``, and Python's ``except`` clause matching is
    first-match, not most-specific-match. Pre-fix, the retry pin's bare
    ``except discord.HTTPException:`` swallows the ``Forbidden`` and logs the
    generic pin-cap message instead of a distinct one — mislabeling a revoked
    permission as a pin-cap failure."""
    stray = _FakeOwnedMessage()
    fresh = _FakeRetryPinMessage(retry_raises=discord.Forbidden(_Resp(), "revoked"))
    channel = _FakeChannel(owned_matches=[stray], fresh_message=fresh)

    with capture_logs() as cap:
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

    events = [entry["event"] for entry in cap]
    assert (
        "panel pin forbidden on retry (permission revoked mid-summon); "
        "fresh panel left unpinned"
    ) in events
    assert "panel pin failed at cap even after evicting a stray" not in events
    # The retry pin never succeeded — Forbidden was logged and swallowed, not
    # silently treated as success — so the fresh panel stays unpinned.
    assert fresh.pinned is False


def test_retry_pin_http_exception_still_logs_the_cap_message():
    """Under-sampling guard, GREEN both pre- and post-fix: a generic
    ``discord.HTTPException`` on the retry pin (NOT ``Forbidden``) must still
    produce the existing cap message. Proves the new ``Forbidden`` branch does
    not swallow the generic case it sits beside."""
    stray = _FakeOwnedMessage()
    fresh = _FakeRetryPinMessage(
        retry_raises=discord.HTTPException(_Resp(), "still at cap")
    )
    channel = _FakeChannel(owned_matches=[stray], fresh_message=fresh)

    with capture_logs() as cap:
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

    events = [entry["event"] for entry in cap]
    assert "panel pin failed at cap even after evicting a stray" in events
    assert (
        "panel pin forbidden on retry (permission revoked mid-summon); "
        "fresh panel left unpinned"
    ) not in events


def test_eviction_delete_failure_keeps_stray_in_cleanup_and_retries_it():
    """DISC-08 — RED pre-fix: ``matches.pop(0)`` removes the stray from
    ``matches`` BEFORE its ``delete()`` is even attempted. If that ``delete()``
    then fails, the stray is already gone from ``matches`` and is never
    retried by the ``for old in matches:`` cleanup loop — ``delete_attempts``
    stays at 1 pre-fix instead of the expected 2 (once as the eviction
    attempt, once via the cleanup loop's retry on the same call)."""
    stray = _FakeStubbornStray(raises=discord.HTTPException(_Resp(), "boom"))
    fresh = _FakeRetryPinMessage(retry_raises=None)
    channel = _FakeChannel(owned_matches=[stray], fresh_message=fresh)

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

    assert stray.delete_attempts == 2
    assert fresh.pinned is True


def test_eviction_delete_success_removes_stray_so_cleanup_does_not_redelete():
    """Pins the other side of the DISC-08 contract, GREEN both pre- and
    post-fix: a SUCCESSFUL eviction delete removes the stray from ``matches``,
    so the cleanup loop must not re-delete it — ``delete_attempts`` stays at
    exactly 1. Guards against the fix degrading into 'always retry everything
    twice'."""
    stray = _FakeStubbornStray(raises=None, fail_count=0)
    fresh = _FakeRetryPinMessage(retry_raises=None)
    channel = _FakeChannel(owned_matches=[stray], fresh_message=fresh)

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

    assert stray.delete_attempts == 1
    assert fresh.pinned is True


def test_pin_cap_with_zero_owned_strays_still_logs_the_d27_residual():
    """Boundary probe one step below the eviction threshold, GREEN both pre-
    and post-fix: zero owned strays and a cap failure on the FIRST pin must
    still hit the existing D-27 residual branch — the foreign-pin-saturation
    message — never the retry-cap message or the new Forbidden message
    (neither retry path is reachable when ``matches`` is empty)."""
    fresh = _FakeRetryPinMessage(retry_raises=None)
    channel = _FakeChannel(owned_matches=[], fresh_message=fresh)

    with capture_logs() as cap:
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

    events = [entry["event"] for entry in cap]
    assert (
        "panel pin failed at cap with no owned stray to evict "
        "(foreign-pin saturation); fresh panel sent but left unpinned"
    ) in events
    assert "panel pin failed at cap even after evicting a stray" not in events
    assert (
        "panel pin forbidden on retry (permission revoked mid-summon); "
        "fresh panel left unpinned"
    ) not in events


class _CoroCapturingClient:
    """A client whose ``close()`` is a PLAIN (non-``async``) method that builds the
    coroutine from an inner ``async def`` and appends it to ``self.coros`` before
    returning it (HYG-03 / PC-B). Production code calls ``self._client.close()`` and
    passes the returned object straight to ``run_coroutine_threadsafe`` — this double
    makes that exact coroutine object reachable from the test so its lifecycle
    (``inspect.getcoroutinestate``) can be asserted directly."""

    def __init__(self) -> None:
        self.coros: list[object] = []

    def close(self):
        async def _close() -> None:
            pass

        coro = _close()
        self.coros.append(coro)
        return coro


class _RaisingCloseClient:
    """A client whose ``close()`` raises once genuinely awaited on a live loop — drives
    the ``future.result()`` (await-failure) branch of ``BotThread.stop`` rather than the
    scheduling-failure branch."""

    async def close(self) -> None:
        raise RuntimeError("close boom")


def test_stop_closes_the_never_scheduled_coroutine_on_a_closed_loop():
    """HYG-03 / PC-B, RED pre-fix: on the TOCTOU race (fast-path proxy reports the loop
    running while the real underlying loop is closed), ``run_coroutine_threadsafe``
    raises before the coroutine returned by ``client.close()`` is ever scheduled.
    Pre-fix, that coroutine is constructed INLINE inside the
    ``run_coroutine_threadsafe(...)`` call — never bound to a name, never closed — so
    its state stays ``CORO_CREATED`` and it is later garbage-collected unawaited. That
    is the live production leak the suite's single warning reports; this test
    reproduces the race, it does not create it. Post-fix, ``stop()`` binds it to
    ``coro`` before scheduling and calls ``coro.close()`` on the scheduling-failure
    branch, so its state is ``CORO_CLOSED``.
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

    class _FakeJoinableThread:
        def __init__(self) -> None:
            self.joined: list[bool] = []

        def join(self, timeout: float | None = None) -> None:
            self.joined.append(True)

        def is_alive(self) -> bool:
            return False

    client = _CoroCapturingClient()
    bot = BotThread("fake-token", client=client)
    bot._loop = _ClosedLoopFastPathProxy(real_closed_loop)
    fake_thread = _FakeJoinableThread()
    bot._thread = fake_thread

    bot.stop()  # must NOT raise RuntimeError

    assert inspect.getcoroutinestate(client.coros[0]) == inspect.CORO_CLOSED
    assert fake_thread.joined == [True]


def test_stop_logs_a_distinct_scheduling_failure_message_on_a_closed_loop():
    """HYG-03 / D-64, RED pre-fix: both the scheduling-failure and await-failure
    branches currently share the same log message
    (``"bot client.close() did not complete cleanly"``). Post-fix, the
    scheduling-failure branch (this same TOCTOU race — the loop is closed before
    ``run_coroutine_threadsafe`` runs) must log a message DISTINCT from the
    await-failure message, so an operator can tell 'the loop died early' from 'the
    client hung' apart — the same don't-conflate-two-causes posture DISC-07 takes in
    ``summon_panel``.
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

    class _FakeJoinableThread:
        def __init__(self) -> None:
            self.joined: list[bool] = []

        def join(self, timeout: float | None = None) -> None:
            self.joined.append(True)

        def is_alive(self) -> bool:
            return False

    client = _CoroCapturingClient()
    bot = BotThread("fake-token", client=client)
    bot._loop = _ClosedLoopFastPathProxy(real_closed_loop)
    bot._thread = _FakeJoinableThread()

    with capture_logs() as cap:
        bot.stop()

    events = [entry["event"] for entry in cap]
    assert "bot client.close() could not be scheduled (bot loop already closed)" in events
    assert "bot client.close() did not complete cleanly" not in events


def test_stop_logs_the_await_failure_message_when_close_raises_on_a_live_loop():
    """HYG-03 / D-64 branch guard, GREEN both pre- and post-fix by design: when
    scheduling succeeds but ``future.result()`` raises (the client's ``close()``
    itself raises, on a genuinely running loop), the coroutine is live on the loop and
    must NOT be closed — closing a running coroutine raises ``RuntimeError: cannot
    close a running coroutine`` — so the existing await-failure message is logged
    unchanged. This is the branch D-64 deliberately leaves untouched; asserting it
    here guards against a future edit accidentally merging the two branches back
    together.
    """

    class _FakeJoinableThread:
        def __init__(self) -> None:
            self.joined: list[bool] = []

        def join(self, timeout: float | None = None) -> None:
            self.joined.append(True)

        def is_alive(self) -> bool:
            return False

    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    started = threading.Event()
    loop.call_soon_threadsafe(started.set)
    assert started.wait(timeout=5.0)

    client = _RaisingCloseClient()
    bot = BotThread("fake-token", client=client)
    bot._loop = loop
    fake_thread = _FakeJoinableThread()
    bot._thread = fake_thread

    try:
        with capture_logs() as cap:
            bot.stop()  # must NOT raise RuntimeError
    finally:
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=5.0)
        loop.close()

    events = [entry["event"] for entry in cap]
    assert "bot client.close() did not complete cleanly" in events
    assert (
        "bot client.close() could not be scheduled (bot loop already closed)"
        not in events
    )
    assert fake_thread.joined == [True]
