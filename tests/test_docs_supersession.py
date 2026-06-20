from teamctx.connectors.docs import parse_frontmatter


def test_parse_frontmatter_reads_superseded_by() -> None:
    text = "---\nsuperseded_by: docs/new.md\ntitle: Old design\n---\n\n# Body\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md", "title": "Old design"}


def test_parse_frontmatter_absent_block_is_empty() -> None:
    assert parse_frontmatter("# No frontmatter here\n") == {}


def test_parse_frontmatter_ignores_non_kv_and_stops_at_close() -> None:
    text = "---\nsuperseded_by: docs/new.md\n---\nsuperseded_by: docs/IGNORED.md\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md"}
