"""Tests for the evidence engine rebuilt on the real broker (foundation Phase 3)."""

from __future__ import annotations

import json

import pytest

from teamctx.core.contracts import RequestContext
from teamctx.eval.pack import export_eval_pack, run_one_scenario
from teamctx.eval.prompts import render_baseline_prompt, render_context_prompt
from teamctx.eval.scenario import EvalScenario, EvalScenarioError, load_scenario

OBSERVED = "2026-06-25T12:00:00Z"


def _collision_scenario_dict() -> dict:
    return {
        "scenario_id": "collision-on-core",
        "task": "Refactor select_context in src/teamctx/core/select.py.",
        "request": {
            "schema_version": "teamctx.request_context.v0",
            "request_id": "eval:collision",
            "repo": "teamctx/teamctx",
            "branch": "feature",
            "task": "Refactor select_context.",
            "paths": ["src/teamctx/core/select.py"],
            "linked_issues": [],
            "requested_at": OBSERVED,
            "requesting_principal": None,
        },
        "signals": [
            {
                "schema_version": "teamctx.source_signal.v0",
                "id": "sig_collision_1",
                "signal_type": "collision",
                "source_family": "git_hosting",
                "scope": {"repo": "teamctx/teamctx", "files": ["src/teamctx/core/select.py"]},
                "evidence_summary": "Open PR #9 changed src/teamctx/core/select.py.",
                "source_display": "GitHub PR #9",
                "freshness": "fresh",
                "confidence": "high",
                "visibility": "visible",
                "created_at": OBSERVED,
                "observed_at": OBSERVED,
                "expires_at": "next_refresh",
                "policy": {
                    "schema_version": "teamctx.policy_decision.v0",
                    "can_render_to_user": True,
                    "can_render_to_agent": True,
                    "can_include_source_text": False,
                    "requires_review_for_guidance": False,
                    "decision_reason": "metadata only",
                },
            }
        ],
        "statuses": [
            {
                "schema_version": "teamctx.source_status.v0",
                "source_id": "github_pr_metadata",
                "source_family": "git_hosting",
                "scope": {"repo": "teamctx/teamctx"},
                "status": "fresh",
                "last_checked_at": OBSERVED,
                "safe_user_message": "refreshed",
                "normal_context_visibility": "silent",
                "policy": {
                    "schema_version": "teamctx.policy_decision.v0",
                    "can_render_to_user": True,
                    "can_render_to_agent": True,
                    "can_include_source_text": False,
                    "requires_review_for_guidance": False,
                    "decision_reason": "metadata only",
                },
            }
        ],
        "workspace_files": [
            {"path": "src/teamctx/core/select.py", "content": "# the file under work\n"}
        ],
    }


def _write_scenario(tmp_path, data: dict, name: str = "scenario.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_scenario_validates_as_contracts_model(tmp_path) -> None:
    scenario = load_scenario(_write_scenario(tmp_path, _collision_scenario_dict()))
    assert isinstance(scenario, EvalScenario)
    assert isinstance(scenario.request, RequestContext)
    assert scenario.signals[0].signal_type == "collision"
    assert scenario.workspace_files[0].path == "src/teamctx/core/select.py"


def test_load_scenario_rejects_unknown_fields(tmp_path) -> None:
    bad = _collision_scenario_dict()
    bad["expected_cards"] = []  # the retired prototype field must not be accepted
    with pytest.raises(EvalScenarioError):
        load_scenario(_write_scenario(tmp_path, bad))


def test_baseline_prompt_has_task_and_no_context() -> None:
    scenario = _scenario()
    prompt = render_baseline_prompt(scenario)
    assert "Task:" in prompt
    assert "Working context" not in prompt  # baseline arm carries no teamctx output


def test_context_prompt_carries_the_real_derived_card() -> None:
    scenario = _scenario()
    prompt = render_context_prompt(scenario)
    # the card text is DERIVED by the real engine, not authored into the scenario
    # (the trailing period is stripped before the appended action, so no `.:` double punctuation)
    assert "Before you start, here is what to handle first:" in prompt
    assert "Open PR #9 changed src/teamctx/core/select.py" in prompt
    assert "look at it before you edit" in prompt  # the real action phrase, from broker_answer


def test_run_one_scenario_dispatches_variant() -> None:
    scenario = _scenario()
    assert run_one_scenario(scenario, variant="baseline") == render_baseline_prompt(scenario)
    assert run_one_scenario(scenario, variant="context") == render_context_prompt(scenario)
    with pytest.raises(ValueError):
        run_one_scenario(scenario, variant="bogus")


def test_export_pack_writes_both_arms_and_manifest(tmp_path) -> None:
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    _write_scenario(scenarios_dir, _collision_scenario_dict(), "01.json")
    output_dir = tmp_path / "out"
    exports = export_eval_pack(scenarios_dir, output_dir)
    assert len(exports) == 1
    assert exports[0].baseline_path.exists()
    assert exports[0].context_path.exists()
    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["scenarios"][0]["scenario_id"] == "collision-on-core"
    assert (output_dir / "score-sheet.csv").exists()
    # the context arm contains the real derived card
    assert "Open PR #9" in exports[0].context_path.read_text()


def test_export_pack_empty_dir_raises(tmp_path) -> None:
    with pytest.raises(ValueError):
        export_eval_pack(tmp_path, tmp_path / "out")


def test_shipped_example_scenario_is_valid_and_runs() -> None:
    """The checked-in example must stay loadable and produce a real context arm; it is the
    out-of-the-box proof that the evidence engine runs against the live engine."""

    from pathlib import Path

    example = Path(__file__).resolve().parents[1] / "examples" / "eval-scenarios"
    scenarios = sorted(example.glob("*.json"))
    assert scenarios, "no example scenarios shipped"
    for path in scenarios:
        scenario = load_scenario(path)
        context = render_context_prompt(scenario)
        # shipped scenario has a collision + gate failure -> heads-up headline
        assert "Before you start, here is what to handle first:" in context
        assert scenario.task in context


def _scenario() -> EvalScenario:
    import json as _json
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "s.json"
        path.write_text(_json.dumps(_collision_scenario_dict()), encoding="utf-8")
        return load_scenario(path)
