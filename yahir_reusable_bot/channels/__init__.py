"""Channel-agnostic delivery surface.

Exports the clean, text-only :class:`Channel` ABC + :class:`DeliveryResult` — the
canonical ``send(text) -> DeliveryResult`` seam every provider implements. This is
a SUBSET surface by design (D-04): the concrete channel implementations and the
``build_channel`` factory stay host-side; the host wires them at its composition root.
"""

from __future__ import annotations

from .base import Channel, DeliveryResult

__all__ = ["Channel", "DeliveryResult"]
