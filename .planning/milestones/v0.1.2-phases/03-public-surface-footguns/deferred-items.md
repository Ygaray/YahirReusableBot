# Deferred Items — Phase 03 (public-surface footguns)

Pre-existing issues discovered during execution that are out of scope for the current
task's changes (SCOPE BOUNDARY rule — only auto-fix issues directly caused by the task).

## Plan 03-02 (LIFE-02 / LIFE-03)

- **`ruff` E731** at `yahir_reusable_bot/lifecycle/identity.py:121` (line number pre-Plan-03-02;
  shifts by +3 after the LIFE-02 fix) — `cmdline_reader = lambda p: _read_proc_cmdline(...)`
  assigns a lambda to a name instead of using `def`. Pre-existing before this plan's changes
  (confirmed via `git stash` diff against the LIFE-02/LIFE-03 edits); not touched by either
  fix in this plan. Not part of GATE-01 (pytest full suite + import-hygiene only, no ruff
  gate is wired into this phase's verification). Logged, not fixed.

## Code review (03-REVIEW.md) — findings deferred out of locked scope

The phase code review surfaced three findings. **WR-01 was fixed** (RED-first, commits
`55ccfdd`→`74cd090`) because it was an in-scope regression from this phase's own LIFE-02 change.
The other two are deferred — they are the user's scope call, not this phase's:

- **WR-02 (Warning) — duplicate `spec.name` not rejected** at
  `yahir_reusable_bot/registry/registry.py:52-59`. The D-34 validation loop checks non-empty +
  already-casefolded, but not uniqueness; a duplicate name silently overwrites in `by_name` while
  `by_keyword_len_desc`/`render_help` carry both, so `match_command` can resolve to a different
  `CommandSpec` than `by_name[name]`. **A genuine public-surface footgun that fits the milestone
  theme, but NOT one of the 9 audited findings (no H-number) and NOT in the locked D-34 decision
  (which was specifically casefold symmetry, not uniqueness).** Pre-existing behavior (the `by_name`
  dict overwrite predates this phase). Recommended as a fast-follow: extend the same loop with a
  `seen: set[str]` uniqueness check raising `ValueError` on a duplicate. Deferred for the user's
  scope decision (a D-34 amendment or a Phase 4 item).

- **IN-01 (Info) — identical log message for two branches** at
  `yahir_reusable_bot/discord/panelkit.py:483,485` (`_safe_error_edit`). Pre-existing code NOT
  touched by this phase (DISC-05/06 touched `interaction_check` and `__init__`). A diagnosability
  nit, not a correctness issue. Deferred.
