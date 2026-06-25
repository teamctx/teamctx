"""teamctx MCP server: expose the work-start broker as an MCP tool.

A thin transport over the same use case the CLI runs (``render_work_start``). An agent calls
the ``work_start`` tool before touching a repo and receives the broker's answer — derived
cards, honest coverage, and one verdict per check — as text it can read and factor into its
plan. The GitHub token is read from the server environment (``GITHUB_TOKEN``), never passed
through a tool call, so credentials stay server-side.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

from teamctx.runner import WorkStartInputs
from teamctx.work_start import render_work_start

mcp = FastMCP("teamctx")

_WORK_START_DESCRIPTION = (
    "Get current team context for a repo BEFORE editing files. Checks, in one call: open "
    "pull requests that touch your paths (collisions), failing required CI gates, changed "
    "acceptance criteria on linked issues, and superseded docs you rely on. Returns cards + "
    "an honest coverage report + one verdict per check (clear / NOT CLEAR / UNKNOWN). It "
    "informs; it does not block — read it and factor it into your plan. A source the inputs "
    "cannot reach is reported UNKNOWN, never a false all-clear."
)


@mcp.tool(name="work_start", description=_WORK_START_DESCRIPTION)
def work_start(
    repo: str,
    paths: list[str],
    branch: str | None = None,
    task: str = "Start work.",
    issues: list[str] | None = None,
    since: str | None = None,
    docs_root: str | None = None,
    ref: str | None = None,
) -> str:
    """Run the unified work-start broker and return its answer as text.

    repo: owner/name. paths: files the work will touch. branch: current branch (also the
    default gate ref). issues: linked issues like ``#42`` (with ``since`` to check criteria
    movement). docs_root: a docs directory to scan for supersession. ref: explicit gate ref.
    """

    inputs = WorkStartInputs(
        repo=repo,
        paths=tuple(paths),
        branch=branch,
        task=task,
        token=os.environ.get("GITHUB_TOKEN"),
        issues=tuple(issues or ()),
        since=since,
        docs_root=docs_root,
        ref=ref,
    )
    return render_work_start(inputs, observed_at=_utc_now_string())


def _utc_now_string() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    """Run the teamctx MCP server over stdio."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
