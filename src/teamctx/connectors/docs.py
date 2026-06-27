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
    base_dir: Path = Path("."),
) -> CoreContractDocument:
    try:
        if reader is not None:
            files = list(reader(root))
        else:
            files = default_doc_reader(root, base_dir=base_dir)
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


def default_doc_reader(root: str, *, base_dir: Path = Path(".")) -> list[tuple[str, str]]:
    """Yield (repo-root-relative POSIX path, text) for every ``*.md`` under ``base_dir/root``.

    Paths are emitted relative to ``base_dir`` (the resolution/project root) so they match the
    ``--path`` a caller passes, regardless of the process working directory. A missing docs
    directory raises ``FileNotFoundError`` so the probe reports it as unavailable (honest
    UNKNOWN) rather than a silent all-clear from an empty scan."""

    docs_dir = base_dir / root
    if not docs_dir.is_dir():
        raise FileNotFoundError(docs_dir)
    files: list[tuple[str, str]] = []
    for path in sorted(docs_dir.rglob("*.md")):
        repo_relative = PurePosixPath(root) / path.relative_to(docs_dir).as_posix()
        files.append((repo_relative.as_posix(), path.read_text(encoding="utf-8")))
    return files
