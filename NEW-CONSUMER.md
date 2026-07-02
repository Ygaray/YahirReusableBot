# NEW-CONSUMER.md — start a new bot on this infrastructure

Operational checklist for spinning up a **consumer** of `yahir_reusable_bot`. The full doctrine
(cross-repo jurisdiction, placement rules, the quarantine model) is in **`ECOSYSTEM.md`** — this
file is just the steps.

**Two separate acts, in this order:**
1. **Scaffold** (steps 1–4) — joins the new repo to the ecosystem: pins the hub, writes the
   `CLAUDE.md` pointer + `_promotable/` quarantine, registers it in the consumers table.
2. **`/gsd-new-project`** (step 5) — plans *what the bot is* (its own GSD project). Deliberately
   kept separate: it's interactive and you drive it.

> **Hub location:** this repo currently lives at `~/Projects/YahirReusableBot`. Commands below use
> `../YahirReusableBot` for a consumer that is a *sibling* directory. If the hub moves, update that
> relative path everywhere (the scaffolder writes it into each new consumer's `CLAUDE.md`).

Example bot name throughout: **ReminderBot**.

---

## 1. Scaffold the consumer (from the hub)

```bash
cd ~/Projects/YahirReusableBot
python3 scripts/new_consumer.py ReminderBot --create-remote private
#   --create-remote {public,private}  also does `gh repo create` + sets origin
#   omit it to scaffold locally only;  --pin vX.Y.Z to pin a specific hub tag (default: latest)
```

This creates `~/Projects/ReminderBot/` **born wired**: the hub git-tag pin in `pyproject.toml`, a
`CLAUDE.md` carrying the ecosystem pointer, the `reminderbot/` package + `reminderbot/_promotable/`
quarantine (with its contract README), a `wiring.py` composition-root stub, `tests/`, a
secrets-guarding `.gitignore`, and `git init -b main`. It also **registers ReminderBot in the
consumers table in `ECOSYSTEM.md` §1**.

## 2. Commit + push the hub

The scaffolder edited `ECOSYSTEM.md` §1 — that change is uncommitted **in the hub**:

```bash
cd ~/Projects/YahirReusableBot
git add ECOSYSTEM.md && git commit -m "docs: register ReminderBot consumer" && git push
```

## 3. Resolve deps in the consumer

```bash
cd ~/Projects/ReminderBot
uv sync          # fetches the hub from the pin, writes uv.lock (reproducible)
```

## 4. First commit + push the consumer

The scaffolder ran `git init` but did not commit:

```bash
git add -A && git commit -m "chore: scaffold ReminderBot (consumer of yahir_reusable_bot)"
git push -u origin main
#   origin is already set if you used --create-remote.
#   if not: create the GitHub repo, then `git remote add origin <url>` before pushing.
```

## 5. Start the consumer's GSD project (separate act)

Open a Claude session at `~/Projects/ReminderBot` and run:

```
/gsd-new-project
```

This is where you define what ReminderBot *is* — milestones, requirements. It is its own,
independent GSD project.

## 6. Build

- **Domain code** → `reminderbot/`
- **Reusable pieces you'll promote** → `reminderbot/_promotable/` (keep hub-clean — imports only
  hub ports + stdlib/third-party, no domain nouns, own tests; the dir's `README.md` states the
  contract). Promote later via `git mv` into the hub → tag → **human-gated** repin. See
  `ECOSYSTEM.md` §6.
- **Wire the hub's engines/adapters** → `reminderbot/wiring.py` (the composition root — the one
  place app specifics are injected into hub mechanisms).
- **Editing the hub live while building?** Overlay an editable install (uncommitted):
  `uv pip install -e ../YahirReusableBot` — revert with `uv sync --frozen`.

---

## Later — when it goes live

Give the consumer its own `deploy/` (a systemd unit + a `REPIN-RITUAL.md` + `PROMOTION-LEDGER.md`)
mirroring WeatherBot's `deploy/`. Repinning the hub to a new tag and restarting a live host is a
**human-gated** step (`ECOSYSTEM.md` §3, §7).
