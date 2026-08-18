# Phase 8: Redaction-hardening cleanup - Research

**Researched:** 2026-08-17
**Domain:** Python static type-checking tooling (pyright) + hardening/pinning of an existing secret-redaction library surface
**Confidence:** HIGH (surface code all read directly this session; pyright tooling claims are CITED/web-confirmed, one package-registry gap independently confirmed empty on both PyPI and npm)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 [malformed-write]:** Keep the fail-closed fixed placeholder
(`yahir_reusable_bot/redact/sink.py:50-54,157-164`) and pin it as the contract with a RED-first
test, AND add an optional `on_error` hook mirroring `on_redaction` so a malformed (`re.error`)
pattern on the write path is observable rather than silently swallowed. Never fail-open (would
emit the very secret the backstop exists to catch); never raise on the hot path (honors the locked
D-52 "never raise inside logging" posture). *(source: human — 06's self-UAT flagged this for owner
Gate-2 judgment)*

**D-02 [reflection]:** Formally ACCEPT the raw-pattern-source reflection residual
(`dataclasses.asdict`/`astuple`, `.pattern.pattern` echoing a `RedactionPattern.literal(...)`
secret). Record the close-vs-accept decision, keep the rationale in `yahir_reusable_bot/redact/core.py`'s
docstring + `05-SECURITY.md` (already logged as UF-01), and pin current behavior with a RED-first
test. Do NOT introduce an opaque pattern wrapper — a breaking API-shape change to a type
WeatherBot is about to pin against immediately before the v0.2.0 repin, and `redact_secrets` needs
`.pattern.sub()` reachable. Accidental `vars`/`__dict__` paths are already closed by `slots=True`.
*(source: human)*

**D-03 [type-checker]:** Adopt pyright in `basic` mode with a first-run baseline
(baseline-and-burn-down); land the gate green now and keep the existing `get_type_hints`
assertions as the narrow enforcement for SURF-02's three signatures (retire-vs-belt-and-suspenders
decided explicitly at plan time). Not mypy; not strict/whole-surface now — the surface is
deliberately `Any`-at-seams and a fix-all would flood this bounded pre-repin cleanup phase.
*(source: human)*

**D-04 [doc-gate]:** Add two token-anchored regression tests to `tests/test_extension_guide.py` —
one pinning the "changed writes, not substitutions / monotonic" telemetry semantics, one pinning
the "call `assert_redaction_active` again after any reconfiguration" discipline — each with its own
non-vacuity self-proof (write a broken temp copy → re-run the gate → assert it fails), mirroring
the existing Known-limitations gate at `tests/test_extension_guide.py:324-403`. The only real
optionality is anchor-token selection; avoid colliding with the recipe-2 `"before any"` assertion
at `:123`. *(source: ai-auto — research recommendation; low optionality)*

### Claude's Discretion

- Anchor-token selection for the two D-04 doc-gate tests (subject to the no-collision constraint
  above).
- Whether the D-01 `on_error` hook's signature/payload mirrors `on_redaction` exactly or carries
  the offending pattern identity — decide at plan time against the existing hook shape.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. The v0.2.0 repin/deploy itself remains human-gated
and out of this phase (see ROADMAP.md close-out).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REDACT-09 | (WR-02) A `RedactionPattern` built via `literal(...)` does not leak its raw pattern source through the public reflection paths, or the residual is a documented accepted-risk with a pinning test. | § Architecture Patterns "D-02 reflection residual — already substantially shipped"; exact `core.py` docstring and existing pinning tests located and quoted below. |
| REDACT-10 | (WR-03) `RedactingWriter.write`'s malformed-pattern behavior is a deliberate, tested, documented decision (docstring + `EXTENSION-GUIDE.md` §7), plus a new `on_error` hook. | § Architecture Patterns "D-01 malformed-write hardening"; exact `sink.py` lines quoted, exact `on_redaction` hook shape quoted as the mirror template, exact gap in `EXTENSION-GUIDE.md` §7 identified. |
| DOCS-05 | (T-06-16 residual) `EXTENSION-GUIDE.md` §7's changed-writes-semantics and reconfigure-discipline claims are regression-gated with non-vacuity self-proofs. | § Architecture Patterns "D-04 doc-gate — copy pattern"; exact anchor text and exact test-file structure to copy quoted below. |
| HYG-04 | A static type checker (pyright, per D-03) is adopted as a dev dependency and standing gate, enforcing SURF-02's narrowed `on_online` (+ sibling) annotations. | § Standard Stack, § Package Legitimacy Audit, § Architecture Patterns "D-03 pyright basic + baseline workaround", § Common Pitfalls. |
</phase_requirements>

## Summary

This is a hardening/pinning phase over already-shipped code — three of the four requirements
(REDACT-09, REDACT-10, DOCS-05) touch a single existing subpackage (`yahir_reusable_bot/redact/`)
and a single existing test file (`tests/test_extension_guide.py`); the fourth (HYG-04) introduces
exactly one new dev-dependency (`pyright`) with no runtime footprint.

**The most important finding for planning:** REDACT-09/D-02's substance is **already shipped**.
`RedactionPattern.__repr__`'s docstring (`core.py:88-128`) already states the WR-02 close-vs-accept
rationale verbatim ("Explicit paths — STILL OPEN, by design... Closing it would mean wrapping the
compiled pattern in an opaque holder: a PUBLIC API shape change, deliberately out of scope here"),
`05-SECURITY.md` already logs it as `UF-01` with a full disposition, and
`tests/test_redact_core.py` already contains both pinning tests
(`test_redaction_pattern_has_no_instance_dict_so_generic_serializers_cannot_leak` and
`test_redaction_pattern_asdict_still_exposes_raw_pattern_source`, lines 236-273) — both already
GREEN against current source. The planner's job for REDACT-09 is narrower than the requirement
text implies: confirm/cross-reference this existing evidence rather than write new code, and
decide whether any formal "ACCEPTED" marker needs to land in `REQUIREMENTS.md` or a new decision
log entry (the docstring + `05-SECURITY.md` already constitute the record CONTEXT.md asked for).

REDACT-10/D-01 is a genuine two-part task: (a) the fail-closed placeholder behavior is *already*
pinned by an existing GREEN test
(`test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern`,
`tests/test_redact_sink.py:435-458`) and already fully documented in `write()`'s own docstring
(`sink.py:114-127`) — what's missing is the `EXTENSION-GUIDE.md` §7 statement (confirmed absent
from the live guide text below) and the **new** `on_error` hook, which is genuinely unbuilt and
needs a real RED-first test (the hook and its wiring do not exist yet).

DOCS-05/D-04 is copy-pattern work: `tests/test_extension_guide.py:324-403` (the Known-limitations
gate) is the exact structural template — extract-section, assert-tokens-present,
self-proof-by-mutation-and-rerun. The two target claims live in
`EXTENSION-GUIDE.md`'s "Telemetry, described accurately." and "Proving it is on." paragraphs
(quoted below), and the collision constraint at `:123` (`"before any"`) is confirmed to belong to
the *recipe-2 ordering* assertion, not either D-04 target claim.

HYG-04/D-03 requires one real piece of new tooling research, now resolved: **pyright has no
native baseline/grandfather mechanism** (confirmed against the official docs) and **no
dedicated `pyright-baseline` helper package exists** on either PyPI or npm (both confirmed 404
this session) — so "baseline-and-burn-down" must be hand-rolled as a small wrapper script that
diffs `pyright --outputjson` output against a committed baseline file. `discord.py==2.7.1` ships
its own `py.typed` marker (confirmed in the installed `.venv`) — no separate stub package is
needed, resolving the backlog doc's open sizing question #3 outright.

**Primary recommendation:** Treat REDACT-09 as a verification-and-formalize task, REDACT-10 as
"guide text + new hook," DOCS-05 as "copy the Known-limitations gate pattern twice," and HYG-04 as
"add `pyright` as a dev dep, run once, hand-roll a baseline-diff script, wire as a local gate
alongside `uv run ruff check`."

## Architectural Responsibility Map

This is a single-tier library project (no browser/frontend/CDN tiers apply — `yahir_reusable_bot`
is a pure Python library imported by consumer bots).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Malformed-pattern fail-closed placeholder (D-01) | Library / hot write path (`redact/sink.py`) | — | Runs synchronously inside every log write; must never raise or block. |
| `on_error` observability hook (D-01) | Library / hot write path (`redact/sink.py`) | — | Mirrors `on_redaction`'s existing push-hook shape, invoked from the same guarded location. |
| Reflection-residual documentation (D-02) | Library source docstring + planning artifact (`redact/core.py`, `05-SECURITY.md`) | — | A documentation/decision-record concern, not runtime behavior — already shipped. |
| Static type-check gate (D-03) | Dev tooling / local & CI-equivalent gate | Build (`pyproject.toml` dev deps) | Runs outside the shipped library; enforces the public surface's annotations at development time only. |
| Doc regression gates (D-04) | Test suite (`tests/test_extension_guide.py`) | Documentation (`EXTENSION-GUIDE.md`) | Pins prose claims about library behavior; the test suite is the enforcement tier, the guide is the content tier. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyright` | 1.1.411 [VERIFIED: pypi.org/pypi/pyright/json, fetched this session] | Static type checker (D-03 locked choice) | Microsoft's official Python type checker; ships a `basic`/`standard`/`strict` mode ladder matching D-03's exact ask; distributed on PyPI as a thin wrapper (`pyright-python`) around the canonical Node-based implementation. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `nodejs-wheel` (optional pyright extra) | n/a — install via `pyright[nodejs]` if node download proves unreliable | More reliable Node runtime provisioning for the `pyright` PyPI wrapper | Only if the default `nodeenv`-based node download fails or is undesirable in CI/dev environments; not required to start. [CITED: pypi.org/project/pyright] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyright | mypy | Explicitly rejected by D-03 (locked decision) — do not research further. |
| Hand-rolled baseline diff script | A dedicated baseline helper package | **Confirmed this session: no such package exists.** `pyright-baseline` returns 404 on both PyPI (`pypi.org/pypi/pyright-baseline/json`) and npm (`registry.npmjs.org/pyright-baseline`) [VERIFIED: direct registry queries, this session]. mypy has a native `--baseline` flag; pyright does not — this is a genuine tooling gap, not a research miss. |

**Installation:**
```bash
uv add --dev pyright
```
This adds `pyright` to the existing `[dependency-groups].dev` table in `pyproject.toml` alongside
`pytest`, `ruff`, `syrupy`, `time-machine`, `grimp` — matching the project's existing dev-tooling
convention exactly [VERIFIED: pyproject.toml:26-35, read this session].

**Version verification:** Confirmed live this session via `curl -s https://pypi.org/pypi/pyright/json`
→ `version: 1.1.411`, 206 total releases (`0.0.1` → `1.1.411`), source repo
`github.com/RobertCraigie/pyright-python` [VERIFIED: PyPI JSON API, this session]. `npm view pyright
version` independently returned `1.1.413` (the upstream Node package trails the PyPI wrapper by a
patch or two, which is normal for this two-package relationship) [VERIFIED: npm registry, this
session].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `pyright` | PyPI | ~6 yrs (first release `0.0.1`, 206 releases total, latest 2026-06-25) | unknown (legitimacy-check API returned no download figure) | `github.com/RobertCraigie/pyright-python` | SUS (reason: `unknown-downloads` only) | Flagged — planner must add `checkpoint:human-verify` before `uv add --dev pyright`, per protocol. |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `pyright` — flagged solely because the automated
legitimacy checker could not retrieve a download-count signal (pypistats.org rate-limited this
session's query, HTTP 429), not because of any adverse finding. Manual cross-check this session:
206 published releases spanning ~6 years, an active GitHub source repo, and the package is the
de-facto standard PyPI distribution channel for Microsoft's pyright (mirrors upstream npm
`pyright` releases 1:1). The `checkpoint:human-verify` gate should be a fast confirm, not a
blocker — but per protocol it must still be inserted since the automated verdict was SUS, not OK.

*No other new packages are introduced by this phase — REDACT-09/REDACT-10/DOCS-05 touch only
existing modules and test files, zero new dependencies.*

## Architecture Patterns

### D-01 malformed-write hardening — exact current code

**`yahir_reusable_bot/redact/sink.py:50-54`** — the fail-closed placeholder constant (verbatim):
```python
_MALFORMED_PATTERN_PLACEHOLDER = (
    "[yahir_reusable_bot.redact: a malformed RedactionPattern raised during "
    "redaction — original text withheld to avoid an unproven, possibly "
    "unredacted write]"
)
```
[VERIFIED: yahir_reusable_bot/redact/sink.py:50-54, read this session]

**`yahir_reusable_bot/redact/sink.py:154-164`** — the fail-closed branch (verbatim; CONTEXT.md's
cited `:157-164` is the `except` block, `:154-156` is the guarding `try`):
```python
if isinstance(data, str) and self._enabled and self._patterns:
    try:
        scrubbed = redact_secrets(data, self._patterns)
    except re.error:
        # WR-03 (see this method's own docstring, point 2a): a hand-built,
        # unregistered pattern is out of `redact_secrets`'s documented
        # contract and can raise here. Fail CLOSED — withhold the original
        # (possibly secret-bearing) payload rather than forward it
        # unredacted, and never let the exception itself reach the caller's
        # hot logging call.
        return self._target.write(_MALFORMED_PATTERN_PLACEHOLDER)
```
[VERIFIED: yahir_reusable_bot/redact/sink.py:154-164, read this session]

**Already shipped, not a gap:** this behavior is already pinned GREEN by
`tests/test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern`
(`tests/test_redact_sink.py:435-458`) and already documented in `write()`'s own docstring at
`sink.py:114-127` (the "2a. WR-03 guard" paragraph). What REDACT-10 still needs:

1. **`EXTENSION-GUIDE.md` §7 gap — confirmed absent.** The live SEAM-08 section (`EXTENSION-GUIDE.md:134-226`,
   read in full this session) documents Recipe 1, Recipe 2, `assert_redaction_active`, the optional
   processor, telemetry, and four "Known limitations" — it contains **zero mentions** of
   "malformed," "fail-closed," "placeholder," or `re.error`. This is the concrete gap CONTEXT.md's
   D-01 asks the plan to close: add a paragraph (or a fifth Known-limitations bullet) stating the
   malformed-pattern fail-closed behavior explicitly.
2. **The `on_error` hook — genuinely new code.** Does not exist anywhere in `sink.py` today
   (confirmed by reading the full file this session). Needs a real RED-first test.

**The `on_redaction` hook — exact shape to mirror**, from
`yahir_reusable_bot/redact/sink.py:66-90` (constructor) [VERIFIED: sink.py:66-90, read this
session]:
```python
def __init__(
    self,
    target: object,
    patterns: Sequence[RedactionPattern],
    *,
    enabled: bool = True,
    on_redaction: Callable[[int], None] | None = None,
) -> None:
```
and its invocation site, `sink.py:169-174` [VERIFIED: sink.py:169-174, read this session]:
```python
hook = self._on_redaction
if hook is not None:
    try:
        hook(current)
    except Exception:  # noqa: BLE001 — never break the hot write path
        pass
```
— fired **outside** the `threading.Lock` (D-59), guarded by a bare swallow-and-continue
`try`/`except Exception`. The mirrored `on_error` hook should adopt the identical shape: an
optional keyword-only `Callable[..., None] | None = None` constructor param, invoked from inside
the same `except re.error:` branch that already exists at `sink.py:157-164`, wrapped in an
identical swallow-and-continue guard so a raising/slow `on_error` callback can never break the hot
write path — mirroring exactly what `on_redaction` already does for the success path. The open
sub-decision CONTEXT.md leaves to plan time (payload shape: mirror `on_redaction`'s `int`-count
signature vs. carry the offending pattern identity) has no existing precedent to copy from inside
this module — `on_redaction` passes a plain `int` because there is a natural int (`current`) to
pass; the malformed-pattern branch has no equivalent natural scalar (there is no "count" of
malformed patterns tracked), so the planner will need to choose between a fixed sentinel payload
(e.g., no-arg call, mirroring `on_redaction`'s single-argument style loosely) or a richer payload
(e.g., the malformed `RedactionPattern` instance itself, or its `repr()`) — bearing in mind
`RedactionPattern.__repr__` is already source-eliding (`core.py:88-128`), so passing the pattern
object itself is safe against accidental logging by a naive hook.

### D-02 reflection residual — already substantially shipped

**`RedactionPattern`, exact current dataclass declaration** (`core.py:26-57`)
[VERIFIED: yahir_reusable_bot/redact/core.py:26-57, read this session]:
```python
@dataclass(frozen=True, repr=False, slots=True)
class RedactionPattern:
    pattern: re.Pattern[str]
    replacement: str
    skip_redos_check: bool = False
```

**The docstring rationale (already written, CONTEXT.md's D-02 ask is already satisfied here)** —
`core.py:100-122` (verbatim, "Scope (WR-02)" section):
```
Scope (WR-02). Two different classes of leak path, handled differently:

- **Accidental paths — CLOSED** by ``slots=True`` on this class. ``vars(rp)``
  raises ``TypeError`` and ``rp.__dict__`` raises ``AttributeError``, because a
  slotted instance has no ``__dict__``. These are the paths a GENERIC
  serializer or logging helper reaches for without intending to introspect a
  dataclass, so a consumer writing ``logger.info(..., extra=vars(rp))`` now
  gets a loud error instead of a silently-leaked secret.
- **Explicit paths — STILL OPEN, by design.** ``dataclasses.asdict(rp)`` and
  ``dataclasses.astuple(rp)`` return the RAW ``pattern`` field (the unwrapped
  ``re.Pattern``), which carries Python's own default ``repr`` and prints its
  source verbatim. This is not closable while ``pattern`` remains a public
  field holding the live compiled object ``redact_secrets`` calls ``.sub()``
  on — and it is no worse than reading ``rp.pattern.pattern``, which is equally
  public and equally deliberate. Closing it would mean wrapping the compiled
  pattern in an opaque holder: a PUBLIC API shape change, deliberately out of
  scope here.
```
[VERIFIED: yahir_reusable_bot/redact/core.py:100-122, read this session]

**Already pinned by two existing tests** (`tests/test_redact_core.py`, confirmed present and
GREEN this session) [VERIFIED: tests/test_redact_core.py:236-273 line range located via grep +
imports at :20 confirmed `asdict, astuple` imported, read this session]:
- `test_redaction_pattern_has_no_instance_dict_so_generic_serializers_cannot_leak` — pins the
  accidental-path closure (`vars`/`__dict__` raise).
- `test_redaction_pattern_asdict_still_exposes_raw_pattern_source` — pins the explicit-path
  residual (`asdict`/`astuple` still expose the sentinel).

**Already logged in `05-SECURITY.md`** as `UF-01` (row present, disposition "Residual of T-05-02a,
not a failure of its declared mitigation... Below the `high` block threshold; documented + tested
+ tripwired. **Non-blocking.**") [VERIFIED: .planning/phases/05-redaction-core-pattern-registration/05-SECURITY.md:77,
read this session].

**Planner implication:** REDACT-09 likely needs **no source-code change** at all. The plan should
verify this evidence chain (docstring + `05-SECURITY.md` + two pinning tests, all cross-checked
above) and decide only whether a *formal* "ACCEPT" marker needs to land somewhere new (e.g., a
`REQUIREMENTS.md` note, or an explicit `D-XX` decision-log entry in `STATE.md`) to satisfy
CONTEXT.md's "the close-vs-accept choice is settled in this phase" language — the substance is
already settled; what may be missing is a citation making the settlement *legible as of Phase 8*
rather than something that quietly happened during Phase 5. This is a low-risk, low-effort task
compared to what the requirement text implies.

### D-04 doc-gate — copy pattern

**Exact target claims to pin**, both from `EXTENSION-GUIDE.md`'s SEAM-08 section (§7):

1. Telemetry semantics — `EXTENSION-GUIDE.md:202-206` (verbatim) [VERIFIED:
   EXTENSION-GUIDE.md:202-206, read this session]:
   > "**Telemetry, described accurately.** `RedactingWriter.redaction_count` is readable off the
   > live writer instance, and an optional `on_redaction` push hook can be supplied at
   > construction. It counts **changed writes**, not individual substitutions, and is monotonic
   > for process lifetime — a rate is obtained by diffing two point-in-time reads, never by
   > treating it as a per-substitution total."

2. Reconfigure discipline — `EXTENSION-GUIDE.md:185-187` (verbatim) [VERIFIED:
   EXTENSION-GUIDE.md:185-187, read this session]:
   > "**Proving it is on.** `assert_redaction_active(*, deep=False)` raises rather than returns a
   > status — call it once at boot AND again after any reconfiguration, because `structlog`'s
   > configuration is global mutable state and a second `structlog.configure()` call can drop the
   > wiring with no error of its own."

**Collision check, confirmed:** the `"before any"` token CONTEXT.md instructs the plan to avoid
colliding with lives at `EXTENSION-GUIDE.md:179` (verbatim, Recipe 2's ordering constraint) —
"...this assignment must happen **before any** stdlib `logging` handler is constructed..." — and
is asserted by the EXISTING `test_seam_08_section_documents_both_recipes` test at
`tests/test_extension_guide.py:123` (`assert "before any" in section_lower`). Neither of the two
target claims above (telemetry / reconfigure-discipline) contains the literal substring
`"before any"`, so a token like `"changed writes"` / `"monotonic"` (claim 1) and
`"after any reconfiguration"` / `"structlog's configuration is global mutable state"` (claim 2) are
safe, non-colliding anchor candidates — note claim 2's own text contains `"and again after any
reconfiguration"`, which is a *different* substring from `"before any"` and does not collide with
the existing assertion's `"before any" in section_lower` check (the strings differ starting at the
5th character: `after` vs `before`).

**Exact structural template to copy** — `tests/test_extension_guide.py:324-403` (Known-limitations
gate), already fully read this session. Its shape is a 3-test group:
1. A content-assertion test (`test_seam_08_section_carries_the_known_limitations_block`,
   `:324-356`) — extracts the SEAM-08 section via the existing `_extract_seam_08_section` helper
   (`:49-73`), lowercases it, asserts a labelled heading substring is present, then asserts a set
   of "concept -> anchor tokens" all survive via a dict-comprehension `missing` check.
2. A self-proof test (`test_selfproof_limitations_gate_catches_deleted_block`, `:359-403`) — reads
   the live guide, uses `re.sub` with `re.DOTALL` to excise the target block into a `broken_content`
   string, asserts the excision actually happened (sanity check), writes `broken_content` to a
   `tempfile.NamedTemporaryFile`, monkey-patches the module-level `GUIDE_PATH` global to point at
   the temp file, re-invokes the content-assertion test function directly (not via pytest
   collection — a plain Python function call), asserts it raises `AssertionError`, and restores
   `GUIDE_PATH` + unlinks the temp file in a `finally` block.

D-04's two new tests should each be a 2-function pair following exactly this shape, targeting the
two paragraphs quoted above instead of the Known-limitations block. `_extract_seam_08_section` is
already a reusable helper — no need to duplicate its logic.

### D-03 pyright basic + baseline workaround

**`typeCheckingMode` config, CITED from pyright's own docs** (`docs/configuration.md`, fetched via
GitHub raw this session) [CITED: raw.githubusercontent.com/microsoft/pyright/main/docs/configuration.md]:
> "**typeCheckingMode** [\"off\", \"basic\", \"standard\", \"strict\"]: Specifies the default rule
> set to use... The default value for this setting is \"standard\"."

Because pyright's own default is `standard` (not `off`/`basic`), D-03's locked `basic` mode MUST
be explicitly configured — omitting `typeCheckingMode` from config would silently run `standard`
mode instead, which is stricter than what CONTEXT.md locked. This is a genuine pitfall (see below).

**Config location, CITED** (same doc):
> "Pyright settings can also be specified in a `[tool.pyright]` section of a `pyproject.toml`
> file. A `pyrightconfig.json` file always takes precedent over `pyproject.toml` if both are
> present."

Recommended config shape (consistent with the project's existing `pyproject.toml`-centric tooling
convention — `[tool.pytest.ini_options]` already lives there, no separate `pytest.ini`):
```toml
[tool.pyright]
typeCheckingMode = "basic"
pythonVersion = "3.12"
include = ["yahir_reusable_bot"]
```
`include` scoped to the library source only is a discretionary recommendation, not a locked
decision — the planner should confirm whether `tests/` should also be type-checked (pyright can
check test files too; the backlog doc's sizing decisions don't address this explicitly).

**No native baseline mechanism — confirmed both from docs and from the absence of any tooling to
paper over the gap**, CITED (same fetch):
> "No such mechanism is described in the provided documentation. There is no mention of baseline
> files, error grandfathering, or similar capabilities for managing pre-existing issues."

`--outputjson`, CITED (`docs/command-line.md`, fetched this session)
[CITED: raw.githubusercontent.com/microsoft/pyright/main/docs/command-line.md]:
> "Output results in JSON format" — includes version info, execution time, per-diagnostic entries,
> and a summary block (file count, error/warning/information counts, duration).

**Confirmed this session: no dedicated baseline-diff helper package exists** for pyright on either
registry [VERIFIED: direct registry queries this session]:
- `curl -s -o /dev/null -w "%{http_code}" https://pypi.org/pypi/pyright-baseline/json` → `404`
- `npm view pyright-baseline version` → `npm error 404 Not Found`

This directly resolves the phase description's open research question — there is no
"`--outputjson` diffing against a committed baseline" tool to install; it must be a small
hand-rolled script. **Recommended pattern** (community-standard shape, not project-specific
invention): run `uv run pyright --outputjson > /tmp/current.json`, on first adoption copy that
output to a committed `pyright-baseline.json`, then write a short wrapper (Python script or a
`Makefile`/shell target) that: (1) re-runs `pyright --outputjson`, (2) loads both the fresh output
and the committed baseline, (3) builds a comparable key per diagnostic (e.g.,
`(file, rule, message)` tuple — `line` alone is too fragile since line numbers shift on unrelated
edits), (4) fails only when the fresh run contains a diagnostic key absent from the baseline. This
mirrors mypy's `--baseline`/`mypy-baseline` ecosystem convention but must be built in-repo since no
equivalent pyright package exists.

**`discord.py==2.7.1` stub quality — resolved, no separate stubs needed.** Confirmed live against
the installed `.venv` this session [VERIFIED: `.venv/lib/python3.13/site-packages/discord/py.typed`
file exists, confirmed via `find` this session]:
```
.venv/lib/python3.13/site-packages/discord/py.typed
```
The presence of a `py.typed` marker file means `discord.py` is a natively-typed package (PEP 561)
— pyright will resolve its inline type annotations directly with zero extra stub package. This
answers the backlog doc's open sizing decision #3 outright: no `discord-stubs` /
`discord.py-stubs` research is needed.

**`Any`-at-seams precedent already exists in the codebase**, useful for keeping `basic` mode green
without new suppression comments — `yahir_reusable_bot/scheduler/engine.py:60-71`
[VERIFIED: yahir_reusable_bot/scheduler/engine.py grep this session, lines 45-77 region], where
`callback: Callable[..., Any]` is deliberately left loose with a docstring rationale (D-62) rather
than a type-checker suppression pragma. `pyright basic` mode does not, by default, flag bare `Any`
usage as an error (that is a `strict`-mode / `reportMissingParameterType`-class concern) — so this
existing pattern is very likely to pass `basic` mode unmodified; the planner should verify this
empirically on the first `pyright` run rather than assume it, since this claim about `basic`
mode's specific rule defaults is CITED from general pyright behavior, not verified against this
exact codebase's first-run output this session (that first run has not yet happened — no `pyright`
config exists in the repo today).

### Recommended Project Structure

No new files or directories are needed. Existing structure:
```
yahir_reusable_bot/redact/
├── core.py         # RedactionPattern, redact_secrets — D-02 target
├── registry.py      # register_patterns (unaffected by this phase)
├── sink.py          # RedactingWriter — D-01 target (on_error hook)
├── processor.py      # redaction_processor (unaffected)
└── verify.py         # assert_redaction_active (unaffected)
tests/
├── test_redact_core.py     # D-02's existing pinning tests already live here
├── test_redact_sink.py     # D-01's new on_error RED-first test lands here
└── test_extension_guide.py # D-04's two new tests + REDACT-10's guide-gap land here
pyproject.toml               # D-03: [tool.pyright] table + dev dep addition
```

### Anti-Patterns to Avoid

- **Re-litigating D-02 with a new wrapper type:** CONTEXT.md explicitly forbids introducing an
  opaque pattern wrapper — `redact_secrets` needs `.pattern.sub()` reachable and WeatherBot is
  about to pin against the current shape. Do not propose this even as a "better" fix.
- **Letting `typeCheckingMode` default to `standard`:** pyright's own default is `standard`, not
  `basic` — an omitted `typeCheckingMode` key silently ships a stricter gate than D-03 locked.
  Always set it explicitly.
- **Keying a baseline diff on line numbers alone:** line numbers drift on unrelated edits,
  producing false "new error" noise on every baseline diff. Key on `(file, rule, message)` or
  similar semantically-stable tuple.
- **Building a new RED test for the malformed-placeholder behavior itself:** it is already GREEN
  and pinned (`tests/test_redact_sink.py:435-458`). Only the new `on_error` hook needs a genuine
  RED-first test.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Static type checking | A custom AST-based annotation checker | `pyright` (D-03 locked) | Mature, actively maintained, official Microsoft tool; reinventing this is out of scope for a bounded cleanup phase. |
| Baseline diffing | — (no existing package to reach for; this genuinely must be hand-rolled) | A small in-repo script (<50 lines) comparing `--outputjson` diagnostic sets | Confirmed this session: no `pyright-baseline` package exists on PyPI or npm. This is the one place in this phase where hand-rolling is correct, not an anti-pattern — there is nothing more do wrong to reach for. |

**Key insight:** Everything else in this phase is either already-shipped code needing
verification/documentation, or a straightforward copy of an existing in-repo test pattern. The
only place genuine new engineering judgment is required is the `on_error` hook's payload shape
(explicitly left to plan time by CONTEXT.md) and the baseline-diff script's key design.

## Common Pitfalls

### Pitfall 1: Assuming REDACT-09/D-02 needs new source code
**What goes wrong:** A plan writes a new pinning test or docstring edit for D-02, duplicating
work that's already GREEN and already documented.
**Why it happens:** The requirement text ("Either those paths are closed, or the residual is a
documented accepted-risk... with a test pinning the current behavior") reads as an open task; it
was actually closed during Phase 5, before Phase 8 existed as a concept.
**How to avoid:** Read `core.py:100-122`, `05-SECURITY.md`'s `UF-01` row, and
`tests/test_redact_core.py:236-273` before scoping any REDACT-09 task — confirm what's missing
(likely just a cross-reference / formal marker) rather than assuming a blank slate.
**Warning signs:** A plan task titled "write RED test for asdict leak" — this test already exists
and is already GREEN.

### Pitfall 2: `typeCheckingMode` omission silently changing strictness
**What goes wrong:** `pyright` is added without an explicit `[tool.pyright]` table, or with a
table that omits `typeCheckingMode` — pyright then runs its own default (`standard`), which is
stricter than D-03's locked `basic` and will surface far more first-run findings than expected,
inflating the baseline file and possibly flooding the "bounded pre-repin cleanup phase" the
backlog doc explicitly warned against.
**Why it happens:** Easy to assume "no config = off" or "no config = lenient"; pyright's actual
default is the opposite.
**How to avoid:** Always set `typeCheckingMode = "basic"` explicitly in `[tool.pyright]`.
**Warning signs:** First-run `pyright` output flags far more than the codebase's `Any`-at-seams
architecture would suggest under `basic` mode.

### Pitfall 3: `on_error` hook breaking the "never raise on the hot path" contract
**What goes wrong:** The new `on_error` hook is wired without the same swallow-and-continue guard
`on_redaction` uses, so a raising/slow `on_error` callback propagates out of `write()` — violating
the D-52 "never raise inside logging" posture CONTEXT.md explicitly calls out as non-negotiable.
**Why it happens:** Easy to copy the hook's *signature* without copying its *invocation guard*.
**How to avoid:** Mirror `sink.py:169-174`'s exact `try: hook(...) except Exception: pass` shape
for the new hook, inside the existing `except re.error:` branch.
**Warning signs:** A test that supplies a raising `on_error` callback and asserts `write()` still
returns normally is the correct regression guard — if that test doesn't exist, the guard is
probably missing.

### Pitfall 4: Baseline-diff script keyed too loosely or too tightly
**What goes wrong:** Keying only on `file` lets genuinely new errors in an already-flagged file
slip through unnoticed (too loose); keying on the full diagnostic including line number makes
every unrelated edit above a flagged line look like "many new errors, many resolved errors" noise
(too tight).
**Why it happens:** No off-the-shelf tool exists to copy this decision from (confirmed above).
**How to avoid:** Key on `(file_path, rule, message)` — stable across line-number drift, specific
enough to distinguish genuinely different diagnostics.
**Warning signs:** The baseline diff script reports large baseline drift after a purely
line-shifting refactor (e.g., adding an unrelated import).

## Code Examples

### Existing `on_redaction` hook wiring (the mirror template for `on_error`)
```python
# Source: yahir_reusable_bot/redact/sink.py:66-90, 169-174 (read this session)
def __init__(
    self,
    target: object,
    patterns: Sequence[RedactionPattern],
    *,
    enabled: bool = True,
    on_redaction: Callable[[int], None] | None = None,
) -> None:
    ...
    self._on_redaction = on_redaction
    ...

# invocation, inside write(), AFTER the lock-guarded increment:
hook = self._on_redaction
if hook is not None:
    try:
        hook(current)
    except Exception:  # noqa: BLE001 — never break the hot write path
        pass
```

### Existing malformed-pattern RED-shape test (template for structuring the on_error test)
```python
# Source: tests/test_redact_sink.py:435-458 (read this session) — GREEN today, already pins
# the placeholder behavior; the on_error test should follow this same
# "hand-build a malformed RedactionPattern, write through it, assert on outcome" shape.
def test_write_never_raises_and_never_leaks_on_a_malformed_hand_built_pattern():
    malformed = RedactionPattern(pattern=re.compile(r"(a)"), replacement=r"\2")
    capture = _CaptureDouble()
    writer = RedactingWriter(capture, (malformed,))

    result = writer.write(f"a secret appid={SENTINEL} a")  # must not raise

    assert isinstance(result, int)
    assert capture.pieces
    forwarded = capture.pieces[0]
    assert f"appid={SENTINEL}" not in forwarded
    assert SENTINEL not in forwarded
```

### Existing `on_redaction` hook test (template for the new on_error hook's regression test)
```python
# Source: tests/test_redact_sink.py:405-432 (read this session)
def test_on_redaction_hook_receives_count_and_cannot_break_logging():
    seen: list[int] = []
    capture = _CaptureDouble()
    writer = RedactingWriter(
        capture, (RedactionPattern.literal(SENTINEL),), on_redaction=seen.append
    )
    writer.write(f"{SENTINEL} one")
    writer.write(f"{SENTINEL} two")
    assert seen == [1, 2]

    def _boom(count: int) -> None:
        raise RuntimeError("hook exploded")

    capture_raising = _CaptureDouble()
    writer_raising = RedactingWriter(
        capture_raising, (RedactionPattern.literal(SENTINEL),), on_redaction=_boom
    )
    writer_raising.write(f"{SENTINEL} three")  # must not raise
    assert SENTINEL not in capture_raising.all_output
    assert writer_raising.redaction_count == 1
```

### D-04 self-proof structural pattern (from the Known-limitations gate)
```python
# Source: tests/test_extension_guide.py:359-403 (read this session) — the exact shape to
# copy for each of D-04's two new self-proof tests, swapping the excision regex and the
# content-assertion function under test.
def test_selfproof_limitations_gate_catches_deleted_block():
    content = GUIDE_PATH.read_text(encoding="utf-8")
    broken_content = re.sub(
        r"\*\*Known limitations\.\*\*.*?(?=\*\*Implemented:\*\*)",
        "",
        content,
        flags=re.DOTALL,
    )
    assert "Known limitations" not in broken_content, (
        "Self-proof setup failed: the limitations block was not actually removed"
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(broken_content)
        tmp_path = Path(tmp.name)
    try:
        original_path = globals()["GUIDE_PATH"]
        globals()["GUIDE_PATH"] = tmp_path
        try:
            test_seam_08_section_carries_the_known_limitations_block()
            assert False, "Self-proof FAILED: ... gate is vacuous"
        except AssertionError as e:
            if "vacuous" in str(e):
                raise
            pass
    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `typing.get_type_hints` runtime assertions as the sole enforcement (SURF-02, Phase 7) | Standing static type-check gate (`pyright basic`) alongside the runtime assertions | This phase (HYG-04, D-03) | Broader, dev-time enforcement of the whole public surface's annotations, not just the three SURF-02 signatures; the `get_type_hints` tests remain as belt-and-suspenders (retire-vs-keep decided at plan time). |

**Deprecated/outdated:** None — no library in this phase's scope is being deprecated or replaced;
this is purely additive tooling plus documentation/test hardening.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `pyright basic` mode does not flag the codebase's existing deliberate `Any`-at-seams pattern (e.g. `scheduler/engine.py`'s `callback: Callable[..., Any]`) as an error by default. | § Architecture Patterns, D-03 | If wrong, the first-run baseline will be larger than expected and may need per-site suppression comments in addition to the baseline file — still solvable, but changes the sizing of the HYG-04 task. Low risk: this is standard, well-documented pyright behavior (bare `Any` is not flagged in `basic` mode; only `strict` mode's `reportMissingTypeArgument`-class rules react to it), but was not verified against a live first-run of `pyright` on this exact codebase this session. |
| A2 | `include = ["yahir_reusable_bot"]` (excluding `tests/`) is the intended scope for the pyright gate. | § Architecture Patterns, D-03 | If the intended scope is the whole repo including `tests/`, the baseline will need to cover test-file diagnostics too (likely more numerous, given test doubles / monkeypatching patterns). This was Claude's Discretion territory in the backlog doc, not explicitly locked by CONTEXT.md — flag for plan-time confirmation. |
| A3 | The `on_error` hook's constructor parameter should be keyword-only, defaulting to `None`, exactly mirroring `on_redaction`'s shape (`Callable[..., None] \| None = None`), even though CONTEXT.md leaves the *payload* shape open. | § Architecture Patterns, D-01 | If a positional or differently-typed parameter is expected instead, the public constructor signature (and any pyright-gate baseline capturing it) would need rework. Low risk — CONTEXT.md explicitly says the hook should "mirror `on_redaction`'s shape/registration path," and the constructor-parameter mechanics (keyword-only, defaulted, optional) are the "shape" half of that instruction; only the payload is left open. |

**If this table is empty:** N/A — three low-risk assumptions logged above; none blocks planning,
all are flagged for explicit plan-time confirmation per CONTEXT.md's own "decide at plan time"
language.

## Open Questions

1. **Does REDACT-09 need any new artifact at all, or is cross-referencing existing evidence
   sufficient?**
   - What we know: the docstring, the `05-SECURITY.md` `UF-01` entry, and both pinning tests all
     already exist and are already GREEN (all read/confirmed this session).
   - What's unclear: whether CONTEXT.md's "the close-vs-accept choice is settled in this phase"
     language requires a *new* artifact (e.g., a fresh `D-XX` STATE.md decision entry dated Phase
     8) purely for Phase-8-local traceability, or whether pointing at the Phase-5 evidence chain
     satisfies the requirement as written.
   - Recommendation: plan a lightweight task — a short verification pass plus (if the planner
     judges it necessary for audit legibility) one new `STATE.md` decision-log line dated Phase 8
     that explicitly says "REDACT-09 verified already-closed via Phase 5 evidence, no new code" —
     cheap either way, and avoids duplicate test-writing.

2. **`pyright` gate scope: source-only or source+tests?**
   - What we know: no CI YAML exists in this repo (confirmed by search this session) — all gates
     (`pytest`, `ruff check`, `test_import_hygiene.py`) are run locally/manually via `uv run`.
   - What's unclear: whether the pyright gate should type-check `tests/` too, given the existing
     `typing.get_type_hints` assertions already live in test files and use dynamic-eval patterns
     (`localns=` overrides) that a type checker may itself flag.
   - Recommendation: start with `include = ["yahir_reusable_bot"]` (source-only) for the initial
     baseline to keep first-run scope bounded, matching the backlog doc's own warning against
     flooding this bounded cleanup phase; note test-file coverage as a natural follow-up, not a
     Phase-8 blocker.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Installing `pyright` as a dev dep | Yes | 0.11.19 [VERIFIED: `uv --version`, this session] | — |
| Node.js (via `pyright`'s own bundling) | Running `pyright` itself | Not directly checked — `pyright`'s PyPI wrapper self-provisions Node via `nodeenv` on first run if Node is absent [CITED: pypi.org/project/pyright] | — | The `nodejs` extra (`pyright[nodejs]`) provides a more reliable pinned Node runtime if the default `nodeenv` download proves unreliable in this environment. |
| Network access to PyPI/npm registries | `uv add --dev pyright`, first `pyright` run (Node download) | Confirmed working this session (multiple successful `curl`/`npm view` calls to pypi.org and registry.npmjs.org) | — | — |

**Missing dependencies with no fallback:** none identified.
**Missing dependencies with fallback:** Node.js runtime for `pyright` — self-provisioning fallback
already built into the `pyright` PyPI package; no action needed unless it fails at plan/execute
time.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (`pytest>=9.0.3`) [VERIFIED: pyproject.toml:30] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`pyproject.toml:37-48`) — `testpaths = ["tests"]`, `filterwarnings = ["error"]` [VERIFIED: pyproject.toml:37-48, read this session] |
| Quick run command | `uv run pytest -q tests/test_redact_sink.py tests/test_redact_core.py tests/test_extension_guide.py` |
| Full suite command | `uv run pytest -q` (per `.planning/config.json` `workflow.test_command`) [VERIFIED: .planning/config.json:13] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| REDACT-09 | `RedactionPattern.literal(...)`'s raw source stays inaccessible via accidental paths; `asdict`/`astuple` residual is documented+pinned | unit | `uv run pytest tests/test_redact_core.py -k "leak or asdict" -x` | Yes — both tests already exist (`tests/test_redact_core.py:236-273`) |
| REDACT-10 | `RedactingWriter.write` fails closed on `re.error`; new `on_error` hook fires observably without raising | unit | `uv run pytest tests/test_redact_sink.py -k "malformed or on_error" -x` | Placeholder test exists (`:435-458`); `on_error` test does NOT exist yet — Wave 0 gap |
| DOCS-05 | Telemetry semantics + reconfigure-discipline claims are regression-gated with non-vacuity self-proofs | unit (doc-content) | `uv run pytest tests/test_extension_guide.py -x` | The two NEW tests do NOT exist yet — Wave 0 gap; existing file/pattern to extend confirmed present |
| HYG-04 | `pyright basic` mode gate lands green (baseline-and-burn-down) | static-analysis (not pytest) | `uv run pyright` (after `uv add --dev pyright` + `[tool.pyright]` config) | Tool not yet installed, config not yet written — Wave 0 gap |

### Sampling Rate

- **Per task commit:** targeted `uv run pytest tests/test_redact_sink.py tests/test_redact_core.py
  tests/test_extension_guide.py -q` (or the single touched file) plus `uv run pyright` once the
  gate is wired.
- **Per wave merge:** `uv run pytest -q` (full suite, `filterwarnings = ["error"]` means zero
  warnings tolerated) + `uv run ruff check` + `uv run pytest tests/test_import_hygiene.py -q`.
- **Phase gate:** Full suite green, `pyright` gate green (post-baseline), before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] New `on_error` hook — does not exist in `sink.py` today; needs a RED-first test in
      `tests/test_redact_sink.py` before implementation (REDACT-10).
- [ ] Two new tests in `tests/test_extension_guide.py` (telemetry-semantics gate,
      reconfigure-discipline gate) — do not exist yet (DOCS-05).
- [ ] `EXTENSION-GUIDE.md` §7 malformed-pattern paragraph — does not exist yet (REDACT-10).
- [ ] `pyright` dev-dependency + `[tool.pyright]` config table + first-run baseline file — none of
      this exists in the repo today (HYG-04).

*(REDACT-09 has no Wave 0 gap — its test coverage already exists.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Out of scope — this phase touches no auth surface. |
| V3 Session Management | No | Out of scope. |
| V4 Access Control | No | Out of scope. |
| V5 Input Validation | Yes | `redact_secrets`'s documented `str -> str` contract (`core.py:144-160`) and `RedactingWriter.write`'s non-`str`/`bytes` triage (`sink.py:96-131`) are the existing input-boundary controls this phase hardens observability around — no new input-validation surface is introduced. |
| V6 Cryptography | No | Not applicable — redaction is pattern-matching/masking, not cryptographic protection. |
| V7 Error Handling and Logging | Yes | This entire phase is precisely an error-handling/logging hardening exercise: D-01's fail-closed-on-malformed-pattern behavior and its new observability hook are textbook V7 concerns (never leak sensitive data via an error path; make failure states observable to operators without leaking the underlying secret). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Secret leakage via a library object's default `repr()`/serialization (already the subject of T-05-02a/UF-01) | Information Disclosure | Source-eliding `__repr__` (`core.py:88-128`) + `slots=True`; the D-02-accepted residual (`asdict`/`astuple`) is a deliberate, documented, tested exception — not a new finding, already logged in `05-SECURITY.md`. |
| Fail-open on a malformed regex, emitting the very secret the backstop exists to catch | Tampering / Information Disclosure | D-01's fail-closed placeholder (`sink.py:157-164`) — already implemented and pinned; this phase only adds *observability* (the `on_error` hook), it does not change the fail-closed behavior itself. |
| A raising/slow hook callback breaking the hot logging path (turning an observability feature into an availability bug) | Denial of Service | The existing `on_redaction` swallow-and-continue guard (`sink.py:169-174`) is the proven mitigation pattern; the new `on_error` hook MUST copy this guard exactly (see Pitfall 3 above). |
| A static-analysis gate silently running stricter than intended, generating noise that trains developers to ignore its output | (not STRIDE — a process/tooling risk) | Explicit `typeCheckingMode = "basic"` in `[tool.pyright]` (see Pitfall 2); never rely on pyright's own default. |

## Sources

### Primary (HIGH confidence)
- `yahir_reusable_bot/redact/sink.py` — read in full this session (263 lines)
- `yahir_reusable_bot/redact/core.py` — read in full this session (176 lines)
- `yahir_reusable_bot/redact/__init__.py` — read in full this session
- `yahir_reusable_bot/scheduler/engine.py` — grepped/read region 45-100 this session
- `tests/test_extension_guide.py` — read in full this session (404 lines)
- `tests/test_redact_sink.py` — read region 390-497 this session; grepped for hook/malformed references across the full file
- `tests/test_redact_core.py` — grepped for asdict/astuple/leak references; imports confirmed
- `tests/test_ready_gate.py`, `tests/test_panelkit.py` — read the SURF-02 `get_type_hints` regions (195-230, 183-217) this session
- `EXTENSION-GUIDE.md` §7 (SEAM-08 section) — read in full this session (lines 134-236)
- `.planning/phases/05-redaction-core-pattern-registration/05-SECURITY.md` — read in full this session
- `.planning/backlog/ADOPT-STATIC-TYPE-CHECKER.md` — read in full this session
- `.planning/v0.2.0-MILESTONE-AUDIT.md` — grepped for WR-02/WR-03 findings
- `.planning/phases/08-redaction-hardening-cleanup/08-CONTEXT.md` — read in full
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/config.json`, `pyproject.toml` — read in full
- PyPI JSON API (`pypi.org/pypi/pyright/json`) — queried live this session, version 1.1.411 confirmed
- Direct registry 404 checks for `pyright-baseline` on both PyPI and npm — queried live this session
- `.venv/lib/python3.13/site-packages/discord/py.typed` — file existence confirmed via `find` this session

### Secondary (MEDIUM confidence)
- `raw.githubusercontent.com/microsoft/pyright/main/docs/configuration.md` — fetched this session via WebFetch, official pyright documentation
- `raw.githubusercontent.com/microsoft/pyright/main/docs/command-line.md` — fetched this session via WebFetch, official pyright documentation
- `pypi.org/project/pyright/` — fetched this session via WebFetch, official PyPI project page

### Tertiary (LOW confidence)
- None — WebSearch tool was unavailable this session (permission denied); all web-sourced claims
  above were obtained via direct WebFetch against official/authoritative sources instead, so no
  tertiary/unverified web claims are included in this document.

## Metadata

**Confidence breakdown:**
- Standard stack (pyright adoption mechanics): HIGH — version, registry existence, config
  location, and default mode all independently confirmed against official docs/registries this
  session.
- Architecture (existing redact/ code, existing test patterns): HIGH — every cited file was read
  directly this session; no claim about existing code shape is based on training memory.
- Pitfalls: HIGH for Pitfalls 1-3 (directly derived from source read this session); MEDIUM for
  Pitfall 4 (general baseline-diffing best practice, not project-specific verification).

**Research date:** 2026-08-17
**Valid until:** 30 days (stable, low-churn domain — pyright's config surface and this repo's
existing redact/ code are both unlikely to shift meaningfully in that window)
