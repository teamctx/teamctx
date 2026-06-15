"""Fixture loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from teamctx.core.models import Fixture


class FixtureError(ValueError):
    """Raised when a fixture cannot be loaded or does not satisfy the contract."""


def load_fixture(path: Path) -> Fixture:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureError(f"Could not read fixture: {path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"Fixture is not valid JSON: {path}") from exc

    try:
        fixture = Fixture.model_validate(data)
    except ValidationError as exc:
        raise FixtureError(f"Fixture does not match the prototype contract: {path}") from exc

    _validate_refs(fixture)
    return fixture


def _validate_refs(fixture: Fixture) -> None:
    known_refs = {signal.id for signal in fixture.source_signals}
    known_refs.update(record.id for record in fixture.guidance_records)

    for card in fixture.expected_cards:
        missing = [ref for ref in card.refs if ref not in known_refs]
        if missing:
            missing_refs = ", ".join(missing)
            raise FixtureError(f"Card {card.id} references unknown fixture ids: {missing_refs}")
