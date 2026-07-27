"""Regression tests for LIFE-01 (H01): ``_argv_matches_marker`` tests ``-m``
and the marker by membership in two OVERLAPPING slices
(``b"-m" in argv[1:3] and proc_marker in argv[1:4]``), which asks "are both
tokens present somewhere in this window" instead of "is the marker the
module target". That accepts a recycled PID running the marker as a
POSITIONAL argument — and the caller signals what it accepts by sending a
SIGHUP (default disposition: terminate) to whatever PID this guard says is
running.

Self-proof note (D-11, matching ``test_selfproof_*`` in
``tests/test_import_hygiene.py``): only ONE of the four D-04/D-19-locked
truth-table rows is wrong today — the recycled-PID decoy
(``test_decoy_positional_marker_arg_does_not_match``). The other three pass
against pre-fix source by pure coincidence of the buggy slice window being
wide enough to cover them. A suite that omitted the decoy row would look
like complete truth-table coverage while leaving the actual live defect
(a signal delivered to an unrelated process) entirely unverified. This file
also adds one row beyond the locked four
(``test_two_interpreter_flags_before_module_switch_matches``, a genuine
live false negative) and a discriminator row proving "first ``-m`` wins" is
the correct rule and not merely a convenient one
(``test_nested_selector_switch_does_not_match``).
"""
from __future__ import annotations

from yahir_reusable_bot.lifecycle.identity import is_running_process

MARKER = b"examplebot"  # neutral placeholder — never a consumer's real marker


def test_decoy_positional_marker_arg_does_not_match(cmdline_bytes):
    """argv ``python -m pytest <marker>``: the marker here is pytest's
    POSITIONAL test-selector argument, so the ``-m`` module target is
    ``pytest``, not the marker. A True here means the reload path can
    deliver SIGHUP to a completely unrelated process that merely recycled
    the PID and happens to be running pytest with the marker name as a
    test-selector argument. RED pre-fix — current code returns True."""
    cmdline = cmdline_bytes(b"python", b"-m", b"pytest", MARKER)
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False


def test_interpreter_flag_before_module_switch_matches(cmdline_bytes):
    """argv ``python -O -m <marker> run``: a genuine daemon started with one
    interpreter flag ahead of the module switch. GREEN pre-fix — the buggy
    ``argv[1:3]``/``argv[1:4]`` windows happen to be wide enough to cover
    exactly one leading flag by coincidence, not by design. This is a
    regression guard against the fix-shape the hardening report literally
    prescribed (``argv[1] == b"-m" and argv[2] == proc_marker``, D-05),
    which would WRONGLY report this row not-running."""
    cmdline = cmdline_bytes(b"python", b"-O", b"-m", MARKER, b"run")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_two_interpreter_flags_before_module_switch_matches(cmdline_bytes):
    """argv ``python -O -B -m <marker> run``: TWO interpreter flags push
    ``-m`` past the buggy window entirely. RED pre-fix — current code
    returns False, a genuine live false negative (the daemon is reported
    not-running). This row is NOT one of the four ROADMAP-locked D-19
    criteria; it is included deliberately because RESEARCH.md reproduced it
    against real source, it costs four lines to fix via the D-04 first-``-m``
    scan, and it is one of only two rows that make this file RED pre-fix."""
    cmdline = cmdline_bytes(b"python", b"-O", b"-B", b"-m", MARKER, b"run")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_plain_module_switch_form_matches(cmdline_bytes):
    """argv ``python -m <marker> run``: the plain, no-flag ``-m`` form.
    GREEN pre-fix; regression guard that the D-04 first-``-m`` scan must
    keep passing."""
    cmdline = cmdline_bytes(b"python", b"-m", MARKER, b"run")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_argv0_basename_form_matches(cmdline_bytes):
    """argv ``/usr/local/bin/<marker> run``: this row must resolve through
    the UNCHANGED argv0-basename branch (identity.py:145-147), not through
    the ``-m`` branch at all — that branch is explicitly out of the D-04
    fix's scope and must stay byte-identical. GREEN pre-fix; regression
    guard."""
    cmdline = cmdline_bytes(b"/usr/local/bin/examplebot", b"run")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_nested_selector_switch_does_not_match(cmdline_bytes):
    """argv ``python -m pytest -m <marker>``: pytest's OWN ``-m`` marker-
    selector flag collides with the interpreter's ``-m``. This row does NOT
    reproduce today's bug — it is GREEN both pre- and post-fix. Its value is
    as a discriminator against a hypothetical any-``-m``-anywhere rule: it is
    the sharpest available demonstration that "FIRST ``-m`` wins" (D-06) is
    the correct rule and not merely a convenient one, because Python's own
    CLI grammar makes everything after ``-m <module>`` belong to the
    module's own argv — pytest's ``-m`` here is never the interpreter's."""
    cmdline = cmdline_bytes(b"python", b"-m", b"pytest", b"-m", MARKER)
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False


def test_trailing_module_switch_without_target_does_not_match(cmdline_bytes):
    """argv ``python -m`` with nothing after it: a truncated/malformed argv.
    Must return False and must NOT raise. Guards the D-04 bounds check.
    identity.py's degrade-vs-raise split (module docstring, lines 1-25) has
    ``write_pid_atomic`` re-raise because it is a writer, but this guard must
    degrade to False, never raise — a reload path that crashes on a
    malformed argv is worse than one that merely reports not-running."""
    cmdline = cmdline_bytes(b"python", b"-m")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False


def test_attached_module_switch_form_matches(cmdline_bytes):
    """argv ``python -mexamplebot``: CPython's ATTACHED ``-m<module>`` form,
    where the module name is baked into the same token with no separating
    space (verified: ``python3 -mjson.tool`` runs identically to
    ``python3 -m json.tool``). RED pre-fix — the first-``-m`` scan only tested
    ``token == b"-m"``, so a daemon launched this way presented argv as the
    single token ``b"-mexamplebot"``, never matched, and a LIVE daemon was
    reported not-running (the WR-01 false negative). Post-fix the token's
    ``-m`` prefix is recognized and the remainder is the module target."""
    cmdline = cmdline_bytes(b"python", b"-mexamplebot")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_attached_module_switch_with_leading_flag_matches(cmdline_bytes):
    """argv ``python -O -mexamplebot``: the attached form behind a SEPARATE
    leading interpreter flag. RED pre-fix (same first-``-m`` blind spot as
    above). Composes the D-05 leading-flag tolerance with the WR-01 attached
    form — both must resolve to the same live daemon."""
    cmdline = cmdline_bytes(b"python", b"-O", b"-mexamplebot")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is True


def test_attached_first_m_wins_over_nested_selector(cmdline_bytes):
    """argv ``python -mpytest -m <marker>``: the ATTACHED interpreter ``-m``
    runs pytest, and pytest's OWN ``-m`` marker-selector carries the marker as
    a positional. The module target is ``pytest``, NOT the marker, so the
    correct answer is False. RED pre-fix — and a false POSITIVE, not merely a
    false negative: the old scan skipped the unrecognized ``-mpytest`` token,
    reached pytest's ``-m``, and matched the marker as its neighbour, so the
    reload path would have delivered SIGHUP to an unrelated pytest process.
    The WR-01 fix closes this by making ``-mpytest`` win the scan as the first
    ``-m`` (D-06 first-``-m``-wins), with ``pytest`` its module target."""
    cmdline = cmdline_bytes(b"python", b"-mpytest", b"-m", MARKER)
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False


def test_bundled_short_option_group_not_matched(cmdline_bytes):
    """argv ``python -Omexamplebot``: CPython also accepts ``-m`` BUNDLED into
    a leading short-option group (verified: ``python3 -Omjson.tool`` and
    ``python3 -Imjson.tool`` both run). This is the WR-01 fix's DELIBERATE
    remaining boundary (D-20): the scan matches only a token whose first two
    bytes are ``-m``, so a bundled group beginning ``-O`` is not decoded and a
    daemon launched this exotic way is still reported not-running. GREEN both
    pre- and post-fix — a boundary guard, not a RED row. Chosen because fully
    decoding Python's short-option-bundling grammar (``-Om``, ``-Xmfoo`` where
    ``-X`` instead consumes the rest) risks FALSE POSITIVES — SIGHUP to the
    wrong PID — which is the strictly worse direction for this guard than the
    false negative it leaves open. No consumer launches a daemon as
    ``python -Om<module>``."""
    cmdline = cmdline_bytes(b"python", b"-Omexamplebot")
    assert is_running_process(1, proc_marker=MARKER, cmdline_reader=lambda _: cmdline) is False
