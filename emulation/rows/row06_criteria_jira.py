"""Row 6: Criteria, Jira (the unconfigured-Jira KEY-N disabled note; the mixed-family no-false-
clear case; the fire path with the pinned operation order once write scope is verified).

Honest stub: the Jira connector does not exist yet, so the criteria fire path and the live read
sub-checks cannot run. It waits for the Jira connector and reports SKIP until then, never a
fabricated PASS.
"""

from __future__ import annotations

from emulation.evidence import RowResult, skipped

ROW_ID = "06"
TITLE = "Criteria, Jira"
WAITS_FOR = "the Jira connector (the S11 Jira/Confluence slice)"


def run_offline() -> RowResult:
    return skipped(ROW_ID, TITLE, f"requires {WAITS_FOR}")
