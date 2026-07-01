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
    scanned_paths = {rel_path for rel_path, _ in files}
    relied_on_in_scope = bool(scanned_paths & set(request_context.paths))
    return normalize_superseded_docs(
        request_context,
        superseded,
        observed_at=observed_at,
        relied_on_doc_in_scope=relied_on_in_scope,
    )


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
    repo-relative ``--path`` a caller passes, regardless of how ``root`` is spelled (relative or
    absolute) or the process working directory. A missing docs directory, or a docs root that
    resolves OUTSIDE the project root, raises ``FileNotFoundError`` so the probe reports it as
    unavailable (honest UNKNOWN) rather than a silent all-clear or an unmatchable absolute path."""

    base = base_dir.resolve()
    docs_dir = (base_dir / root).resolve()
    if not docs_dir.is_dir():
        raise FileNotFoundError(docs_dir)
    try:
        docs_dir.relative_to(base)
    except ValueError as exc:
        raise FileNotFoundError(docs_dir) from exc
    files: list[tuple[str, str]] = []
    for path in sorted(docs_dir.rglob("*.md")):
        repo_relative = path.resolve().relative_to(base).as_posix()
        files.append((repo_relative, path.read_text(encoding="utf-8")))
    return files
