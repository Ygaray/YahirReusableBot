"""The import-hygiene gates — the reusable module must never reach back into a host app.

``yahir_reusable_bot`` is the clean core future bots import (D-01). Its whole value is a
ONE-WAY dependency: a host app may import the module, but no module file may ever import
``weatherbot`` (or any ``weatherbot.*`` submodule) — the original host app's namespace, kept
here as the canonical forbidden-prefix literal. A second, softer contract guards the module's
PUBLIC SURFACE: no ``def``/``class``/parameter/annotation NAME may carry a weather noun
(``weather|forecast|location|openweather|\\buv\\b|briefing``) — so the relocated code reads as
a generic bot core, not a weather bot in disguise (D-11/D-13). Docstrings and comments are
PROSE and are deliberately ignored.

Three standing gates enforce this, each paired with a self-proof — a guard is only trustworthy
if a deliberately-injected violation is PROVEN to trip it. So every retained gate has TWO halves:

1. The REAL module tree must PASS the gate (the relocated code is clean).
2. A deliberately-constructed leak/noun, run through the SAME gate logic, must FAIL.

STANDALONE-REPO RE-SCOPE NOTE (Phase 28 physical split, Pitfall 6 / Open Question 2):
This file was relocated verbatim from the WeatherBot repo's ``tests/test_import_hygiene.py``
and re-scoped because the ``weatherbot`` package NO LONGER EXISTS in this standalone repo:

  * The two grimp graph gates (``test_module_imports_zero_app_code`` /
    ``test_discord_adapter_imports_zero_app_code``) now build a SINGLE-package graph
    ``grimp.build_graph(MODULE, cache_dir=None)``. The original two-package
    ``build_graph(MODULE, APP)`` graphed the app package to make a cross-package leak edge
    visible; with no ``weatherbot`` package present that build would raise. The
    ``_scan_app_leaks`` prefix scan still catches any ``weatherbot.*`` *string* edge a module
    might declare, so the one-way-dependency contract is still enforced.
  * The two REAL-IMPORT self-proofs (``test_selfproof_import_gate_catches_real_app_edge`` and
    ``test_selfproof_isolated_import_catches_real_app_edge``) and the ``_injected_app_leak()``
    helper were DROPPED. They wrote a literal ``import weatherbot.config.models`` into the
    package and relied on a real ``weatherbot`` package resolving — which raises
    ``ModuleNotFoundError: weatherbot`` here. The retained synthetic-dict self-proof
    (``test_selfproof_import_gate_catches_injected_app_edge``), the litmus self-proof, and the
    isolated-import blocker self-proof (retargeted to a synthetic blocked name, below) still
    prove the gate logic bites without any real app package.
  * ``test_no_deferred_cycle_import_survives_in_app_interactive`` was NOT relocated — it is an
    APP invariant reading ``weatherbot/interactive/``; it stays in the WeatherBot suite.
"""

from __future__ import annotations

import ast
import contextlib  # noqa: F401  (retained import idiom; harmless)
import importlib
import pkgutil
import re
import sys
from pathlib import Path

import grimp
import pytest

MODULE = "yahir_reusable_bot"
APP = "weatherbot"  # the forbidden-prefix literal — a STRING guard, not an import; the
# ``weatherbot`` package does not exist in this standalone repo (Phase 28 split).

# D-13 locked litmus pattern. Known gap: ``\buv\b`` only matches a STANDALONE ``uv`` — a
# ``uv_index``-style name slips through because ``_`` is a ``\w`` char (no word boundary after
# ``uv``). This is a documented limitation, NOT a bug to fix: the pattern is the roadmap's
# locked literal (D-13).
_LITMUS = re.compile(r"weather|forecast|location|openweather|\buv\b|briefing", re.IGNORECASE)

_MODULE_ROOT = Path(__file__).resolve().parent.parent / MODULE


# ---------------------------------------------------------------------------
# Shared gate logic — the SAME helpers the gates AND their self-proofs call.
# ---------------------------------------------------------------------------


def _scan_app_leaks(
    importers_to_targets: dict[str, set[str]],
) -> list[tuple[str, str]]:
    """Flag every (importer, imported) edge that points at the app package.

    The prefix check (``== APP`` or ``startswith(APP + ".")``) is a STRING guard: it catches
    any ``weatherbot.*`` edge a module declares even though the ``weatherbot`` package is not
    installed in this standalone repo. Takes a plain edge mapping so the self-proof can drive
    it with a SYNTHETIC leak set (proving the scan logic, not a copy).
    """
    leaks: list[tuple[str, str]] = []
    for importer, targets in importers_to_targets.items():
        for target in targets:
            if target == APP or target.startswith(APP + "."):
                leaks.append((importer, target))
    return leaks


def _public_names(source: str) -> list[str]:
    """Extract public SIGNATURE-surface names from Python source (NOT prose).

    Collects ``def``/``async def``/``class`` names, ``arg`` names + their unparsed
    annotations, and function return annotations. Docstrings and comments are never
    visited, so prose mentions of a weather noun are ignored by construction (D-11).
    """
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        if isinstance(node, ast.arg):
            names.append(node.arg)
            if node.annotation is not None:
                names.append(ast.unparse(node.annotation))
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.returns is not None
        ):
            names.append(ast.unparse(node.returns))
    return names


class _AppBlocker:
    """A ``sys.meta_path`` finder that raises ``ImportError`` for any app import.

    It checks the NAME STRING and raises before resolution, so it bites for any
    ``weatherbot``/``weatherbot.*`` name whether or not such a package is installed — which is
    why the isolated-import self-proof can drive it with a synthetic blocked name.
    """

    def find_spec(self, name, path=None, target=None):  # noqa: ANN001
        if name == APP or name.startswith(APP + "."):
            raise ImportError(f"BLOCKED app import inside the reusable module: {name}")
        return None  # defer to the normal finders for everything else


# ---------------------------------------------------------------------------
# Gate 1: grimp import-graph — no module → app edge (TYPE_CHECKING incl. by default).
# ---------------------------------------------------------------------------


def test_module_imports_zero_app_code():
    """No ``yahir_reusable_bot.*`` module may declare a ``weatherbot.*`` import edge (D-09).

    Builds the grimp import graph over the MODULE package alone (single-package build —
    ``weatherbot`` does not exist in this standalone repo, so a two-package build would raise).
    TYPE_CHECKING edges are graphed (default ``exclude_type_checking_imports=False``) so a
    type-only app import would still appear. The ``_scan_app_leaks`` prefix scan flags any
    ``weatherbot.*`` *string* edge. ``cache_dir=None`` reads source FRESH each run (no stale
    cache false-pass/fail). On the clean module there are zero leaks.
    """
    graph = grimp.build_graph(MODULE, cache_dir=None)  # TYPE_CHECKING edges incl. (default)
    edges = {
        module: graph.find_modules_directly_imported_by(module)
        for module in graph.modules
        if module == MODULE or module.startswith(MODULE + ".")
    }
    leaks = _scan_app_leaks(edges)
    detail = {
        (imp, tgt): [
            (d["line_number"], d["line_contents"])
            for d in graph.get_import_details(importer=imp, imported=tgt)
        ]
        for imp, tgt in leaks
    }
    assert leaks == [], f"reusable module imports app code: {detail}"


def test_config_module_never_imports_pydantic():
    """No ``yahir_reusable_bot.config.*`` module may import ``pydantic`` (D-03 / Pitfall 1).

    The grimp leak-scan above only guards the module→APP boundary; it does NOT catch a
    THIRD-PARTY ``pydantic`` import. The config hot-reload seam must route ALL validation
    through the host's injected concrete validator — the module never parses/validates the
    config itself. So an explicit gate clones the same grimp-graph idiom and asserts no
    ``config``-subpackage module directly imports ``pydantic`` (or any ``pydantic.*``).
    ``cache_dir=None`` reads source FRESH every run (no stale-cache false-pass/fail).
    """
    graph = grimp.build_graph(MODULE, cache_dir=None)
    offenders: list[tuple[str, str]] = []
    for module in graph.modules:
        if not module.startswith(MODULE + ".config"):
            continue
        for imported in graph.find_modules_directly_imported_by(module):
            if imported == "pydantic" or imported.startswith("pydantic."):
                offenders.append((module, imported))
    assert offenders == [], (
        f"config module imports pydantic — validation must be injected (D-03): {offenders}"
    )


def test_selfproof_import_gate_catches_injected_app_edge():
    """Prove the grimp leak-scan is not a no-op: a synthetic app edge MUST be flagged.

    Drives the SAME ``_scan_app_leaks`` helper the real gate uses against a synthetic edge
    set carrying a ``(importer, "weatherbot.weather.models")`` pair (plus a benign
    third-party edge that must NOT be flagged). If the scan were ever loosened to a no-op,
    this self-proof goes RED. (Synthetic strings only — no real ``weatherbot`` import, so it
    survives the standalone-repo split unchanged.)
    """
    synthetic = {
        "yahir_reusable_bot.channels.base": {
            "weatherbot.weather.models",  # the injected leak — must be flagged
            "httpx",  # a legitimate third-party edge — must NOT be flagged
        }
    }
    leaks = _scan_app_leaks(synthetic)
    assert leaks == [("yahir_reusable_bot.channels.base", "weatherbot.weather.models")]


# ---------------------------------------------------------------------------
# Gate 2: isolated-import smoke — import every module with `weatherbot` blocked.
# ---------------------------------------------------------------------------


def test_module_imports_with_app_blocked():
    """Every ``yahir_reusable_bot.*`` module imports cleanly with the app namespace blocked.

    Installs an ``_AppBlocker`` ``sys.meta_path`` finder that raises ``ImportError`` for any
    ``weatherbot``/``weatherbot.*`` name, then imports every module under the package via
    ``pkgutil.walk_packages``. A module-import-time OR TYPE_CHECKING-realized app import would
    raise loudly here. The ``finally:`` purges ``sys.modules`` keys starting with
    ``yahir_reusable_bot`` so other tests re-import cleanly.
    """
    blocker = _AppBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        pkg = importlib.import_module(MODULE)
        for info in pkgutil.walk_packages(pkg.__path__, prefix=MODULE + "."):
            importlib.import_module(info.name)  # raises if the module reaches app code
    finally:
        sys.meta_path.remove(blocker)
        for key in [k for k in sys.modules if k.startswith(MODULE)]:
            del sys.modules[key]


def test_selfproof_isolated_import_catches_app_import():
    """Prove the blocker actually blocks: importing an app-prefixed name MUST raise ImportError.

    With the SAME ``_AppBlocker`` installed, resolving a ``weatherbot.*`` name must raise
    ``ImportError``. The blocker checks the NAME STRING and raises before resolution, so this
    self-proof needs NO real ``weatherbot`` package (it was retargeted to a synthetic blocked
    name for the standalone-repo split — Open Question 2). If the blocker were ever a no-op,
    the import would fall through to the normal finders, raise ``ModuleNotFoundError`` instead
    of the blocker's ``ImportError`` message, and this assertion's message check would catch
    the regression.
    """
    target = "weatherbot.synthetic_selfproof_target"  # never a real package — string-blocked
    blocker = _AppBlocker()
    sys.meta_path.insert(0, blocker)
    try:
        with pytest.raises(ImportError) as exc_info:
            importlib.import_module(target)
        assert "BLOCKED app import" in str(exc_info.value), (
            "the ImportError must come from the _AppBlocker (proving it bit), not from a "
            f"normal-finder ModuleNotFoundError: {exc_info.value}"
        )
    finally:
        sys.meta_path.remove(blocker)
        for key in [k for k in sys.modules if k == target]:
            del sys.modules[key]


# ---------------------------------------------------------------------------
# Gate 3: AST signature-only litmus — no weather noun in the public name surface.
# ---------------------------------------------------------------------------


def test_litmus_clean():
    """No ``def``/``class``/param/annotation NAME under the module matches a weather noun.

    Walks every ``.py`` under ``yahir_reusable_bot/``, AST-extracts the public signature
    surface via ``_public_names`` (NOT docstrings/comments), and asserts none matches the
    D-13 litmus pattern. Prose is ignored by construction. On the clean module → zero hits.
    """
    # Assert the lifecycle package is genuinely in the scanned tree (so a future refactor
    # that relocates it cannot silently drop it from litmus coverage).
    scanned = {path.name for path in _MODULE_ROOT.rglob("*.py")}
    assert {"ready_gate.py", "sdnotify.py", "health.py", "identity.py"} <= scanned, (
        f"lifecycle package not in the litmus scan tree (coverage gap): {sorted(scanned)}"
    )
    registry_scanned = {
        path.name for path in (_MODULE_ROOT / "registry").rglob("*.py")
    }
    assert {"spec.py", "registry.py", "match.py", "dispatch.py"} <= registry_scanned, (
        "registry/dispatcher package not in the litmus scan tree (coverage gap): "
        f"{sorted(registry_scanned)}"
    )
    discord_scanned = {
        path.name for path in (_MODULE_ROOT / "discord").rglob("*.py")
    }
    assert {"panelkit.py", "gateway.py", "selection.py"} <= discord_scanned, (
        "discord adapter package not in the litmus scan tree (coverage gap): "
        f"{sorted(discord_scanned)}"
    )
    hits = {
        (path.name, name)
        for path in _MODULE_ROOT.rglob("*.py")
        for name in _public_names(path.read_text(encoding="utf-8"))
        if _LITMUS.search(name)
    }
    assert hits == set(), f"weather noun in module public surface: {sorted(hits)}"


def test_selfproof_litmus_catches_weather_noun():
    """Prove the litmus catches a NAME and ignores PROSE — through the SAME extractor.

    Half 1: a synthetic ``def send_briefing(forecast): ...`` source fed through
    ``_public_names`` must surface names the litmus matches (the ``send_briefing`` def name and
    the ``forecast`` param). Half 2: a source whose ONLY weather noun lives in a docstring must
    yield zero litmus hits — proving prose is ignored (D-11). If the extractor ever started
    surfacing prose, or stopped surfacing signature names, this self-proof goes RED.
    """
    leaky = "def send_briefing(forecast):\n    return forecast\n"
    leaky_hits = [n for n in _public_names(leaky) if _LITMUS.search(n)]
    assert leaky_hits, "litmus extractor failed to surface a weather noun in a signature"

    prose_only = (
        "def send(text):\n"
        '    """Deliver the weather briefing for the configured location."""\n'
        "    return text\n"
    )
    prose_hits = [n for n in _public_names(prose_only) if _LITMUS.search(n)]
    assert prose_hits == [], f"litmus must ignore prose, but flagged: {prose_hits}"


# ---------------------------------------------------------------------------
# Phase-27 (PKG-01 / SC#2): the Discord adapter must not reach back into the app.
# ---------------------------------------------------------------------------


def test_discord_adapter_imports_zero_app_code():
    """No ``yahir_reusable_bot.discord.*`` module declares a ``weatherbot.*`` edge (SEAM-07).

    The general ``test_module_imports_zero_app_code`` gate already covers every module via the
    ``startswith(MODULE)`` scan; this is the EXPLICIT, intent-pinned assertion naming the
    ``discord`` adapter package (the layer most at risk of reaching back for ``render_embed`` /
    a host panel). Single-package build (``weatherbot`` does not exist here); the
    ``_scan_app_leaks`` prefix scan flags any ``weatherbot.*`` string edge. ``cache_dir=None``
    reads source FRESH (no stale false-pass/fail).
    """
    discord_pkg = MODULE + ".discord"
    graph = grimp.build_graph(MODULE, cache_dir=None)  # TYPE_CHECKING edges incl. (default)
    edges = {
        module: graph.find_modules_directly_imported_by(module)
        for module in graph.modules
        if module == discord_pkg or module.startswith(discord_pkg + ".")
    }
    # Self-proof the scope actually selected the adapter modules (a typo'd prefix that matched
    # nothing would make this gate a silent no-op).
    assert edges, (
        "no yahir_reusable_bot.discord.* modules were graphed — the adapter package is "
        "missing or the scope prefix is wrong (the isolation gate would be a no-op)"
    )
    leaks = _scan_app_leaks(edges)
    detail = {
        (imp, tgt): [
            (d["line_number"], d["line_contents"])
            for d in graph.get_import_details(importer=imp, imported=tgt)
        ]
        for imp, tgt in leaks
    }
    assert leaks == [], f"discord adapter imports app code (cycle re-introduced?): {detail}"
