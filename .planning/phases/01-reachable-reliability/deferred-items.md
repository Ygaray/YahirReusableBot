# Deferred Items — Phase 01 (reachable-reliability)

Out-of-scope discoveries logged per the executor's scope-boundary rule (fix only what the
current task's changes directly caused; log everything else here, do not fix).

## Pre-existing repo-wide `uv run ruff check` failures (found during Plan 02, Task 2)

`uv run ruff check` (whole repo) reports 4 pre-existing errors, none in files touched by
Plan 02 (`tests/test_retry.py`, `yahir_reusable_bot/reliability/retry.py`). Confirmed
pre-existing by running `uv run ruff check` against the stashed pre-fix tree (identical
4 errors before and after this plan's changes):

- `scripts/new_consumer.py:197` — E741 ambiguous variable name `l`
- `yahir_reusable_bot/config/reload.py:46` — F401 unused import `pathlib.Path`
- `yahir_reusable_bot/discord/selection.py:30` — E741 ambiguous variable name `I`
  (this one is a deliberate unbound TypeVar per an inline D-02 comment — likely a
  ruff-config/noqa gap rather than a real naming problem)
- `yahir_reusable_bot/lifecycle/identity.py:121` — E731 lambda assignment

None of these files are in Plan 02's `files_modified`. `uv run ruff check` scoped to the
two files this plan touches (`tests/test_retry.py`,
`yahir_reusable_bot/reliability/retry.py`) passes clean. Not fixed here — out of scope.
Candidate for a future housekeeping pass or Phase 3/4 if any of these land in a plan's
`files_modified`.
