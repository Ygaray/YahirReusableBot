"""Process identity + PID-file / staleness-guard primitives for the lifecycle layer.

The reusable-module generalization of the app's PID-file control primitive
(SEAM-05, D-03). Two pieces:

- :class:`LifecycleIdentity` — an immutable struct carrying the FIVE INDEPENDENT
  identity facts a bot's process has (``name``, ``pid_file``, ``runtime_dir``,
  ``console_name``, ``proc_marker``). They are deliberately NOT fused into one
  string: the ``/proc`` staleness marker comes from the bot's console-script
  argv0, which the module must NOT assume equals the pid-dir name (D-03 — a bot
  may install a console script whose name differs from its runtime dir).

- The pid/proc helpers (``write_pid_atomic`` / ``read_pid`` /
  ``is_running_process``) lifted from the app's ``pidfile.py`` and parameterized:
  the writer/reader take the path per-callsite (supplied by ``identity.pid_file``,
  no module default constant), and the ``/proc`` staleness guard takes the
  ``proc_marker`` to match — so the PID-recycling defense generalizes to ANY bot
  without naming one. The atomic-write body, re-raise posture, and the
  /proc-degrade behavior are preserved byte-identical from the analog.

stdlib ``os`` / ``tempfile`` / ``pathlib`` ONLY — zero new dependencies. The
WRITER deliberately re-raises (a startup PID-write failure must be visible); the
guard/reader degrade cleanly. Names no app concept, so the litmus over the module
stays clean.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LifecycleIdentity:
    """The five independent identity facts of a bot's long-running process.

    - ``name`` — the human/log name of the bot (e.g. for a Description line).
    - ``pid_file`` — the absolute path the daemon writes its PID to.
    - ``runtime_dir`` — the systemd ``RuntimeDirectory=`` / ``/run/<dir>`` the
      pid file lives inside.
    - ``console_name`` — the ``[project.scripts]`` console-script name (the argv0
      basename the staleness guard matches).
    - ``proc_marker`` — the NUL-separated-argv token the ``/proc`` staleness guard
      matches (argv0 basename or the ``-m`` module target); typically the bytes
      form of ``console_name`` but kept independent because the ``python -m`` form
      uses the module name, which may differ.

    Immutable: constructed once at the app's composition root and threaded into
    the lifecycle layer.
    """

    name: str
    pid_file: Path
    runtime_dir: Path
    console_name: str
    proc_marker: bytes


def write_pid_atomic(pid_file: Path | str) -> None:
    """Write ``os.getpid()`` to ``pid_file`` atomically (temp + ``os.replace``).

    A reader never observes a partial/torn PID file: the pid is written to a temp
    file in the same directory, then ``os.replace`` (atomic on POSIX) swaps it
    into place (T-09-07). On any error the temp file is unlinked and the error is
    RE-RAISED — this runs in ``run_daemon`` startup where a PID-write failure must
    be loud, not swallowed.
    """
    pid_file = Path(pid_file)
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(pid_file.parent), prefix=".wbpid-")
    try:
        os.write(fd, f"{os.getpid()}\n".encode())
        os.close(fd)
        fd = -1  # D-42 (LIFE-02): mark closed so the except-path never re-closes
        # this integer — if the OS reused it for an unrelated descriptor between
        # the two closes, a second close here would silently close THAT one, and
        # the old `except OSError: pass` would hide it entirely.
        os.replace(tmp, pid_file)  # atomic on POSIX — never a partial PID file
    except BaseException:
        # Best-effort cleanup of the temp file, then re-raise so the daemon
        # startup sees the failure. Guarded on fd != -1 (D-42): once the
        # happy-path close above has run, this branch must never re-close the
        # same fd integer. The close is ALSO wrapped in try/except OSError
        # (WR-01) so that a genuine close failure on the still-open fd — e.g. a
        # delayed ENOSPC/EIO surfacing on close, plausible on the same disk-full
        # condition that made os.write fail — cannot mask the original error or
        # skip the unlink/re-raise below (the writer's documented contract).
        if fd != -1:
            try:
                os.close(fd)
            except OSError:
                pass
        Path(tmp).unlink(missing_ok=True)
        raise


def read_pid(pid_file: Path | str) -> int:
    """Return the int PID stored in ``pid_file``.

    Raises ``FileNotFoundError`` when the file is absent and ``ValueError`` when
    its contents are not a clean integer — the established catch set the
    ``do_reload`` sender handles to report "no valid PID file" (outcome-only, no
    secrets).
    """
    text = Path(pid_file).read_text(encoding="utf-8").strip()
    return int(text)


def is_running_process(
    pid: int,
    *,
    proc_marker: bytes,
    cmdline_reader: Callable[[int], bytes] | None = None,
) -> bool:
    """Return True only if PID ``pid`` is a live process matching ``proc_marker``.

    Reads ``/proc/<pid>/cmdline`` and checks for ``proc_marker`` BEFORE the caller
    signals it, so a SIGHUP can never be delivered to a recycled/unrelated PID
    (T-09-06). Returns ``False`` when the PID is not running
    (``FileNotFoundError`` on the cmdline path). If ``/proc`` itself is absent
    (non-Linux), the guard degrades to ``True`` — the host is Linux, so this only
    affects portability, and the documented degrade signals directly.

    ``cmdline_reader`` is an injectable reader (``pid -> bytes``) used by tests to
    stub the ``/proc`` read; production passes ``None`` and reads ``/proc``.
    """
    if cmdline_reader is None:
        cmdline_reader = lambda p: _read_proc_cmdline(p, proc_marker=proc_marker)
    try:
        cmdline = cmdline_reader(pid)
    except FileNotFoundError:
        # /proc/<pid>/cmdline missing -> the PID is not running (stale/recycled).
        return False
    return _argv_matches_marker(cmdline, proc_marker=proc_marker)


def _argv_matches_marker(cmdline: bytes, *, proc_marker: bytes) -> bool:
    """Return True only when NUL-separated ``cmdline`` names the marker PROGRAM.

    The PID-recycling defense (T-09-06) must key on program identity, NOT on the
    token appearing anywhere in argv (CR-02). A raw ``proc_marker in cmdline``
    substring test wrongly accepts unrelated recycled-PID processes whose argv
    merely *mentions* the path — ``vim .../bot/config.toml``,
    ``tail -f bot.log`` — and would deliver SIGHUP (default disposition:
    terminate) to them. So match ``argv0``'s basename, and for the
    ``python -m <module>`` form match the ``-m`` module target in the next two
    fields; never the whole buffer.

    THE rule for the ``-m`` form (D-06, not a heuristic): the FIRST ``-m``
    module switch in argv wins, and its target is the module name. This handles
    BOTH shapes CPython accepts (D-20, WR-01): the space-separated
    ``-m <module>`` form (target is the next token) and the ATTACHED
    ``-m<module>`` form (target is the same token's remainder, e.g.
    ``-mexamplebot`` -> ``examplebot``; verified: ``python3 -mjson.tool`` runs
    identically to ``python3 -m json.tool``). Everything after ``-m <module>``
    belongs to the module's own argv — which is exactly what makes
    ``python -m pytest -m <marker>`` (and its attached twin
    ``python -mpytest -m <marker>``) resolve correctly: pytest's own ``-m``
    marker-selector flag is never the interpreter's, so it must never win the
    scan.

    A fixed-position check (``argv[1] == b"-m" and argv[2] == proc_marker``,
    the shape originally prescribed) is REJECTED on evidence (D-05): it fails
    on ``python -O -m <marker> run``, where the interpreter flag shifts
    ``-m`` to index 2 and a live daemon would be reported not-running.
    Scanning for the first ``-m`` tolerates any number of leading interpreter
    flags.

    ``argv[0]`` is deliberately NOT additionally required to look like a
    Python interpreter (D-07): that would close a vanishingly rare false
    positive (a non-Python program taking ``-m <marker>``) at the cost of
    breaking legitimate daemons on pypy or a custom-named interpreter — this
    library must not assume its consumer's runtime.

    REMAINING BOUNDARY (D-20, WR-01): CPython additionally accepts ``-m``
    BUNDLED into a leading short-option group — ``python -Omexamplebot`` and
    ``python -Imjson.tool`` both run. This scan matches only a token whose
    first two bytes are ``-m``, so a bundled group beginning with another flag
    (``-O``, ``-I``, ...) is NOT decoded, and a daemon launched that exotic way
    is reported not-running. This residual false negative is deliberate:
    fully reconstructing Python's short-option-bundling grammar (where ``-Om``
    is ``-O`` + ``-m`` but ``-Xmfoo`` is ``-X`` consuming ``mfoo`` as its
    argument) risks matching the wrong token and delivering SIGHUP to an
    unrelated PID — a false POSITIVE, the strictly worse failure for this
    guard. No consumer launches a daemon as ``python -Om<module>``. Requiring
    an exact ``-m`` token prefix keeps the scan false-positive-free (nothing
    but a real ``-m`` module switch begins with ``-m``) while closing the
    ordinary attached form WR-01 reported.

    Like the rest of this guard, this branch degrades to False and never
    raises: the bounds check on the token after a standalone ``-m`` (there may
    be none) is what keeps a truncated/malformed argv safe rather than an
    IndexError.

    D-39 (LIFE-03): ``proc_marker`` is basenamed on the RHS, symmetric with
    ``argv[0]``'s basenaming on the LHS one line below. This fixes two things
    with one change: (1) the non-Linux ``/proc``-absent degrade
    (``_read_proc_cmdline`` returns the RAW ``proc_marker`` as its sentinel),
    which previously broke for a path-shaped marker because the LHS was
    basenamed but the RHS was not; and (2) real Linux matching for a
    path-shaped ``proc_marker`` (e.g. ``b"/opt/thebot"``), which was equally
    broken by the same asymmetry. It is a no-op for the ordinary, already-
    basename-shaped marker (``Path("examplebot").name == "examplebot"``) and
    does NOT touch the ``-m`` module branch below — a module target is never
    path-shaped.
    """
    argv = [part for part in cmdline.split(b"\x00") if part]
    if not argv:
        return False
    prog = Path(argv[0].decode("utf-8", "replace")).name
    if prog == Path(proc_marker.decode("utf-8", "replace")).name:
        return True
    # `python -m <module> [run]` and `python -m<module> [run]`: first `-m`
    # module switch wins (D-06). A standalone `b"-m"` token takes the NEXT
    # token as its module target; an attached `b"-m<module>"` token (D-20,
    # WR-01) carries the module in its own remainder. Never continues scanning
    # past the first `-m` module switch found. A bundled `-Om…` group does not
    # begin with `-m`, so it is intentionally not decoded (see docstring).
    for i, token in enumerate(argv[1:], start=1):
        if token == b"-m":
            return i + 1 < len(argv) and argv[i + 1] == proc_marker
        if token.startswith(b"-m"):
            return token[2:] == proc_marker
    return False


def _read_proc_cmdline(pid: int, *, proc_marker: bytes) -> bytes:
    """Read ``/proc/<pid>/cmdline`` raw bytes (NUL-separated argv).

    Raises ``FileNotFoundError`` when the PID is not running. When ``/proc`` as a
    whole is absent (non-Linux), degrade by returning a sentinel that contains
    ``proc_marker`` so :func:`is_running_process` signals directly (documented
    degraded guard; host is Linux).
    """
    proc_pid = Path(f"/proc/{pid}/cmdline")
    if not Path("/proc").exists():
        return proc_marker  # /proc absent (non-Linux) -> degrade to signal
    return proc_pid.read_bytes()
