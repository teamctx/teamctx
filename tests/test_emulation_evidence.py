"""Unit tests for the Phase 5 emulation primitives (evidence diffing + the redaction map).

These live in the normal test tree so CI runs them; the emulation package is on the pytest
pythonpath (pyproject ``pythonpath = ["src", "."]``).
"""

from __future__ import annotations

import pytest

from emulation.evidence import (
    Expectation,
    ProgramResult,
    RowResult,
    combine,
    compile_template,
    evaluate,
    passed_or_failed,
    skipped,
)
from emulation.redact import (
    ATLASSIAN_BASE_TOKEN,
    ID_TOKEN,
    PROJECT_KEY_TOKEN,
    SPACE_KEY_TOKEN,
    RedactionMap,
)


def test_byte_exact_literal_span_matches_verbatim() -> None:
    actual = "Looks clear to start.\n  Checked: no failing checks found."
    status, outcomes = evaluate(actual, Expectation(must_match=("no failing checks found",)))
    assert status == "PASS"
    assert outcomes[0].ok is True


def test_byte_exact_literal_span_is_not_fuzzy() -> None:
    # one character off the stable copy is a FAIL: byte-exact means byte-exact.
    expectation = Expectation(must_match=("no failing checks found",))
    status, _ = evaluate("no failing check found", expectation)
    assert status == "FAIL"


def test_templated_n_span_matches_any_digits() -> None:
    prefix = "the linked issue's criteria are unchanged (issue #"
    template = f"{prefix}{{n}} from your branch name)"
    for number in ("42", "7", "1234"):
        actual = f"{prefix}{number} from your branch name)"
        assert compile_template(template).search(actual) is not None


def test_templated_n_span_does_not_match_letters() -> None:
    template = "PR #{n}"
    assert compile_template(template).search("PR #abc") is None


def test_templated_url_and_id_spans() -> None:
    template = "open {url} for issue {id}"
    actual = "open https://github.com/acme/widgets/issues/42 for issue ABC-9"
    assert compile_template(template).search(actual) is not None


def test_repeated_placeholders_do_not_collide() -> None:
    # two {n} in one block must both compile (numbered, not named groups).
    template = "PR #{n} touches file number {n}"
    assert compile_template(template).search("PR #7 touches file number 3") is not None


def test_unknown_placeholder_is_rejected_loudly() -> None:
    with pytest.raises(ValueError, match="unknown expected-block placeholder"):
        compile_template("a {bogus} token")


def test_must_absent_catches_a_false_all_clear() -> None:
    actual = "Heads up: I can't confirm the important things yet:\n  Open PRs: ..."
    status, outcomes = evaluate(actual, Expectation(must_absent=("Looks clear to start.",)))
    assert status == "PASS"
    assert outcomes[0].kind == "absent"


def test_must_absent_fails_when_forbidden_line_present() -> None:
    expectation = Expectation(must_absent=("Looks clear to start.",))
    status, _ = evaluate("Looks clear to start.", expectation)
    assert status == "FAIL"


def test_passed_or_failed_packages_a_rowresult() -> None:
    result = passed_or_failed(
        "01", "Collision, GitHub", "PR #7 changed src/a.py",
        Expectation(must_match=("PR #{n} changed src/a.py",)),
    )
    assert isinstance(result, RowResult)
    assert result.status == "PASS"
    assert result.row_id == "01"
    assert result.actual == "PR #7 changed src/a.py"


def test_combine_fails_if_any_part_fails() -> None:
    good = passed_or_failed("x", "t", "hello", Expectation(must_match=("hello",)))
    bad = passed_or_failed("x", "t", "hello", Expectation(must_match=("goodbye",)))
    merged = combine("10", "Transports agree", [good, bad])
    assert merged.status == "FAIL"


def test_combine_passes_when_all_parts_pass() -> None:
    a = passed_or_failed("x", "t", "hello", Expectation(must_match=("hello",)), note="cli")
    b = passed_or_failed("x", "t", "world", Expectation(must_match=("world",)), note="mcp")
    merged = combine("10", "Transports agree", [a, b])
    assert merged.status == "PASS"
    assert "--- cli ---" in merged.actual and "--- mcp ---" in merged.actual


def test_skipped_is_neither_pass_nor_fail() -> None:
    result = skipped("02", "Collision, GitLab", "requires the S9b connector")
    assert result.status == "SKIP"
    assert "S9b" in result.note


def test_program_result_ok_and_failed() -> None:
    rows = (
        RowResult("01", "a", "PASS"),
        RowResult("02", "b", "SKIP"),
        RowResult("03", "c", "FAIL"),
    )
    program = ProgramResult(rows=rows)
    assert program.ok is False
    assert [r.row_id for r in program.failed] == ["03"]


def test_program_result_ok_ignores_skips() -> None:
    program = ProgramResult(rows=(RowResult("01", "a", "PASS"), RowResult("02", "b", "SKIP")))
    assert program.ok is True


# --- redaction map (spec verbatim) ---


def test_redaction_map_spec_verbatim() -> None:
    text = (
        "Open the source: https://acme.atlassian.net/browse/ENG-14 in project ENG, "
        "space DEV, page 90210."
    )
    redacted = RedactionMap(
        atlassian_base="https://acme.atlassian.net",
        project_key="ENG",
        space_key="DEV",
        ids=("90210",),
    ).apply(text)
    assert ATLASSIAN_BASE_TOKEN in redacted
    assert "acme.atlassian.net" not in redacted
    assert f"project {PROJECT_KEY_TOKEN}" in redacted
    assert f"space {SPACE_KEY_TOKEN}" in redacted
    assert f"page {ID_TOKEN}" in redacted


def test_redaction_leaves_github_lab_slug_as_is() -> None:
    # GitHub/GitLab lab repo slugs are committed AS-IS: they are disposable lab assets.
    text = "GitHub PR #7 in teamctx-emulation-lab/widgets"
    assert RedactionMap().apply(text) == text


def test_redaction_longest_id_first() -> None:
    # a shorter id that is a substring of a longer one must not mask the longer one first.
    redacted = RedactionMap(ids=("42", "4213")).apply("ids 4213 and 42")
    assert redacted == f"ids {ID_TOKEN} and {ID_TOKEN}"


def test_null_redaction_is_identity() -> None:
    assert RedactionMap().apply("nothing to redact here") == "nothing to redact here"
