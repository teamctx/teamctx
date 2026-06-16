"""Pure fixture validation for the fixture-backed prototype."""

from __future__ import annotations

import json

from pydantic import ValidationError

from teamctx.core.models import Fixture


class FixtureError(ValueError):
    """Raised when a fixture cannot be loaded or does not satisfy the contract."""


def load_fixture_json(raw: str, *, source: str = "fixture") -> Fixture:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FixtureError(f"Fixture is not valid JSON: {source}") from exc
    return load_fixture_data(data, source=source)


def load_fixture_data(data: object, *, source: str = "fixture") -> Fixture:
    try:
        fixture = Fixture.model_validate(data)
    except ValidationError as exc:
        raise FixtureError(f"Fixture does not match the prototype contract: {source}") from exc

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
