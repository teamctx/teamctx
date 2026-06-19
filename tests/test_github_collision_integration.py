"""Network-isolated golden test of the collision loop end to end.

A synthetic GitHub pulls payload flows through the real parse -> normalize -> derive
chain (no network), proving the same path the live project-foundry dogfood exercised:
an open PR touching a requested path yields a source-backed, derived collision card.
"""

from __future__ import annotations

from teamctx.connectors.forge_review import normalize_forge_review_prs
from teamctx.connectors.github import parse_github_pull_requests
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


def pulls_payload(number: int) -> list[dict[str, object]]:
    return [
        {
            "number": number,
            "html_url": f"https://github.com/acme/widgets/pull/{number}",
            "state": "open",
            "created_at": "2026-06-19T00:00:00Z",
            "updated_at": "2026-06-19T00:05:00Z",
            "labels": [],
        }
    ]


def test_open_pr_touching_requested_path_yields_a_derived_collision_card() -> None:
    prs = parse_github_pull_requests(
        repo="acme/widgets",
        pulls_payload=pulls_payload(7),
        files_by_pr={7: [{"filename": "src/widgets/core.py"}, {"filename": "README.md"}]},
    )
    request = make_request(["src/widgets/core.py"])

    document = normalize_forge_review_prs(request, prs, observed_at="2026-06-19T00:10:00Z")
    selection = select_context(request, document.source_signals, document.source_statuses)

    assert len(selection.cards) == 1
    card = selection.cards[0]
    assert card.section == "Needs attention"
    assert card.refs == ["sig_github_pr_7_collision"]
    assert card.source_display == "GitHub PR #7"
    assert "src/widgets/core.py" in card.reason
    assert selection.coverage.complete is True


def test_open_pr_not_touching_requested_path_yields_no_card() -> None:
    prs = parse_github_pull_requests(
        repo="acme/widgets",
        pulls_payload=pulls_payload(8),
        files_by_pr={8: [{"filename": "docs/unrelated.md"}]},
    )
    request = make_request(["src/widgets/core.py"])

    document = normalize_forge_review_prs(request, prs, observed_at="2026-06-19T00:10:00Z")
    selection = select_context(request, document.source_signals, document.source_statuses)

    assert selection.cards == ()
