"""A local mock of just enough Confluence v2 REST for the offline emulation rows.

Bound to 127.0.0.1 on an ephemeral port and reached only through the normal
``work_start.confluence.base_url`` project-config seam (program spec rev 2, row 8). It never
calls out; it serves fabricated payloads through the REAL teamctx Confluence connector. Covers the
three endpoint shapes the connector reads: ``spaces?keys=``, ``spaces/{id}/pages`` with v2 cursor
links, and ``pages/{id}/properties?key=teamctx.superseded_by``.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

PROPERTY_KEY = "teamctx.superseded_by"


# --- payload builders (the exact shapes the connector parses) ---


def space_item(space_id: str, key: str, name: str = "Testing spaces") -> dict[str, Any]:
    return {"id": space_id, "key": key, "name": name}


def spaces_payload(*spaces: dict[str, Any]) -> dict[str, Any]:
    return {"results": list(spaces), "_links": {}}


def page_item(page_id: str, title: str, *, webui: str) -> dict[str, Any]:
    return {
        "id": page_id,
        "status": "current",
        "title": title,
        "_links": {"webui": webui},
    }


def pages_payload(
    *pages: dict[str, Any], next_link: str | None = None
) -> dict[str, Any]:
    links = {"next": next_link} if next_link is not None else {}
    return {"results": list(pages), "_links": links}


def property_payload(value: str) -> dict[str, Any]:
    return {"results": [{"id": "property-1", "key": PROPERTY_KEY, "value": value}]}


def no_property_payload() -> dict[str, Any]:
    return {"results": []}


# --- the server ---


@dataclass
class ConfluenceFixtures:
    """What the mock serves.

    ``spaces`` is keyed by Confluence space key, ``pages`` by resolved space id, ``cursor_pages``
    by the cursor query value in a v2 ``_links.next`` URL, and ``properties`` by page id.
    """

    spaces: dict[str, dict[str, Any]] = field(default_factory=dict)
    pages: dict[str, dict[str, Any]] = field(default_factory=dict)
    cursor_pages: dict[str, dict[str, Any]] = field(default_factory=dict)
    properties: dict[str, dict[str, Any]] = field(default_factory=dict)


class _MockServer(ThreadingHTTPServer):
    fixtures: ConfluenceFixtures


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
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/wiki/api/v2/spaces":
            key = query.get("keys", [""])[0]
            space = self.server.fixtures.spaces.get(key)
            self._send(200, spaces_payload(space) if space is not None else spaces_payload())
            return

        space_id = _space_pages_id(path)
        if space_id is not None:
            cursor = query.get("cursor", [None])[0]
            payload = (
                self.server.fixtures.cursor_pages.get(cursor, pages_payload())
                if cursor is not None
                else self.server.fixtures.pages.get(space_id, pages_payload())
            )
            self._send(200, payload)
            return

        page_id = _page_properties_id(path)
        if page_id is not None:
            if query.get("key", [""])[0] != PROPERTY_KEY:
                self._send(200, no_property_payload())
                return
            self._send(200, self.server.fixtures.properties.get(page_id, no_property_payload()))
            return

        self._send(404, {"message": "not found"})


def _space_pages_id(path: str) -> str | None:
    marker = "/wiki/api/v2/spaces/"
    if not path.startswith(marker) or not path.endswith("/pages"):
        return None
    tail = path[len(marker):]
    return unquote(tail[: -len("/pages")])


def _page_properties_id(path: str) -> str | None:
    marker = "/wiki/api/v2/pages/"
    if not path.startswith(marker) or not path.endswith("/properties"):
        return None
    tail = path[len(marker):]
    return unquote(tail[: -len("/properties")])


class MockConfluence:
    """Context manager: start the mock on 127.0.0.1, expose ``base_url``, stop on exit."""

    def __init__(self, fixtures: ConfluenceFixtures) -> None:
        self._fixtures = fixtures
        self._server: _MockServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> MockConfluence:
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
