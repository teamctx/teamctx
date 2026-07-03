from __future__ import annotations

import pytest

from teamctx.onboard import (
    _LEGACY_SNIPPET_BODY,
    _SNIPPET_END,
    _SNIPPET_HEADING,
    _SNIPPET_START,
    CLAUDE_MD_SNIPPET,
    SnippetState,
    classify_claude_md,
)


@pytest.mark.parametrize(
    ("existing", "state"),
    [
        (
            f"# Project\n\n{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_END}\n",
            "current",
        ),
        (
            f"{_SNIPPET_START}\n{_LEGACY_SNIPPET_BODY}{_SNIPPET_END}\n",
            "outdated",
        ),
        (
            f"{_SNIPPET_START}\n{_SNIPPET_HEADING}\nI rewrote this.\n{_SNIPPET_END}\n",
            "edited",
        ),
        (
            f"{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_START}\n{_SNIPPET_END}\n",
            "conflicted_markers",
        ),
        (
            f"# Project\n\n{_LEGACY_SNIPPET_BODY}\n## Other\n",
            "legacy",
        ),
        (
            f"# Project\n\n{_SNIPPET_HEADING}\nMy own setup note.\n",
            "edited_heading",
        ),
        ("# Project\n\nNothing about teamctx here.\n", "absent"),
    ],
)
def test_classify_claude_md_states(existing: str, state: SnippetState) -> None:
    assert classify_claude_md(existing) == state
