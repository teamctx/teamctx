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
    GitHubProbeError,
    HttpResponse,
    github_error_message,
    parse_github_pull_requests,
    run_github_pr_probe,
)
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


def test_github_parser_omits_titles_unless_allowed() -> None:
    pulls_payload: list[dict[str, Any]] = [
        {
            "number": 482,
            "html_url": "https://github.com/org/app/pull/482",
            "state": "open",
            "title": "Add retry behavior",
            "created_at": "2026-06-16T11:00:00Z",
            "updated_at": "2026-06-16T11:49:00Z",
            "user": {"login": "not-normalized"},
            "labels": [{"name": "auth"}],
        }
    ]
    files_by_pr = {482: [{"filename": "src/auth/token.py"}]}

    omitted = parse_github_pull_requests(
        repo="org/app",
        pulls_payload=pulls_payload,
        files_by_pr=files_by_pr,
        include_titles=False,
    )
    included = parse_github_pull_requests(
        repo="org/app",
        pulls_payload=pulls_payload,
        files_by_pr=files_by_pr,
        include_titles=True,
    )

    assert omitted[0].title is None
    assert included[0].title == "Add retry behavior"
    assert not hasattr(omitted[0], "author")
    assert omitted[0].labels == ("auth",)


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
