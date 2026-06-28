from __future__ import annotations

from pathlib import Path

from teamctx.tokens import resolve_github_token


def test_env_value_wins(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_github_token() == "from-env"


def test_falls_back_to_file_then_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    token_file = tmp_path / "tok"
    token_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))
    assert resolve_github_token() == "from-file"

    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_github_token() is None

    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(tmp_path / "missing"))
    assert resolve_github_token() is None
