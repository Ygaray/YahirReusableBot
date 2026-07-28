"""Regression tests for DISC-05 and DISC-06 (H11/H12) in ``discord/panelkit.py``.

**DISC-05 (D-40):** ``interaction_check`` (`panelkit.py:299-331`) dereferences
``interaction.user.bot`` with no guard — an absent ``interaction.user`` crashes with
``AttributeError``. Self-proof note (D-11): RESEARCH.md's Pitfall 1 is a VERIFIED
CORRECTION of the original finding — the pre-fix ``AttributeError`` does NOT "escape"
``View.on_error`` (it IS caught and routed there by discord.py 2.7.1's own
``_scheduled_task``); the correct RED test calls ``interaction_check`` **directly** and
asserts it returns ``False`` without raising, sidestepping the ``on_error`` question
entirely — this file never asserts anything about ``on_error``. The absence sentinel in
discord.py 2.7.1 is ``discord.utils.MISSING`` (a distinct falsy-but-not-``None`` object),
so the two adversarial rows below are ``user=None`` AND a falsy, non-``None`` double
(``_FalsySentinel``) — an ``is None`` guard would pass the first row and silently
false-negative the second, re-opening the crash path. Both rows are RED pre-fix (both hit
an ``AttributeError`` on the unguarded ``.bot`` access, for different reasons: ``None`` has
no ``.bot`` attribute, and ``_FalsySentinel`` likewise defines none). A third row
(legitimate non-operator user) is GREEN both pre- and post-fix by design — it proves the
new falsy guard cannot false-positive on a real, truthy user and the existing non-operator
reject still fires after it.

**DISC-06 (D-41):** ``PanelKit.__init__`` (`panelkit.py:157-192`) accepts ``marker`` with
no validation; ``cid.startswith("")`` is always ``True``, so an empty marker makes
``is_owned_panel`` claim every bot-authored pin. Self-proof note: pre-fix, an empty or
whitespace-only marker constructs SILENTLY (no exception at all), so the RED assertion is
``pytest.raises(ValueError)`` at construction — there is no pre-fix return value to
compare against, only the absence of the raise. A fourth row confirms a valid, non-empty
marker still constructs (no regression to the happy path), and a fifth confirms the raised
message names the offending (empty) value, so a consumer sees why construction failed.

Style: a synthetic inline double (``_FakeInteraction``/``_FalsySentinel``) plus a
docstring-first adversarial-row layout, mirroring ``tests/test_identity.py``.
"""
from __future__ import annotations

import asyncio
import types

import pytest

from yahir_reusable_bot.discord.panelkit import PanelKit
from yahir_reusable_bot.discord.selection import SelectedContext

MARKER = "mk:"  # neutral placeholder marker, never a consumer's real prefix
OPERATOR_ID = 111
NON_OPERATOR_ID = 222


class _FakeResponse:
    """A no-op stand-in for ``discord.InteractionResponse`` — the non-operator reject
    path awaits ``interaction.response.send_message(...)``; this double just records
    nothing and returns, so the test never touches real discord.py networking."""

    async def send_message(self, *args, **kwargs) -> None:
        return None


class _FakeInteraction:
    """A synthetic interaction double carrying only what ``interaction_check`` reads:
    ``.user``, ``.data`` (for the reject-log's ``custom_id``), and ``.response`` (for the
    non-operator ephemeral ack). Never touches real discord.py Interaction machinery
    (RESEARCH.md Code Example #4)."""

    def __init__(self, user, data: dict | None = None) -> None:
        self.user = user
        self.data = data if data is not None else {"custom_id": f"{MARKER}cmd:status"}
        self.response = _FakeResponse()


class _FakeUser:
    """A minimal truthy user double — real ``discord.User``/``Member`` never override
    ``__bool__``, so any instance (even one with falsy-looking fields) is truthy."""

    def __init__(self, id: int, bot: bool = False) -> None:
        self.id = id
        self.bot = bot


class _FalsySentinel:
    """A ``discord.utils.MISSING``-shaped double: falsy (``__bool__`` -> False) but NOT
    ``None`` and NOT a ``User``/``Member`` — proves the guard must be a falsy check, not
    an identity (``is None``) check (RESEARCH.md Pitfall 1 bonus finding)."""

    def __bool__(self) -> bool:
        return False


def _build_test_panel(*, marker: str = MARKER) -> PanelKit:
    """A minimal valid ``PanelKit`` — one curated command, no contributors, injected
    ``render``/``dispatch`` stubs that raise if ever actually called (these tests never
    reach the command-dispatch path, only the operator gate / construction)."""

    registry = types.SimpleNamespace(by_name={"status": object()})

    async def _dispatch(name, selection):
        raise AssertionError("dispatch must not be invoked by these tests")

    def _render(reply, render_arg):
        raise AssertionError("render must not be invoked by these tests")

    return PanelKit(
        registry=registry,
        command_names=("status",),
        marker=marker,
        operator_id=OPERATOR_ID,
        selection=SelectedContext(None),
        contributors=[],
        render=_render,
        dispatch=_dispatch,
        labels={"status": "Status"},
        command_rows={"status": 1},
    )


# -- DISC-05: None/MISSING falsy guard in interaction_check ------------------------- #


def test_disc_05_interaction_check_returns_false_without_raising_when_user_is_none():
    """``_FakeInteraction(user=None)`` -> ``interaction_check`` must return False and must
    NOT raise. RED pre-fix: unguarded ``None.bot`` raises ``AttributeError``."""
    panel = _build_test_panel()
    interaction = _FakeInteraction(user=None)
    result = asyncio.run(panel.interaction_check(interaction))
    assert result is False


def test_disc_05_interaction_check_returns_false_for_missing_shaped_falsy_user():
    """A falsy-but-not-``None`` double (mimicking ``discord.utils.MISSING``) must also
    return False without raising. RED pre-fix (same unguarded ``.bot`` access raises
    ``AttributeError`` — ``_FalsySentinel`` has no ``.bot`` attribute either). This row is
    the one an ``is None`` guard would silently fail to catch — proving the fix must be a
    falsy check, not an identity check (RESEARCH.md Pitfall 1 bonus finding)."""
    panel = _build_test_panel()
    interaction = _FakeInteraction(user=_FalsySentinel())
    result = asyncio.run(panel.interaction_check(interaction))
    assert result is False


def test_disc_05_interaction_check_still_rejects_legitimate_non_operator_user():
    """A truthy, real-shaped non-operator user must still be gated by the EXISTING
    non-operator reject, proving the new falsy guard cannot false-positive on a
    legitimate user. GREEN both pre- and post-fix — a regression guard."""
    panel = _build_test_panel()
    interaction = _FakeInteraction(user=_FakeUser(id=NON_OPERATOR_ID, bot=False))
    result = asyncio.run(panel.interaction_check(interaction))
    assert result is False


# -- DISC-06: reject empty/whitespace marker at PanelKit construction --------------- #


def test_disc_06_empty_marker_raises_value_error_at_construction():
    """``PanelKit(..., marker="")`` must raise ``ValueError`` at construction. RED
    pre-fix: no marker validation exists, so this constructs SILENTLY — closing the
    ``cid.startswith("")``-owns-everything hole (an empty marker matches every
    bot-authored pin, so ``summon_panel`` could delete unrelated pins)."""
    with pytest.raises(ValueError):
        _build_test_panel(marker="")


def test_disc_06_whitespace_only_marker_raises_value_error_at_construction():
    """A whitespace-only marker is equally invalid — ``cid.startswith("   ")`` would
    never match a real custom_id, but the validation must reject on `str.strip()`
    emptiness, not mere non-emptiness. RED pre-fix (constructs silently)."""
    with pytest.raises(ValueError):
        _build_test_panel(marker="   ")


def test_disc_06_valid_marker_still_constructs():
    """A normal, non-empty marker must still construct successfully — no regression to
    the valid path. GREEN both pre- and post-fix."""
    panel = _build_test_panel(marker="wbpanel")
    assert panel is not None


def test_disc_06_value_error_names_the_offending_marker():
    """The raised message must reference the offending (empty) value so a consumer sees
    why construction failed — exact wording is Claude's Discretion, but the value must be
    named."""
    with pytest.raises(ValueError) as exc_info:
        _build_test_panel(marker="")
    assert repr("") in str(exc_info.value)
