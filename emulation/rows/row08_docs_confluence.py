"""Row 8: Docs, Confluence (the reflex-skip note on a full work-start with profile=reflex; the
hook asserts docs SILENCE, since docs is not a glanceable check; openability recorded as a
live-verified boolean, never a committed clickable URL, program spec rev 2, P0-2/P2-2).

Honest stub: the Confluence connector does not exist yet, so this row cannot drive a real space.
It waits for that connector and reports SKIP until then, never a fabricated PASS.
"""

from __future__ import annotations

from emulation.evidence import RowResult, skipped

ROW_ID = "08"
TITLE = "Docs, Confluence"
WAITS_FOR = "the Confluence connector (the S11 Jira/Confluence slice)"


def run_offline() -> RowResult:
    return skipped(ROW_ID, TITLE, f"requires {WAITS_FOR}")
