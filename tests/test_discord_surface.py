"""SURF-01 (H17) — the ``discord`` package's public-surface agreement.

``discord/__init__.py``'s docstring already advertises the "create-before-delete summon
orchestration" and ``gateway.py``'s ``__all__`` already lists ``summon_panel``, but the
package ``__init__`` never re-exports it — so ``from yahir_reusable_bot.discord import
summon_panel`` raises ``ImportError`` against unfixed source. D-47 locks the fix as the
missing re-export leg ONLY (no docstring edit, no top-level ``yahir_reusable_bot`` widening).

RED-first (D-13): this test's body IS the success-criterion import statement itself, not an
indirect ``hasattr`` check performed after some other test has already imported
``yahir_reusable_bot.discord.gateway`` in the same session — that ordering would false-pass
via import-cache side effects (RESEARCH.md Pitfall 4). No mocking library is used, per the
repo-wide convention.
"""

from __future__ import annotations


def test_summon_panel_reexport_succeeds() -> None:
    from yahir_reusable_bot.discord import summon_panel  # noqa: F401 — import IS the assertion

    import yahir_reusable_bot.discord as discord_pkg

    assert "summon_panel" in discord_pkg.__all__


def test_summon_panel_not_widened_to_top_level_package() -> None:
    """D-47's second half: the re-export is scoped to the ``discord`` subpackage
    ONLY — the top-level ``yahir_reusable_bot`` package must NOT gain
    ``summon_panel``. Widening is the easy, well-intentioned regression (a
    missing re-export is caught by any consumer's first import; an over-broad one
    is not), so guard it explicitly (WR-01)."""
    import yahir_reusable_bot as pkg

    assert not hasattr(pkg, "summon_panel")
    assert "summon_panel" not in getattr(pkg, "__all__", [])
