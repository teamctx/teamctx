"""The work-start use case: inputs -> unified context text.

One application-level function that ties the connector runner, the broker, governance
authority, and the human-plane renderer into the single "produce the work-start answer"
operation. Every transport — the CLI and the MCP server — calls this, so they deliver an
identical answer over one code path.
"""

from __future__ import annotations

from pathlib import Path

from teamctx.connectors.declared_authority import load_declared_authority
from teamctx.contract_render import render_broker_answer
from teamctx.core.broker import BrokerAnswer, broker_answer_from_documents
from teamctx.runner import WorkStartInputs, run_work_start_connectors

DEFAULT_AUTHORITY_PATH = Path(".teamctx/authority.json")


def work_start_answer(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path = DEFAULT_AUTHORITY_PATH,
    project_root: Path = Path("."),
) -> BrokerAnswer:
    """Run every applicable connector, compose, and evaluate — returning the structured
    broker answer (cards + honest coverage + one verdict per check). Transports render it;
    the hook maps it to a signal."""

    request_context, documents = run_work_start_connectors(
        inputs, observed_at=observed_at, project_root=project_root
    )
    declarations = load_declared_authority(authority_path)
    return broker_answer_from_documents(request_context, documents, declarations)


def render_work_start(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path = DEFAULT_AUTHORITY_PATH,
    project_root: Path = Path("."),
) -> str:
    """Render the work-start answer (cards + honest coverage + one verdict per check) as text."""

    answer = work_start_answer(
        inputs, observed_at=observed_at, authority_path=authority_path, project_root=project_root
    )
    return render_broker_answer(answer)
