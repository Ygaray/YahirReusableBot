"""Regression tests for EXTENSION-GUIDE.md seam table and documentation.

The guide is the sole source of truth for a consumer integrating the hub. Gaps or
regressions in the SEAM-08 documentation—especially the architectural inversion
(consumer wires toolkit, NOT Protocol to implement)—are caught here. Each test
reads the live guide, and each has a self-proof that proves the gate actually
catches regressions.
"""

from pathlib import Path
import re
import tempfile


GUIDE_PATH = Path(__file__).resolve().parent.parent / "EXTENSION-GUIDE.md"


def test_seam_08_row_exists_and_reads_implemented():
    """The Plug-Point Summary table must contain a SEAM-08 row with status implemented.

    This is DOCS-04's literal requirement: the guide's promotion row must flip to
    implemented, marking the seam as shipped. A future edit that deletes or regresses
    this row turns this test red.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")

    # Assert at least one SEAM-08 mention (the table row; the section heading adds another)
    seam_08_count = content.count("SEAM-08")
    assert seam_08_count >= 2, (
        f"SEAM-08 appears {seam_08_count} times in guide (expected >=2 for row + section): "
        "the seam documentation is incomplete or missing"
    )

    # Assert the table row exists and reads "implemented"
    table_row_pattern = r"^\|.*SEAM-08.*\|"
    table_rows = [line for line in content.split("\n") if re.match(table_row_pattern, line)]
    assert len(table_rows) >= 1, (
        "No SEAM-08 row found in the Plug-Point Summary table (DOCS-04 requires this row)"
    )

    # Assert the row's status column reads "implemented" (case-insensitive)
    row_text = " ".join(table_rows)  # join in case row is split across lines
    assert "implemented" in row_text.lower(), (
        f"SEAM-08 row does not read 'implemented' — status regression detected.\n"
        f"Row text: {row_text}"
    )


def _extract_seam_08_section(content: str) -> str:
    """Extract the SEAM-08 section from the guide (from ## 7 to the --- separator).

    Returns the full section text from the heading to the separator.
    """
    # Find the SEAM-08 section heading: "## 7.*SEAM-08"
    seam_08_heading_match = re.search(r"^## 7\..*SEAM-08.*$", content, re.MULTILINE)
    assert seam_08_heading_match, "SEAM-08 heading (## 7) not found in guide"

    section_start = seam_08_heading_match.start()

    # Find the end: the next "---" separator that comes after this section
    separator_match = re.search(r"\n---\n", content[section_start:])
    if separator_match:
        section_end = section_start + separator_match.start()
    else:
        # Fallback: find the next "##" heading
        next_heading_match = re.search(r"^##", content[section_start + 10:], re.MULTILINE)
        section_end = (
            section_start + next_heading_match.start() + 10
            if next_heading_match
            else len(content)
        )

    return content[section_start : section_end]


def test_seam_08_section_states_architectural_inversion():
    """The SEAM-08 section must state the architectural inversion explicitly.

    Every other seam: host implements a Protocol the module calls.
    SEAM-08: module supplies mechanism; HOST wires it into its OWN structlog.configure().
    There is no redaction Protocol to implement.

    This is DOCS-04's single most useful sentence for a future reader. A
    rewording that loses the inversion, or a deletion that removes the section,
    turns this test red.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    section_text = _extract_seam_08_section(content)
    section_lower = section_text.lower()

    # Assert the inversion is named (key tokens that must coexist in the section)
    inversion_tokens = ["invert", "protocol", "host wire", "module supplies"]
    found_tokens = [token for token in inversion_tokens if token in section_lower]
    assert len(found_tokens) >= 2, (
        f"SEAM-08 section does not state the architectural inversion clearly. "
        f"Expected to find most of {inversion_tokens}; found {found_tokens}. "
        f"Section text:\n{section_text[:500]}"
    )


def test_seam_08_section_documents_both_recipes():
    """The SEAM-08 section must document both wiring recipes (required + optional).

    Recipe 1 (required): pass RedactingWriter as render target.
    Recipe 2 (optional, broader): assign to sys.stderr before any logging handler.

    A regression that drops one recipe or fails to name the wiring-order
    constraint on recipe 2 turns this test red.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    section_text = _extract_seam_08_section(content)
    section_lower = section_text.lower()

    # Assert both recipes are mentioned
    assert "recipe 1" in section_lower or "render target" in section_lower, (
        "SEAM-08 section missing Recipe 1 (pass RedactingWriter as render target)"
    )
    assert "recipe 2" in section_lower or "sys.stderr" in section_lower, (
        "SEAM-08 section missing Recipe 2 (broader sys.stderr assignment)"
    )

    # Assert the ordering constraint is stated for recipe 2
    assert "before any" in section_lower, (
        "SEAM-08 section missing the hard ordering constraint on Recipe 2 "
        "(must happen before any stdlib logging handler is constructed)"
    )


def test_seam_08_section_names_no_protocol():
    """The SEAM-08 section must explicitly state there is no redaction Protocol.

    This prevents future readers from searching for a nonexistent Protocol
    implementation, addressing the core confusion SEAM-08's inversion solves.
    A rewording that drops this statement turns this test red.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    section_text = _extract_seam_08_section(content)

    # Assert the "no protocol" statement (in various forms)
    section_lower = section_text.lower()
    assert (
        "no redaction protocol" in section_lower
        or "no protocol" in section_lower
        or "there is no" in section_lower
    ), (
        "SEAM-08 section must state there is no redaction Protocol to implement. "
        f"Section snippet:\n{section_text[:300]}"
    )


def test_selfproof_seam_08_gate_catches_deleted_row():
    """Prove the SEAM-08 row test is not vacuous: deleting the row MUST fail the gate.

    Writes the guide to a temp copy with the SEAM-08 table row deleted, re-runs
    test_seam_08_row_exists_and_reads_implemented against the broken copy,
    and asserts it fails. If this self-proof passes, the real gate actually catches regressions.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")

    # Remove the SEAM-08 table row (leave section intact to test row detection independently)
    broken_content = re.sub(
        r"^\|.*SEAM-08 \(P06\).*\|.*$",
        "",  # delete the entire line
        content,
        flags=re.MULTILINE,
    )

    # Verify the row was actually deleted (sanity check)
    assert "SEAM-08 (P06)" not in broken_content, (
        "Self-proof setup failed: SEAM-08 row not actually deleted"
    )

    # Write to temp file and re-run the row test against it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(broken_content)
        tmp_path = Path(tmp.name)

    try:
        # Monkey-patch GUIDE_PATH for this test only
        original_path = globals()["GUIDE_PATH"]
        globals()["GUIDE_PATH"] = tmp_path

        # The gate MUST fail when the row is missing
        try:
            test_seam_08_row_exists_and_reads_implemented()
            # If we reach here, the gate didn't catch the regression — test fails
            assert False, (
                "Self-proof FAILED: test_seam_08_row_exists_and_reads_implemented did not "
                "catch a deleted SEAM-08 row (gate is vacuous)"
            )
        except AssertionError as e:
            # Expected — the gate should fail. Verify it failed for the right reason.
            if "vacuous" in str(e):
                raise  # re-raise our own failure message from above
            # Otherwise, the gate caught the deletion as expected
            pass

    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()


def test_selfproof_seam_08_gate_catches_status_regression():
    """Prove the status check is not vacuous: changing status to 'deferred' MUST fail.

    Writes the guide to a temp copy with SEAM-08's status changed to 'deferred',
    re-runs test_seam_08_row_exists_and_reads_implemented against it, and asserts
    it fails. If this self-proof passes, the real gate actually catches regressions.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")

    # Change SEAM-08's status from "**implemented**" to "**deferred**"
    broken_content = re.sub(
        r"(^\|.*SEAM-08 \(P06\).*?)\*\*implemented\*\*",
        r"\1**deferred**",
        content,
        flags=re.MULTILINE,
    )

    # Verify the status was actually changed
    assert "**deferred**" in broken_content and re.search(
        r"SEAM-08.*deferred", broken_content, re.IGNORECASE
    ), ("Self-proof setup failed: status not actually changed to deferred")

    # Write to temp file and re-run the gate
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(broken_content)
        tmp_path = Path(tmp.name)

    try:
        original_path = globals()["GUIDE_PATH"]
        globals()["GUIDE_PATH"] = tmp_path

        try:
            test_seam_08_row_exists_and_reads_implemented()
            assert False, (
                "Self-proof FAILED: test_seam_08_row_exists_and_reads_implemented did not "
                "catch a status regression (SEAM-08 changed to deferred; gate is vacuous)"
            )
        except AssertionError as e:
            if "vacuous" in str(e):
                raise
            pass

    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()


def test_selfproof_inversion_gate_catches_missing_concept():
    """Prove the inversion test is not vacuous: removing 'invert' mention MUST fail.

    Writes a temp copy of the guide with the entire architectural-inversion paragraph
    removed from the SEAM-08 section, re-runs the inversion test, and asserts it fails.
    If this self-proof passes, the gate actually catches regressions of the architectural
    inversion statement.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    section_text = _extract_seam_08_section(content)

    # Remove the entire inversion-explanation paragraph (ends with "for a future reader.")
    # This removes all mentions of "invert", "protocol", "host wire", "module supplies"
    # that form the architectural inversion explanation.
    broken_section = re.sub(
        r"Every other seam.*?for a future reader\.\n\n",
        "",
        section_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Verify we actually broke it by checking the broken section lacks key tokens
    assert "invert" not in broken_section.lower(), (
        "Self-proof setup failed: inversion concept not actually removed from section"
    )
    # After removing the inversion paragraph, we need fewer of the key tokens
    inversion_tokens = ["invert", "protocol", "host wire", "module supplies"]
    remaining_tokens = [t for t in inversion_tokens if t in broken_section.lower()]
    assert len(remaining_tokens) < 2, (
        f"Self-proof setup failed: section still has {len(remaining_tokens)} inversion tokens "
        f"after removal: {remaining_tokens}"
    )

    # Reconstruct the full document with the broken section
    section_start_match = re.search(r"^## 7\..*SEAM-08.*$", content, re.MULTILINE)
    section_start_idx = section_start_match.start()
    separator_match = re.search(r"\n---\n", content[section_start_idx:])
    section_end_idx = (
        section_start_idx + separator_match.start() if separator_match else len(content)
    )
    broken_content = (
        content[:section_start_idx] + broken_section + content[section_end_idx:]
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
            test_seam_08_section_states_architectural_inversion()
            assert False, (
                "Self-proof FAILED: test_seam_08_section_states_architectural_inversion did not "
                "catch a removed inversion statement (gate is vacuous)"
            )
        except AssertionError as e:
            if "vacuous" in str(e):
                raise
            pass

    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()


def test_seam_08_section_carries_the_known_limitations_block():
    """The SEAM-08 section must carry the labelled 'Known limitations.' block with its four limits.

    T-06-16's mitigation is that the seam is documented WITH its limits, not as an
    unqualified 'implemented' — the omission class that let the original leak path survive
    undocumented. The four honest limitations are: proxy nesting, the private-attribute /
    version coupling, the raw-buffer / file-descriptor blind spot, and the name=value
    boundary under-redaction. Deleting the block turns this red. Verified non-vacuous by
    test_selfproof_limitations_gate_catches_deleted_block below.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")
    section = _extract_seam_08_section(content).lower()

    # The labelled heading is unique to this block — its removal is the primary regression.
    assert "known limitations" in section, (
        "SEAM-08 section is missing its labelled 'Known limitations.' block (T-06-16)"
    )

    # Each limitation is anchored by a distinctive concept token; require all four to survive.
    concepts = {
        "proxy nesting": ("proxy",),
        "private-attribute / version coupling": ("lower bound", "installed version"),
        "raw-buffer / file-descriptor blind spot": ("buffer", "file-descriptor"),
        "name=value boundary under-redaction": ("boundary", "literal-value mode"),
    }
    missing = [
        name for name, anchors in concepts.items()
        if not any(anchor in section for anchor in anchors)
    ]
    assert not missing, (
        f"SEAM-08 'Known limitations.' block is missing documented limit(s): {missing}. "
        "All four honest limitations must remain present (T-06-16)."
    )


def test_selfproof_limitations_gate_catches_deleted_block():
    """Prove the limitations gate is not vacuous: deleting the block MUST fail the gate.

    Writes a temp copy of the guide with the entire 'Known limitations.' block removed
    (from its heading up to the 'Implemented:' line), re-runs
    test_seam_08_section_carries_the_known_limitations_block against it, and asserts it fails.
    """
    content = GUIDE_PATH.read_text(encoding="utf-8")

    # Excise the whole block: from its bold heading up to (not including) the Implemented line.
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
            assert False, (
                "Self-proof FAILED: test_seam_08_section_carries_the_known_limitations_block "
                "did not catch a deleted limitations block (gate is vacuous)"
            )
        except AssertionError as e:
            if "vacuous" in str(e):
                raise
            pass

    finally:
        globals()["GUIDE_PATH"] = original_path
        tmp_path.unlink()
