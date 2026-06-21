from click.testing import CliRunner

from teamctx.cli import main


def test_gate_probe_surfaces_missed_gate_card_and_verdict(monkeypatch) -> None:
    # Inject a failing check-run by patching the probe's fetch at the github_checks boundary.
    import teamctx.connectors.github_checks as gc

    def fake_fetch(*, repo, ref, token, opener=None):  # type: ignore[no-untyped-def]
        return [("pytest", "https://gh/run/1")]

    monkeypatch.setattr(gc, "fetch_failing_check_runs", fake_fetch)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        ["gate-probe", "--repo", "teamctx/teamctx", "--ref", "build/x",
         "--path", "src/teamctx/core/select.py"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Gate check: NOT CLEAR" in result.output
    assert "pytest" in result.output


def test_gate_probe_without_token_degrades_honestly(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = CliRunner().invoke(
        main,
        ["gate-probe", "--repo", "teamctx/teamctx", "--ref", "build/x",
         "--path", "src/teamctx/core/select.py"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Gate check: UNKNOWN" in result.output  # absence is not an all-clear
