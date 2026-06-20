"""Narrow docs-supersession probe: read declared supersession from markdown frontmatter."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from teamctx.connectors.docs_supersession import (
    SupersededDoc,
    normalize_superseded_docs,
    unavailable_docs_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading ``---`` fenced ``key: value`` block. No YAML dependency: only
    top-level string scalars are read, the block ends at the first closing ``---``, and a
    file without a leading ``---`` has no frontmatter."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


# (repo-relative-posix-path, file-text) pairs under the docs root.
DocReader = Callable[[str], Iterable[tuple[str, str]]]


def run_docs_supersession_probe(
    *,
    repo: str,
    root: str,
    request_context: RequestContext,
    observed_at: str,
    reader: DocReader | None = None,
) -> CoreContractDocument:
    read = reader if reader is not None else default_doc_reader
    try:
        files = list(read(root))
    except OSError:
        return unavailable_docs_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="Docs are unavailable at the configured root.",
        )
    superseded = parse_superseded_docs(repo=repo, files=files)
    return normalize_superseded_docs(request_context, superseded, observed_at=observed_at)


def parse_superseded_docs(
    *, repo: str, files: Iterable[tuple[str, str]]
) -> list[SupersededDoc]:
    docs: list[SupersededDoc] = []
    for rel_path, text in files:
        target = parse_frontmatter(text).get("superseded_by")
        if not target:
            continue
        docs.append(
            SupersededDoc(
                repo=repo,
                doc=PurePosixPath(rel_path).as_posix(),
                superseded_by=target,
            )
        )
    return docs


def default_doc_reader(root: str) -> list[tuple[str, str]]:
    """Yield (repo-relative-posix-path, text) for every ``*.md`` under ``root``. Run from the
    repo root so that paths match the ``--path`` a caller passes."""

    base = Path(root)
    return [(p.as_posix(), p.read_text(encoding="utf-8")) for p in sorted(base.rglob("*.md"))]
