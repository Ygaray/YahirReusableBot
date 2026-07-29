---
status: confirmed
platform: python-library
---

# UAT driver playbook — `yahir_reusable_bot` (pure Python library, no runnable app)

This hub ships **no console script and no server/UI surface** — it is imported and wired by a
consumer's composition root (`CLAUDE.md`: "never run on its own"). The Gate-1 self-UAT spine's
`<driver_playbook_contract>` still applies; the roles below map the generic D1–D8 mechanics onto a
library target instead of a device/browser.

## D1 — Target + preflight
"The running app" = a REAL Python process running the **built and installed** package (a wheel
installed into a scratch venv), driven from a working directory that is NOT the repo root — the
same vantage point a real consumer has. Preflight: confirm `uv` is on `PATH` and the repo tree
builds (`uv build`). A build failure is `INFRA`, not a behavior FAIL.

## D2 — Build / install / launch
```bash
uv build --out-dir <scratch>/dist                      # build the CURRENT tree
uv venv <scratch>/venv --python 3.12                    # scratch venv, NEVER the project .venv
uv pip install --python <scratch>/venv/bin/python <scratch>/dist/*.whl
```
Record build identity: `git rev-parse --short HEAD` (sha) + `md5sum <scratch>/dist/*.whl` (artifact
hash). Sanity: `unzip -l <scratch>/dist/*.whl | grep <new-subpackage>` — confirms hatchling actually
shipped the new code, not just the source tree having it (`[tool.hatch.build.targets.wheel]
packages = ["yahir_reusable_bot"]` in `pyproject.toml` is the one line that governs this).

## D3 — Act
"Driving the UI" = calling the public API directly from a Python script/`-c` one-liner, executed by
the scratch venv's interpreter, from a `cwd` outside the repo (e.g. `<scratch>/consumer_cwd`) so the
repo root is never on `sys.path` and the import genuinely resolves through `site-packages`.

## D4 — Observe
- (a) return values / raised exceptions — the primary observation layer for a library.
- (c) nothing else runs here (no logs/DB/UI) — a pure function's output IS the observation.
- Visual capture (rung 5) never applies to this project.

## D5 — Fixture/seed integrity + programmatic seeding
No persistent fixture. "Seeding" = constructing the Python objects (patterns, sample text, sample
consumer objects) a criterion needs, in-script, before calling the SUT function — always
programmatic, never blocked.

## D6 — Ladder commands (library mapping)
| Rung | Command |
|------|---------|
| 0 | `uv build` (also exercises hatchling packaging) |
| 1 | `uv run pytest -q` (source-tree suite — necessary, NOT sufficient: `pythonpath=["."]` bypasses packaging) |
| 2 | `gsd-validate-phase` |
| 3 | **The consumer-facing check**: scratch-venv install + `python -c "..."` probes against the installed wheel, run from a non-repo cwd. This is the ceiling rung for a library — there is no rung 4/5 target. |

## D7 — Gotchas
- `uv run pytest` imports from the working directory (`pythonpath = ["."]`) — it CANNOT catch a
  packaging omission (a subpackage present in source but missing from
  `[tool.hatch.build.targets.wheel] packages`). Only an installed-wheel probe catches that class of
  defect.
- Never install into or mutate the project's own `.venv` / `uv.lock` during Gate-1 — always a
  disposable scratch venv under the session scratchpad.
- Any ReDoS/timing-budget probe MUST be run under a hard `timeout` wrapper — stdlib `re.search` is
  uninterruptible; a regression here can hang the tester itself, not just the SUT.

## D8 — Target arbitration
Not applicable — no shared/physical target; a scratch venv is disposable and can be created fresh
per run with no contention.
