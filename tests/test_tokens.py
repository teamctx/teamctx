from __future__ import annotations

from pathlib import Path

from teamctx.tokens import resolve_atlassian_auth, resolve_github_token, resolve_token


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


def test_github_token_prefers_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    assert resolve_github_token() == "envtok"


def test_github_token_falls_back_to_gh_on_default(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TEAMCTX_DISABLE_GH_AUTH", raising=False)
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token() == "ghtok"


def test_github_token_no_gh_for_custom_env(monkeypatch) -> None:
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.delenv("MY_TOKEN_FILE", raising=False)
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token("MY_TOKEN") is None


def test_github_token_gh_skipped_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token() is None


def test_resolve_github_token_with_source_env(monkeypatch) -> None:
    from teamctx.tokens import resolve_github_token_with_source
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    assert resolve_github_token_with_source() == ("x", "env")


def test_resolve_github_token_with_source_file(monkeypatch, tmp_path) -> None:
    from teamctx.tokens import resolve_github_token_with_source
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    f = tmp_path / "t"
    f.write_text("secret\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(f))
    assert resolve_github_token_with_source() == ("secret", "file")


def test_resolve_github_token_with_source_none(monkeypatch) -> None:
    from teamctx.tokens import resolve_github_token_with_source
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    assert resolve_github_token_with_source() == (None, None)


def test_resolve_atlassian_auth_reads_email_and_token(monkeypatch) -> None:
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    monkeypatch.delenv("ATLASSIAN_API_TOKEN_FILE", raising=False)

    assert resolve_atlassian_auth() == ("person@example.com", "token")


def test_resolve_atlassian_auth_reads_token_file(monkeypatch, tmp_path: Path) -> None:
    token_file = tmp_path / "atlassian-token"
    token_file.write_text("file-token\n", encoding="utf-8")
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.delenv("ATLASSIAN_API_TOKEN", raising=False)
    monkeypatch.setenv("ATLASSIAN_API_TOKEN_FILE", str(token_file))

    assert resolve_atlassian_auth() == ("person@example.com", "file-token")


def test_resolve_atlassian_auth_returns_none_when_both_missing(monkeypatch) -> None:
    monkeypatch.delenv("ATLASSIAN_EMAIL", raising=False)
    monkeypatch.delenv("ATLASSIAN_API_TOKEN", raising=False)
    monkeypatch.delenv("ATLASSIAN_API_TOKEN_FILE", raising=False)

    assert resolve_atlassian_auth() is None


def test_resolve_atlassian_auth_returns_none_for_exactly_one_half(monkeypatch) -> None:
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.delenv("ATLASSIAN_API_TOKEN", raising=False)
    monkeypatch.delenv("ATLASSIAN_API_TOKEN_FILE", raising=False)
    assert resolve_atlassian_auth() is None

    monkeypatch.delenv("ATLASSIAN_EMAIL", raising=False)
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    assert resolve_atlassian_auth() is None
