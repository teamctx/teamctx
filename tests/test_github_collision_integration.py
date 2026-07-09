"""Network-isolated golden test of the collision loop end to end."""

from __future__ import annotations

from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.contracts import RequestContext
from teamctx.core.select import select_context


def make_request(paths: list[str]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="req_integration",
        repo="acme/widgets",
        branch="feature/core",
        task="Edit the widget core.",
        paths=paths,
        linked_issues=[],
        requested_at="2026-06-19T00:00:00Z",
        requesting_principal=None,
    )


def pr(number: int, changed_paths: tuple[str, ...]) -> ForgeReviewPullRequest:
    return ForgeReviewPullRequest(
        provider="github",
        repo="acme/widgets",
        number=number,
        state="open",
        url=f"https://github.com/acme/widgets/pull/{number}",
        title=None,
        changed_paths=changed_paths,
        created_at="2026-06-19T00:00:00Z",
        updated_at="2026-06-19T00:05:00Z",
    )


def test_open_pr_touching_requested_path_yields_a_derived_collision_card() -> None:
    request = make_request(["src/widgets/core.py"])

    document = normalize_forge_review_prs(
        request,
        [pr(7, ("src/widgets/core.py", "README.md"))],
        observed_at="2026-06-19T00:10:00Z",
    )
    selection = select_context(request, document.source_signals, document.source_statuses)

    assert len(selection.cards) == 1
    card = selection.cards[0]
    assert card.section == "Needs attention"
    assert card.refs == ["sig_github_pr_7_collision"]
    assert card.source_display == "GitHub PR #7"
    assert "src/widgets/core.py" in card.reason
    assert selection.closure[0].status == "complete"


def test_open_pr_not_touching_requested_path_yields_no_card() -> None:
    request = make_request(["src/widgets/core.py"])

    document = normalize_forge_review_prs(
        request,
        [pr(8, ("docs/unrelated.md",))],
        observed_at="2026-06-19T00:10:00Z",
    )
    selection = select_context(request, document.source_signals, document.source_statuses)

    assert selection.cards == ()
