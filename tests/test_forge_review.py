from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from typing import Any, cast
from urllib.error import HTTPError
from urllib.request import Request

from click.testing import CliRunner

from teamctx.cli import main
from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.connectors.github import (
    ForgeReviewFetch,
    GitHubProbeError,
    HttpResponse,
    github_error_message,
    run_github_pr_probe,
)
from teamctx.contract_render import render_broker_answer, render_open_source
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext
from teamctx.core.select import derive_cards

OBSERVED_AT = "2026-06-16T12:00:00Z"


def request_context() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="req_test",
        repo="org/app",
        branch="feature/token-retry",
        task="Update src/auth/token.py",
        paths=["src/auth/token.py"],
        linked_issues=["API-482"],
        requested_at=OBSERVED_AT,
        requesting_principal=None,
    )


def test_forge_review_normalizer_emits_collision_card() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="github",
                repo="org/app",
                number=482,
                state="open",
                url="https://github.com/org/app/pull/482",
                title=None,
                changed_paths=("src/auth/token.py", "README.md"),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
                labels=("auth",),
            )
        ],
        observed_at=OBSERVED_AT,
    )

    assert [signal.id for signal in document.source_signals] == ["sig_github_pr_482_collision"]
    assert document.source_signals[0].policy.can_include_source_text is False
    cards = derive_cards(document.request_context, document.source_signals)
    assert cards[0].text == "Open PR #482 changed src/auth/token.py."
    assert cards[0].source_body == "status_only"
    assert cards[0].reason_code == "collision.same_path"
    assert cards[0].source_open_target_id is None
    assert document.source_open_targets[0].id == "open_github_pr_482"
    assert document.source_open_targets[0].body_availability == "status_only"


def test_forge_review_normalizer_omits_non_overlapping_prs() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="github",
                repo="org/app",
                number=17,
                state="open",
                url="https://github.com/org/app/pull/17",
                title=None,
                changed_paths=("docs/readme.md",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
            )
        ],
        observed_at=OBSERVED_AT,
    )

    assert document.source_signals == []
    assert derive_cards(document.request_context, document.source_signals) == []
    assert document.context_cards == []
    assert document.source_statuses[0].status == "fresh"


def test_unbounded_list_sets_status_and_verbatim_note() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="github",
                repo="org/app",
                number=17,
                state="open",
                url="https://github.com/org/app/pull/17",
                title=None,
                changed_paths=("docs/readme.md",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
            )
        ],
        observed_at=OBSERVED_AT,
        coverage_unbounded_list=True,
    )

    status = document.source_statuses[0]
    assert status.status == "unbounded"
    assert status.safe_user_message == (
        "Checked the 1 most recently updated open PRs; more exist, so this is not a "
        "complete check."
    )


def test_unbounded_files_sets_status_and_verbatim_note() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="github",
                repo="org/app",
                number=17,
                state="open",
                url="https://github.com/org/app/pull/17",
                title=None,
                changed_paths=("docs/readme.md",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
            )
        ],
        observed_at=OBSERVED_AT,
        unbounded_files_prs=[17],
    )

    status = document.source_statuses[0]
    assert status.status == "unbounded"
    assert status.safe_user_message == (
        "Open PR #17 changes more files than teamctx checked; it may touch yours."
    )


def test_unbounded_list_and_files_notes_concatenate_in_order() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="github",
                repo="org/app",
                number=17,
                state="open",
                url="https://github.com/org/app/pull/17",
                title=None,
                changed_paths=("docs/readme.md",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
            )
        ],
        observed_at=OBSERVED_AT,
        coverage_unbounded_list=True,
        unbounded_files_prs=[17],
    )

    assert document.source_statuses[0].safe_user_message == (
        "Checked the 1 most recently updated open PRs; more exist, so this is not a "
        "complete check. Open PR #17 changes more files than teamctx checked; it may touch yours."
    )


def test_github_probe_missing_token_returns_unavailable_status() -> None:
    document = run_github_pr_probe(
        repo="org/app",
        token=None,
        request_context=request_context(),
        observed_at=OBSERVED_AT,
    )

    assert document.source_signals == []
    assert derive_cards(document.request_context, document.source_signals) == []
    assert document.context_cards == []
    assert document.source_statuses[0].status == "unavailable"
    assert "no token" in document.source_statuses[0].safe_user_message


def test_github_error_message_preserves_safe_failure_states() -> None:
    unauthorized = github_error_message(GitHubProbeError("nope", status_code=401))
    rate_limited = github_error_message(GitHubProbeError("nope", status_code=403))

    assert unauthorized == "GitHub PR metadata is unavailable with current access."
    assert rate_limited == "GitHub PR metadata is unavailable or rate-limited with current access."


def test_github_probe_api_error_returns_source_status() -> None:
    def forbidden(_request: Request) -> HttpResponse:
        raise HTTPError(
            "https://api.github.com/repos/org/app/pulls",
            403,
            "Forbidden",
            hdrs=Message(),
            fp=BytesIO(b""),
        )

    document = run_github_pr_probe(
        repo="org/app",
        token="token",
        request_context=request_context(),
        observed_at=OBSERVED_AT,
        opener=forbidden,
    )

    assert document.source_signals == []
    assert document.source_statuses[0].status == "unavailable"
    assert "rate-limited" in document.source_statuses[0].safe_user_message


def test_cli_github_pr_probe_missing_token_outputs_contract_document() -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "dev", "github-pr-probe",
            "--repo",
            "org/app",
            "--path",
            "src/auth/token.py",
            "--task",
            "Update token rotation",
        ],
        env={"GITHUB_TOKEN": ""},
    )

    assert result.exit_code == 0
    output = cast(dict[str, Any], json.loads(result.output))
    assert output["schema_version"] == "teamctx.core_contract_document.v0"
    assert output["source_signals"] == []
    assert output["source_statuses"][0]["status"] == "unavailable"
    assert "no token" in output["source_statuses"][0]["safe_user_message"]


def test_cli_github_pr_probe_include_title_threads_to_fetch(monkeypatch) -> None:
    import teamctx.connectors.github as gh

    captured: dict[str, object] = {}

    def fake_fetch(**kwargs: object) -> ForgeReviewFetch:
        captured["include_titles"] = kwargs["include_titles"]
        return ForgeReviewFetch(pull_requests=[])

    monkeypatch.setattr(gh, "fetch_github_pull_requests", fake_fetch)
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "dev",
            "github-pr-probe",
            "--repo",
            "org/app",
            "--path",
            "src/auth/token.py",
            "--include-title",
        ],
        env={"GITHUB_TOKEN": "tok"},
    )

    assert result.exit_code == 0
    assert captured["include_titles"] is True


def test_gitlab_normalizer_emits_mr_worded_collision_card() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="gitlab",
                repo="org/app",
                number=12,
                state="opened",
                url="https://gitlab.com/org/app/-/merge_requests/12",
                title=None,
                changed_paths=("src/auth/token.py",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
                head_ref="feature/other",
                source_project_id=101,
                target_project_id=101,
            )
        ],
        observed_at=OBSERVED_AT,
        provider="gitlab",
        source_id="gitlab_mr_metadata",
    )

    signal = document.source_signals[0]
    assert signal.id == "sig_gitlab_mr_12_collision"
    assert signal.source_display == "GitLab MR !12"
    assert signal.evidence_summary == "Open MR !12 changed src/auth/token.py."
    assert signal.scope["provider"] == "gitlab"
    status = document.source_statuses[0]
    assert status.source_id == "gitlab_mr_metadata"
    assert status.scope["provider"] == "gitlab"
    cards = derive_cards(document.request_context, document.source_signals)
    assert cards[0].text == "Open MR !12 changed src/auth/token.py."
    assert cards[0].source_display == "GitLab MR !12"
    assert cards[0].scope["provider"] == "gitlab"
    assert document.source_open_targets[0].id == "open_gitlab_mr_12"
    assert document.source_open_targets[0].open_label == "Open MR"


def test_gitlab_own_branch_mr_uses_mr_fyi_copy() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="gitlab",
                repo="org/app",
                number=12,
                state="opened",
                url="https://gitlab.com/org/app/-/merge_requests/12",
                title=None,
                changed_paths=("src/auth/token.py",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
                head_ref="feature/token-retry",
                source_project_id=101,
                target_project_id=101,
            )
        ],
        observed_at=OBSERVED_AT,
        provider="gitlab",
        source_id="gitlab_mr_metadata",
    )

    assert document.source_signals == []
    status = document.source_statuses[0]
    assert status.scope["own_branch_prs"] == ["12"]
    assert status.safe_user_message == (
        "Your own open MR !12 for this branch touches these files; "
        "not flagged as a collision."
    )


def test_gitlab_collision_render_has_no_gh_hint_and_open_source_shows_url() -> None:
    document = normalize_forge_review_prs(
        request_context(),
        [
            ForgeReviewPullRequest(
                provider="gitlab",
                repo="org/app",
                number=12,
                state="opened",
                url="https://gitlab.com/org/app/-/merge_requests/12",
                title=None,
                changed_paths=("src/auth/token.py",),
                created_at="2026-06-16T11:00:00Z",
                updated_at="2026-06-16T11:49:00Z",
                head_ref="feature/other",
                source_project_id=101,
                target_project_id=101,
            )
        ],
        observed_at=OBSERVED_AT,
        provider="gitlab",
        source_id="gitlab_mr_metadata",
    )
    answer = broker_answer(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        open_targets=document.source_open_targets,
    )

    text = render_broker_answer(answer)
    assert "Open MR !12 changed src/auth/token.py" in text
    assert "gh pr view" not in text

    source = render_open_source(answer.selection.cards[0], answer.open_targets)
    assert "gh pr view" not in source
    assert "open https://gitlab.com/org/app/-/merge_requests/12" in source
