# Human UAT Pending — Gate-2 Sign-off Ledger

Deferred human Gate-2 items, collected across phases and signed off in bulk at milestone
completion. Each entry's Gate-1 self-UAT (autonomous, this file's producer) has already PASSED on
the real built artifact; what remains is the human's own confirmation at milestone close.

## Entries

### Phase 5 — redaction-core-pattern-registration (v0.2.0)

- **Status:** `pending`
- **Milestone:** v0.2.0 (self-heal PC-01 redaction)
- **Gate 1 self-UAT log:** [`.planning/phases/05-redaction-core-pattern-registration/05-SELF-UAT.md`](phases/05-redaction-core-pattern-registration/05-SELF-UAT.md) — Verdict: **ALL 5 criteria PASS** (installed wheel `yahir_reusable_bot-0.1.2-py3-none-any.whl`, md5 `0c2fd03b79993bf65438f998b10cc3b8` @ `09dd075`, 2026-07-29). No device/browser surface exists for this project — verification drove the real, built wheel installed into a scratch venv and exercised from a non-repo `cwd`, the consumer-facing layer `uv run pytest` (in-repo `pythonpath=["."]`) cannot reach.
- **Items covered (5 ROADMAP success criteria):**
  - **SC1 — masking + diagnostics survival + idempotence.** `redact_secrets` masked a labeled secret while endpoint/HTTP-status/neighbouring params survived, and re-applying to already-redacted output was a byte-identical no-op. (Non-`str` input clause deliberately out of scope per D-52 — relocated to Phase 6.)
  - **SC2 — compile-once, frozen, no shared state.** `register_patterns` returns a genuine frozen `tuple`; repeated/interleaved calls in one process and a reversed-order call in a fresh process never leaked or reordered state; no module-level mutable container found in `registry.py`.
  - **SC3 — ReDoS rejected at registration.** Both `(a|aa)+$` (CR-01's alternation shape, wall-clock-only catch) and `(a+)+$` (structural pre-check catch) rejected with `ValueError` in <1s under a hard 20s `timeout` wrapper; a benign pattern and an explicit `skip_redos_check=True` opt-out were still accepted (rejection is not a blanket stub).
  - **SC4 — literal secret blocked everywhere, incl. inside `repr()`.** `RedactionPattern.literal()` masked a secret embedded in a hand-written object's `__repr__` (no `name=value` shape), a URL path segment, a list-repr, and a value containing regex metacharacters (confirms `re.escape` applied).
  - **SC5 — AST litmus + pure leaf, verified against the INSTALLED copy.** Independently re-derived AST litmus scan (0 hits) and sibling-import scan (0 sibling `yahir_reusable_bot.*` imports) against `site-packages`, not just the source tree.
- **Owner how-to-verify (run at milestone completion):**
  1. Read `05-SELF-UAT.md` above for per-criterion evidence and the exact probe scripts' output.
  2. Optionally re-run the same scratch-venv drill yourself: `uv build`, `uv venv <dir>`, `uv pip install` the wheel, then from outside the repo import `yahir_reusable_bot.redact` and repeat any of the 5 probes described in the log.
  3. Confirm the Phase-6 scope fence (`RedactingWriter` sink, structlog processor, `assert_redaction_active`, redaction-count telemetry, `EXTENSION-GUIDE.md` SEAM-08) is still correctly absent from this phase's diff.
- **Note:** No schema/migration involved (pure library, no persistent state). Environment caveat: no device/browser target exists for this project by design; `.planning/AGENT-LIBRARY-TESTING.md` (new this phase) documents the scratch-venv consumer-probe driver for future Gate-1 runs on this hub.
