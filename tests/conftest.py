import pytest


@pytest.fixture(autouse=True)
def _no_gh_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a developer's local credentials leak into the suite and reach a live GitHub
    request. The GitHub token resolver only consults `gh auth token` when TEAMCTX_DISABLE_GH_AUTH
    is unset; we set it for every test so token resolution is deterministic. We also clear
    GITHUB_TOKEN and GITHUB_TOKEN_FILE so an inherited credential can't make a test hit the network;
    tests that need a token set it explicitly (which overrides this), and tests exercising the gh
    fallback delete TEAMCTX_DISABLE_GH_AUTH and mock teamctx.tokens._gh_auth_token."""
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TEAMCTX_GITHUB_API_ROOT", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TEAMCTX_GITLAB_API_ROOT", raising=False)
