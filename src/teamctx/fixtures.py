"""File-backed fixture loading outside the pure core package."""

from __future__ import annotations

from pathlib import Path

from teamctx.core.fixtures import FixtureError, load_fixture_json
from teamctx.core.models import Fixture


def load_fixture(path: Path) -> Fixture:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureError(f"Could not read fixture: {path}") from exc
    return load_fixture_json(raw, source=str(path))


__all__ = ["FixtureError", "load_fixture"]
