"""Pin the card-kind registry tables before (and across) the S6 consolidation.

S6 makes one ``CardKind`` entry carry every fact about a kind and DERIVES every other table
from ``CARD_KINDS`` at import. This test snapshots the exact table contents that exist on main
before the move as hardcoded literals, then asserts the live tables equal them. Before the
move the tables are the hand-written registries in prop/select/severity/assessment; after the
move they are derived in ``core/kinds.py``. The expected literals never change, so the refactor
is proven byte-identical: any derive that drifts from the pre-consolidation values fails here.
"""

from __future__ import annotations

# Pinned literals: the exact table contents on main before S6 consolidation.
EXPECTED_PREDICATE_REGISTRY: dict[str, str] = {
    "pr_conflicts_with_path": "existential",
    "no_pr_conflicts_with_paths": "universal",
    "issue_criteria_changed": "existential",
    "no_criteria_changed_for_issues": "universal",
    "doc_superseded": "existential",
    "no_superseded_docs": "universal",
    "gate_failed": "existential",
    "all_gates_pass": "universal",
}
EXPECTED_REFUTES_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pr_conflicts_with_path", "no_pr_conflicts_with_paths"),
        ("issue_criteria_changed", "no_criteria_changed_for_issues"),
        ("doc_superseded", "no_superseded_docs"),
        ("gate_failed", "all_gates_pass"),
    }
)
EXPECTED_DEPS_REGISTRY: dict[str, frozenset[str]] = {
    "no_pr_conflicts_with_paths": frozenset({"git_hosting"}),
    "no_criteria_changed_for_issues": frozenset({"issue_tracker"}),
    "no_superseded_docs": frozenset({"docs"}),
    "all_gates_pass": frozenset({"ci_deploy"}),
}
EXPECTED_KIND_BASE: dict[str, float] = {
    "pr_conflicts_with_path": 0.8,
    "issue_criteria_changed": 0.5,
    "doc_superseded": 0.4,
    "gate_failed": 0.7,
}
EXPECTED_LABELS: tuple[tuple[str, str], ...] = (
    ("Conflict check", "conflict"),
    ("Criteria check", "criteria"),
    ("Docs check", "docs"),
    ("Gate check", "gate"),
)


def test_predicate_registry_matches_pin() -> None:
    from teamctx.core.kinds import PREDICATE_REGISTRY

    assert dict(PREDICATE_REGISTRY) == EXPECTED_PREDICATE_REGISTRY


def test_refutes_pairs_match_pin() -> None:
    from teamctx.core.kinds import REFUTES_PAIRS

    assert REFUTES_PAIRS == EXPECTED_REFUTES_PAIRS


def test_deps_registry_matches_pin() -> None:
    from teamctx.core.kinds import DEPS_REGISTRY

    assert dict(DEPS_REGISTRY) == EXPECTED_DEPS_REGISTRY


def test_kind_base_matches_pin() -> None:
    from teamctx.core.kinds import KIND_BASE

    assert dict(KIND_BASE) == EXPECTED_KIND_BASE


def test_verdict_label_check_pairs_match_pin() -> None:
    from teamctx.core.kinds import LABEL_CHECK_PAIRS

    assert tuple(LABEL_CHECK_PAIRS) == EXPECTED_LABELS


def test_render_copy_has_one_entry_per_card_kind() -> None:
    from teamctx.contract_render import RENDER_COPY
    from teamctx.core.kinds import CARD_KINDS

    assert set(RENDER_COPY) == {kind.check_id for kind in CARD_KINDS}


def test_hook_gap_is_present_exactly_for_important_checks() -> None:
    from teamctx.assessment import IMPORTANT_CHECKS
    from teamctx.contract_render import RENDER_COPY

    with_hook_gap = {check for check, copy in RENDER_COPY.items() if copy.hook_gap is not None}
    assert with_hook_gap == set(IMPORTANT_CHECKS)
