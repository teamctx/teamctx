"""Tests for the teamctx MCP server (CURPLAN3: agents consume teamctx over MCP).

The tool is a thin wrapper over the same use case the CLI runs, so these focus on the MCP
seam: the tool is registered, callable, returns the broker's text, and degrades honestly.
"""

from __future__ import annotations

import asyncio

from teamctx.mcp_server import _resolve_github_token, mcp, work_start


def _content_text(result: object) -> str:
    """Flatten whatever call_tool returns (content blocks, or a (content, structured) tuple)
    into a single string for assertions."""

    items: object = result
    if isinstance(result, tuple):
        items = result[0]
    if isinstance(items, list | tuple):
        parts = [getattr(block, "text", "") for block in items]
        return "\n".join(p for p in parts if p)
    return str(items)


def test_work_start_tool_is_directly_callable_and_degrades_without_token(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    output = work_start(repo="acme/widgets", paths=["src/app/core.py"])
    assert "Working context" in output
    # no token => source unavailable => Unknown, never a false clear
    assert "Conflict check: UNKNOWN" in output


def test_work_start_tool_surfaces_a_collision(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest

    def fake_prs(**kwargs):  # type: ignore[no-untyped-def]
        return [
            ForgeReviewPullRequest(
                provider="github",
                repo="acme/widgets",
                number=7,
                state="open",
                url="https://github.com/acme/widgets/pull/7",
                title=None,
                changed_paths=("src/app/core.py",),
                created_at="2026-06-25T10:00:00Z",
                updated_at="2026-06-25T11:00:00Z",
            )
        ]

    monkeypatch.setattr(gh, "fetch_github_pull_requests", fake_prs)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    output = work_start(repo="acme/widgets", paths=["src/app/core.py"])
    assert "Conflict check: NOT CLEAR" in output
    assert "PR #7" in output


def test_resolve_token_prefers_env_then_file_then_none(monkeypatch, tmp_path) -> None:
    # 1) GITHUB_TOKEN value wins
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert _resolve_github_token() == "from-env"

    # 2) no value, but GITHUB_TOKEN_FILE points at a file -> read + strip it
    token_file = tmp_path / "ghtoken"
    token_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))
    assert _resolve_github_token() == "from-file"

    # 3) nothing configured -> None (honest UNKNOWN downstream)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert _resolve_github_token() is None

    # 4) a token file path that does not exist -> None, never a crash
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(tmp_path / "missing"))
    assert _resolve_github_token() is None


def test_list_tools_exposes_work_start() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}
    assert "work_start" in names
    # the description tells the agent when to call it
    work_start_tool = next(tool for tool in tools if tool.name == "work_start")
    assert "before" in (work_start_tool.description or "").lower()


def test_call_tool_runs_the_broker_over_mcp(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = asyncio.run(
        mcp.call_tool("work_start", {"repo": "acme/widgets", "paths": ["src/app/core.py"]})
    )
    text = _content_text(result)
    assert "Working context" in text
    assert "Conflict check: UNKNOWN" in text


def test_work_start_resolves_repo_from_root(monkeypatch, tmp_path) -> None:
    import subprocess

    import teamctx.mcp_server as mcp_server

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    # git needs a committed HEAD before a remote can be added
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "i"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "git@github.com:acme/widgets.git"], check=True)
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))

    captured: dict[str, object] = {}

    def fake_render(inputs, *, observed_at, **kwargs):  # type: ignore[no-untyped-def]
        captured["repo"] = inputs.repo
        return "ok"

    monkeypatch.setattr(mcp_server, "render_work_start", fake_render)
    assert work_start(paths=["src/x.py"]) == "ok"
    assert captured["repo"] == "acme/widgets"


def test_work_start_returns_error_text_when_repo_unresolvable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))  # non-git, no config
    out = work_start(paths=["src/x.py"])
    assert "could not determine the repository" in out


def test_work_start_docs_scanned_from_project_root_not_cwd(monkeypatch, tmp_path) -> None:
    import json

    proj = tmp_path / "proj"
    (proj / ".teamctx").mkdir(parents=True)
    (proj / ".teamctx" / "config.json").write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "acme/widgets", "docs_root": "docs"},
            }
        ),
        encoding="utf-8",
    )
    (proj / "docs").mkdir()
    (proj / "docs" / "old.md").write_text(
        "---\nsuperseded_by: docs/new.md\n---\n", encoding="utf-8"
    )
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)  # cwd != project root
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(proj))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    out = work_start(paths=["docs/old.md"])

    assert "Docs check: NOT CLEAR" in out
    assert "docs/new.md" in out  # names the superseding doc
