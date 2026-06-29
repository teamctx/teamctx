"""Unit tests for the sound consumer rule (Theorem 2 in code)."""

from __future__ import annotations

from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.contracts import RequestContext
from teamctx.core.evaluate import Valuation, evaluate
from teamctx.core.select import ClaimCard, ClosureEntry, derive_claims, no_conflict_query


def _request(paths: tuple[str, ...]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="r",
        repo="svc",
        task="t",
        paths=list(paths),
        requested_at="2026-01-01T00:00:00Z",
    )


def _collision_claim_card(path: str) -> ClaimCard:
    request = _request((path,))
    pr = ForgeReviewPullRequest(
        provider="github",
        repo="svc",
        number=1,
        state="open",
        url="https://example/pr/1",
        title=None,
        changed_paths=(path,),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    document = normalize_forge_review_prs(request, [pr], observed_at="2026-01-01T00:00:00Z")
    return derive_claims(request, document.source_signals)[0]


def _closure(status: str) -> tuple[ClosureEntry, ...]:
    return (ClosureEntry(proposition="no_pr_conflicts_with_paths", status=status),)


def test_universal_is_false_by_counterexample_even_if_coverage_incomplete() -> None:
    query = no_conflict_query(_request(("a.py",)))
    claim_cards = (_collision_claim_card("a.py"),)
    assert evaluate(query, claim_cards, _closure("incomplete[policy-gap]")) == Valuation("false")


def test_universal_is_true_only_under_complete_closure_with_no_counterexample() -> None:
    query = no_conflict_query(_request(("a.py",)))
    assert evaluate(query, (), _closure("complete")) == Valuation("true")


def test_universal_is_unknown_when_closure_incomplete_and_no_counterexample() -> None:
    query = no_conflict_query(_request(("a.py",)))
    assert evaluate(query, (), _closure("incomplete[policy-gap]")) == Valuation(
        "unknown", "incomplete[policy-gap]"
    )
    assert evaluate(query, (), _closure("incomplete[stale-dep]")) == Valuation(
        "unknown", "incomplete[stale-dep]"
    )


def test_universal_propagates_the_new_carrier_reasons_verbatim() -> None:
    # The carrier relies on evaluate passing any non-complete completeness through as the
    # valuation reason, so the two new states reach the assessment with NO change to evaluate.
    query = no_conflict_query(_request(("a.py",)))
    assert evaluate(query, (), _closure("incomplete[pending]")) == Valuation(
        "unknown", "incomplete[pending]"
    )
    assert evaluate(query, (), _closure("not_applicable[out-of-scope]")) == Valuation(
        "unknown", "not_applicable[out-of-scope]"
    )


def test_universal_is_unknown_when_no_closure_entry_for_the_query() -> None:
    query = no_conflict_query(_request(("a.py",)))
    assert evaluate(query, (), ()) == Valuation("unknown", "incomplete[policy-gap]")


def test_universal_is_false_by_counterexample_even_under_complete_closure() -> None:
    query = no_conflict_query(_request(("a.py",)))
    claim_cards = (_collision_claim_card("a.py"),)
    # a counterexample falsifies the universal even when coverage is complete:
    # `refutes` must take priority over `complete`.
    assert evaluate(query, claim_cards, _closure("complete")) == Valuation("false")
