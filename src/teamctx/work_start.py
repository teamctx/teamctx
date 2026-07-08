"""The work-start use case: inputs -> unified context text.

One application-level function that ties the connector runner, the broker, governance
authority, and the human-plane renderer into the single "produce the work-start answer"
operation. Every transport (the CLI and the MCP server) calls this, so they deliver an
identical answer over one code path.
"""

from __future__ import annotations

from pathlib import Path

from teamctx.config_failure import format_config_failure
from teamctx.connectors.declared_authority import load_declared_authority
from teamctx.contract_render import render_broker_answer
from teamctx.core.authority import AuthorityDecl
from teamctx.core.broker import BrokerAnswer, broker_answer_from_documents
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.runner import WorkStartInputs, run_work_start_connectors
from teamctx.team_semantics import load_team_authority, semantics_notices


def render_with_config_notices(notices: tuple[str, ...], text: str) -> str:
    unique = tuple(dict.fromkeys(line for line in notices if line))
    if not unique:
        return text
    return "\n".join(unique) + "\n" + text


def ground_work_start(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    project_root: Path = Path("."),
) -> tuple[RequestContext, list[CoreContractDocument]]:
    """Ground the work: run every applicable connector against one shared request and return the
    request plus its connector documents, BEFORE composing. This is the one grounding seam the
    ambient hook needs: it can diff the composed answer against the session baseline and, when
    something changed, compose the SAME documents again with an appended delta document (no second
    network round). The answer functions below delegate here, so grounding stays identical."""

    return run_work_start_connectors(inputs, observed_at=observed_at, project_root=project_root)


def work_start_answer(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path | None = None,
    project_root: Path = Path("."),
    authority_declarations: list[AuthorityDecl] | None = None,
) -> BrokerAnswer:
    """Run every applicable connector, compose, and evaluate, returning the structured
    broker answer (cards + honest coverage + one verdict per check). Transports render it;
    the hook maps it to a signal. Authority defaults to ``project_root/.teamctx/authority.json``
    so it is resolved from the same root as config and docs, never the process cwd."""

    request_context, documents = ground_work_start(
        inputs, observed_at=observed_at, project_root=project_root
    )
    if authority_declarations is not None:
        declarations = authority_declarations
    elif authority_path is not None:
        declarations = load_declared_authority(authority_path)
    else:
        declarations = load_team_authority(
            project_root, allow_dirty=inputs.semantics_allow_dirty
        ).declarations
    return broker_answer_from_documents(
        request_context,
        documents,
        declarations,
        enabled_checks=inputs.enabled_checks,
        important_checks=inputs.important_checks,
        disabled_checks=inputs.disabled_checks,
    )


def render_work_start(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path | None = None,
    project_root: Path = Path("."),
) -> str:
    """Render the work-start answer (cards + honest coverage + one verdict per check) as text."""

    authority_notices: tuple[str, ...] = ()
    authority_declarations: list[AuthorityDecl] | None = None
    if authority_path is None:
        authority = load_team_authority(project_root, allow_dirty=inputs.semantics_allow_dirty)
        authority_notices = semantics_notices(
            authority=authority.file, allow_dirty=inputs.semantics_allow_dirty
        )
        authority_declarations = authority.declarations
    answer = work_start_answer(
        inputs,
        observed_at=observed_at,
        authority_path=authority_path,
        project_root=project_root,
        authority_declarations=authority_declarations,
    )
    return render_with_config_notices(
        (*inputs.semantics_notices, *authority_notices),
        render_broker_answer(answer),
    )


def render_config_failure(exc: Exception) -> str:
    return format_config_failure(exc)
