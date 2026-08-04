# YahirReusableBot — Adopt a static type checker (deferred from Phase 7 / SURF-02)

> Deferred candidate — **NOT adopted.** No type checker is added to `[dependency-groups].dev`
> (still `pytest`, `ruff`, `syrupy`, `time-machine`, `grimp` only), and none was added by this
> entry's filing. Filed so the idea is pickup-ready rather than buried in a phase artifact, per
> the user's explicit request when it was deferred.
>
> **Source:** `.planning/phases/07-v0-1-2-debt-paydown/07-CONTEXT.md` § Deferred Ideas and § D-63
> (SURF-02). Raised unprompted by the user during the SURF-02 discussion.

---

## What was raised

While deciding SURF-02 (narrowing three loose `Callable[...]` annotations across
`ready_gate.py`, `panelkit.py`, `scheduler/engine.py`), the user observed that **an annotation
nothing checks is a comment with extra syntax.** This hub runs no static type checker today —
`typing.get_type_hints` signature-assertion tests (D-63) are the enforcement mechanism SURF-02
shipped instead, and they guard *these three signatures specifically*, not the codebase's whole
annotation surface. The user's instinct — that this narrower net leaves systemic drift
unguarded — is correct and is exactly why this entry exists.

## Why it was deferred out of Phase 7 rather than rejected

- **It is a toolchain change every future phase then pays**, not a one-off fix. Once a type
  checker is a standing gate, every subsequent plan's diff must stay clean under it.
- **The first run over this codebase will surface its own backlog.** The injection architecture
  is *deliberately* `Any`-heavy at every seam: `scheduler: Any`, `trigger: Any`, `render_arg: Any`,
  the opaque `dispatch`/`render` closures (`SchedulerEngine.register`'s `callback`, `panelkit`'s
  `render`, `DispatchOutcome.render_arg`). A first-run type-check pass over this surface will
  either flag every one of those seams (in `strict` mode, a flood) or pass near-clean (in `basic`
  mode) — either way, triaging that first-run output is its own scoped piece of work, separate
  from "close 9 audit items."
- Phase 7 was sequenced last specifically to **absorb slip** from Phases 5–6 (the PC-01 redaction
  promotion). Folding "adopt static typing" into it would have turned a bounded debt-paydown phase
  into an open-ended toolchain migration, defeating that sequencing choice.

## Head start already shipped

Phase 7's SURF-02 plan (07-04) already narrowed and pinned three signatures with
`typing.get_type_hints` assertions: `ready_gate.py`'s `on_online`, `panelkit.py`'s `render`
(arity-narrowed), and the deliberate leave-variadic verdict on `scheduler/engine.py`'s
`register.callback` (recorded in its docstring, not narrowed). Whoever picks up this entry
inherits **three known-good, already-decided signatures** — not a blank slate — plus the D-62
"reviewed and left `Any`" rationale already in the `register` docstring as a precedent for how to
annotate an intentional seam so a type checker doesn't flag it as unexamined.

## Sizing decisions for whoever picks this up

Four decisions the adopter must make before wiring the gate — none of them defaulted here:

1. **`basic` vs `strict` mode.** `basic` is likely near-clean given the codebase's existing
   annotation discipline; `strict` will flag the deliberate `Any`-at-seams architecture broadly.
   Recommendation to weigh: start `basic`, revisit `strict` once the seams are annotated as
   intentional (see decision 4).
2. **Baseline-and-burn-down vs fix-all-before-green.** A first-run baseline file (pyright's
   `# pyright: baseline` mechanism, or an equivalent) lets the gate land now with existing findings
   grandfathered, vs. blocking the gate's introduction on fixing every flagged site up front.
3. **`discord.py==2.7.1`'s stub quality.** The pin is exact (the persistent-view `custom_id` wire
   contract requires it — see `CLAUDE.md`), so its type stubs are fixed at that version. Check
   `discord.py`'s bundled stubs (or the `discord-stubs` / `discord.py-stubs` package landscape, if
   any) resolve cleanly before committing to a mode.
4. **Confirm the `Any`-at-seams sites are annotated as INTENTIONAL, not flagged.** Every
   deliberately-`Any` injection point (`scheduler/engine.py:register`'s `callback`, `panelkit.py`'s
   `render` closure body, `DispatchOutcome.render_arg`) needs either a type-checker suppression
   comment with a reason, or confirmation the tool has a "trust this annotation" mode — so the gate
   doesn't spend its first year red on architecture that is correct by design (per the D-62
   rationale already on record).

## When actioned

1. Decide the four sizing items above.
2. Add the chosen checker to `[dependency-groups].dev` in `pyproject.toml`.
3. Run it over the codebase; triage the first-run output per the baseline decision.
4. Wire it as a standing CI/local gate alongside `uv run ruff check` and the import-hygiene suite.
5. Target: a future milestone — not v0.2.0 (Phase 7 closes without it, by design).

---

*Filed: Phase 7 (v0.1.2 debt paydown), plan 07-07 — GATE-02 close-out.*
