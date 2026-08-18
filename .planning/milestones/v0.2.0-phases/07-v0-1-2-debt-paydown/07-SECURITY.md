---
phase: 7
slug: v0-1-2-debt-paydown
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: 2026-08-05
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time across `07-01-PLAN.md` … `07-07-PLAN.md`
> (`register_authored_at_plan_time: true`); verified retroactively against the implemented
> code on 2026-08-05. No implementation file, test file, or other phase artifact was
> modified by this audit.

---

## Register Reconciliation (read this first)

The seven plan-time `<threat_model>` blocks declare **34 threat IDs**, not 31 as the audit
brief stated. Counted directly from the `<threat_model>` blocks:

| Plan | IDs | Count |
|------|-----|-------|
| 07-01 | `-01`, `-02`, `-03`, `-SC` | 4 |
| 07-02 | `-01`…`-04`, `-SC` | 5 |
| 07-03 | `-01`…`-04`, `-SC` | 5 |
| 07-04 | `-01`, `-02`, `-03`, `-SC` | 4 |
| 07-05 | `-01`…`-04`, `-SC` | 5 |
| 07-06 | `-01`…`-05`, `-SC` | 6 |
| 07-07 | `-01`…`-04`, `-SC` | 5 |
| **total** | | **34** |

IDs are plan-scoped (`T-07-{plan}-{n}`) so there are **no collisions** — every ID is a
distinct verification unit, unlike Phase 6 where two IDs were reused across plans. Split by
disposition: **27 mitigate · 7 accept · 0 transfer**. Split by severity: **15 high · 7 medium
· 12 low · 0 critical**.

The seven `-SC` supply-chain threats are each declared **high / mitigate** in this phase
(Phases 5 and 6 declared theirs low/accept). They are verified **once, phase-wide** by a
single consolidated dependency-table diff — see § *Supply Chain (T-07-\*-SC)* below — because
they assert the identical fact about the identical two tables. That one diff is positive
evidence, not an accepted-risk line.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| consumer composition root → `CommandRegistry.__init__` | Consumer-supplied `CommandSpec` tuple crosses into hub-owned validation | `spec.name` (text), `spec.bind` (an opaque consumer closure whose `repr` can carry a bound token) |
| Discord REST API → `summon_panel` | Remote HTTP failures (403 `Forbidden`, 404 `NotFound`, generic `HTTPException`) cross into hub control flow | Exception type + payload; pin-state of a remote channel |
| hub → operator logs | Event strings and structured fields read by a human operator; a mislabeled cause is a diagnosability failure | `channel_id`, `label` — non-secret structured fields only |
| host thread → bot event loop | `stop()` schedules work cross-thread onto a loop it does not own; the loop can close in the gap between the liveness check and the schedule (D-28 TOCTOU) | A `close()` coroutine object |
| hook value → log record | The `label` value crosses from a caller into a rendered log line — the class of bug that produces log injection | `label` string |
| OS process table → identity guard | `/proc/<pid>/cmdline` bytes from an arbitrary, possibly **recycled** PID cross into a match decision that gates a `SIGHUP` (default disposition: *terminate*) | Raw argv bytes |
| consumer composition root → hub constructor signatures | Narrowed public annotations are the hub's published contract for consumer-supplied callables | Type-check-time contract only; no runtime value |
| planning artifact → human executing a repin | A path claim in a planning document is acted on by a human at repin time | Source file paths in a sibling repository |
| test gate → developer confidence | A gate that silently does not run, or greps a narrower string than the error, produces false assurance | Pass/fail signal |
| workflow → consumer repository and release surface | Version bump, tag cut, repin, deploy cross **out** of this repo's jurisdiction into the human's (`ECOSYSTEM.md` §3) | Release artifacts; another repo's working tree |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-07-01-01 | Information Disclosure | the new `ValueError` message | low | mitigate | `registry/registry.py:68-72` — message interpolates `{spec.name!r}` **only**. Confirmed `CommandSpec` carries `bind: Callable[[DispatchContext], Any]` (`registry/spec.py:69`) and neither `spec.bind` nor the whole `spec` appears in either raise. Repo-wide: both `ValueError`s in the file (`:63`, `:68`) interpolate `spec.name` and nothing else | closed |
| T-07-01-02 | Denial of Service | `CommandRegistry.__init__` | low | **accept** | `registry.py:41` materializes `tuple(specs)` first; `:60` `seen: set[str]`, `:67` `spec.name in seen` (O(1) hash), `:73` `seen.add` — all **inside the existing D-34 loop**, no second pass. `registry/match.py` has **zero** commits in the phase → no per-match hot-path cost. AR-07-01 | closed |
| T-07-01-03 | Tampering | consumers relying on last-writer-wins duplicate registration | medium | mitigate | Surfacing landed durably in **four** artifacts: `ROADMAP.md:457` (close-out step 4, "Sweep WeatherBot for duplicate `spec.name` values"), `:458-460` (step 5, "two separate, individually green checks"), `REQUIREMENTS.md:261-262`, `PROJECT.md:64`. Nothing executed — see T-07-07-01 | closed |
| T-07-01-SC | Tampering | package installs | **high** | mitigate | Consolidated §*Supply Chain* below: `[project.dependencies]` and `[dependency-groups].dev` have **zero** diff lines across the whole phase; `uv.lock` untouched | closed |
| T-07-02-01 | Repudiation | retry-pin `_log.critical` | medium | mitigate | `discord/gateway.py:227-239` — `except discord.Forbidden:` with the distinct event `"panel pin forbidden on retry (permission revoked mid-summon); fresh panel left unpinned"`, ordered **BEFORE** `except discord.HTTPException:` at `:240` (Python `except` is first-match; `Forbidden` subclasses `HTTPException`, so the reverse order is dead code). Pinned by `tests/test_gateway.py:342` and its under-sampling twin `:378` (asserts the generic case still gets the cap message) | closed |
| T-07-02-02 | Information Disclosure | new log event | low | mitigate | `gateway.py:238` emits `channel_id=getattr(channel, "id", None)` and nothing else — matching every sibling branch (`:221`, `:243`, `:253`, `:265`, `:280`). No token, no message content, no exception payload, no `exc_info`. Whole-phase diff adds **zero** new imports and zero new interpolations | closed |
| T-07-02-03 | Denial of Service | eviction retry via the cleanup loop | low | **accept** | `gateway.py:215` peeks (`stray = matches[0]`); `:223-224` pops **only** in the `else:` (successful delete). A failed eviction therefore costs exactly ONE extra `delete()` via the bounded `for old in matches:` loop at `:259` — no loop, no backoff, bounded by owned-pin count (≤ Discord's 50-pin ceiling, `gateway.py:190`). Both sides pinned: `tests/test_gateway.py:411` (fail → `delete_attempts == 2`), `:439` (success → `== 1`). AR-07-02 | closed |
| T-07-02-04 | Elevation of Privilege | Discord permission model | low | **accept** | `REQUIRED_PANEL_PERMS` (`gateway.py:53`) has **zero** phase commits (`git log -S` returns empty); the outer TOCTOU backstop `except discord.Forbidden:` at `:274-282` is present and untouched. The phase changed classification + cleanup bookkeeping only. AR-07-03 | closed |
| T-07-02-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*. `structlog.testing` (the only new test import) ships inside the already-pinned `structlog>=26.1.0` (`pyproject.toml:12`) | closed |
| T-07-03-01 | Denial of Service | `BotThread.stop` | medium | mitigate | `gateway.py:388` binds `coro = self._client.close()` **before** any scheduling attempt; `:392` `coro.close()` on the never-scheduled branch only. Pinned by `tests/test_gateway.py:530` asserting `inspect.getcoroutinestate(client.coros[0]) == inspect.CORO_CLOSED`. RED-ness reproduced by this audit at `b5cbe36` — the `RuntimeWarning: coroutine … was never awaited` fires there and not at HEAD | closed |
| T-07-03-02 | Denial of Service | `stop()` raising and skipping the join | **high** | mitigate | Both `try` blocks keep the best-effort posture (`:391` and `:399`, each `except Exception:`), and `grep -c "self._thread.join(timeout=timeout)"` returns **1**, at `:402` — **outside both**, at method-body indentation, after the whole `if loop is not None…` block. No early `return` exists in either except branch. The original reproducer `tests/test_gateway.py:249` (retained, see T-07-03-04) asserts `fake_thread.joined == [True]`, and so does the new `:530` | closed |
| T-07-03-03 | Repudiation | shutdown diagnostics | medium | mitigate | Two distinct event strings: `gateway.py:394` `"bot client.close() could not be scheduled (bot loop already closed)"` vs `:401` `"bot client.close() did not complete cleanly"`. Pinned from **both** sides — `tests/test_gateway.py:577` (scheduling failure present, await message absent) and `:623` (await failure present on a genuinely running loop, scheduling message absent) | closed |
| T-07-03-04 | Tampering | the test signal itself | **high** | mitigate | Mechanically re-run by this audit. (a) `git diff --numstat e8049ec~1..HEAD -- tests/test_gateway.py` → **`378  0`** — 378 insertions, **zero deletions**; the file's whole-phase diff contains no `-` line. (b) `_FakeCloseableClient` (`tests/test_gateway.py:275`) and the original reproducer `:249` appear **nowhere** in the phase diff → untouched. (c) `! grep -q 'ignore::' pyproject.toml` → **PASS** (no `ignore::` anywhere in the file). `filterwarnings = ["error"]` is live at `pyproject.toml:48` | closed |
| T-07-03-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*. `filterwarnings` is a `[tool.pytest.ini_options]` key, not a package — it is the **only** pyproject line the phase added, and it sits outside both dependency tables | closed |
| T-07-04-01 | Denial of Service | consumer builds after repin | low | mitigate | Signature-only: whole-phase package diff adds **zero** `def`/`class`/`__all__`/import lines, so no runtime call shape changed. Blast radius surfaced durably at `STATE.md:166` ("Human-gated close-out surfaced (… SURF-02 blast radius …)") and `07-07-SUMMARY.md:286-291`, which records the on-disk finding: `WeatherBot/weatherbot/scheduler/wiring.py:442`'s `_on_online(_result)` is already single-positional. *Advisory #2 below: the ROADMAP/REQUIREMENTS close-out enumerations do not carry this step* | closed |
| T-07-04-02 | Tampering | annotation accuracy | low | mitigate | The two `get_type_hints` assertions ARE the enforcement mechanism and exist: `tests/test_ready_gate.py:212-214` (`hints["on_online"] == Callable[[HealthResult], None] \| None`) and `tests/test_panelkit.py:212-216` (`hints["render"] == Callable[[Any, Any], discord.Embed]`, with the load-bearing `localns` override). Live annotations: `ready_gate.py:97`, `panelkit.py:172`. Proven non-vacuous — both go RED at `7f60a90` (reproduced by this audit). Sibling regression guard `tests/test_ready_gate.py:217` pins `on_fail` unperturbed | closed |
| T-07-04-03 | Information Disclosure | — | low | **accept** | Verified against the diff, not the prose: 07-04's package diff (`panelkit.py`, `ready_gate.py`, `engine.py`) contains **no** `_log` call, no input read, no data-path change — annotations and docstrings only. AR-07-04 | closed |
| T-07-04-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*. `grep -Ei 'pyright\|mypy\|pyre\|basedpyright'` over `pyproject.toml` **and** `uv.lock` → **zero hits**; the deferred adoption is filed as `.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md`, not installed | closed |
| T-07-05-01 | Tampering | `_best_effort_hook` log message | medium | mitigate | Fixed literal event + structured field at **both** sites: `config/reload.py:339` and `lifecycle/ready_gate.py:194`, each `_log.warning("hook failed; engine result unaffected", label=label)`. Repo-wide `grep '_log\.<level>(f"'` over `yahir_reusable_bot/` → **zero hits**, so no f-string log call survives anywhere. Pinned by `tests/test_ready_gate.py:249` driving `label="{weird}%café"` and asserting `cap[0]["event"] == cap[1]["event"]`; both sites additionally pinned by the RED pair reproduced at `b44e555` (`test_ready_gate.py` + `test_reload.py`). Defense-in-depth note: all four call sites (`reload.py:143,168,176`; `ready_gate.py:141,147`) pass **hub-owned literals**, not consumer data | closed |
| T-07-05-02 | Repudiation | operator log searchability | low | mitigate | Same evidence — `label=` is now its own structured key, filterable/aggregatable, matching the hub-wide `_log.warning("message", key=value)` discipline. Asserted at `tests/test_ready_gate.py:246` (`cap[0]["label"] == "on_online"`) and `tests/test_reload.py:138` | closed |
| T-07-05-03 | Elevation of Privilege | `_argv_matches_marker` → SIGHUP delivery | **high** | mitigate | Verified **literally**: `git diff e8049ec~1..HEAD -- yahir_reusable_bot/lifecycle/identity.py` → `5  0` (five insertions, zero deletions), all five inside the `_argv_matches_marker` docstring at `identity.py:194-198`. **Zero executable lines added, removed, or modified** across the entire phase. The false-positive-free exact `-m` token-prefix scan is byte-for-byte the pre-phase code. The doc half landed consumer-facing at `EXTENSION-GUIDE.md:97-108` (names `python -Omyourmodule`/`-Imyourmodule`, states the asymmetric failure direction). Pinned limitation test `tests/test_identity.py::test_bundled_short_option_group_not_matched` green | closed |
| T-07-05-04 | Information Disclosure | hook failure logging | low | **accept** | Read both handlers in full (`reload.py:326-339`, `ready_gate.py:181-194`): the `except Exception:` body logs the fixed sentence plus `label` and **nothing** else — no `exc_info`, no `str(exc)`, no `arg`. Docstrings state "logged (outcome-only)". AR-07-05 | closed |
| T-07-05-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*. `structlog.testing` ships inside the already-pinned `structlog>=26.1.0` | closed |
| T-07-06-01 | Repudiation | archived planning records | **high** | mitigate | Whole-subtree exemption `"milestones/"` present at `tests/test_doc_drift.py:67` with its per-entry reason. Banner-annotation commit `058ff75` re-checked by this audit: `--numstat` is `2  0` on each of **7** archived files → **14 insertions, 0 deletions**. The archive's primary evidence (`04-01-PLAN.md:257`, the check that passed by grepping the wrong string) survives verbatim | closed |
| T-07-06-02 | Spoofing | the gate's own assurance | **high** | mitigate | All **four** non-vacuity guards located and run: (1) scan-visited-files — `test_doc_drift.py:162` (`_PLANNING_ROOT.is_dir()`) + `:165` (`assert files_to_lines`); (2) phantom-exemption — `test_requirements_docs02_exemption_is_not_a_phantom` `:227`, requires the DOCS-02 window to be non-empty **and** to contain a real match; (3) exempt-prefix-resolves-on-disk — `test_every_exempt_prefix_resolves_on_disk` `:248`; (4) synthetic self-proof driving the **same** `_scan_drift` helper — `:189` and `:209`. `uv run pytest tests/test_doc_drift.py -q` → **5 passed** | closed |
| T-07-06-03 | Tampering | exemption list used as a silencer | **high** | mitigate | Stronger than the declared criterion. `git log -- tests/test_doc_drift.py` returns **exactly one** commit for the file's entire history: `2793076`, the RED-add. Both commits that turned the gate green (`824702e` corrections, `058ff75` archive banner) have an **empty** diff for that file. Because the exemption list shipped in the RED commit and the gate was still RED there (reproduced by this audit: `1 failed, 4 passed`, naming `REQUIREMENTS.md:119` + `HUB-HARDENING-REPORT-v0.1.2.md:213`), the exemptions provably did not silence the two real drift sites | closed |
| T-07-06-04 | Information Disclosure | corrected enumerations | low | **accept** | The corrected text names sibling-repo source paths (`weatherbot/scheduler/daemon.py`, `weatherbot/ops/selfcheck.py`, `weatherbot/scheduler/wiring.py`) — already-public structural information. No credentials, no environment values, no host data. AR-07-06 | closed |
| T-07-06-05 | Denial of Service | the gate's file walk | low | **accept** | `_collect_planning_lines` (`test_doc_drift.py:80-92`) does one `rglob("*.md")` + one `read_text` per file. Measured live by this audit: `tests/test_doc_drift.py` → **5 passed in 0.07s**; full suite **191 passed in 1.60s**, inside the ~2s budget. AR-07-07 | closed |
| T-07-06-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*. `test_doc_drift.py:30-31` imports **stdlib only** (`re`, `pathlib`) — no `grimp`, no new dependency. Confirmed by reading the file's whole import block | closed |
| T-07-07-01 | Elevation of Privilege | release + consumer repo | **high** | mitigate | Re-derived independently, not read from the SUMMARY. (a) **No tag** — `git tag --list` returns exactly `v0.1.0 / v0.1.1 / v0.1.2`; `v0.2.0` is empty; the newest tag dates `2026-07-28`, while the phase's first commit is `2026-08-03` → no tag was cut during the phase. (b) **Version unchanged** — `pyproject.toml:3` reads `version = "0.1.2"` and the whole-phase pyproject diff (below) never touches line 3. (c) **`pyproject.toml` untouched by this plan** — `git show --stat` on both 07-07 commits (`df277b8`, `be30b68`) lists only `.planning/` files. (d) **Consumer repo** — see *Verification Limit* below; recorded honestly rather than asserted | closed |
| T-07-07-02 | Spoofing | the GATE-02 claim | **high** | mitigate | **Every one of the 18 facts re-derived from git by this audit, in a scratch `git worktree` outside the repo** (main `HEAD` unchanged throughout). Adjacency: all 6 pairs MATCH (`d92351d`←`7da4568`, `c42e90f`←`802ac85`, `b5cbe36`←`b6ba940`, `7f60a90`←`94e14d9`, `b44e555`←`d2e9ca3`, `2793076`←`824702e`). Genuine RED-ness: all 6 reproduced, matching the SUMMARY's recorded counts and failure text exactly (`3 failed, 2 passed` / `2 failed` ×4 / `1 failed, 4 passed`). Purity: all 6 RED commits touch `tests/` only (75 / 203 / 175 / 66 / 125 / 258 insertions, zero source files). Full table in §*GATE-02* below | closed |
| T-07-07-03 | Repudiation | exemptions omitted from the audit | medium | mitigate | LIFE-05's D-61a exemption recorded verbatim at `07-07-SUMMARY.md:168-193` **with** the git evidence inline (the docstring-only diff) — not silently skipped. All three manual-only verifications recorded with reasons at `:195-226`: SURF-02 `engine.py` variadic verdict, LIFE-05 `EXTENSION-GUIDE.md` §4 doc half, DOCS-03 filesystem enumeration. Coverage row `D4` carries `human_judgment: true` + rationale (`:81-86`) rather than claiming automation | closed |
| T-07-07-04 | Tampering | the warning filter | medium | mitigate | The gate runs the **real** filter explicitly, not the default summary: recorded at `07-07-SUMMARY.md:127` and `07-VERIFICATION.md:75`. Re-run live by this audit: `uv run pytest -q -o 'filterwarnings=error'` → **191 passed**, and the standing `pyproject.toml:48` `filterwarnings = ["error"]` makes the default run equivalent (`uv run pytest -q` → 191 passed, zero warnings) | closed |
| T-07-07-SC | Tampering | package installs | **high** | mitigate | §*Supply Chain*, phase-wide. Additionally: no type checker entered the toolchain (zero hits for `pyright\|mypy\|pyre\|basedpyright` in `pyproject.toml` **and** `uv.lock`), and `pyproject.toml` is untouched by both 07-07 commits | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `block_on: high` count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

**Closed: 34/34. Open (blocking): 0. Open (non-blocking): 0.**

---

## Supply Chain (T-07-01-SC … T-07-07-SC) — one consolidated verification

All seven `-SC` threats assert the identical fact about the identical two tables, so they are
verified once, phase-wide, with a positive diff rather than seven restatements. Phase commit
range: `e8049ec~1` … `854389c` (`e8049ec` = first phase-7 commit, `854389c` = phase close-out).

```
$ git diff --stat e8049ec~1..854389c -- pyproject.toml uv.lock
 pyproject.toml | 8 ++++++++
 1 file changed, 8 insertions(+)

$ git diff e8049ec~1..854389c -- pyproject.toml
@@ -38,3 +38,11 @@ dev = [
  testpaths = ["tests"]
  pythonpath = ["."]
  addopts = "-ra"
+# HYG-03 (D-65): … Remedy policy: … targeted per-warning-class suppression …
+filterwarnings = ["error"]

$ git log --oneline e8049ec~1..HEAD -- pyproject.toml uv.lock
bbe5d50 chore(07-03): enforce zero warnings structurally via filterwarnings=error (D-65)
```

Findings:

- **`[project.dependencies]` (`pyproject.toml:6-14`): zero diff lines.** The four pins
  (`discord.py==2.7.1`, `httpx>=0.28.1`, `structlog>=26.1.0`, `tenacity>=9.1.4`) are
  byte-identical to their pre-phase state.
- **`[dependency-groups].dev` (`:29-35`): zero diff lines.** Five dev deps unchanged.
- **`uv.lock`: not touched by any commit in the phase.** Its mtime is still `Jul 28 17:15` —
  the `v0.1.2` tag commit's timestamp.
- **Exactly one commit in the entire phase touched `pyproject.toml`** (`bbe5d50`), adding
  8 lines in `[tool.pytest.ini_options]` — a config key, not a package.
- **Zero new imports** entered `yahir_reusable_bot/` across the whole phase (whole-phase diff
  grep for `^\+(import |from )` → no hits). `structlog.testing`, the only new import anywhere,
  is in `tests/` and ships inside the already-pinned `structlog>=26.1.0`.
- **No type checker** anywhere: `grep -Ei 'pyright|mypy|pyre|basedpyright' pyproject.toml uv.lock`
  → zero hits.

**All seven `-SC` threats are closed on positive evidence.** No `[ASSUMED]`/`[SUS]` package
exists in this phase, so no legitimacy checkpoint is warranted.

---

## GATE-02 RED-First Ancestry — re-derived by this audit (T-07-07-02)

Not read from `07-07-SUMMARY.md`. Each RED sha was checked out into a detached
`git worktree` under the session scratchpad (never `git stash`; the main working tree's
`HEAD` stayed at `6cf40aa` and `git status` was unchanged before and after), the requirement's
test command was run there against the repo venv, and the worktrees were removed
(`git worktree remove --force` + `prune`, verified back to a single worktree).

| Requirement | RED → GREEN | Adjacency (`rev-parse <GREEN>^`) | Genuine RED-ness reproduced at the RED tree | Purity (`show --stat <RED>`) |
|---|---|---|---|---|
| MATCH-03 | `d92351d` → `7da4568` | MATCH | `3 failed, 2 passed` — `DID NOT RAISE ValueError` ×3 | `tests/test_registry.py` only, 75 ins |
| DISC-07/08 | `c42e90f` → `802ac85` | MATCH | `2 failed` — Forbidden-distinct event absent; `delete_attempts == 1` | `tests/test_gateway.py` only, 203 ins |
| HYG-03 | `b5cbe36` → `b6ba940` | MATCH | `2 failed` + `RuntimeWarning: coroutine … was never awaited` — the live leak, reproduced | `tests/test_gateway.py` only, 175 ins |
| SURF-02 | `7f60a90` → `94e14d9` | MATCH | `2 failed` — both `get_type_hints` assertions | `tests/test_panelkit.py` + `test_ready_gate.py`, 66 ins |
| HYG-02 | `b44e555` → `d2e9ca3` | MATCH | `2 failed` — **both** sites (`test_ready_gate.py` + `test_reload.py`) | `tests/test_ready_gate.py` + `test_reload.py`, 125 ins |
| DOCS-02 | `2793076` → `824702e` | MATCH | `1 failed, 4 passed` — `REQUIREMENTS.md:119`, `HUB-HARDENING-REPORT-v0.1.2.md:213` | `tests/test_doc_drift.py` only (new file), 258 ins |

Every count and every failure string matches `07-07-SUMMARY.md:150-155` exactly. The GATE-02
claim is evidence, not narrative. The seventh requirement, **LIFE-05**, is the declared D-61a
exemption (no behavioral change) — see T-07-05-03 and T-07-07-03.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-01-02 | **O(n) uniqueness check at construction.** Hash-set membership over an already-materialized `tuple(specs)` (`registry.py:41`), inside the pre-existing D-34 validation loop — no second pass, no unbounded work. Deliberately NOT at match time: D-34 already rejected match-time casefolding for exactly the per-match hot-path cost this would incur. `registry/match.py` has zero commits in the phase | plan-time (07-01), re-verified by this audit | 2026-08-05 |
| AR-07-02 | T-07-02-03 | **One extra `delete()` per failed eviction.** Tying the `matches.pop(0)` to a *successful* delete means a failed eviction is retried exactly once, by the existing bounded `for old in matches:` cleanup loop in the same `summon_panel` invocation. No loop, no backoff, no unbounded retry; the upper bound is the owned-pin count, itself capped by Discord's 50-pin ceiling. Both sides pinned (`tests/test_gateway.py:411`, `:439`) | plan-time (07-02) | 2026-08-05 |
| AR-07-03 | T-07-02-04 | **The Discord permission model stays the boundary.** Phase 7 changed exception *classification* and cleanup bookkeeping only. `REQUIRED_PANEL_PERMS` (`gateway.py:53`) and the outer TOCTOU `discord.Forbidden` backstop (`:274-282`) are the permission boundary and were not modified — the hub cannot, and does not attempt to, evict pins it does not own (D-27 residual) | plan-time (07-02) | 2026-08-05 |
| AR-07-04 | T-07-04-03 | **No disclosure surface in the annotation plan.** 07-04's package diff (`panelkit.py`, `ready_gate.py`, `engine.py`) is annotations + docstrings only: no log emission, no input read, no data-path change. Verified against the diff, not the plan text | plan-time (07-04) | 2026-08-05 |
| AR-07-05 | T-07-05-04 | **Outcome-only hook-failure logging.** Both `_best_effort_hook` handlers log a fixed sentence plus the `label` key and deliberately never the exception payload or the hook's argument — the pre-existing "never mask the engine result" posture, unchanged by this phase. Trade-off accepted: an operator sees *that* a hook failed and *which* one, not *why*; the consumer's own hook is expected to log its own cause | plan-time (07-05) | 2026-08-05 |
| AR-07-06 | T-07-06-04 | **Corrected enumerations name sibling-repo paths.** `weatherbot/scheduler/daemon.py`, `weatherbot/ops/selfcheck.py`, `weatherbot/scheduler/wiring.py` — already-public structural information about a repository the hub already references by name in `ECOSYSTEM.md`. No credentials, no environment values, no host paths | plan-time (07-06) | 2026-08-05 |
| AR-07-07 | T-07-06-05 | **The drift gate re-reads every `.planning/**/*.md` per run.** A few dozen small files, one `rglob` + one `read_text` each, no caching. Measured live: 5 passed in 0.07s; the full suite is 1.60s. Cost accepted in exchange for a gate with no cross-repo dependency and no `skipif` (a `skipif` would be the same false-assurance class the phase exists to close) | plan-time (07-06) | 2026-08-05 |

*Accepted risks do not resurface in future audit runs.*

---

## New Attack Surface Appearing During Implementation

**No SUMMARY in this phase carries a `## Threat Flags` section** — verified independently:
`grep -n "Threat Flags\|threat_flag"` across `07-01-SUMMARY.md` … `07-07-SUMMARY.md` returns
zero hits, and a dump of every `## ` heading across all seven confirms the section is absent
(the only `threat`-adjacent line anywhere is `07-01-SUMMARY.md:100`, which *cites* T-07-01-01
rather than flagging new surface).

Absence of the section is not evidence that no new surface appeared, so the whole-phase diff
was read directly instead of trusted:

```
$ git diff --numstat e8049ec~1..HEAD -- yahir_reusable_bot/
1   1   config/reload.py          8   2   lifecycle/ready_gate.py
59  15  discord/gateway.py       16   0   registry/registry.py
7   1   discord/panelkit.py      12   0   scheduler/engine.py
5   0   lifecycle/identity.py

$ git diff … | grep -E '\+.*__all__|^\+def |^\+class '   → NONE
$ git diff … | grep -E '^\+(import |from )'              → NONE
```

**Zero new exports, zero new public functions or classes, zero new imports, zero new
dependencies across the entire phase.** Every changed file maps to a declared threat ID. No
`unregistered_flag` found.

Two informational post-plan changes were checked and are **not** new surface:

1. **`6ca3ad3` (code-review WR-01 fix) is docstring-only.** It rewrites `summon_panel`'s D-26
   paragraph (`gateway.py:173-181`) from the stale `>=2` threshold to `>=1`. `git show` confirms
   6 insertions / 3 deletions, all inside the docstring; zero executable lines. This *closes*
   doc-vs-code drift rather than opening surface — squarely on this phase's own DOCS theme.
2. **`07-REVIEW.md`'s CR-01 was REJECTED as a false positive** ("pin-cap retry-failure path can
   delete every owned panel, leaving zero pinned"). Independently sanity-checked against live
   source and the rejection holds: `channel.send(...)` at `gateway.py:196` runs **before** any
   delete (create-before-delete), `matches` was collected at `:191` and therefore never contains
   the fresh panel, so the retry-failure tail ends with exactly one **live** panel — unpinned,
   with a loud CRITICAL at `:241`/`:250`. That is the documented D-27 residual (availability
   degradation, out-of-authority), not a security regression, and the reviewer's proposed remedy
   would leave two live click-responsive Views — the D-24/D-25 failure mode.

---

## Verification Limit (recorded, not asserted)

**T-07-07-01(d) — the consumer repository's git status is NOT re-verified by this audit.**
`/home/yahir/Projects/WeatherBot` is outside this audit's jurisdiction and was deliberately not
touched, read, or `git status`-ed. What *is* provable from inside this repo, and was proved:
every commit in the phase range is confined to this repository, no tag was cut, no version
string moved, and `pyproject.toml` is untouched by the close-out plan. The consumer-repo
cleanliness claim rests on `07-07-SUMMARY.md:269-274` and `07-VERIFICATION.md:84`, which record
it as pre-existing unrelated dirt from WeatherBot's own concurrent session. That is a
plan-recorded claim, not an independently re-derived one — stated here rather than folded into
the evidence column. It does **not** change T-07-07-01's status: the three release-surface
facts this repo owns (no tag, no version bump, pyproject untouched) are each independently
verified, and no phase commit could have reached another repository.

---

## Advisory Observations (not threats, not blocking)

Surfaced because the register's "surfaced for the human-gated repin" mitigations depend on the
telling landing where the human will actually look. Neither is a declared threat; neither
counts toward `threats_open`; both are outside this audit's write scope.

1. **`HUMAN-UAT-PENDING.md` carries no Phase 7 entry.** The Gate-2 sign-off ledger has
   `### Phase 5` and `### Phase 6` sections only. Phase 7's human-gated items live in
   `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`, and `07-07-SUMMARY.md` instead — durable, but
   not in the ledger a human reads for pending sign-offs.
2. **The SURF-02 blast-radius confirmation is absent from both operative close-out lists.**
   `ROADMAP.md:447-467` (7 numbered steps) and `REQUIREMENTS.md:250-266` (5 steps) both carry
   the MATCH-03 duplicate sweep (T-07-01-03) but neither carries "confirm the consumer's
   `on_online` handler is single-positional" (T-07-04-01). It is recorded at `STATE.md:166` and
   `07-07-SUMMARY.md:286-291`. T-07-04-01 is CLOSED on those two artifacts; *recommended: carry
   the step into the ROADMAP close-out list before the v0.2.0 repin.* This is the same class of
   observation Phase 6's audit raised as its finding #5 (the recipe-2 gap), which also has not
   propagated to the ROADMAP list.

---

## Verification Method

ASVS Level 1 (`asvs_level: 1`) — mitigations verified PRESENT in the cited file. Depth applied
**exceeded L1** for every high-severity threat: the seven `-SC` claims were re-derived from the
dependency-table diff rather than read from `07-RESEARCH.md`; `identity.py`'s no-executable-change
claim was verified from the whole-phase diff literally; all 18 GATE-02 ancestry facts were
re-derived from git trees including six live RED reproductions in scratch worktrees; the
`Forbidden`-before-`HTTPException` ordering was traced against Python's first-match `except`
semantics rather than pattern-matched; and `summon_panel`'s create-before-delete ordering was
walked end-to-end to adjudicate the rejected CR-01.

Commands run by this audit:

```
uv run pytest -q                                → 191 passed in 1.60s (zero warnings)
uv run pytest -q -o 'filterwarnings=error'      → 191 passed in 1.35s
uv run pytest tests/test_import_hygiene.py -q   → 10 passed
uv run pytest tests/test_doc_drift.py -q        → 5 passed in 0.07s
uv run ruff check                               → All checks passed!
git diff --stat e8049ec~1..854389c -- pyproject.toml uv.lock   → 8 insertions, pytest ini only
git diff --numstat e8049ec~1..HEAD -- <identity.py|test_gateway.py>  → 5/0 and 378/0
grep -q 'ignore::' pyproject.toml               → no match (T-07-03-04 gate PASSES)
git rev-parse <GREEN>^ × 6                      → all adjacent to the claimed RED sha
git worktree add --detach × 6 + pytest at each  → all 6 RED failures reproduced, then removed
git show --stat <RED> × 6                       → tests/ only, zero source files
git tag --list                                  → v0.1.0 v0.1.1 v0.1.2 (no v0.2.0; all pre-phase)
```

Post-audit state confirmed: one worktree (`main` @ `6cf40aa`), `git status` unchanged, no
implementation or test file modified.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-05 | 34 (declared across 7 plans; no ID collisions) | 34 | 0 | gsd-security-auditor (retroactive, `/gsd-secure-phase`) |

---

## Sign-Off

- [x] All 34 threats have a disposition (27 mitigate / 7 accept / 0 transfer)
- [x] All seven high-severity `-SC` threats closed on **positive** dependency-diff evidence, not accepted-risk lines
- [x] All 8 non-`-SC` high-severity threats verified beyond L1 depth
- [x] Accepted risks documented in Accepted Risks Log (7 entries)
- [x] New attack surface surveyed despite the absence of any `## Threat Flags` section (0 unregistered flags; whole-phase diff shows zero new exports/imports)
- [x] Consumer-repo verification limit recorded rather than asserted
- [x] `threats_open: 0` confirmed (`block_on: high`; zero open threats at any severity)
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-05
