"""Severity decomposition is deterministic and conformance-comparable (calibration deferred)."""

from __future__ import annotations

from teamctx.core.prop import Prop, SubjectRef
from teamctx.core.severity import compute_severity


def _claim(predicate: str, paths: tuple[str, ...]) -> Prop:
    return Prop(predicate=predicate, subject=SubjectRef(repo="r", paths=paths))


def test_collision_severity_conformance_golden() -> None:
    sev = compute_severity("pr_conflicts_with_path", _claim("pr_conflicts_with_path", ("a.py",)))
    # kind_base 0.8, magnitude_norm = 1/5 = 0.2, scope_mult 1.0
    # value = clamp01(0.8 * (1 + 0.5*0.2) * 1.0) = 0.88
    assert sev.kind_base == 0.8
    assert sev.magnitude_norm == 0.2
    assert sev.scope_mult == 1.0
    assert sev.value == 0.88


def test_severity_value_is_clamped_to_one() -> None:
    # five overlapping paths -> magnitude_norm clamps at 1.0; high kind_base stays <= 1.
    sev = compute_severity(
        "pr_conflicts_with_path",
        _claim("pr_conflicts_with_path", ("a", "b", "c", "d", "e", "f")),
    )
    assert sev.magnitude_norm == 1.0
    assert 0.0 <= sev.value <= 1.0


def test_each_kind_has_a_registered_base() -> None:
    from teamctx.core.severity import KIND_BASE

    for predicate in (
        "pr_conflicts_with_path",
        "issue_criteria_changed",
        "doc_superseded",
        "gate_failed",
    ):
        assert predicate in KIND_BASE


def test_unregistered_predicate_severity_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="no severity base"):
        compute_severity("nope", _claim("pr_conflicts_with_path", ("a.py",)))
