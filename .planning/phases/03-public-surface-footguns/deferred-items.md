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
</content>
