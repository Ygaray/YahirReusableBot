"""The generic ``CommandRegistry`` mechanism + ``build_registry`` constructor entry.

This is the relocated registry assembly (SEAM-06, D-02): given an app-supplied tuple
of :class:`~yahir_reusable_bot.registry.spec.CommandSpec`, it computes — ONCE, frozen,
at construction — the three immutable views every surface reads:

- ``commands`` — the spec tuple as registered.
- ``by_name`` — ``{spec.name: spec}`` (one entry per spec; names are unique).
- ``by_keyword_len_desc`` — the specs sorted longest-name-first so the matcher tries
  a longer command before any shorter command that prefixes it.

plus a ``render_help`` that emits surface-agnostic, group-headered help text.

The class mirrors the module's established constructor-injection idiom
(``SchedulerEngine(scheduler)`` / ``ConfigHolder(config)`` / ``ReloadEngine(holder, …)``):
the app passes its specs in; the registry stores + derives, never bakes a default
command set of its own. A reminder bot supplies its OWN specs — ``specs`` is a
required param. The registry reads ONLY ``spec.name`` / ``spec.group`` / ``spec.summary``
structurally, so an app's richer spec satisfies it by construction.
"""

from __future__ import annotations

from typing import Iterable

from yahir_reusable_bot.registry.spec import CommandSpec


class CommandRegistry:
    """Immutable registry computed once from app-supplied specs (D-02).

    Construct with the app's spec tuple (a required arg — the module holds no
    baked-in default command set). The three frozen views (``commands`` /
    ``by_name`` / ``by_keyword_len_desc``) are computed in ``__init__`` and never
    recomputed. ``render_help`` renders the registry's own specs by default, or an
    explicitly-passed spec list (the per-call override the app's re-export needs).
    """

    def __init__(self, specs: Iterable[CommandSpec]) -> None:
        # Freeze the registered specs into a tuple, then derive the read views once.
        self.commands: tuple[CommandSpec, ...] = tuple(specs)
        # D-34 (MATCH-02): validate every spec.name INSIDE this same pass, before any
        # view is derived from it — non-empty AND already-casefolded. Deny-by-default,
        # matching is_transient's posture (retry.py:88-92): match_command casefolds the
        # INPUT text and tests it against spec.name verbatim, so an uppercase name would
        # never match anything, forever, with no signal at build time; an empty name
        # would silently claim blank input. Rejected alternative: casefold spec.name at
        # match time as a tolerant fallback — that silently hides a consumer wiring bug
        # and pays a per-match cost on the hot path. Reject loudly here instead, once,
        # at construction — raise (not assert), since this is genuine untrusted-input
        # validation that must survive `-O`.
        # MATCH-03 (v0.1.2 WR-02): the D-34 loop above validates each spec.name in
        # isolation but never checks for a duplicate across specs — a duplicate silently
        # overwrites in by_name below while by_keyword_len_desc and render_help still
        # carry both entries, so match_command can resolve a different CommandSpec than
        # by_name holds. Same posture as D-34's rejected tolerant-fallback: the check
        # lands here, in the construction loop, rather than at match time, and runs
        # before any derived view is computed. raise (not assert) — this is genuine
        # consumer-input validation that must survive `-O`.
        seen: set[str] = set()
        for spec in self.commands:
            if not spec.name or spec.name != spec.name.casefold():
                raise ValueError(
                    f"CommandSpec.name must be non-empty and already casefolded "
                    f"(match_command folds input, never spec.name); got {spec.name!r}"
                )
            if spec.name in seen:
                raise ValueError(
                    f"CommandSpec.name must be unique per registry (a duplicate "
                    f"silently overwrites in by_name while by_keyword_len_desc and "
                    f"render_help still carry both entries); got duplicate {spec.name!r}"
                )
            seen.add(spec.name)
        # name -> spec (every name is unique; one entry per spec).
        self.by_name: dict[str, CommandSpec] = {c.name: c for c in self.commands}
        # Longest-keyword-first ordering so a longer command (e.g. "next-cloudy") is
        # matched before any shorter command that prefixes it. Stable sort.
        self.by_keyword_len_desc: tuple[CommandSpec, ...] = tuple(
            sorted(self.commands, key=lambda c: len(c.name), reverse=True)
        )

    def render_help(
        self, commands: Iterable[CommandSpec] | None = None
    ) -> str:
        """Render surface-agnostic plain-text help, grouped by ``.group``.

        Groups appear in order of first appearance; each command emits a
        ``  {name} — {summary}`` line under its group header. With no argument the
        registry renders its OWN frozen specs; pass an explicit spec list to render
        that list instead (a per-call override — NOT a baked-in default command set).
        This dual signature is load-bearing: the app re-exports this method so BOTH
        ``render_help()`` and ``render_help(COMMANDS + (extra,))`` work byte-identically
        — the parameterized form must not raise ``TypeError``.

        The EM DASH and the two leading spaces are golden-sensitive — do not alter.
        """
        specs = self.commands if commands is None else tuple(commands)

        groups: list[str] = []
        by_group: dict[str, list[CommandSpec]] = {}
        for spec in specs:
            if spec.group not in by_group:
                by_group[spec.group] = []
                groups.append(spec.group)
            by_group[spec.group].append(spec)

        lines: list[str] = []
        for group in groups:
            lines.append(group)
            for spec in by_group[group]:
                lines.append(f"  {spec.name} \N{EM DASH} {spec.summary}")
        return "\n".join(lines)


def build_registry(specs: Iterable[CommandSpec]) -> CommandRegistry:
    """Build a :class:`CommandRegistry` from app-supplied ``specs`` (the app entry).

    ``specs`` is required — the module never holds a default command set; a reminder
    bot calls ``build_registry(its_own_specs)`` with its own handler closures.
    """
    return CommandRegistry(specs)
