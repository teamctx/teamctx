from __future__ import annotations

from pathlib import Path

from teamctx.tokens import resolve_token


def test_env_value_wins(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_token() == "from-env"


def test_falls_back_to_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    token_file = tmp_path / "tok"
    token_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))
    assert resolve_token() == "from-file"


def test_nothing_set_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_token() is None


def test_missing_file_returns_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(tmp_path / "missing"))
    assert resolve_token() is None


def test_custom_token_env_reads_own_name(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.delenv("MY_TOKEN_FILE", raising=False)
    monkeypatch.setenv("MY_TOKEN", "custom-value")
    assert resolve_token("MY_TOKEN") == "custom-value"


def test_custom_token_env_falls_back_to_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MY_TOKEN", raising=False)
    token_file = tmp_path / "my_tok"
    token_file.write_text("custom-from-file\n", encoding="utf-8")
    monkeypatch.setenv("MY_TOKEN_FILE", str(token_file))
    assert resolve_token("MY_TOKEN") == "custom-from-file"


def test_custom_token_env_nothing_set_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.delenv("MY_TOKEN_FILE", raising=False)
    assert resolve_token("MY_TOKEN") is None
