"""Unit tests for the typed-proposition seam."""

from __future__ import annotations

import pytest

from teamctx.core.prop import Prop, SubjectRef


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
