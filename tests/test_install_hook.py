from __future__ import annotations

import json

from click.testing import CliRunner

from teamctx.cli import main


def test_install_hook_writes_idempotent_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r1 = CliRunner().invoke(main, ["install-hook"])
    assert r1.exit_code == 0, r1.output
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pre = settings["hooks"]["PreToolUse"]
    assert any(
        h.get("matcher") == "Edit|Write|MultiEdit"
        and any(c.get("command") == "teamctx-hook" for c in h.get("hooks", []))
        for h in pre
    )
    r2 = CliRunner().invoke(main, ["install-hook"])  # idempotent: no duplicate
    assert r2.exit_code == 0, r2.output
    settings2 = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings2["hooks"]["PreToolUse"]) == len(pre)
    assert "work-start" in r1.output  # prints the portable instruction


def test_print_writes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["install-hook", "--print"])
    assert r.exit_code == 0
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert "teamctx-hook" in r.output


def test_install_hook_merges_existing_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": []}]}}), encoding="utf-8"
    )
    CliRunner().invoke(main, ["install-hook"])
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["model"] == "opus"  # preserved
    assert "Stop" in settings["hooks"]  # preserved
    assert "PreToolUse" in settings["hooks"]  # added


def test_malformed_settings_error_paths(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    p = tmp_path / ".claude" / "settings.json"
    p.parent.mkdir()
    p.write_text("[]", encoding="utf-8")  # valid JSON, not an object
    r = CliRunner().invoke(main, ["install-hook"])
    assert r.exit_code != 0 and "JSON object" in r.output
    p.write_text(json.dumps({"hooks": "bad"}), encoding="utf-8")  # hooks not a dict
    r = CliRunner().invoke(main, ["install-hook"])
    assert r.exit_code != 0 and "Fix or remove" in r.output
    p.write_text(json.dumps({"hooks": None}), encoding="utf-8")  # hooks explicitly null
    r = CliRunner().invoke(main, ["install-hook"])
    assert r.exit_code != 0 and "Fix or remove" in r.output
