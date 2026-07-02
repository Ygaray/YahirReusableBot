#!/usr/bin/env python3
"""Scaffold a new consumer bot on the yahir_reusable_bot infrastructure.

This is the CANONICAL way to start a consumer — do not hand-wire the pin,
the CLAUDE.md pointer, and the consumers-table row separately. This script
does all of it deterministically (ECOSYSTEM.md §8, steps 1 + 2), reading the
hub's live state (latest tag, remote URL) so a new consumer is born already
wired into the ecosystem.

Usage (run from anywhere; the script locates the hub via its own path):

    python3 scripts/new_consumer.py <BotName> [--dir PATH] [--pin TAG]
                                    [--create-remote {public,private}]

Examples:
    python3 scripts/new_consumer.py ReminderBot
    python3 scripts/new_consumer.py ReminderBot --create-remote private

Stdlib only — no uv env needed. Idempotent-ish: refuses to overwrite an
existing non-empty target dir; updates (not duplicates) the consumers-table row.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent


def sh(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def hub_remote_url() -> str:
    url = sh("git", "-C", str(HUB_ROOT), "remote", "get-url", "origin")
    return re.sub(r"\.git$", "", url)


def hub_latest_tag() -> str:
    tags = sh("git", "-C", str(HUB_ROOT), "tag", "--sort=-v:refname")
    first = tags.splitlines()[0] if tags else ""
    if not first:
        sys.exit("FATAL: hub has no tags — cut a release tag before scaffolding a consumer.")
    return first


def import_root(bot_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", bot_name.lower())


# ---------------------------------------------------------------- templates

def pyproject(name_pkg: str, imp: str, bot: str, hub_url: str, pin: str, hub_dir: str) -> str:
    return f"""\
[project]
name = "{name_pkg}"
version = "0.1.0"
description = "{bot} — a bot built on the yahir_reusable_bot infrastructure."
requires-python = ">=3.12"
dependencies = [
    # The shared bot infrastructure (the hub). Transitively pins discord.py etc.
    "yahir-reusable-bot",
    # add this bot's own deps below
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
{imp} = "{imp}.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["{imp}"]

[tool.uv.sources]
# Hub pinned to a tag; uv.lock freezes the resolved sha (deploy-reproducible).
# For live cross-repo dev, overlay an EDITABLE install (uncommitted — never a
# committed path source):   uv pip install -e {hub_dir}
# revert with:              uv sync --frozen
yahir-reusable-bot = {{ git = "{hub_url}", tag = "{pin}" }}

[dependency-groups]
dev = [
    "pytest>=9",
    "ruff>=0.15",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
"""


def claude_md(bot: str, imp: str, hub_url: str, pin: str) -> str:
    return f"""\
# CLAUDE.md — {bot}

**{bot}** is a bot built on the shared `yahir_reusable_bot` infrastructure. Its own domain
code lives in `{imp}/`; all reusable mechanism comes from the hub.

## Ecosystem — consumer of `yahir_reusable_bot`

This repo is a **consumer** in a multi-repo bot ecosystem. It depends on the shared hub
`yahir_reusable_bot` (repo `{hub_url}`, dev checkout `../YahirReusableBot`), pinned via
`[tool.uv.sources]` at tag **`{pin}`**.

**Before working across repos, read `../YahirReusableBot/ECOSYSTEM.md`.** Key rules:
- **Cross-repo jurisdiction:** if a bug is actually in the hub, fix it upstream in the hub — but
  cutting a hub tag + repinning + deploying is a **human-gated** step (surface it, don't ship it
  autonomously).
- **This app runs the *pinned* hub, not its source.** For live cross-repo dev use the editable
  overlay: `uv pip install -e ../YahirReusableBot` (uncommitted; revert with `uv sync --frozen`).
- **Placement:** reusable mechanism → hub; build new reusable impls in this repo's `{imp}/_promotable/`
  quarantine (hub-clean), promote via `git mv`; app-specific wiring/config/domain → stays here.
  Litmus: "could a different bot reuse this with zero domain assumptions?"
"""


PROMOTABLE_README = """\
# `_promotable/` — hub-candidate quarantine

Code here is slated to be **promoted to the hub** (`yahir_reusable_bot`) via a `git mv`. It obeys
the hub contract so promotion is a *move, not a rewrite*. See `../../ECOSYSTEM.md` §6 (in the hub).

**Every file in here MUST:**
1. Import only the hub's public ports + stdlib/third-party. **No imports from this app's own code.**
2. Name no domain noun — it passes the litmus in place ("could a different bot reuse this with
   zero domain assumptions?").
3. Have its own self-contained tests.
4. Be wired at the app's composition root by injection — the app *uses* it; nothing here reaches
   back into the app.

**Promote when** it's proven in production here **or** a second consumer wants it (rule of three):
`git mv` the file into the hub, export it, add it to the hub `EXTENSION-GUIDE.md`, run the hub's
litmus gate, cut a hub tag, then (human-gated) repin this consumer and swap the import.
"""


def wiring_stub(imp: str) -> str:
    return f'''\
"""Composition root for {imp}.

This is the ONE place app-specific values are injected into the hub's generic
mechanisms — the hub assembles nothing of its own (one-way dependency). Mirror
WeatherBot's `weatherbot/scheduler/wiring.py build_runtime(...)`: construct the
hub engines/adapters here, injecting this app's config, callbacks, channels,
command specs, render, marker, etc.

Anything reusable you build lives in `{imp}/_promotable/` (hub-clean) until promoted.
"""


def build_runtime():  # noqa: D401 - stub
    raise NotImplementedError("wire the hub mechanisms here — see the hub's EXTENSION-GUIDE.md")
'''


CLI_STUB = '''\
"""Console entry point."""


def main() -> None:
    print("hello from the bot — wire me up (see CLAUDE.md + the hub ECOSYSTEM.md)")
'''

GITIGNORE = """\
.venv/
__pycache__/
*.egg-info/
dist/
*.pyc
.pytest_cache/

# Secrets — never commit
.env
.env.*
!.env.example
*.pem
*.key
"""


# ---------------------------------------------------------------- table edit

def register_in_ecosystem(bot: str, repo_disp: str, dev_path: str, pin: str) -> None:
    """Insert-or-update the consumers-table row in the hub's ECOSYSTEM.md (§1)."""
    eco = HUB_ROOT / "ECOSYSTEM.md"
    lines = eco.read_text().splitlines()
    # locate the consumers table header (it is indented under a bullet — match after lstrip)
    hdr = next((i for i, l in enumerate(lines) if l.lstrip().startswith("| Consumer |")), None)
    if hdr is None:
        print("  ! could not find consumers table in ECOSYSTEM.md — add the row by hand")
        return
    indent = lines[hdr][: len(lines[hdr]) - len(lines[hdr].lstrip())]
    row = f"{indent}| {bot} | {repo_disp} | `{dev_path}` | `{pin}` | — |"
    # find the span of table rows (header, separator, then data rows)
    end = hdr + 2
    replaced = False
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        if re.search(rf"\|\s*{re.escape(bot)}\s*\|", lines[end]):
            lines[end] = row  # update existing (e.g. a "_(planned)_" placeholder)
            replaced = True
        end += 1
    if not replaced:
        lines.insert(end, row)
    eco.write_text("\n".join(lines) + "\n")
    print(f"  ✓ {'updated' if replaced else 'added'} consumers-table row in ECOSYSTEM.md "
          f"(commit the hub to publish it)")


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Scaffold a consumer bot on yahir_reusable_bot.")
    ap.add_argument("bot_name", help="e.g. ReminderBot")
    ap.add_argument("--dir", help="target dir (default: sibling of the hub)")
    ap.add_argument("--pin", help="hub tag to pin (default: latest hub tag)")
    ap.add_argument("--create-remote", choices=["public", "private"],
                    help="also create the GitHub repo via gh and push")
    args = ap.parse_args()

    bot = args.bot_name
    imp = import_root(bot)
    if not imp:
        sys.exit("FATAL: bot name has no alphanumerics.")
    pin = args.pin or hub_latest_tag()
    hub_url = hub_remote_url()
    owner = hub_url.rstrip("/").split("/")[-2]
    target = Path(args.dir).resolve() if args.dir else (HUB_ROOT.parent / bot)

    if target.exists() and any(target.iterdir()):
        sys.exit(f"FATAL: {target} exists and is not empty — refusing to overwrite.")

    print(f"Scaffolding consumer '{bot}'")
    print(f"  dir:  {target}")
    print(f"  pkg:  {imp}/   pin: {pin}   hub: {hub_url}")

    pkg = target / imp
    (pkg / "_promotable").mkdir(parents=True, exist_ok=True)
    (target / "tests").mkdir(exist_ok=True)

    name_pkg = re.sub(r"[^a-z0-9]+", "-", bot.lower()).strip("-")
    (target / "pyproject.toml").write_text(
        pyproject(name_pkg, imp, bot, hub_url, pin, str(HUB_ROOT)))
    (target / "CLAUDE.md").write_text(claude_md(bot, imp, hub_url, pin))
    (target / ".gitignore").write_text(GITIGNORE)
    (target / "README.md").write_text(f"# {bot}\n\nA bot on the yahir_reusable_bot infrastructure. "
                                      f"See CLAUDE.md and ../YahirReusableBot/ECOSYSTEM.md.\n")
    (pkg / "__init__.py").write_text("")
    (pkg / "cli.py").write_text(CLI_STUB)
    (pkg / "wiring.py").write_text(wiring_stub(imp))
    (pkg / "_promotable" / "__init__.py").write_text("")
    (pkg / "_promotable" / "README.md").write_text(PROMOTABLE_README)
    (target / "tests" / "__init__.py").write_text("")
    print("  ✓ wrote pyproject.toml, CLAUDE.md (with ecosystem pointer), "
          f"{imp}/ (+ _promotable/), tests/, .gitignore")

    if not (target / ".git").exists():
        sh("git", "init", "-q", "-b", "main", cwd=target)
        print("  ✓ git init (branch: main)")

    repo_disp = f"`github.com/{owner}/{bot}`"
    register_in_ecosystem(bot, repo_disp, str(target), pin)

    if args.create_remote:
        sh("gh", "repo", "create", f"{owner}/{bot}", f"--{args.create_remote}",
           "--source", str(target), "--remote", "origin", cwd=target)
        print(f"  ✓ created {args.create_remote} GitHub repo {owner}/{bot} (origin set)")

    print(f"""
Done. Next:
  cd {target}
  uv sync                         # resolves the hub from the pin
  # start the GSD project:  /gsd-new-project
  # co-dev on the hub live:  uv pip install -e {HUB_ROOT}   (revert: uv sync --frozen)

Remember to commit + push the hub — {('the ECOSYSTEM.md row was updated')}.
""")


if __name__ == "__main__":
    main()
