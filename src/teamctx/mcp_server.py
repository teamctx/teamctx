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
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from teamctx.project_config import ProjectConfigError
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs
from teamctx.tokens import resolve_github_token
from teamctx.work_start import render_work_start

mcp = FastMCP("teamctx")

_WORK_START_DESCRIPTION = (
    "Get current team context for a repo BEFORE editing files. Checks, in one call: open "
    "pull requests that touch your paths (collisions), failing required CI gates, changed "
    "acceptance criteria on linked issues, and superseded docs you rely on. Returns cards + "
    "an honest coverage report + one verdict per check (clear / NOT CLEAR / UNKNOWN). It "
    "informs; it does not block — read it and factor it into your plan. A source the inputs "
    "cannot reach is reported UNKNOWN, never a false all-clear. Repo, branch, and docs root "
    "are auto-detected from the working tree and .teamctx/config.json; pass them only to override."
)


@mcp.tool(name="work_start", description=_WORK_START_DESCRIPTION)
def work_start(
    paths: list[str],
    repo: str | None = None,
    branch: str | None = None,
    task: str = "Start work.",
    issues: list[str] | None = None,
    since: str | None = None,
    docs_root: str | None = None,
    ref: str | None = None,
) -> str:
    """Run the unified work-start broker and return its answer as text.

    paths: files the work will touch (required). repo/branch/docs_root are auto-detected from
    the server's working tree and ``.teamctx/config.json``; pass them only to override.
    """

    try:
        inputs = resolve_work_start_inputs(
            paths=tuple(paths),
            repo=repo,
            branch=branch,
            docs_root=docs_root,
            task=task,
            issues=tuple(issues or ()),
            since=since,
            ref=ref,
            token=_resolve_github_token(),
            root=_resolution_root(),
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        return str(exc)
    return render_work_start(inputs, observed_at=_utc_now_string(), project_root=_resolution_root())


def _resolution_root() -> Path:
    override = os.environ.get("TEAMCTX_PROJECT_ROOT")
    return Path(override) if override else Path.cwd()


def _resolve_github_token() -> str | None:
    """The token, resolved server-side (see teamctx.tokens). No token → honest UNKNOWN."""

    return resolve_github_token()


def _utc_now_string() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    """Run the teamctx MCP server over stdio."""

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
