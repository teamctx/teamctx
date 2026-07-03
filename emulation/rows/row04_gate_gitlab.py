"""Row 4: Gate, GitLab (the P0 scenarios: pinned cancel recipe; zero-pipelines reads a disabled
note, never clear, the other half of the GitHub/GitLab asymmetry).

Honest stub: the GitLab pipeline connector does not exist yet, so this row cannot drive a real
pipeline. It waits for that connector and reports SKIP until then, never a fabricated PASS.
"""

from __future__ import annotations

from emulation.evidence import RowResult, skipped

ROW_ID = "04"
TITLE = "Gate, GitLab"
WAITS_FOR = "the GitLab pipeline connector (the S9b/S10 GitLab slice)"


def run_offline() -> RowResult:
    return skipped(ROW_ID, TITLE, f"requires {WAITS_FOR}")
