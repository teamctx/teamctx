"""Row 2: Collision, GitLab (MR terminology, web_url, no gh-hint) plus the own-MR FYI sub-row.

Honest stub: GitLab own-detection is a distinct code path from GitHub (program spec rev 2, P1-3),
so it needs its own evidence and cannot be faked from the GitHub connector. It waits for the GitLab
merge-request connector. Until then this row reports SKIP, never a fabricated PASS.
"""

from __future__ import annotations

from emulation.evidence import RowResult, skipped

ROW_ID = "02"
TITLE = "Collision, GitLab"
WAITS_FOR = "the GitLab merge-request connector (the S9b/S10 GitLab slice)"


def run_offline() -> RowResult:
    return skipped(ROW_ID, TITLE, f"requires {WAITS_FOR}")
