from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, cast

import pytest

from teamctx.ambient import (
    BaselineMaterial,
    build_delta_document,
    compute_baseline_material,
    compute_deltas,
    deltas_from_signals,
    finding_key,
)
from teamctx.assessment import assess
from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceFamily, SourceSignal, SourceStatus
from teamctx.core.kinds import (
    CARD_KINDS,
    CHECK_COPY,
    DOCS_FAILURE_COPY,
    FORGE_REVIEW_SOURCE_CONTRACT,
    IMPORTANT_CHECKS,
    CardKind,
)

ROOT = Path(__file__).resolve().parent.parent
KIND_PATH = ROOT / "src/teamctx/core/kinds.py"
OBSERVED_AT = "2026-07-08T00:00:00Z"
EM_DASH = chr(0x2014)


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="contract-conformance",
        repo="acme/widgets",
        forge="github",
        branch="feature",
        task="work",
        paths=["src/app.py"],
        linked_issues=["#42"],
        input_provenance={"issue:#42": "your branch name"},
        requested_at=OBSERVED_AT,
        requesting_principal=None,
    )


def _signal(kind: CardKind) -> SourceSignal:
    scope: dict[str, Any]
    if kind.check_id == "conflict":
        scope = {
            "provider": "github",
            "repo": "acme/widgets",
            "pr_number": 7,
            "files": ["src/app.py"],
            "url": "https://example.invalid/pr/7",
        }
    elif kind.check_id == "criteria":
        scope = {
            "repo": "acme/widgets",
            "issue": "#42",
            "url": "https://example.invalid/issues/42",
        }
    elif kind.check_id == "docs":
        scope = {
            "repo": "acme/widgets",
            "doc": "docs/spec.md",
            "superseded_by": "docs/spec-v2.md",
            "url": "docs/spec-v2.md",
        }
    else:
        scope = {
            "repo": "acme/widgets",
            "gate": "build",
            "url": "https://example.invalid/actions/1",
        }
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id=f"sig_{kind.check_id}_sample",
        signal_type=kind.signal_type,  # type: ignore[arg-type]
        source_family=cast(SourceFamily, kind.deps_family),
        scope=scope,
        evidence_summary=_evidence_summary(kind.check_id),
        source_display=_source_display(kind.check_id),
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at=OBSERVED_AT,
        observed_at=OBSERVED_AT,
        expires_at="next_refresh",
        policy=metadata_only_policy(f"{kind.check_id} metadata is evidence"),
    )


def _mutated_signal(kind: CardKind) -> SourceSignal:
    signal = _signal(kind)
    scope = dict(signal.scope)
    if kind.check_id == "conflict":
        scope["files"] = ["src/other.py"]
    elif kind.check_id == "criteria":
        scope["issue"] = "#99"
    elif kind.check_id == "docs":
        scope.pop("doc")
    else:
        scope["gate"] = ""
    return signal.model_copy(update={"scope": scope})


def _status(kind: CardKind) -> SourceStatus:
    return source_status(
        source_id=f"{kind.check_id}-probe",
        source_family=cast(SourceFamily, kind.deps_family),
        scope={"repo": "acme/widgets"},
        status="fresh",
        observed_at=OBSERVED_AT,
        safe_user_message="checked",
        visibility="silent",
        policy_reason="status only",
    )


def _evidence_summary(check: str) -> str:
    if check == "conflict":
        return "Open PR #7 changed src/app.py."
    if check == "criteria":
        return "Issue #42 acceptance criteria changed."
    if check == "docs":
        return "docs/spec.md was superseded by docs/spec-v2.md."
    return "Check 'build' is failing on this branch."


def _source_display(check: str) -> str:
    if check == "conflict":
        return "GitHub PR #7"
    if check == "criteria":
        return "GitHub issue #42"
    if check == "docs":
        return "docs/spec.md"
    return "CI: build"


def _copy_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, tuple):
        strings: list[str] = []
        for item in value:
            strings.extend(_copy_strings(item))
        return strings
    if is_dataclass(value):
        strings = []
        for field in fields(value):
            strings.extend(_copy_strings(getattr(value, field.name)))
        return strings
    return []


def test_check_contract_module_stays_pure() -> None:
    text = KIND_PATH.read_text(encoding="utf-8")
    banned_imports = (
        "from pathlib",
        "import pathlib",
        "import os",
        "import subprocess",
        "import tempfile",
        "import time",
        "from datetime",
        "import datetime",
        "import random",
        "import secrets",
    )

    for banned in banned_imports:
        assert banned not in text


def test_every_check_declares_the_full_contract_shape() -> None:
    assert {kind.check_id for kind in CARD_KINDS} == {"conflict", "criteria", "docs", "gate"}

    for kind in CARD_KINDS:
        assert kind.id == kind.check_id
        assert kind.contract_version == 1
        assert kind.claim.card_predicate
        assert kind.claim.query_predicate
        assert kind.claim.proposition
        assert kind.consumes
        assert kind.query_predicate in kind.closure.propositions
        assert kind.copy is CHECK_COPY[kind.check_id]
        assert kind.identity.key_scope_fields
        assert kind.profile in {"reflex", "full"}
        assert kind.lane in {"important", "fyi"}
        assert kind.config_schema.options == ()


def test_closure_completeness_is_declared_for_every_registered_query() -> None:
    request = _request()

    for kind in CARD_KINDS:
        query = kind.query(request)
        assert query.predicate in kind.closure.propositions
        assert len(kind.closure.propositions) == 1


def test_copy_tables_have_no_em_dashes() -> None:
    strings: list[str] = []
    for kind in CARD_KINDS:
        strings.extend(_copy_strings(kind.copy))
    strings.extend(_copy_strings(FORGE_REVIEW_SOURCE_CONTRACT))

    assert strings
    assert all(EM_DASH not in text for text in strings)


def test_docs_source_status_copy_is_keyed_by_source_id_and_status() -> None:
    assert DOCS_FAILURE_COPY == {
        ("docs_supersession", "unavailable"): "couldn't read the local docs folder",
        ("docs_supersession", "stale"): "couldn't fully check the local docs folder",
        ("confluence_pages", "unavailable"): "couldn't reach Confluence",
        ("confluence_pages", "stale"): "couldn't fully check Confluence",
    }


def test_advisory_copy_is_owned_by_the_source_contract() -> None:
    check_owned_copy = "\n".join(
        text for kind in CARD_KINDS for text in _copy_strings(kind.copy)
    )
    source_copy = "\n".join(_copy_strings(FORGE_REVIEW_SOURCE_CONTRACT))

    assert "Your own open" not in check_owned_copy
    assert "Your own open" in source_copy


@pytest.mark.parametrize("kind", CARD_KINDS, ids=lambda kind: kind.check_id)
def test_derive_and_render_are_deterministic(kind: CardKind) -> None:
    request = _request()
    signal = _signal(kind)
    before = signal.model_dump(mode="json")

    first = kind.derive(request, signal)
    second = kind.derive(request, signal)

    assert first == second
    assert signal.model_dump(mode="json") == before
    assert first is not None
    assert kind.render(first) == kind.render(second)


@pytest.mark.parametrize("kind", CARD_KINDS, ids=lambda kind: kind.check_id)
def test_mutating_a_claim_input_stops_the_claim(kind: CardKind) -> None:
    assert kind.derive(_request(), _signal(kind)) is not None
    assert kind.derive(_request(), _mutated_signal(kind)) is None


@pytest.mark.parametrize("kind", CARD_KINDS, ids=lambda kind: kind.check_id)
def test_identity_fields_exist_in_rendered_card_scope(kind: CardKind) -> None:
    claim = kind.derive(_request(), _signal(kind))
    assert claim is not None

    card = kind.render(claim)

    for field_name in kind.identity.all_scope_fields:
        assert field_name in card.scope


@pytest.mark.parametrize("kind", CARD_KINDS, ids=lambda kind: kind.check_id)
def test_declared_identity_round_trips_through_baseline_and_delta(kind: CardKind) -> None:
    request = _request()
    answer = broker_answer(request, [_signal(kind)], [_status(kind)])

    material = compute_baseline_material(answer)
    check_material = next(check for check in material.checks if check.check == kind.check_id)
    assert len(check_material.findings) == 1

    card = next(
        card for card in answer.selection.cards if card.reason_code.startswith(kind.reason_prefix)
    )
    assert check_material.findings[0].key == finding_key(kind.check_id, card.scope)

    deltas = compute_deltas(BaselineMaterial(), material)
    check_deltas = tuple(delta for delta in deltas if delta.check == kind.check_id)
    assert len(check_deltas) == 1
    assert check_deltas[0].direction == "appear"

    delta_document = build_delta_document(request, check_deltas, observed_at=OBSERVED_AT)
    assert deltas_from_signals(delta_document.source_signals) == check_deltas

    with_delta = broker_answer(
        request,
        [*_signal_tuple(kind), *delta_document.source_signals],
        [_status(kind)],
    )
    assert assess(with_delta).deltas == check_deltas


def _signal_tuple(kind: CardKind) -> tuple[SourceSignal, ...]:
    return (_signal(kind),)


def test_important_checks_are_derived_from_lanes() -> None:
    assert frozenset(kind.check_id for kind in CARD_KINDS if kind.lane == "important") == (
        IMPORTANT_CHECKS
    )
