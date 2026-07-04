"""Row 10: Transports agree (program spec rev 2, P2-5).

On one CONFLICT scenario, the three transports must agree: the CLI report and the in-process MCP
tool produce byte-identical text (both go through ``render_work_start``; the render is
observed_at-independent), and the reflex hook signal surfaces the SAME PR and, like the others,
never reads clear. The MCP tool is invoked in-process via ``teamctx.mcp_server`` with
``TEAMCTX_PROJECT_ROOT`` set to the clone, exactly as an MCP client would reach it.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from emulation.actors import (
    SubprocessEnv,
    pretooluse_event,
    process_env,
    run_cli,
    run_hook,
)
from emulation.evidence import (
    Expectation,
    RowResult,
    combine,
    evaluate,
    passed_or_failed,
)
from emulation.mockgh import MockGitHub
from emulation.rows._shared import (
    CONFLICT_FILE,
    build_conflict_repo,
    conflict_fixtures,
)
from teamctx import mcp_server

ROW_ID = "10"
TITLE = "Transports agree"

_SURFACES_PR = Expectation(
    must_match=("PR #{n}",), must_absent=("Looks clear to start.", "looks clear to start")
)


def _mcp_text(clone: Path, api_root: str) -> str:
    with process_env(
        TEAMCTX_PROJECT_ROOT=str(clone),
        TEAMCTX_GITHUB_API_ROOT=api_root,
        GITHUB_TOKEN=SubprocessEnv(api_root=api_root).token,
        TEAMCTX_DISABLE_GH_AUTH="1",
        GITHUB_TOKEN_FILE=None,
    ):
        # str(): the FastMCP tool decorator erases the str return type to Any at the call site.
        return str(mcp_server.work_start(paths=[CONFLICT_FILE]))


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        clone = build_conflict_repo(Path(raw) / "repo").root
        with MockGitHub(conflict_fixtures()) as server:
            env = SubprocessEnv(api_root=server.api_root, ambient_state=Path(raw) / "ambient")
            cli = run_cli(["work-start", "--path", CONFLICT_FILE], cwd=clone, env=env)
            mcp_text = _mcp_text(clone, server.api_root)
            event = pretooluse_event(cwd=clone, file_path=CONFLICT_FILE)
            hook_text = run_hook(event, cwd=clone, env=env)

    cli_result = passed_or_failed(ROW_ID, TITLE, cli.output, _SURFACES_PR, note="CLI")
    mcp_result = passed_or_failed(ROW_ID, TITLE, mcp_text, _SURFACES_PR, note="MCP (in-process)")
    hook_result = passed_or_failed(ROW_ID, TITLE, hook_text, _SURFACES_PR, note="reflex hook")

    # The strong claim: CLI and MCP are byte-identical (same render, no observed_at leakage).
    agree_status, agree_outcomes = evaluate(
        "IDENTICAL" if cli.output == mcp_text else "DIFFERENT",
        Expectation(must_match=("IDENTICAL",)),
    )
    agree = RowResult(ROW_ID, TITLE, agree_status, agree_outcomes, note="CLI == MCP text")
    return combine(ROW_ID, TITLE, [cli_result, mcp_result, hook_result, agree])


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
