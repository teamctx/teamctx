"""Unit tests for the typed-proposition seam."""

from __future__ import annotations

import pytest

from teamctx.core.prop import Prop, SubjectRef, witnesses


def test_prop_shape_comes_from_the_predicate_registry() -> None:
    existential = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("a.py",)),
    )
    universal = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("a.py",)),
    )
    assert existential.shape == "existential"
    assert universal.shape == "universal"


def test_unregistered_predicate_is_rejected() -> None:
    bad = Prop(predicate="not_a_real_predicate", subject=SubjectRef(repo="svc"))
    with pytest.raises(ValueError, match="unregistered predicate"):
        _ = bad.shape


def test_collision_claim_refutes_the_no_conflict_universal() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py",)),
        args=("sig_pr_482_collision",),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py", "src/other.py")),
    )
    # A single existential counterexample refutes the universal — the polarity trap the
    # paper flags (a single-witness "True-only" scheme would mis-handle this universal).
    assert witnesses(claim, query) == "refutes"


def test_claim_over_unrelated_paths_is_not_a_witness() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc", paths=("src/auth/token.py",)),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc", paths=("src/unrelated.py",)),
    )
    assert witnesses(claim, query) == "unrelated"


def test_claim_in_a_different_repo_is_not_a_witness() -> None:
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo="svc-a", paths=("src/auth/token.py",)),
    )
    query = Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo="svc-b", paths=("src/auth/token.py",)),
    )
    assert witnesses(claim, query) == "unrelated"
