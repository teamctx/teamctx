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
    # no token => conflict check unreachable => cant_verify headline
    assert "Heads up: I can't confirm the important things yet:" in result.output
    assert "couldn't reach GitHub" in result.output
    assert "GITHUB_TOKEN" in result.output


def test_work_start_unified_surfaces_all_four_checks(monkeypatch, tmp_path: Path) -> None:
    """Unified work-start runs every connector the inputs allow and reports one verdict per
    check. With a branch + issue + docs-root supplied (and the fetchers stubbed), all four
    verdict lines appear (collision, gate, criteria, docs) in a single answer."""

    monkeypatch.chdir(tmp_path)
    import teamctx.connectors.github as gh
    import teamctx.connectors.github_checks as gc
    import teamctx.connectors.github_issues as gi
    import teamctx.runner as runner_mod
    from teamctx.connectors.github import ForgeReviewFetch

    monkeypatch.setattr(
        gh, "fetch_github_pull_requests",
        lambda **kw: ForgeReviewFetch(pull_requests=[], truncated=False),
    )
    from teamctx.connectors.github_checks import CheckRunsFetch
    monkeypatch.setattr(
        gc, "fetch_failing_check_runs",
        lambda **kw: CheckRunsFetch(failing=[], truncated=False, pending=False),
    )
    monkeypatch.setattr(gi, "fetch_issue_changes", lambda **kw: [])
    # docs probe reads the filesystem; inject a reader with one relied-on, non-superseded doc so
    # docs is in scope and current (no real I/O). With docs_root set but nothing relied-on in
    # scope, docs would honestly read not_applicable, not "current".
    real_docs_probe = runner_mod.run_docs_supersession_probe
    monkeypatch.setattr(
        runner_mod,
        "run_docs_supersession_probe",
        lambda **kw: real_docs_probe(reader=lambda root: [("docs/guide.md", "# guide\n")], **kw),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        [
            "work-start", "--github-repo", "acme/widgets",
            "--path", "src/widgets/core.py", "--path", "docs/guide.md",
            "--branch", "feature", "--issue", "#7", "--since", "2026-06-24T00:00:00Z",
            "--docs-root", "docs",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    # all four checks clear: they appear in the "Checked:" coverage line
    assert "Looks clear to start." in result.output
    assert "no other open PRs touch your files" in result.output
    assert "no failing checks found" in result.output
    assert "the linked issue's criteria are unchanged" in result.output
    assert "the docs you rely on are current" in result.output


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
    # repo resolved + no token => both conflict and gate unreachable => cant_verify
    assert "Heads up: I can't confirm the important things yet:" in result.output
    assert "GITHUB_TOKEN" in result.output


def test_work_start_errors_when_repo_unresolvable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # not a git repo, no config
    result = CliRunner().invoke(main, ["work-start", "--path", "src/x.py"])
    assert result.exit_code != 0
    assert "could not determine the repository" in result.output


def test_work_start_reads_token_from_file(monkeypatch, tmp_path: Path) -> None:
    """CLI gains the file-based token fallback: GITHUB_TOKEN_FILE is honoured when GITHUB_TOKEN
    is unset. With a token present the connector attempts a network call and gets a GitHub auth
    error rather than the no-token can't-verify path, proving the token was picked up."""

    token_file = tmp_path / "token"
    token_file.write_text("file-based-token\n", encoding="utf-8")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))
    monkeypatch.chdir(tmp_path)

    import teamctx.connectors.github as gh
    from teamctx.connectors.github import ForgeReviewFetch

    # The connector is called with the file-sourced token; capture it.
    captured: list[str | None] = []

    def _fake_fetch(**kw: object) -> ForgeReviewFetch:
        captured.append(kw.get("token"))
        return ForgeReviewFetch(pull_requests=[], truncated=False)

    monkeypatch.setattr(gh, "fetch_github_pull_requests", _fake_fetch)

    result = CliRunner().invoke(
        main,
        ["work-start", "--github-repo", "acme/widgets", "--path", "src/widgets/core.py"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    # Token was read from the file and forwarded to the connector.
    assert captured == ["file-based-token"]


def test_work_start_errors_on_malformed_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text("{ not valid json", encoding="utf-8")
    result = CliRunner().invoke(
        main, ["work-start", "--github-repo", "acme/widgets", "--path", "src/x.py"]
    )
    assert result.exit_code != 0
    assert "config" in result.output.lower()  # clean message, not a traceback


def test_work_start_finds_config_from_subdirectory(monkeypatch, tmp_path: Path) -> None:
    """Run from a subdirectory: the committed config at the repo root is still found, because
    root resolution uses the git toplevel, not the process cwd."""
    import json

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text(
        json.dumps(
            {"schema_version": "teamctx.project_config.v0", "work_start": {"repo": "owner/name"}}
        ),
        encoding="utf-8",
    )
    sub = tmp_path / "src"
    sub.mkdir()
    monkeypatch.chdir(sub)
    result = CliRunner().invoke(
        main,
        ["work-start", "--path", "src/x.py", "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code == 0, result.output
    assert "could not determine the repository" not in result.output
