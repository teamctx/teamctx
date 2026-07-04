"""A local mock of just enough Jira REST for the offline emulation rows.

Bound to 127.0.0.1 on an ephemeral port and reached only through the normal
``work_start.jira.base_url`` project-config seam (program spec rev 2, row 6). It never calls
out; it serves fabricated payloads through the REAL teamctx Jira connector. Covers the two
endpoints the connector reads: issue fields and the per-issue changelog with Jira's ``isLast``
history-completeness flag.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import unquote, urlparse

# --- payload builders (the exact shapes the connector parses) ---


def issue_payload(
    key: str,
    *,
    updated_at: str,
    summary: str = "Acceptance criteria",
    status: str = "In Progress",
    labels: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "key": key.upper(),
        "fields": {
            "summary": summary,
            "status": {"name": status},
            "labels": list(labels),
            "updated": updated_at,
        },
    }


def changelog_item(field: str) -> dict[str, Any]:
    return {"field": field}


def changelog_history(created: str, fields: tuple[str, ...]) -> dict[str, Any]:
    return {"created": created, "items": [changelog_item(field) for field in fields]}


def changelog_payload(
    histories: list[dict[str, Any]], *, is_last: bool = True
) -> dict[str, Any]:
    return {"isLast": is_last, "values": histories}


# --- the server ---


@dataclass
class JiraFixtures:
    """What the mock serves. Keys are normalized to uppercase when the request is routed."""

    issues: dict[str, dict[str, Any]] = field(default_factory=dict)
    changelogs: dict[str, dict[str, Any]] = field(default_factory=dict)


class _MockServer(ThreadingHTTPServer):
    fixtures: JiraFixtures


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

    def do_GET(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler dispatch name)
        path = urlparse(self.path).path
        key = _issue_key(path)
        if key is None:
            self._send(404, {"message": "not found"})
            return

        fixtures = self.server.fixtures
        if path.endswith("/changelog"):
            self._send(200, fixtures.changelogs.get(key, changelog_payload([])))
            return

        issue = fixtures.issues.get(key)
        if issue is None:
            self._send(404, {"message": "no such issue"})
        else:
            self._send(200, issue)


def _issue_key(path: str) -> str | None:
    marker = "/rest/api/3/issue/"
    if marker not in path:
        return None
    tail = path.split(marker, 1)[1].strip("/")
    if not tail:
        return None
    key = tail.split("/", 1)[0]
    return unquote(key).upper()


class MockJira:
    """Context manager: start the mock on 127.0.0.1, expose ``base_url``, stop on exit."""

    def __init__(self, fixtures: JiraFixtures) -> None:
        self._fixtures = fixtures
        self._server: _MockServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> MockJira:
        server = _MockServer(("127.0.0.1", 0), _Handler)
        server.fixtures = self._fixtures
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
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"
