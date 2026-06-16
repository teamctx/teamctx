"""File-backed Core Contract document helpers outside the pure core package."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from teamctx.core.contracts import CoreContractDocument, load_core_contract_document


class ContractDocumentError(ValueError):
    """Raised when a Core Contract document cannot be loaded or written."""


def load_contract_document(path: Path) -> CoreContractDocument:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractDocumentError(f"Could not read contract document: {path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractDocumentError(f"Contract document is not valid JSON: {path}") from exc

    try:
        return load_core_contract_document(data)
    except ValidationError as exc:
        message = f"Contract document does not match Core Contract V0: {path}"
        raise ContractDocumentError(message) from exc


def write_contract_document(path: Path, document: CoreContractDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
