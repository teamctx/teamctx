"""S8b: the API root is env-overridable so the emulation program can drive fabricated
payloads through the REAL pipeline (Phase 5 program spec rev 2, P0-1 seam)."""

from __future__ import annotations

from teamctx.connectors.github import github_api_root


def test_default_api_root_is_github() -> None:
    assert github_api_root() == "https://api.github.com"


def test_env_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", "http://127.0.0.1:9999")
    assert github_api_root() == "http://127.0.0.1:9999"


def test_env_override_strips_trailing_slash(monkeypatch) -> None:
    monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", "http://127.0.0.1:9999/")
    assert github_api_root() == "http://127.0.0.1:9999"


def test_override_reaches_the_graphql_url(monkeypatch) -> None:
    monkeypatch.setenv("TEAMCTX_GITHUB_API_ROOT", "http://127.0.0.1:9999")
    from urllib.request import Request

    captured: list[str] = []

    class _Resp:
        def read(self) -> bytes:
            return (
                b'{"data": {"repository": {"pullRequests": '
                b'{"nodes": [], "pageInfo": {"hasNextPage": false, "endCursor": null}}}}}'
            )

        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *a: object) -> None:
            return None

    def opener(request: Request) -> _Resp:
        captured.append(request.full_url)
        return _Resp()

    from teamctx.connectors.github import fetch_github_pull_requests

    fetch_github_pull_requests(repo="o/r", token="t", opener=opener)
    assert captured and captured[0].startswith("http://127.0.0.1:9999/graphql")
