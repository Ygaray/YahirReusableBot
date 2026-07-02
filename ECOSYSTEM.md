# ECOSYSTEM.md — the multi-repo bot ecosystem (read this before working across repos)

> **Audience: coding agents (and humans) working in `yahir_reusable_bot` — this hub — or in
> any consumer bot that depends on it.** This is the constitution for how the repos relate,
> who has authority over what, and where new code goes. If you are about to fix a bug that
> might live upstream, or add a feature that might be reusable, read the relevant section
> *before* you start. When it conflicts with a single repo's stale note, this document wins;
> flag the drift.

---

## 1. The shape — hub + spokes

This is **not one project.** It is a shared infrastructure module plus N independent bots that
consume it:

- **The hub — `yahir_reusable_bot`** (this repo; PyPI name `yahir-reusable-bot`; public at
  `github.com/Ygaray/YahirReusableBot`). Generic, channel-agnostic bot infrastructure:
  scheduler engine, config hot-reload, delivery `Channel` abstraction + reliability, process
  lifecycle, command registry/dispatch, the Discord adapter + panel kit. **Zero domain
  assumptions** — it names no weather, no reminders, nothing app-specific.
- **The consumers (spokes)** — separate repos, each its own GSD project, each pinning the hub
  via a uv git dependency:

  | Consumer | Repo | Dev checkout | Pins hub at | Deploy host |
  |----------|------|--------------|-------------|-------------|
  | WeatherBot | `github.com/Ygaray/WeatherBot` | `/home/yahir/Projects/WeatherBot` | `v0.1.0` | `yahir-mint` (systemd) |
  | ReminderBot | _(planned)_ | `/home/yahir/Projects/ReminderBot` | — | — |

  _(Keep this table current — a new consumer adds a row; a repin updates the "Pins hub at"
  cell. It is best-effort, not authoritative — the authoritative pin is each consumer's
  `[tool.uv.sources]` + `uv.lock`.)_

**The load-bearing invariant (one-way dependency):** consumers import from the hub; **no hub
file ever imports a consumer.** Everything app-specific is *injected* at the consumer's
composition root (e.g. WeatherBot's `weatherbot/scheduler/wiring.py build_runtime(...)`). The
hub assembles nothing of its own. This is enforced in the hub by an import-hygiene gate
(`grimp` + a litmus grep) — see §5.

---

## 2. How a consumer actually consumes the hub (and why it matters for bug-fixing)

A consumer does **not** run the hub *source*. It runs the **pinned, installed copy**:
`[tool.uv.sources]` names a git tag, `uv.lock` freezes the exact resolved sha, and `uv sync`
installs that. So "the hub" a running consumer sees is a wheel built from a frozen commit — not
your local `../YahirReusableBot` working tree.

**This is the single most important thing to understand before you edit the hub from a
consumer.** If you fix a bug in `../YahirReusableBot` source, then re-run the consumer's tests,
they will **still fail** — because the consumer is running the old pinned wheel, not your edit.

Two mechanisms bridge that gap:

- **Dev-time — the editable overlay.** To make your in-progress hub edits live in the consumer,
  install the hub editable *over* the pin:
  ```bash
  # from the consumer repo:
  uv pip install -e /home/yahir/Projects/YahirReusableBot
  ```
  Now the consumer imports your live hub source. This is **uncommitted and local only** — never
  add a path source to `[tool.uv.sources]` (uv ships no path-override feature; a committed path
  would leak into deploy). Revert with `uv sync --frozen`, which restores the pinned wheel.
- **Ship-time — the repin ritual.** To make a hub change *real* in production, see §6. This is a
  **human-gated** step (see §3).

---

## 3. Cross-repo jurisdiction — you may fix the hub, but shipping it is gated

**You have standing authority to fix hub bugs from a consumer.** The v2.0 split (WeatherBot →
this hub) was mechanical and may have left rough edges; if a bug you hit in a consumer actually
lives in the shared hub, the correct fix is *upstream in the hub*, not a consumer-side
work-around. Do not paper over a hub bug.

But respect the blast radius: **a hub change ripples to every consumer, present and future.**
So the authority is scoped by *when* you act, not *whether*:

- ✅ **Autonomous:** read/edit the hub source, add/adjust its tests, run the hub's own suite +
  the litmus gate, and verify the fix live in the consumer via the editable overlay. Fix it,
  prove it, keep it litmus-clean.
- 🛑 **Surface and confirm before doing:** the step that changes *what production runs* — cutting
  a new hub tag, repinning a consumer's `[tool.uv.sources]`/`uv.lock`, and deploying/restarting a
  live bot. Do everything up to that point, then stop and present the repin+deploy for human
  confirmation (this is the ecosystem's B-(ii) rule). A tag bump that reaches `yahir-mint` is a
  deliberate act, not a side effect.

When you fix a hub bug, also make sure the hub's own tests cover it (so the next consumer can't
regress it), and confirm the consumer's suite passes against the fixed hub via the overlay.

---

## 4. Where new code goes — the three tiers

When adding a capability, classify it into exactly one tier. The decision procedure is the
**litmus** (§5).

| Tier | What it is | Where it lives |
|------|------------|----------------|
| **Ports / seams / generic contracts** | The abstract interface a capability plugs into | **The hub.** Many already exist: `Channel` (SEAM-01), `JobStore` Protocol (SEAM-03), config-schema hooks `validate`/`desired_jobs` (SEAM-04), health-check callback (SEAM-05), command registry/`bind` (SEAM-06), panel `SelectedContext[I]` (SEAM-07). See `EXTENSION-GUIDE.md`. |
| **Concrete implementations of those seams** | A real adapter/impl of a port (e.g. a Slack `Channel`, a durable `JobStore`) | **Built in the consumer's `_promotable/` quarantine first** (hub-clean), then **promoted to the hub via `git mv`** once it earns it (§6). |
| **Consumer-specific wiring / config / domain** | The app's own logic and how it *uses* the seams | **The consumer, forever.** Never promotes. |

**Worked example — adding Slack to ReminderBot:**
- The generic `SlackChannel` adapter → built in ReminderBot's `_promotable/`, promoted to the hub
  (it's reusable — WeatherBot could send to Slack too).
- *Which* reminders fire a Slack message, the Slack webhook config, message formatting →
  ReminderBot, permanently.
- The `Channel` port it plugs into already exists in the hub — you build the *impl* against it,
  you don't invent a new seam.

---

## 5. The litmus — the one test that decides tier

> **"Could a *different* bot reuse this with zero domain assumptions?"**

- **Yes** → it belongs in (or promotes to) the **hub**. It must name no domain noun (no
  `weather`, `forecast`, `reminder`, `location`, …) and import no consumer code — only hub ports
  + stdlib/third-party.
- **No** → it stays in the **consumer**.

In the hub this is enforced, not just aspirational: an import-hygiene gate (`grimp` import graph +
a litmus grep + isolated-import smoke, in `tests/test_import_hygiene.py`) fails if hub code
imports a consumer or names a domain term. Anything you promote to the hub must pass it.

---

## 6. Consumer-first + the quarantine model (the promotion recipe)

We build reusable impls **in the consumer first, then promote** — but *cleanly*, so promotion is
a move, not a rewrite. The mechanism is a **quarantine subpackage**.

**Why consumer-first (not hub-first):** designing a "generic" abstraction against a single
*imagined* consumer over-fits it — you build the perfect adapter for ReminderBot, then WeatherBot
wants it and it doesn't fit, so you redesign the supposedly-generic thing anyway. Building it
against a *real* consumer first shapes it correctly. The quarantine keeps that from being messy.

**This is the same pattern as the v2.0 extraction, scaled down:** Phases 22–27 built the reusable
code as a *clean in-place boundary* (a litmus-clean subpackage inside WeatherBot, import-gated,
suite proving behavior), and Phase 28 was a *physical `git mv`* to this repo. "Build it clean in
place, then move it." A single promoted adapter is that recipe for one file instead of a module.

### The quarantine — `_promotable/` in the consumer

```
<consumer>/
  _promotable/                  ← hub-candidate code; obeys the hub contract; slated to move up
    README.md                   ← states the promotion contract (below)
    slack_channel.py            ← class SlackChannel(Channel): imports ONLY hub ports + stdlib/
                                   third-party; names NO domain noun; its own tests
    test_slack_channel.py
  <domain>/…                    ← real app code (stays here forever)
  wiring.py                     ← composition root: injects the _promotable impl like any other
```

**The contract for anything in `_promotable/` (write it this way from day one):**
1. Imports only the hub's public ports + stdlib/third-party. **No consumer imports.**
2. Names no domain noun — it passes the litmus (§5) *in place*.
3. Has its own unit tests, self-contained.
4. Is wired at the consumer's composition root by injection — the app *uses* it; the quarantine
   file doesn't reach back into the app.

If all four hold, promotion is a `git mv`. If any is violated, you've built the *messy* kind of
consumer-first and promotion becomes a refactor — don't.

### What earns promotion (the trigger)

Promote when **either** holds:
- it's **proven in production** in its consumer, **or**
- a **second consumer wants it** (the rule of three).

Until then it lives in quarantine. A designed-but-unbuilt hub seam whose *impl* is deferred (e.g.
the durable `JobStore` + its serialization contract — `EXTENSION-GUIDE.md`) follows exactly this:
build the impl in a consumer's `_promotable/` against the existing port, promote when the shape is
solid.

### The promotion move (once it's earned it)

1. `git mv <consumer>/_promotable/slack_channel.py yahir_reusable_bot/channels/slack.py`
2. Export it from the hub package; document it in `EXTENSION-GUIDE.md` (flip its row to
   implemented); run the hub suite **+ the litmus gate** (§5).
3. Commit in the hub; cut a new tag (§7).
4. **[human-gated]** Repin the consumer(s): bump `[tool.uv.sources]` tag →
   `uv lock --upgrade-package yahir-reusable-bot` → `uv sync --frozen` → tests → deploy.
5. In the consumer, delete the local copy and swap the import to
   `from yahir_reusable_bot.channels import SlackChannel`.

---

## 7. Versioning & the repin ritual (shipping a hub change)

- The hub uses **semver git tags** (`v0.1.0`, `v0.2.0`, …). Tags are **immutable** — a re-cut is a
  new version number. A backward-incompatible change is a **major** bump.
- Each consumer pins **one tag** and repins on its own cadence. One hub release does not force all
  consumers to move at once.
- The full, ordered ritual lives consumer-side in `deploy/REPIN-RITUAL.md` (WeatherBot's is the
  reference) and is summarized in §6. It ends at a live-host restart — **human-gated (§3)**.
- Each consumer keeps a `deploy/PROMOTION-LEDGER.md` recording which hub sha its live host runs;
  the host's `module provenance` startup-log line must match the ledger's latest row.

---

## 8. Onboarding a new consumer

When you spin up a new bot on this infrastructure (e.g. ReminderBot):

1. New repo, its own GSD project. Add `yahir-reusable-bot` to `dependencies` + a
   `[tool.uv.sources]` git tag pin (copy WeatherBot's `pyproject.toml` shape).
2. Add a row to the §1 consumers table here in the hub.
3. Paste the **consumer pointer block** into the new repo's `CLAUDE.md` (template below) so its
   agents auto-load the ecosystem rules.
4. Create an empty `_promotable/` only when you first have hub-candidate code (§6).

### Consumer `CLAUDE.md` pointer block (paste verbatim, adjust the pin)

```markdown
## Ecosystem — consumer of `yahir_reusable_bot`

This repo is a **consumer** in a multi-repo bot ecosystem. It depends on the shared hub
`yahir_reusable_bot` (repo `github.com/Ygaray/YahirReusableBot`, dev checkout
`../YahirReusableBot`), pinned via `[tool.uv.sources]` at tag **`vX.Y.Z`**.

**Before working across repos, read `../YahirReusableBot/ECOSYSTEM.md`.** Key rules:
- **Cross-repo jurisdiction:** if a bug is actually in the hub, fix it upstream in the hub — but
  cutting a hub tag + repinning + deploying is a **human-gated** step (surface it, don't ship it
  autonomously).
- **The consumer runs the *pinned* hub, not its source.** For live cross-repo dev use the
  editable overlay: `uv pip install -e ../YahirReusableBot` (uncommitted; revert with
  `uv sync --frozen`).
- **Placement:** reusable mechanism → hub; build new reusable impls in this repo's `_promotable/`
  quarantine (hub-clean), promote via `git mv`; app-specific wiring/config/domain → stays here.
  Litmus: "could a different bot reuse this with zero domain assumptions?"
```

---

*Canonical ecosystem doctrine. Lives in the hub; mirrored by a pointer block in each consumer's
`CLAUDE.md`. Update the consumers table (§1) and any changed rule here first — this file is the
source of truth.*
