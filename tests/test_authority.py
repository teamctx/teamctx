"""Authority: evidence vs. governance. Surface conflict, never adjudicate (pillar S2)."""

from __future__ import annotations

from teamctx.core.authority import AuthorityDecl, AuthorityEntry, assess_authority


def _decl(value: str, priority: int, fresh: bool, source: str) -> AuthorityDecl:
    return AuthorityDecl(
        subject="rounding-cap", source=source, priority=priority, value=value, fresh=fresh
    )


def test_unique_fresh_maximal_authority_resolves() -> None:
    decls = [_decl("3", priority=10, fresh=True, source="policy")]
    assert assess_authority("rounding-cap", decls) == AuthorityEntry(
        "rounding-cap", "resolved", "3"
    )


def test_two_fresh_maximal_with_divergent_values_is_conflicted_and_picks_nothing() -> None:
    decls = [
        _decl("5", priority=10, fresh=True, source="ticket-mirror"),
        _decl("3", priority=10, fresh=True, source="policy-mirror"),
    ]
    entry = assess_authority("rounding-cap", decls)
    assert entry.state == "conflicted"
    assert entry.value is None  # refuse to pick


def test_stale_high_priority_is_not_overridden_by_fresh_low_priority() -> None:
    # the policy-sensitive case: stale HIGH authority + fresh LOW authority.
    decls = [
        _decl("3", priority=10, fresh=False, source="policy"),  # authoritative but stale
        _decl("5", priority=1, fresh=True, source="ticket"),  # fresh but lower priority
    ]
    entry = assess_authority("rounding-cap", decls)
    assert entry.state == "unknown[stale-authority]"
    assert entry.value is None  # NOT resolved to the fresh low-priority ticket


def test_no_applicable_declaration_is_missing() -> None:
    assert assess_authority("rounding-cap", []) == AuthorityEntry("rounding-cap", "missing", None)


def test_only_declarations_for_the_subject_apply() -> None:
    decls = [AuthorityDecl(subject="other", source="x", priority=10, value="9", fresh=True)]
    assert assess_authority("rounding-cap", decls).state == "missing"
