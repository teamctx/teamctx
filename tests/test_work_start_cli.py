"""The work-start transport: the command an agent runs to get context at work-start.

Tested network-free via the no-token path: with no credential, the source is
unavailable, and the command must degrade honestly (print incomplete coverage, exit 0)
rather than crash or block. Fail-safe and prints-never-blocks, proven without a network.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main


def test_work_start_with_no_token_degrades_honestly(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "work-start",
            "--github-repo",
            "acme/widgets",
            "--path",
            "src/widgets/core.py",
            "--token-env",
            "TEAMCTX_DEFINITELY_UNSET_TOKEN",
        ],
    )

    assert result.exit_code == 0  # prints, never blocks
    assert "Working context" in result.output
    assert "Coverage" in result.output
    # no token => source unavailable => coverage incomplete => honest warning
    assert "not an all-clear" in result.output
    # the engine's verdict is surfaced: no token => unknown, never a false "clear".
    assert "Conflict check: UNKNOWN" in result.output


def test_work_start_unified_surfaces_all_four_checks(monkeypatch) -> None:
    """Unified work-start runs every connector the inputs allow and reports one verdict per
    check. With a branch + issue + docs-root supplied (and the fetchers stubbed), all four
    verdict lines appear — collision, gate, criteria, docs — in a single answer."""

    import teamctx.connectors.github as gh
    import teamctx.connectors.github_checks as gc
    import teamctx.connectors.github_issues as gi
    import teamctx.runner as runner_mod

    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: [])
    monkeypatch.setattr(gc, "fetch_failing_check_runs", lambda **kw: [])
    monkeypatch.setattr(gi, "fetch_issue_changes", lambda **kw: [])
    # docs probe reads the filesystem; inject an empty reader so no real I/O happens.
    real_docs_probe = runner_mod.run_docs_supersession_probe
    monkeypatch.setattr(
        runner_mod,
        "run_docs_supersession_probe",
        lambda **kw: real_docs_probe(reader=lambda root: [], **kw),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        [
            "work-start", "--github-repo", "acme/widgets",
            "--path", "src/widgets/core.py",
            "--branch", "feature", "--issue", "#7", "--since", "2026-06-24T00:00:00Z",
            "--docs-root", "docs",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    # all four checks reported, each clear since every source was checked and found nothing
    assert "Conflict check: clear" in result.output
    assert "Gate check: clear" in result.output
    assert "Criteria check: clear" in result.output
    assert "Docs check: clear" in result.output


def _init_repo_with_origin(root: Path, url: str, branch: str) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", branch], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


def test_work_start_resolves_repo_from_git_without_flag(monkeypatch, tmp_path: Path) -> None:
    _init_repo_with_origin(tmp_path, "git@github.com:acme/widgets.git", "feature")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["work-start", "--path", "src/widgets/core.py",
         "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code == 0, result.output
    assert "Working context" in result.output
    assert "Conflict check: UNKNOWN" in result.output  # repo resolved; no token => honest


def test_work_start_errors_when_repo_unresolvable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # not a git repo, no config
    result = CliRunner().invoke(main, ["work-start", "--path", "src/x.py"])
    assert result.exit_code != 0
    assert "could not determine the repository" in result.output
