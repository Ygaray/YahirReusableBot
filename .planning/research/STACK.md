# Stack Research

**Domain:** Generic log secret-redaction backstop (PC-01 promotion) for a channel-agnostic bot library
**Researched:** 2026-07-29
**Confidence:** HIGH (structlog API + versions verified against this repo's installed venv and `uv.lock`; LOW/MEDIUM only for the two prior-art libraries surveyed and explicitly rejected)

## Verdict: Zero new dependencies

`structlog` (already pinned, `>=26.1.0`, resolved to **26.1.0** in `uv.lock`) plus the stdlib `re`
module fully cover PC-01. **Do not add any dependency for this feature.** The whole shape of the
work — a pure-function regex substitution core plus a thin sink/processor insertion seam — is
exactly what WeatherBot's proven app-local `_redact.py` (28 lines, zero deps) already does; the
promotion is a generalization of that file, not a new capability class that needs new tooling.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `structlog` | 26.1.0 (already a dep, pinned `>=26.1.0`) | Processor chain + `PrintLoggerFactory` sink — the two documented insertion seams for the backstop | Already the hub's sole logging library; the redaction hook is a matter of *where* in the existing chain you call `redact_secrets`, not a new logging system |
| stdlib `re` | bundled with CPython 3.12/3.13 | Pattern compilation + substitution core (`redact_secrets(text, patterns) -> text`) | This is a bounded-scope string substitution problem — exactly `re`'s job. No parsing, no NLP, no PII classification needed; a compiled pattern + `.sub()` is the entire mechanism WeatherBot already ships in production |

### Supporting Libraries

None. There is no supporting-library gap here — no third-party regex engine, no config/schema
library for "pattern registration" (a plain `Iterable[re.Pattern[str]]` parameter is the API, per
WeatherBot's proven shape), no serialization helper.

### Development Tools

No additions to the dev group either. Existing `pytest` covers the RED-first regression tests
this milestone requires; `grimp` + the litmus AST checks already gate "no domain noun leaks into
the hub surface," which is the only hygiene concern PC-01 introduces (consumer-specific patterns
must never be hardcoded in hub code — see PITFALLS).

## Installation

```bash
# Nothing to install. structlog is already present:
uv pip show structlog
# Name: structlog
# Version: 26.1.0
# Location: .../YahirReusableBot/.venv/lib/python3.13/site-packages
```

## What a new dependency would buy — and why it isn't worth it

Two real libraries exist for this problem space; both were checked and both are rejected:

**`scrubadub`** (latest 2.0.1) — a PII-scrubbing toolkit, not a secret-redaction one. Its mandatory
dependency set is `catalogue`, `dateparser`, `faker`, `phonenumbers`, `python-stdnum`,
`scikit-learn`, `textblob`, `typing-extensions` — an ML/NLP stack pulled in to detect names, phone
numbers, and addresses in prose. PC-01 needs to scrub a handful of *consumer-registered, known-shape*
tokens (API keys, tokens) out of structured log fields and formatted tracebacks — a problem
`scrubadub`'s statistical detectors are the wrong tool for, and the dependency weight (scikit-learn
alone) is wildly disproportionate for a library whose entire value proposition is a small,
audit-hygiene-proven core. Rejected outright.

**`loggingredactor`** (latest 0.0.7, released 2026-06-30) — closer in shape: a `mask_patterns`
(iterable of compiled `re.Pattern`) + `mask_keys` (dict-key redaction) API, with a
`CommonPIIRedactingFilter` convenience preset. This is useful **prior art for the API shape**
(confirms "iterable of pre-compiled patterns" as the right registration contract — see below) but
it is a young, low-adoption package (0.0.x versions, narrow install base) whose entire
functionality — compile patterns once, `.sub()` them over rendered text — is what `_redact.py`
already implements in 4 lines. Taking an external dependency to save ~15 lines of stdlib `re` code,
in a library whose litmus test is minimal generic surface, is not a good trade. Rejected — used
only as a confirmation that the planned API shape (pattern list, not config-file/DSL) matches
ecosystem convention.

**Conclusion:** neither library buys anything `structlog` + `re` don't already provide for this
scope. If PC-01 ever needed statistical PII detection (names, addresses, free-text scanning) that
verdict would flip toward `scrubadub`-style tooling — but that is explicitly out of scope per
`PROMOTION-CANDIDATES.md` ("only the *pattern* is consumer-specific... hub owns the mechanism").

## structlog 26.1.0 — verified API surfaces

Verified directly against the installed package in this repo's venv (`uv run python3 -c
"import structlog; ..."`), not recalled:

### (a) Processors — the event-dict insertion seam

- Signature: `processor(logger, method_name, event_dict) -> event_dict` (or raises
  `structlog.DropEvent`). `event_dict` is a plain mutable `dict`; a redaction processor mutates
  string values in place before returning it.
- **Ordering matters for tracebacks.** `structlog.processors.format_exc_info` /
  `ExceptionRenderer` / `dict_tracebacks` turn `exc_info` into rendered text (or a structured
  dict) partway through the chain. A redaction processor must run **after** those — and as late
  as possible, immediately before the renderer (`ConsoleRenderer`/`JSONRenderer`/`KeyValueRenderer`)
  — so it sees the fully-formed `exception`/`event` string fields rather than a raw `exc_info`
  tuple it can't regex against.
- No built-in censoring/redaction processor exists in `structlog.processors` at this version (full
  attribute list checked: `JSONRenderer`, `KeyValueRenderer`, `LogfmtRenderer`,
  `ExceptionRenderer`, `ExceptionPrettyPrinter`, `format_exc_info`, `dict_tracebacks`,
  `CallsiteParameterAdder`, `TimeStamper`, `UnicodeDecoder`/`UnicodeEncoder`, `add_log_level`,
  `StackInfoRenderer` — nothing redaction-shaped). Confirms the hub has to supply this processor
  itself; there's no "just import structlog's version" shortcut.

### (b) `PrintLoggerFactory` / sink file target — the choke-point seam

- `PrintLoggerFactory.__init__(self, file: TextIO | None = None)` — verified signature.
- `PrintLogger.__init__(self, file: TextIO | None = None)` — same shape; `file=None` defaults to
  `sys.stdout`.
- The factory's `file` target is duck-typed: it only needs `.write()` (and `.flush()` for
  parity). This is exactly the seam WeatherBot's `_LiveStderr` proxy exploits — wrap whatever
  stream object is passed with a proxy whose `.write()` calls `redact_secrets(data, patterns)`
  before forwarding to the real stream. This wrapper is renderer-agnostic: it sees the final
  rendered line (event + traceback in one `write()` call per WeatherBot's own comment), so it
  catches secrets regardless of which renderer/processor chain produced them — the strongest
  "belt-and-suspenders" backstop of the two seams, and the one WeatherBot actually shipped.
- **No relevant deprecations.** `structlog.threadlocal` is deprecated (since 22.1.0, superseded by
  `contextvars`) but is unrelated to this work. 26.1.0's changelog deprecates `better-exceptions`
  support — also unrelated. `PrintLoggerFactory`/`PrintLogger` and the processor contract are
  stable, current APIs.

**Recommendation:** promote the hub module to offer **both** seams as documented options (matching
`PROMOTION-CANDIDATES.md`'s "and/or"), but treat the sink-wrapper (`PrintLoggerFactory(file=...)`
proxy) as the primary/proven pattern since it's the one already battle-tested in WeatherBot
production, with the processor as a secondary insertion point for consumers who configure a
different logger factory (e.g. `WriteLoggerFactory`, or piping through a non-file sink).

## `re` module considerations for the redaction core

- **Compile once, reuse the `Pattern` object.** `redact_secrets(text, patterns)` should take
  `patterns: Iterable[re.Pattern[str]]` — already-compiled objects, registered once by the
  consumer at wiring time (exactly WeatherBot's `_APPID_RX = re.compile(...)` module-level
  constant, and exactly `loggingredactor`'s `mask_patterns` contract). Do **not** accept raw
  pattern strings and compile per-call: CPython's `re` module does cache the last ~512
  dynamically-compiled patterns behind `re.sub`/`re.match` convenience calls, but that cache is
  process-global and shared with every other regex in the host application — relying on it for a
  security-relevant hot path is fragile. Mandating pre-compiled `Pattern` objects in the public
  API sidesteps the question entirely and matches the one data point of prior art surveyed.
- **Named groups over positional backreferences for consumer-authored patterns.** WeatherBot's
  `_APPID_RX` uses a positional capture (`(appid=)[^&\s"'<>\\]+` + replacement `r"\1***"`). That
  works for a single hardcoded pattern but is fragile once the hub accepts *arbitrary* consumer
  patterns: if a consumer's own regex adds or reorders capture groups, a hardcoded `\1` becomes
  wrong silently. Recommend the hub's pattern-authoring convention use a **named** group
  (e.g. `(?P<keep>appid=)[^&\s"'<>\\]+`) so the redaction core can look up `match.group("keep")`
  by name regardless of what else the pattern captures — self-documenting and reorder-safe.
- **`re.sub` with a callable `repl`.** `Pattern.sub(repl, text)` accepts a callable that receives
  the `Match` object and returns the replacement string. This is the escape hatch for consumers
  who want something other than "keep group, mask the rest" — e.g. preserving the trailing 4
  characters of a token for support/debugging (`"***1234"`), or a fixed-width mask regardless of
  secret length. No dependency is needed for this; it's a stdlib capability the API should simply
  not foreclose (i.e., let a consumer supply a callable replacement alongside — or instead of — the
  named-group convention, rather than hardcoding `"***"` as the only possible output).
- **Performance is a non-concern at this scale.** A compiled `Pattern.sub()` call over a single
  rendered log line is a thin C loop; there is no case here where a caching library or a compiled-
  regex-pool package would measurably help. This reinforces the "compile once at registration,
  call many times" contract above as sufficient.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| stdlib `re` + `structlog` (zero new deps) | `scrubadub` | Only if the hub ever needs *statistical* PII detection (names, addresses, free-text NLP scanning) rather than known-shape secret patterns — not this milestone's scope |
| stdlib `re` + `structlog` (zero new deps) | `loggingredactor` | Only if the hub wanted an off-the-shelf `mask_keys`-style dict-key redaction alongside regex patterns and was willing to take an external, low-adoption (0.0.x) dependency to save writing ~15 lines — not a good trade for this repo's litmus |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| `scrubadub` (or any NLP/PII-detection library) | Pulls in `scikit-learn`, `faker`, `dateparser`, `textblob` — an ML stack for a problem that's actually "substitute known-shape tokens," wildly disproportionate to this repo's small-core value prop | `redact_secrets(text, patterns)` — a stdlib `re` function, consumer-supplied patterns |
| `loggingredactor` or any third-party log-scrubbing package | Young (0.0.x), low-adoption; its entire functionality is a `re.compile` + `.sub()` loop this repo can own directly without an external import-hygiene surface to audit | Promote WeatherBot's proven `_redact.py` pattern generalized to accept an `Iterable[re.Pattern[str]]` |
| Compiling patterns from raw strings inside the hot path (per-call `re.compile`) | Relies on the process-global `re` internal cache instead of an explicit contract; fragile under a shared host app with many other regexes | Accept only pre-compiled `re.Pattern[str]` objects in the public API, compiled once by the consumer at wiring time |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|------------------|-------|
| `structlog==26.1.0` | Python 3.12/3.13 (`requires-python >=3.12`) | No version bump needed; `>=26.1.0` pin in `pyproject.toml` already covers this. Installed venv here runs Python 3.13, well within range. |
| stdlib `re` | Python 3.12/3.13 | Bundled; `re.Pattern[str]` generic subscript syntax used in type hints requires Python 3.9+ typing support, already satisfied by `requires-python >=3.12` |

## Sources

- This repo's `uv.lock` (`structlog` pinned/resolved to `26.1.0`) — HIGH confidence, direct file read
- `uv pip show structlog` in this repo's venv — HIGH confidence, direct environment verification
- `uv run python3 -c "import structlog; ..."` introspection of `PrintLoggerFactory.__init__`,
  `PrintLogger.__init__`, and `structlog.processors` module attributes — HIGH confidence, direct
  runtime verification against the installed 26.1.0 package
- `/home/yahir/Projects/WeatherBot/weatherbot/_redact.py` and `weatherbot/__init__.py`
  (`_LiveStderr` proxy + `structlog.configure(...)` wiring) — HIGH confidence, proven production
  code being promoted
- structlog stable API reference (`structlog.org/en/stable/api.html`) — MEDIUM confidence
  (WebFetch digest), used to cross-check processor signature and confirm no built-in
  redaction/censoring processor exists
- `scrubadub` PyPI/ecosystem search — LOW confidence (WebSearch digest), sufficient only to
  confirm its dependency footprint and reject it
- `loggingredactor` PyPI digest — LOW confidence (WebFetch digest), used only as a data point for
  API-shape prior art (`mask_patterns`/`mask_keys` convention), not adopted

---
*Stack research for: generic log secret-redaction backstop (PC-01 promotion)*
*Researched: 2026-07-29*
