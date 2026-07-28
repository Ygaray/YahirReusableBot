# Codebase Concerns

**Analysis Date:** 2026-07-08

## Tech Debt

**Incomplete error handling in relay layer:**
- Issue: `summon_panel()` in `yahir_reusable_bot/discord/gateway.py` only catches `discord.Forbidden` but silently fails on other HTTPException/NotFound errors
- Files: `yahir_reusable_bot/discord/gateway.py:167-188`
- Impact: Can leave duplicate live pinned panels or unpinned fresh panels, violating the create-before-delete invariant
- Fix approach: Wrap each write operation (pin, delete) in per-item try/except catching both Forbidden and HTTPException/NotFound; consider delete-then-pin ordering or reserve headroom for the 50-pin cap

**Asymmetric scheduler API contract:**
- Issue: `SchedulerEngine.remove()` raises `JobLookupError` on missing ID, but `register()` silently handles this case with `replace_existing`
- Files: `yahir_reusable_bot/scheduler/engine.py:72-74`
- Impact: Reload reconcile and concurrent misfires can raise uncaught JobLookupError if an ID is already removed
- Fix approach: Either swallow-on-missing in `remove()` or document the asymmetry; guard calls via `list_live_ids()` check

**Config reload missing reject hook on PHASE-2 failure:**
- Issue: When job reconciliation fails (scheduler/register raises), `on_rejected` callback never fires
- Files: `yahir_reusable_bot/config/reload.py:146-158`
- Impact: No rejection alert reaches the operator when a valid config fails during job (de)registration; only PHASE-1 validation failures alert
- Fix approach: Add `on_rejected` hook call in the reconcile exception handler before re-raise (mirror PHASE-1 at L138)

**Edge case in arg extraction with Unicode casefold:**
- Issue: `match_command()` uses casefolded keyword length to slice raw string, but casefold is not length-preserving
- Files: `yahir_reusable_bot/registry/match.py:59-61`
- Impact: Commands with casefold-changing input (e.g. 'ß'->'ss', ligatures) corrupt the extracted argument or fail to parse
- Fix approach: Apply casefold BEFORE slicing, or measure folded length on folded string: `rest = folded[len(spec.name):]`

## Known Bugs

**PID-recycling guard false positive/negative in `-m` module detection:**
- Symptoms: `_argv_matches_marker()` both false-positives on unrelated processes (`python -m pytest weatherbot`) and false-negatives on genuine daemon with interpreter flags before -m
- Files: `yahir_reusable_bot/lifecycle/identity.py:149`
- Trigger: (a) PID recycled to `python -m <tool> <argname>` where argname matches proc_marker; (b) daemon started with flags: `python -W ignore -m weatherbot run`
- Workaround: None; the guard is bypassed. In case (a), SIGHUP is misdirected to unrelated process. In case (b), reload reports daemon not running.
- Fix approach: Replace `b'-m' in argv[1:3] and proc_marker in argv[1:4]` with `len(argv) >= 3 and argv[1] == b'-m' and argv[2] == proc_marker`

**Transient classification misses common httpx network errors:**
- Symptoms: `is_transient()` does not recognize `RemoteProtocolError` or `WriteError`, so they are NOT retried; fire_slot records wrong reason
- Files: `yahir_reusable_bot/reliability/retry.py:80-91`
- Trigger: Server hangup mid-response (routine with external APIs like OpenWeather)
- Workaround: None; missing retries silently miss the briefing with wrong alert (internal_error instead of transient_exhausted)
- Fix approach: Catch `httpx.TransportError` or `httpx.NetworkError` (parent class) instead of the specific trio

**No reconnect supervisor for non-recoverable Discord disconnect:**
- Symptoms: When discord.py client.start() encounters a non-recoverable disconnect, the bot thread dies permanently; `is_alive()` returns False forever
- Files: `yahir_reusable_bot/discord/gateway.py:273-278`
- Trigger: Auth/intents close codes, exhausted retries, session invalidation
- Workaround: None; manual service restart required. Scheduled briefings continue on separate thread (unaffected).
- Fix approach: Add retry loop with exponential backoff around `await self._client.start()` in `_amain()`

## Security Considerations

**Marker validation gap — empty marker matches all bot messages:**
- Risk: If consumer wires `marker=''` at composition root, `is_owned_panel()` treats every bot-authored pinned message as owned and summon_panel would delete unrelated bot pins
- Files: `yahir_reusable_bot/discord/panelkit.py:479`
- Current mitigation: No validation; contract is REQUIRED with no default
- Recommendations: Add one-line non-empty guard in `PanelKit.__init__()` or document the non-empty precondition with an assertion

**Interaction.user None guard missing in operator gate:**
- Risk: `interaction_check()` dereferences `interaction.user.bot` and `.id` without None guard; discord.py can return None in some contexts
- Files: `yahir_reusable_bot/discord/panelkit.py:309`
- Current mitigation: None; AttributeError raised outside View.on_error handler (interactive gate fails unpredictably)
- Recommendations: Add None guard before dereferencing user attributes; return False cleanly if interaction.user is None

**Command name validation gap — empty/uppercase names unmatchable:**
- Risk: (a) Empty spec.name makes blank input match (wrong claim); (b) Uppercase in spec.name makes command permanently unmatchable (casefolded input never matches)
- Files: `yahir_reusable_bot/registry/match.py:57-67`
- Current mitigation: No validation on spec.name; precondition undocumented
- Recommendations: Validate spec.name is non-empty and lowercase at CommandSpec construction or in the registry bind path; document the precondition

## Performance Bottlenecks

**Zero-division edge in retry wait calculation:**
- Problem: `_within_burst_wait()` divides by `(burst_size - 1)`, raising ZeroDivisionError when `burst_size == 1`
- Files: `yahir_reusable_bot/reliability/retry.py:141`
- Cause: Early guard at L137 shields only the first retry; second attempt falls through to division
- Improvement path: Add guard `if burst_size < 2: raise ValueError(...)` early in `build_retrying()`, or document minimum burst_size >= 2 as a precondition

**Mismatched burst configuration in two_burst_wait direct usage:**
- Problem: `two_burst_wait()` mid-pause fires at `attempt_number == burst_size` (default 8), independent of a caller's custom `stop_after_attempt(N)`
- Files: `yahir_reusable_bot/reliability/retry.py:146`
- Cause: Standalone function offers no coupling assertion between burst_size and stop bound
- Improvement path: If callers use `two_burst_wait` directly with custom stop bounds, enforce or document matching burst_size parameter; prefer callers use `build_retrying()` wrapper

## Fragile Areas

**Cross-tap render race in SelectedContext:**
- Files: `yahir_reusable_bot/discord/selection.py:49`
- Why fragile: Single-writer assumption violated by discord.py's async task-per-interaction; consumer wiring reads selection.value pre-await, then re-reads post-await (after dispatch), allowing tap during fetch to change render_arg
- Safe modification: Either capture render_arg once (pre-await) and reuse it, or disable components before await (currently done as a secondary guard)
- Test coverage: Cosmetic mismatch (wrong location label on embed); data integrity preserved. Existing on_command double-tap guard mitigates in the consumer.

**BotThread stop() TOCTOU race on loop lifecycle:**
- Files: `yahir_reusable_bot/discord/gateway.py:244-250`
- Why fragile: Reads `self._loop.is_running()`, then schedules onto loop outside try block; loop may stop between check and `run_coroutine_threadsafe()`, raising RuntimeError
- Safe modification: Wrap `run_coroutine_threadsafe()` call in try/except catching RuntimeError; or re-check is_running() immediately before call
- Test coverage: Refuted by consumer's wrapping try/except at daemon call site (L1587-1591) and client.close() already ran via async-with; no actual crash risk, but latent robustness gap

**Pid file double-close in write_pid_atomic error path:**
- Files: `yahir_reusable_bot/lifecycle/identity.py:62-87`
- Why fragile: On `os.replace()` failure, exception handler calls `os.close(fd)` again; fd integer can be reallocated to unrelated file between closes
- Safe modification: Set a `closed` flag after first close, check before second; or unlink tmp and re-raise without the second close attempt
- Test coverage: Latent (single-threaded early startup makes it rare); `OSError` guard silently hides the misdirected close

**Non-Linux proc_marker comparison misses path-like tokens:**
- Files: `yahir_reusable_bot/lifecycle/identity.py:162`
- Why fragile: Non-Linux returns raw proc_marker as sentinel when /proc is absent; then `_argv_matches_marker()` basenames argv[0] but compares to proc_marker verbatim
- Safe modification: Ensure proc_marker is always a basename token (document precondition); or degrade to False instead of True for non-Linux so behavior matches stated portability
- Test coverage: Only affects non-Linux with path-like proc_marker; documented contract is basename, so mis-shaped marker is a caller error

## Scaling Limits

**Retry schedule incompleteness against network failures:**
- Current capacity: Covers `TimeoutException`, `ConnectError`, `ReadError` and TRANSIENT HTTP status codes
- Limit: `RemoteProtocolError` and `WriteError` not retried; causes briefing miss under routine server blips
- Scaling path: Expand `is_transient()` to catch `httpx.NetworkError` parent class; add integration test with mocked protocol/write errors

**Import hygiene enforcement on single-package graph:**
- Current capacity: Grimp gate checks for app-package imports; litmus grep checks for domain nouns
- Limit: Standalone repo split removed two-package graph (weatherbot doesn't exist); string-only scan catches `weatherbot.*` declarations but not live imports
- Scaling path: When adding a second consumer bot, extend the prefix-scan guard to cover multiple forbidden packages; update gate documentation

## Dependencies at Risk

**Exact discord.py pin (2.7.1) required for persistent-view wire contract:**
- Risk: Live panels' `custom_id` routing is valid only against this exact discord.py version; loosening the pin breaks all saved panels
- Impact: Cannot upgrade discord.py without a consumer redeployment that re-renders all persisted panels
- Migration plan: Document the pin as immutable in CLAUDE.md; when upgrading becomes necessary, coordinate with all consumers to re-render their panels (non-breaking if coordinated)

## Missing Critical Features

**No alert/visibility into PHASE-2 reload reconcile failures:**
- Problem: Reload validates config (PHASE 1), then reconciles jobs (PHASE 2); failures in reconcile silently swallow operator notification
- Blocks: Operator unaware of job-registration failures (e.g., duplicate job IDs, invalid trigger syntax)
- Fix priority: High — affects observability of config reload correctness

**No graceful reconnect for non-recoverable Discord disconnect:**
- Problem: Bot thread dies on auth/intents errors and never respawns
- Blocks: Interactive commands (panel taps, message handler) completely unavailable until manual restart; scheduled work continues
- Fix priority: High — affects interactive feature availability

## Test Coverage Gaps

**Import hygiene gates re-scoped for standalone repo but missing some evidence:**
- What's not tested: Real-import self-proofs (test_selfproof_import_gate_catches_real_app_edge / test_selfproof_isolated_import_catches_real_app_edge) were dropped because weatherbot package doesn't exist
- Files: `tests/test_import_hygiene.py:18-38`
- Risk: Grimp graph gate now uses single-package build; string prefix scan still catches declared imports but not live ones. If a module somehow imports weatherbot at runtime (e.g. via `importlib.import_module` or `__import__`), the gate would not catch it.
- Priority: Medium — edge case mitigated by the isolated-import blocker + synthetic self-proof; consider adding a dynamic import test or documenting the limitation

**Command-name edge cases untested:**
- What's not tested: `match_command()` with empty spec.name, uppercase spec.name, or casefold-changing input (ß, ligatures)
- Files: `yahir_reusable_bot/registry/match.py`, `tests/` (no dedicated match tests visible in exploration)
- Risk: Consumer could wire a malformed spec that silently mismatches or over-matches input
- Priority: Medium — add property-based test over spec.name constraints and casefold edge cases

**Retry edge case: burst_size == 1 never triggered in tests:**
- What's not tested: `build_retrying(burst_size=1)` path to ZeroDivisionError
- Files: `yahir_reusable_bot/reliability/retry.py:141`, `tests/` (WeatherBot validator guards burst_size >= 2)
- Risk: Hub function exposed publicly; another consumer or test could bypass validator and trigger zero-divide
- Priority: Low — latent in hub but not reachable in WeatherBot; add a parameterized test with `burst_size < 2` and assert ValueError

---

*Concerns audit: 2026-07-08*
*Source: HUB-FINDINGS-HANDOFF.md (17 findings from WeatherBot v2.1 multi-agent audit)*
