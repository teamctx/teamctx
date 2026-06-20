from teamctx.connectors.docs import parse_frontmatter
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
    document = normalize_superseded_docs(_request(), [doc], observed_at="2026-06-20T00:00:00Z")
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
