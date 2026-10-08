"""``ReportingChannel`` — a :class:`Channel` decorator that tells an observer how each send went.

Wrap a bot's real channel at its composition root: ``ReportingChannel(channel, reporter.record_delivery)``.
A send that raises is reported as ``DeliveryResult(ok=False, detail="<Type>: <msg>")`` and then re-raised
unchanged, so retry logic above it behaves exactly as before. An observer that itself fails is ignored —
reporting must never break delivery.
"""

from __future__ import annotations

from typing import Callable

from .base import Channel, DeliveryResult


class ReportingChannel(Channel):
    def __init__(self, inner: Channel, on_result: Callable[[DeliveryResult], None]) -> None:
        self._inner = inner
        self._on_result = on_result
        self.name = inner.name

    def send(self, text: str) -> DeliveryResult:
        try:
            result = self._inner.send(text)
        except Exception as exc:
            self._observe(DeliveryResult(ok=False, detail=f"{type(exc).__name__}: {exc}"))
            raise
        self._observe(result)
        return result

    def _observe(self, result: DeliveryResult) -> None:
        try:
            self._on_result(result)
        except Exception:
            pass
