"""CI coverage of the offline scenario matrix: the runner drives every row against tmp repos and
the bundled mock, so a regression in the real CLI/hook/MCP render breaks these rows loudly. The
whole matrix runs once (module-scoped) since each row spins up subprocesses and the mock server.
"""

from __future__ import annotations

import pytest

from emulation.evidence import ProgramResult
from emulation.runner import run_program

_IMPLEMENTED = {
    "01", "02", "03", "04",
    "05", "06", "07", "08",
    "09", "10", "11", "12",
    "13", "14", "15", "16",
}
_STUBS: set[str] = set()


@pytest.fixture(scope="module")
def program() -> ProgramResult:
    return run_program()


def test_no_row_fails(program: ProgramResult) -> None:
    failures = {row.row_id: [o.subject for o in row.outcomes if not o.ok] for row in program.failed}
    assert failures == {}, failures


def test_implemented_offline_rows_pass(program: ProgramResult) -> None:
    passed = {row.row_id for row in program.rows if row.status == "PASS"}
    assert passed >= _IMPLEMENTED


def test_no_provider_rows_remain_as_honest_skips(program: ProgramResult) -> None:
    stubs = {row.row_id for row in program.rows if row.status == "SKIP"}
    assert stubs == _STUBS


def test_every_matrix_row_is_present(program: ProgramResult) -> None:
    assert {row.row_id for row in program.rows} == _IMPLEMENTED | _STUBS
