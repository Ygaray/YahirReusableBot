---
phase: 03-public-surface-footguns
source_review: 03-REVIEW.md
applied: 2026-07-27
findings_total: 3
findings_fixed: 1
findings_deferred: 2
gate_after: "71 passed; import-hygiene 8 passed"
---

# Phase 03 — Code Review Fix Report

Disposition of the 3 findings in `03-REVIEW.md` (0 Critical / 2 Warning / 1 Info). The reviewer
confirmed all nine core footgun fixes are correct (it hand-traced `_keyword_boundary` against
multiple casefold-expansion cases — no off-by-one — and verified every RED-pre-fix claim is genuine).

## Fixed

- **WR-01 (Warning) — `write_pid_atomic` except-path close no longer exception-safe.**
  IN SCOPE: a regression introduced by this phase's own LIFE-02 fix (`0c14258`), which replaced
  `try: os.close(fd) except OSError: pass` with a bare `if fd != -1: os.close(fd)`. That closed the
  double-close hole but left the *first*-close scenario (os.write fails, fd still open) unguarded —
  a close that itself raises (ENOSPC/EIO on the same disk-full condition) would mask the original
  error and skip the temp-file unlink, violating the function's documented contract and D-42's
  "temp-file unlink otherwise byte-identical." Fix keeps the `fd != -1` double-close guard AND
  re-wraps the close in `try/except OSError`. RED-first: test `55ccfdd` → fix `74cd090`.
  New regression test: `test_life_02_except_path_close_failure_does_not_mask_original_error`.

## Deferred (out of locked scope — user's scope decision; see `deferred-items.md`)

- **WR-02 (Warning) — duplicate `spec.name` not rejected** (`registry.py`). A genuine footgun that
  fits the "public-surface footguns" theme, but NOT one of the 9 audited findings (no H-number) and
  NOT in the locked D-34 decision (casefold symmetry, not uniqueness). Pre-existing (`by_name` dict
  overwrite predates this phase). Recommended fast-follow: a `seen` uniqueness check in the same loop.
- **IN-01 (Info) — duplicate log message** in `panelkit.py` `_safe_error_edit` — pre-existing code
  this phase did not touch. Diagnosability nit.

## Gate after fixes

`uv run pytest -q` → **71 passed**, 0 failed. `uv run pytest tests/test_import_hygiene.py -q` → 8 passed.
