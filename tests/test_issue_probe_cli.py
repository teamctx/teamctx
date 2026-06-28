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
    assert "Before you start, here is what to handle first:" in result.output
    assert "Issue #42" in result.output
    assert "re-check the criteria before you rely on them" in result.output


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
    # no token => issue_tracker unavailable => criteria unreachable (not an important check),
    # so kind stays "ready". But honest-UNKNOWN must not be dropped: the gap is surfaced on the
    # "Couldn't check:" line, not silently hidden behind the clear headline.
    assert "Looks clear to start." in result.output
    assert "Couldn't check: spec changes" in result.output
    assert "Not checked:" in result.output


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
    # criteria clear: appears in the "Checked:" coverage line, not as a "NOT CLEAR" finding
    assert "Looks clear to start." in result.output
    assert "the linked issue's criteria are unchanged" in result.output
    assert "Before you start" not in result.output
