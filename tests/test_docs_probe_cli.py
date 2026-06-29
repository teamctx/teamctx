from click.testing import CliRunner

from teamctx.cli import main


def test_docs_probe_surfaces_superseded_card_and_verdict(tmp_path, monkeypatch) -> None:
    root = tmp_path / "docs" / "superpowers" / "specs"
    root.mkdir(parents=True)
    (root / "old.md").write_text(
        "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n# Old\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        [
            "dev", "docs-probe",
            "--repo", "tempo-64/model-citizens",
            "--root", "docs/superpowers",
            "--path", "docs/superpowers/specs/old.md",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Before you start, here is what to handle first:" in result.output
    assert "docs/superpowers/research/new.md" in result.output  # names the current doc
    assert "rely on the current one instead" in result.output  # the action phrase


def test_docs_probe_with_no_supersession_is_clean(tmp_path, monkeypatch) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "fine.md").write_text("# nothing declared\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["dev", "docs-probe", "--repo", "owner/name", "--root", "docs", "--path", "docs/fine.md"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output


def test_docs_probe_normalizes_dot_slash_path(tmp_path, monkeypatch) -> None:
    # a leading ./ on --path must still match the scanned repo-relative doc (normalization).
    root = tmp_path / "docs" / "superpowers" / "specs"
    root.mkdir(parents=True)
    (root / "old.md").write_text(
        "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n# Old\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        [
            "dev", "docs-probe",
            "--repo", "tempo-64/model-citizens",
            "--root", "docs/superpowers",
            "--path", "./docs/superpowers/specs/old.md",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "docs/superpowers/research/new.md" in result.output  # the finding still fires
