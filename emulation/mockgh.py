"""A local mock of just enough GitHub REST + GraphQL for the offline emulation rows.

Bound to 127.0.0.1 on an ephemeral port and reached only through the ``TEAMCTX_GITHUB_API_ROOT``
seam (program spec rev 2, P0-1). It never calls out; it serves fabricated payloads through the
REAL teamctx pipeline. Covers: the GraphQL open-PR connection (collision + unbounded rows), the
REST check-runs endpoint (gate rows), the REST issue + events endpoints (criteria row), and the
REST open-pulls endpoint (onboard reachability). Owner/name is ignored: routing is by shape, so
any github.com slug resolves against the same fixtures.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

# --- payload builders (the exact shapes the connectors parse) ---


def pr_node(
    number: int,
    paths: list[str],
    *,
    head_ref: str,
    head_repo: str | None,
    url: str | None = None,
    slug: str = "teamctx-emulation-lab/widgets",
    created_at: str = "2026-07-01T00:00:00Z",
    updated_at: str = "2026-07-02T00:00:00Z",
    files_has_next: bool = False,
    title: str | None = None,
) -> dict[str, Any]:
    node: dict[str, Any] = {
        "number": number,
        "url": url or f"https://github.com/{slug}/pull/{number}",
        "createdAt": created_at,
        "updatedAt": updated_at,
        "headRefName": head_ref,
        "headRepository": None if head_repo is None else {"nameWithOwner": head_repo},
        "files": {
            "nodes": [{"path": path} for path in paths],
            "pageInfo": {"hasNextPage": files_has_next},
        },
    }
    if title is not None:
        node["title"] = title
    return node


def graphql_page(
    nodes: list[dict[str, Any]], *, has_next: bool = False, end_cursor: str | None = None
) -> dict[str, Any]:
    return {
        "data": {
            "repository": {
                "pullRequests": {
                    "nodes": nodes,
                    "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
                }
            }
        }
    }


def check_run(
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    slug: str = "teamctx-emulation-lab/widgets",
    url: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "html_url": url or f"https://github.com/{slug}/runs/1",
    }


def check_runs_payload(
    runs: list[dict[str, Any]], *, total_count: int | None = None
) -> dict[str, Any]:
    return {
        "total_count": len(runs) if total_count is None else total_count,
        "check_runs": runs,
    }


def issue_payload(
    number: int,
    *,
    updated_at: str,
    state: str = "open",
    title: str = "Fix auth",
    slug: str = "teamctx-emulation-lab/widgets",
    labels: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "number": number,
        "updated_at": updated_at,
        "state": state,
        "title": title,
        "html_url": f"https://github.com/{slug}/issues/{number}",
        "labels": [{"name": name} for name in labels],
    }


# --- the server ---


@dataclass
class Fixtures:
    """What the mock serves. GraphQL pages are served in sequence (the fetch loop is sequential),
    so the last page's ``hasNextPage`` drives the unbounded-list case."""

    graphql_pages: list[dict[str, Any]] = field(default_factory=list)
    check_runs: dict[str, Any] | None = None
    issues: dict[int, dict[str, Any]] = field(default_factory=dict)
    issue_events: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    pulls: list[dict[str, Any]] | None = None


class _MockServer(ThreadingHTTPServer):
    fixtures: Fixtures
    graphql_index: int
    lock: threading.Lock


class _Handler(BaseHTTPRequestHandler):
    server: _MockServer

    def log_message(self, *args: Any) -> None:  # keep the harness output clean
        return

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler dispatch name)
        length = int(self.headers.get("Content-Length", "0") or "0")
        self.rfile.read(length)  # drain the body; owner/name is not needed for routing
        if urlparse(self.path).path.endswith("/graphql"):
            self._serve_graphql()
        else:
            self._send(404, {"message": "not found"})

    def _serve_graphql(self) -> None:
        pages = self.server.fixtures.graphql_pages
        if not pages:
            self._send(404, {"message": "no graphql fixture"})
            return
        with self.server.lock:
            index = min(self.server.graphql_index, len(pages) - 1)
            self.server.graphql_index += 1
        self._send(200, pages[index])

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        fixtures = self.server.fixtures
        if path.endswith("/check-runs"):
            if fixtures.check_runs is None:
                self._send(404, {"message": "no check-runs fixture"})
            else:
                self._send(200, fixtures.check_runs)
            return
        if "/issues/" in path and path.endswith("/events"):
            number = _issue_number(path.rsplit("/events", 1)[0])
            self._send(200, fixtures.issue_events.get(number, []))
            return
        if "/issues/" in path:
            number = _issue_number(path)
            issue = fixtures.issues.get(number)
            if issue is None:
                self._send(404, {"message": "no such issue"})
            else:
                self._send(200, issue)
            return
        if path.endswith("/pulls"):
            self._send(200, fixtures.pulls if fixtures.pulls is not None else [])
            return
        self._send(404, {"message": "not found"})


def _issue_number(path: str) -> int:
    tail = path.rstrip("/").rsplit("/", 1)[-1]
    try:
        return int(tail)
    except ValueError:
        return -1


class MockGitHub:
    """Context manager: start the mock on 127.0.0.1, expose ``api_root``, stop on exit."""

    def __init__(self, fixtures: Fixtures) -> None:
        self._fixtures = fixtures
        self._server: _MockServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> MockGitHub:
        server = _MockServer(("127.0.0.1", 0), _Handler)
        server.fixtures = self._fixtures
        server.graphql_index = 0
        server.lock = threading.Lock()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._server = server
        self._thread = thread
        return self

    def __exit__(self, *exc: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    @property
    def port(self) -> int:
        assert self._server is not None
        return self._server.server_address[1]

    @property
    def api_root(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def reset_graphql(self) -> None:
        """Rewind the GraphQL page cursor so a replay run re-serves the same pages (row 11)."""

        if self._server is not None:
            with self._server.lock:
                self._server.graphql_index = 0
