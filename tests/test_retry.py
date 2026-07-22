"""Regression tests for RELY-01 (H02): ``is_transient`` misses common httpx
network / protocol failures, so a routine mid-response server hangup never
drives the two-burst retry and a delivery is silently dropped.

Self-proof note (D-11, matching ``test_selfproof_*`` in
``tests/test_import_hygiene.py``): a test that only asserts
``pytest.raises(httpx.RemoteProtocolError)`` around an exhausted retry passes
IDENTICALLY before and after the fix — pre-fix, ``is_transient`` returns
``False``, so the exception escapes immediately (after 1 attempt) rather than
after the full budget. The escaped exception TYPE is the same either way. It
is the attempt-COUNT assertion — 4, not 1 — that is genuinely RED against
pre-fix source; a type-only assertion would prove nothing.
"""
from __future__ import annotations

import httpx
import pytest

from yahir_reusable_bot.reliability.retry import build_retrying, is_transient


def test_classification_includes_remote_protocol_error():
    """A server that hangs up mid-response raises RemoteProtocolError. Pre-fix,
    is_transient misses it entirely (D-01) — a routine hangup is never retried
    and a delivery silently drops."""
    assert is_transient(httpx.RemoteProtocolError("server hung up mid-response")) is True


def test_classification_includes_network_errors():
    """Every httpx.NetworkError subclass must classify transient (D-01/D-03):
    WriteError and CloseError are real pre-fix misses; ConnectError and
    ReadError were already covered but must stay covered under the broadened
    tuple. PoolTimeout and ReadTimeout are asserted too, via the unchanged
    TimeoutException arm (D-03) — so the broadening cannot silently drop
    them."""
    assert is_transient(httpx.WriteError("write failed mid-request")) is True
    assert is_transient(httpx.CloseError("connection closed")) is True
    assert is_transient(httpx.ConnectError("connect failed")) is True
    assert is_transient(httpx.ReadError("read failed")) is True
    assert is_transient(httpx.PoolTimeout("pool exhausted")) is True
    assert is_transient(httpx.ReadTimeout("read timed out")) is True


def test_classification_excludes_local_protocol_error():
    """A client-side request-construction bug (LocalProtocolError) never
    resolves by waiting; retrying it just burns the delivery window. GREEN
    pre-fix — this is a regression guard against the rejected blanket
    httpx.TransportError shape (D-02)."""
    assert is_transient(httpx.LocalProtocolError("bad request construction")) is False


def test_classification_excludes_proxy_error_and_unsupported_protocol():
    """ProxyError and UnsupportedProtocol are the other two TransportError
    children a blanket rule would have swept in (D-02). ProxyError-as-transient
    is an explicitly DEFERRED idea, not part of this phase: neither current
    transport proxies (OpenWeather via httpx directly, Discord via
    discord.py), so treating it as transient here would be unreachable code
    with no honest RED test behind it. GREEN pre-fix; regression guard."""
    assert is_transient(httpx.ProxyError("proxy hiccup")) is False
    assert is_transient(httpx.UnsupportedProtocol("unsupported://x")) is False


def test_classification_status_branch_unchanged():
    """The D-01 change touches only the exception-type arm of is_transient;
    the HTTPStatusError / TRANSIENT-status arm below it must be undisturbed.
    503 and 429 stay transient; 404 and 401 stay permanent. GREEN pre-fix;
    regression guard."""
    request = httpx.Request("GET", "https://example.invalid")

    def _status_error(status_code: int) -> httpx.HTTPStatusError:
        response = httpx.Response(status_code, request=request)
        return httpx.HTTPStatusError("error", request=request, response=response)

    assert is_transient(_status_error(503)) is True
    assert is_transient(_status_error(429)) is True
    assert is_transient(_status_error(404)) is False
    assert is_transient(_status_error(401)) is False


def test_classification_is_pure_and_repeatable():
    """is_transient must be a pure classifier: calling it repeatedly on the
    SAME exception instance returns the same boolean every time and writes no
    module-level state. This is the idempotency contract the classifier must
    hold across the two bursts of a single retry schedule (edge probe:
    RELY-01). RED pre-fix — pre-fix is_transient(RemoteProtocolError) returns
    False for every call, failing this assertion; this also guards that a
    future refactor doesn't introduce per-call nondeterminism (e.g. caching
    keyed on identity) into the classifier."""
    exc = httpx.RemoteProtocolError("server hung up mid-response")
    results = [is_transient(exc), is_transient(exc), is_transient(exc)]
    assert results == [True, True, True]


def test_exhausted_transient_escapes_as_itself_after_full_budget(fake_stop_event):
    """The D-16/D-17 behavioral proof — this is the test that carries the
    phase's real evidence.

    D-17 restatement: the ROADMAP's literal criterion ("reports
    transient_exhausted on exhaustion") is NOT assertable in this repo —
    REASON_TRANSIENT_EXHAUSTED is defined at retry.py:75 but assigned only by
    consumer-side code (fire_slot lives in WeatherBot, not here). The
    hub-scoped equivalent this test asserts instead: an exhausted
    RemoteProtocolError propagates out of Retrying.__call__ AS ITSELF, never
    wrapped in a tenacity.RetryError — the exact mechanism behind the
    consumer symptom (retry.py:247's retry_error_callback exists precisely to
    prevent the RetryError wrapper that fire_slot would otherwise
    mis-classify as internal_error). This plan does not replicate fire_slot's
    reason-picking logic here (D-18) — that would encode consumer behavior in
    a hub test.
    """
    attempts = [0]

    def _always_hangs_up():
        attempts[0] += 1
        raise httpx.RemoteProtocolError("server hung up mid-response")

    retrying = build_retrying(
        fake_stop_event, attempts_per_burst=2, burst_spread_s=0, mid_pause_s=0
    )

    with pytest.raises(httpx.RemoteProtocolError) as exc_info:
        retrying(_always_hangs_up)

    assert attempts[0] == 4, (
        "expected 2 * attempts_per_burst == 4 attempts; a count of 1 means "
        "is_transient returned False and the retry loop never ran at all — "
        "exactly the pre-fix behavior this test must catch"
    )
    assert type(exc_info.value) is httpx.RemoteProtocolError, (
        "the exhausted exception must escape as itself, not wrapped in "
        "tenacity.RetryError — a RetryError here is the exact wrapper the "
        "consumer mis-classifies as internal_error instead of "
        "transient_exhausted; retry_error_callback at retry.py:247 is what "
        "prevents it"
    )
