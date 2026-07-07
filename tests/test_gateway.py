"""Regression tests for the gateway client wiring (yahir_reusable_bot.discord.gateway).

Covers the P27-extraction recursion bug: build_client's `@client.event on_message`
shadowed the injected `on_message` handler, so the event dispatched to ITSELF
(infinite recursion → RecursionError) instead of the app handler. The mocked-Discord
behavioral suites never dispatched a real message, so only a live `!panel` surfaced it.
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
