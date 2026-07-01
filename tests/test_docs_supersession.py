import pytest

from teamctx.connectors.docs import (
    default_doc_reader,
    parse_frontmatter,
    parse_superseded_docs,
    run_docs_supersession_probe,
)
from teamctx.connectors.docs_supersession import (
    SupersededDoc,
    normalize_superseded_docs,
    unavailable_docs_document,
)
from teamctx.core.contracts import RequestContext


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="tempo-64/model-citizens",
        branch=None,
        task="work",
        paths=["docs/superpowers/specs/old.md"],
        linked_issues=[],
        requested_at="2026-06-20T00:00:00Z",
        requesting_principal=None,
    )


def test_parse_frontmatter_reads_superseded_by() -> None:
    text = "---\nsuperseded_by: docs/new.md\ntitle: Old design\n---\n\n# Body\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md", "title": "Old design"}


def test_parse_frontmatter_absent_block_is_empty() -> None:
    assert parse_frontmatter("# No frontmatter here\n") == {}


def test_parse_frontmatter_ignores_non_kv_and_stops_at_close() -> None:
    text = "---\nsuperseded_by: docs/new.md\n---\nsuperseded_by: docs/IGNORED.md\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md"}


def test_normalize_emits_doc_superseded_signal_with_scope() -> None:
    doc = SupersededDoc(
        repo="tempo-64/model-citizens",
        doc="docs/superpowers/specs/old.md",
        superseded_by="docs/superpowers/research/new.md",
    )
    document = normalize_superseded_docs(
        _request(), [doc], observed_at="2026-06-20T00:00:00Z", relied_on_doc_in_scope=True
    )
    assert len(document.source_signals) == 1
    signal = document.source_signals[0]
    assert signal.signal_type == "doc_superseded"
    assert signal.source_family == "docs"
    assert signal.scope["repo"] == "tempo-64/model-citizens"
    assert signal.scope["doc"] == "docs/superpowers/specs/old.md"
    assert signal.scope["superseded_by"] == "docs/superpowers/research/new.md"
    assert any(s.source_family == "docs" and s.status == "fresh" for s in document.source_statuses)


def test_unavailable_docs_document_reports_status_only() -> None:
    document = unavailable_docs_document(
        _request(),
        repo="tempo-64/model-citizens",
        observed_at="2026-06-20T00:00:00Z",
        safe_user_message="Docs are unavailable at the configured root.",
    )
    assert document.source_signals == []
    assert document.source_statuses[0].status == "unavailable"


def test_parse_superseded_docs_keeps_only_declared() -> None:
    files = [
        (
            "docs/superpowers/specs/old.md",
            "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n# Old\n",
        ),
        ("docs/superpowers/specs/current.md", "# No frontmatter\n"),
    ]
    docs = parse_superseded_docs(repo="tempo-64/model-citizens", files=files)
    assert len(docs) == 1
    assert docs[0].doc == "docs/superpowers/specs/old.md"
    assert docs[0].superseded_by == "docs/superpowers/research/new.md"


def test_probe_uses_injected_reader_and_emits_signal() -> None:
    def reader(root: str) -> list[tuple[str, str]]:
        assert root == "docs/superpowers"
        return [
            (
                "docs/superpowers/specs/old.md",
                "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n",
            )
        ]

    document = run_docs_supersession_probe(
        repo="tempo-64/model-citizens",
        root="docs/superpowers",
        request_context=_request(),
        observed_at="2026-06-20T00:00:00Z",
        reader=reader,
    )
    assert len(document.source_signals) == 1
    assert document.source_signals[0].scope["doc"] == "docs/superpowers/specs/old.md"


def test_default_reader_scans_base_dir_not_cwd(tmp_path, monkeypatch) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "old.md").write_text("---\nsuperseded_by: docs/new.md\n---\n", encoding="utf-8")
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)  # process cwd is NOT the project root
    document = run_docs_supersession_probe(
        repo="r", root="docs", base_dir=tmp_path,
        request_context=_request(), observed_at="2026-06-20T00:00:00Z",
    )
    assert len(document.source_signals) == 1
    assert document.source_signals[0].scope["doc"] == "docs/old.md"


def test_missing_docs_dir_is_unavailable_not_clear(tmp_path) -> None:
    document = run_docs_supersession_probe(
        repo="r", root="docs", base_dir=tmp_path,  # tmp_path has no docs/ dir
        request_context=_request(), observed_at="2026-06-20T00:00:00Z",
    )
    assert document.source_signals == []
    assert document.source_statuses[0].status == "unavailable"


def _request_with_paths(paths: list[str]) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t",
        repo="tempo-64/model-citizens", branch=None, task="work", paths=paths,
        linked_issues=[], requested_at="2026-06-20T00:00:00Z", requesting_principal=None,
    )


def test_normalize_not_applicable_when_no_relied_on_doc_in_scope() -> None:
    document = normalize_superseded_docs(
        _request(), [], observed_at="2026-06-20T00:00:00Z", relied_on_doc_in_scope=False
    )
    assert document.source_statuses[0].status == "not_applicable"


def test_probe_not_applicable_when_scanned_docs_not_in_scope() -> None:
    # a docs root is scanned, but none of the files in scope are docs we rely on.
    reader = lambda root: [("docs/guide.md", "# nothing declared\n")]  # noqa: E731
    document = run_docs_supersession_probe(
        repo="o/n", root="docs", request_context=_request_with_paths(["src/a.py"]),
        observed_at="2026-06-20T00:00:00Z", reader=reader,
    )
    assert document.source_signals == []
    assert document.source_statuses[0].status == "not_applicable"


def test_probe_fresh_when_a_scanned_doc_is_in_scope() -> None:
    reader = lambda root: [("docs/guide.md", "# nothing declared\n")]  # noqa: E731
    document = run_docs_supersession_probe(
        repo="o/n", root="docs", request_context=_request_with_paths(["docs/guide.md"]),
        observed_at="2026-06-20T00:00:00Z", reader=reader,
    )
    assert document.source_statuses[0].status == "fresh"


def test_default_reader_emits_repo_relative_for_absolute_root(tmp_path) -> None:
    # an absolute docs_root must still emit repo-relative POSIX paths, or the in-scope check and
    # the card derivation both miss and a relied-on superseded doc reads not_applicable.
    docs = tmp_path / "docs"
    docs.mkdir()
    body = "---\nsuperseded_by: docs/new.md\n---\n"
    (docs / "old.md").write_text(body, encoding="utf-8")
    files = default_doc_reader(str(tmp_path / "docs"), base_dir=tmp_path)  # absolute root
    assert files == [("docs/old.md", body)]


def test_default_reader_fails_closed_for_docs_root_outside_base(tmp_path) -> None:
    outside = tmp_path / "outside" / "docs"
    outside.mkdir(parents=True)
    (outside / "x.md").write_text("# x\n", encoding="utf-8")
    base = tmp_path / "project"
    base.mkdir()
    with pytest.raises(FileNotFoundError):
        default_doc_reader(str(outside), base_dir=base)  # escapes the project root -> fail closed


def test_probe_absolute_docs_root_still_finds_superseded_in_scope(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "old.md").write_text("---\nsuperseded_by: docs/new.md\n---\n", encoding="utf-8")
    document = run_docs_supersession_probe(
        repo="o/n", root=str(tmp_path / "docs"),  # absolute
        request_context=_request_with_paths(["docs/old.md"]),
        observed_at="2026-06-20T00:00:00Z", base_dir=tmp_path,
    )
    assert len(document.source_signals) == 1
    assert document.source_signals[0].scope["doc"] == "docs/old.md"
    assert document.source_statuses[0].status == "fresh"


def test_default_reader_fails_closed_for_symlink_escaping_base(tmp_path) -> None:
    base = tmp_path / "project"
    docs = base / "docs"
    docs.mkdir(parents=True)
    outside = tmp_path / "outside.md"  # inside tmp_path but OUTSIDE the project root
    outside.write_text("---\nsuperseded_by: x\n---\n", encoding="utf-8")
    try:
        (docs / "escape.md").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")
    with pytest.raises(FileNotFoundError):
        default_doc_reader("docs", base_dir=base)  # a doc resolving outside base -> fail closed
