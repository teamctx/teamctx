"""The evidence engine, built on the real broker.

A deconfounded A/B: for each scenario, a *baseline* prompt (task only) and a *context*
prompt (the same task plus the REAL work-start answer from ``broker_answer``). Whether
teamctx context changes an agent's behavior is measured against the live engine, not a
prototype stand-in. Scenarios are expressed in the contracts model, so there is one model
end to end.
"""

from __future__ import annotations

__all__ = [
    "EvalScenario",
    "ScenarioExport",
    "export_eval_pack",
    "load_scenario",
    "render_baseline_prompt",
    "render_context_prompt",
]

from teamctx.eval.pack import ScenarioExport, export_eval_pack
from teamctx.eval.prompts import render_baseline_prompt, render_context_prompt
from teamctx.eval.scenario import EvalScenario, load_scenario
