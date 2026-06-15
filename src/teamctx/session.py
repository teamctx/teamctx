"""Session-only context selection for the prototype."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from teamctx.core.models import SessionSelection


def default_session_root() -> Path:
    return Path(tempfile.gettempdir()) / "teamctx-sessions"


def session_path(session_id: str, *, root: Path | None = None) -> Path:
    base = root if root is not None else default_session_root()
    return base / f"{session_id}.json"


def read_session(session_id: str, *, root: Path | None = None) -> SessionSelection:
    path = session_path(session_id, root=root)
    if not path.exists():
        return SessionSelection(session_id=session_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return SessionSelection.model_validate(data)


def add_card_to_session(
    session_id: str,
    card_id: str,
    *,
    root: Path | None = None,
) -> SessionSelection:
    selection = read_session(session_id, root=root)
    if card_id not in selection.card_ids:
        selection.card_ids.append(card_id)

    path = session_path(session_id, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(selection.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return selection
