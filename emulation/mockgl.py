"""A local mock of just enough GitLab REST for the offline emulation rows.

Bound to 127.0.0.1 on an ephemeral port and reached only through the ``TEAMCTX_GITLAB_API_ROOT``
seam that S9b added (program spec rev 2, P0-1). It never calls out; it serves fabricated payloads
through the REAL teamctx GitLab connectors. Covers the four endpoints the connector reads: the
open merge-request list (collision + own-MR rows), the per-MR diffs (which files an MR touches),
the latest pipeline for a ref (gate rows), and that pipeline's jobs (the named failing job). The
project id in the path is url-encoded (``group%2Fproject``); routing is by shape, so any gitlab.com
slug resolves against the same fixtures, exactly like the GitHub mock.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

_DEFAULT_SLUG = "teamctx-emulation-lab/widgets"

# --- payload builders (the exact shapes the connector parses) ---


def mr_item(
    iid: int,
    *,
    source_branch: str,
    source_project_id: int = 1,
    target_project_id: int = 1,
    state: str = "opened",
    slug: str = _DEFAULT_SLUG,
    web_url: str | None = None,
    created_at: str = "2026-07-01T00:00:00Z",
    updated_at: str = "2026-07-02T00:00:00Z",
    title: str | None = None,
) -> dict[str, Any]:
    """One merge-request list entry. ``source_project_id == target_project_id`` means the MR's
    branch lives in the target project (not a fork), which is what own-MR detection keys on."""

    item: dict[str, Any] = {
        "iid": iid,
        "state": state,
        "web_url": web_url or f"https://gitlab.com/{slug}/-/merge_requests/{iid}",
        "created_at": created_at,
        "updated_at": updated_at,
        "source_branch": source_branch,
        "source_project_id": source_project_id,
        "target_project_id": target_project_id,
    }
    if title is not None:
        item["title"] = title
    return item


def diff_item(new_path: str, *, old_path: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"new_path": new_path}
    if old_path is not None:
        item["old_path"] = old_path
    return item


def pipeline_item(
    pipeline_id: int,
    status: str,
    *,
    slug: str = _DEFAULT_SLUG,
    web_url: str | None = None,
) -> dict[str, Any]:
    return {
        "id": pipeline_id,
        "status": status,
        "web_url": web_url or f"https://gitlab.com/{slug}/-/pipelines/{pipeline_id}",
    }


def job_item(
    name: str,
    status: str,
    *,
    job_id: int = 1,
    slug: str = _DEFAULT_SLUG,
    web_url: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "web_url": web_url or f"https://gitlab.com/{slug}/-/jobs/{job_id}",
    }


# --- the server ---


@dataclass
class GitLabFixtures:
    """What the mock serves. ``mr_pages`` is a list of pages (each a list of MR items); the mock
    sets ``x-next-page`` when a further page exists, so the connector's pagination loop is
    exercised faithfully. ``mr_diffs`` maps an MR iid to its diff items; ``pipelines`` is the
    latest-first pipeline list for the ref (the connector reads only the first); ``pipeline_jobs``
    maps a pipeline id to its jobs."""

    mr_pages: list[list[dict[str, Any]]] = field(default_factory=list)
    mr_diffs: dict[int, list[dict[str, Any]]] = field(default_factory=dict)
    pipelines: list[dict[str, Any]] = field(default_factory=list)
    pipeline_jobs: dict[int, list[dict[str, Any]]] = field(default_factory=dict)


class _MockServer(ThreadingHTTPServer):
    fixtures: GitLabFixtures


class _Handler(BaseHTTPRequestHandler):
    server: _MockServer

    def log_message(self, *args: Any) -> None:  # keep the harness output clean
        return

    def _send(self, code: int, payload: Any, *, headers: dict[str, str] | None = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802  (BaseHTTPRequestHandler dispatch name)
        parsed = urlparse(self.path)
        path = parsed.path
        fixtures = self.server.fixtures
        if path.endswith("/merge_requests"):
            self._serve_merge_requests(parsed.query, fixtures)
            return
        if path.endswith("/diffs") and "/merge_requests/" in path:
            iid = _path_int(path.rsplit("/diffs", 1)[0])
            self._send(200, fixtures.mr_diffs.get(iid, []))
            return
        if path.endswith("/jobs") and "/pipelines/" in path:
            pipeline_id = _path_int(path.rsplit("/jobs", 1)[0])
            self._send(200, fixtures.pipeline_jobs.get(pipeline_id, []))
            return
        if path.endswith("/pipelines"):
            self._send(200, fixtures.pipelines)
            return
        self._send(404, {"message": "404 Not found"})

    def _serve_merge_requests(self, query: str, fixtures: GitLabFixtures) -> None:
        pages = fixtures.mr_pages
        page = _page_param(query)
        body = pages[page - 1] if 1 <= page <= len(pages) else []
        headers = {"x-next-page": str(page + 1)} if page < len(pages) else {}
        self._send(200, body, headers=headers)


def _page_param(query: str) -> int:
    values = parse_qs(query).get("page", ["1"])
    try:
        return int(values[0])
    except ValueError:
        return 1


def _path_int(path: str) -> int:
    tail = path.rstrip("/").rsplit("/", 1)[-1]
    try:
        return int(tail)
    except ValueError:
        return -1


class MockGitLab:
    """Context manager: start the mock on 127.0.0.1, expose ``api_root``, stop on exit."""

    def __init__(self, fixtures: GitLabFixtures) -> None:
        self._fixtures = fixtures
        self._server: _MockServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> MockGitLab:
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
    def api_root(self) -> str:
        return f"http://127.0.0.1:{self.port}"
