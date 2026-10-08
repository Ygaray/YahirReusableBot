"""``ReportingChannel`` — a :class:`Channel` decorator that tells an observer how each send went.

Wrap a bot's real channel at its composition root: ``ReportingChannel(channel, reporter.record_delivery)``.
A send that raises is reported as ``DeliveryResult(ok=False, detail="<Type>: <msg>")`` and then re-raised
unchanged, so retry logic above it behaves exactly as before. An observer that itself fails is ignored —
reporting must never break delivery.

An app channel may deliver through more than ``send`` (e.g. a ``send_briefing(text, extra)``): name those
methods in ``record=`` and each is proxied and observed exactly like ``send``. Every other attribute
passes through to the wrapped channel unobserved, so the wrapper is a drop-in for the app's channel.
An app delivery method you do NOT name in ``record=`` still works but is never observed: name every
method that delivers.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .base import Channel, DeliveryResult


class ReportingChannel(Channel):
    def __init__(self, inner: Channel, on_result: Callable[[DeliveryResult], None], *,
                 record: Iterable[str] = ()) -> None:
        self._inner = inner
        self._on_result = on_result
        self.name = inner.name
        if isinstance(record, str):
            raise TypeError(f"record= takes a tuple of method names, not the string {record!r}")
        for method in record:
            if method == "send":
                continue
            if method.startswith("_"):
                raise ValueError(f"record= cannot name private attribute {method!r}")
            target = getattr(inner, method)  # AttributeError names the missing method
            if not callable(target):
                raise TypeError(f"record= names {method!r}, which is not a method of the wrapped channel")
            setattr(self, method, self._observed(target))

    def send(self, text: str) -> DeliveryResult:
        return self._observed(self._inner.send)(text)

    def __getattr__(self, attr: str) -> Any:
        # Only reached for attributes this wrapper doesn't define: defer to the wrapped channel.
        if attr.startswith("_"):
            raise AttributeError(attr)
        return getattr(self._inner, attr)

    def _observed(self, deliver: Callable[..., DeliveryResult]) -> Callable[..., DeliveryResult]:
        def call(*args: Any, **kwargs: Any) -> DeliveryResult:
            try:
                result = deliver(*args, **kwargs)
            except Exception as exc:
                self._observe(DeliveryResult(ok=False, detail=f"{type(exc).__name__}: {exc}"))
                raise
            self._observe(result)
            return result
        return call

    def _observe(self, result: DeliveryResult) -> None:
        try:
            self._on_result(result)
        except Exception:
            pass
