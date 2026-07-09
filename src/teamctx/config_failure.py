"""Shared user-facing copy for team config failures and committed-semantics notices."""

from __future__ import annotations

CONFIG_DIRTY_NOTE = (
    "using the committed HEAD config; working-tree config changes take effect when committed"
)
COMMIT_CONFIG_TO_ACTIVATE_LINE = "commit .teamctx/config.json to activate the team's configuration"
TEAM_CONFIG_UPGRADE_LINE = (
    "your teamctx is behind this repo's team config; upgrade to run the team's checks"
)
ALLOW_DIRTY_CONFIG_BANNER = "using working-tree team config because --allow-dirty was set"


def format_config_failure(exc: Exception) -> str:
    """One formatter for CLI, MCP, and hook config failures."""

    return str(exc)
