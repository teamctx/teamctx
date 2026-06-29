import pytest


@pytest.fixture(autouse=True)
def _no_gh_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never let a developer's local `gh` login leak into the suite. The GitHub token resolver
    only consults `gh auth token` when TEAMCTX_DISABLE_GH_AUTH is unset; we set it for every test
    so token resolution is deterministic. Tests that exercise the gh fallback delete this var and
    mock teamctx.tokens._gh_auth_token."""
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
