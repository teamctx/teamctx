"""The work-start transport: the command an agent runs to get context at work-start.

Tested network-free via the no-token path: with no credential, the source is
unavailable, and the command must degrade honestly (print incomplete coverage, exit 0)
rather than crash or block. Fail-safe and prints-never-blocks, proven without a network.
"""

from __future__ import annotations

from click.testing import CliRunner

from teamctx.cli import main


def test_work_start_with_no_token_degrades_honestly() -> None:
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "work-start",
            "--github-repo",
            "acme/widgets",
            "--path",
            "src/widgets/core.py",
            "--token-env",
            "TEAMCTX_DEFINITELY_UNSET_TOKEN",
        ],
    )

    assert result.exit_code == 0  # prints, never blocks
    assert "Working context" in result.output
    assert "Coverage" in result.output
    # no token => source unavailable => coverage incomplete => honest warning
    assert "not an all-clear" in result.output
