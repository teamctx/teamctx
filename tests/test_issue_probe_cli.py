from click.testing import CliRunner

from teamctx.cli import main


def test_issue_probe_surfaces_criteria_changed_card(monkeypatch) -> None:
    import teamctx.connectors.github_issues as gi

    def fake_fetch(*, repo, issues, since, token, opener=None):  # type: ignore[no-untyped-def]
        from teamctx.connectors.issue_criteria import IssueCriteriaChange

        return [
            IssueCriteriaChange(
                repo=repo,
                issue="#42",
                issue_url="https://github.com/teamctx/teamctx/issues/42",
                title="Add widget support",
                state="closed",
                labels=(),
                change_kinds=("state_changed",),
                detail="Issue #42 updated: state is now closed.",
                updated_at="2026-06-25T10:00:00Z",
            )
        ]

    monkeypatch.setattr(gi, "fetch_issue_changes", fake_fetch)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        [
            "issue-probe", "--repo", "teamctx/teamctx",
            "--issue", "#42", "--since", "2026-06-24T00:00:00Z",
            "--path", "src/teamctx/cli.py",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Criteria check: NOT CLEAR" in result.output
    assert "Issue #42" in result.output


def test_issue_probe_without_token_degrades_honestly(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = CliRunner().invoke(
        main,
        [
            "issue-probe", "--repo", "teamctx/teamctx",
            "--issue", "#42", "--since", "2026-06-24T00:00:00Z",
            "--path", "src/teamctx/cli.py",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Criteria check: UNKNOWN" in result.output


def test_issue_probe_no_changes_shows_clear(monkeypatch) -> None:
    import teamctx.connectors.github_issues as gi

    def fake_fetch(*, repo, issues, since, token, opener=None):  # type: ignore[no-untyped-def]
        return []

    monkeypatch.setattr(gi, "fetch_issue_changes", fake_fetch)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        [
            "issue-probe", "--repo", "teamctx/teamctx",
            "--issue", "#42", "--since", "2026-06-24T00:00:00Z",
            "--path", "src/teamctx/cli.py",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Criteria check:" in result.output
    assert "NOT CLEAR" not in result.output
