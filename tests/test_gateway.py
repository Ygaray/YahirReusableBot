"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: build_client's `@client.event on_message`
shadowed the injected `on_message` handler, so the event dispatched to ITSELF
(infinite recursion → RecursionError) instead of the app handler. The mocked-Discord
behavioral suites never dispatched a real message, so only a live `!panel` surfaced it.
"""
from __future__ import annotations

import asyncio

import discord

from yahir_reusable_bot.discord.gateway import BotThread, build_client


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
