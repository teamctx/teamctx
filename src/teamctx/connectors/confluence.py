"""Narrow Confluence docs probe: read ``teamctx.superseded_by`` page properties in a space.

Confluence is the first remote docs source. Every page in the configured space that carries the
``teamctx.superseded_by`` content property becomes a superseded-doc signal with an openable page
link. The one law holds here as everywhere: no path from "no data" to a clear. A typo'd space, a
failed property fetch, a malformed cursor, or a budget hit can never read as a clean scan.

Does network I/O via an injected opener; no live calls in tests.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from teamctx.connectors.docs_supersession import (
    SupersededDoc,
    normalize_superseded_docs,
    unavailable_docs_document,
)
from teamctx.connectors.github import DEFAULT_OPENER, HttpOpener
from teamctx.core.contracts import CoreContractDocument, RequestContext

_SOURCE_ID = "confluence_pages"
_PROPERTY_KEY = "teamctx.superseded_by"
_PAGE_LIMIT = 100
_PAGE_BUDGET = 500

_NO_CREDENTIAL = (
    "Confluence is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL and "
    "ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE)."
)
_SPACE_NOT_FOUND = "the configured Confluence space couldn't be found with current access."
_UNREACHABLE = "Confluence is unavailable with current access."
_BUDGET = "Checked the first 500 pages of the space; more exist, so this is not a complete check."
_PROPERTY_FAILURE = (
    "A page's supersession marker couldn't be read; the docs scan is not complete."
)


class ConfluenceProbeError(RuntimeError):
    """A Confluence fetch failed. ``user_message`` carries a pre-determined honest message for a
    logical failure (a space that could not be found); otherwise the probe uses the generic
    unreachable copy."""

    def __init__(self, message: str, *, user_message: str | None = None) -> None:
        super().__init__(message)
        self.user_message = user_message


@dataclass(frozen=True)
class _ConfluencePage:
    id: str
    title: str
    webui: str


@dataclass(frozen=True)
class _ConfluenceScan:
    docs: tuple[SupersededDoc, ...]
    truncated: bool = False
    truncated_message: str = _BUDGET


def run_confluence_docs_probe(
    *,
    base_url: str,
    space_key: str,
    auth: tuple[str, str] | None,
    request_context: RequestContext,
    observed_at: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if auth is None:
        return unavailable_docs_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id=_SOURCE_ID,
            status="unavailable",
            safe_user_message=_NO_CREDENTIAL,
        )

    try:
        scan = fetch_confluence_superseded_docs(
            base_url=base_url,
            space_key=space_key,
            auth=auth,
            repo=request_context.repo,
            opener=opener,
        )
    except ConfluenceProbeError as exc:
        return unavailable_docs_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id=_SOURCE_ID,
            status="unavailable",
            safe_user_message=exc.user_message or _UNREACHABLE,
        )

    return normalize_superseded_docs(
        request_context,
        scan.docs,
        observed_at=observed_at,
        source_id=_SOURCE_ID,
        coverage_truncated=scan.truncated,
        truncated_user_message=scan.truncated_message,
    )


def fetch_confluence_superseded_docs(
    *,
    base_url: str,
    space_key: str,
    auth: tuple[str, str],
    repo: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> _ConfluenceScan:
    space_id = _resolve_space_id(base_url, space_key, auth, opener)
    docs: list[SupersededDoc] = []
    next_url: str | None = (
        f"{base_url}/wiki/api/v2/spaces/{space_id}/pages?limit={_PAGE_LIMIT}&status=current"
    )
    pages_read = 0
    while next_url is not None:
        payload = _get_json(next_url, auth=auth, opener=opener)
        pages, next_link = _parse_page_batch(payload)
        for page in pages:
            try:
                superseded_by = _fetch_property(base_url, page.id, auth, opener)
            except ConfluenceProbeError:
                # ANY per-page property failure -> the whole source is stale. Skip-and-continue is
                # banned: a marker we could not read means the scan is not complete. Surface the
                # docs found so far and mark it stale.
                return _ConfluenceScan(
                    docs=tuple(docs), truncated=True, truncated_message=_PROPERTY_FAILURE
                )
            if superseded_by is not None:
                docs.append(
                    SupersededDoc(
                        repo=repo,
                        doc=page.title,
                        superseded_by=superseded_by,
                        url=f"{base_url}/wiki{page.webui}",
                    )
                )
            pages_read += 1
        if next_link is None:
            break
        if pages_read >= _PAGE_BUDGET:
            return _ConfluenceScan(docs=tuple(docs), truncated=True, truncated_message=_BUDGET)
        next_url = f"{base_url}{next_link}"
    return _ConfluenceScan(docs=tuple(docs))


def _resolve_space_id(
    base_url: str, space_key: str, auth: tuple[str, str], opener: HttpOpener
) -> str:
    payload = _get_json(
        f"{base_url}/wiki/api/v2/spaces?keys={quote(space_key)}", auth=auth, opener=opener
    )
    if not isinstance(payload, dict):
        raise ConfluenceProbeError("Confluence spaces payload was malformed")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ConfluenceProbeError("Confluence spaces payload was malformed")
    if not results:
        raise ConfluenceProbeError("space not found", user_message=_SPACE_NOT_FOUND)
    first = results[0]
    if not isinstance(first, dict):
        raise ConfluenceProbeError("Confluence space item was malformed")
    space_id = first.get("id")
    if isinstance(space_id, int):
        return str(space_id)
    if isinstance(space_id, str) and space_id:
        return space_id
    raise ConfluenceProbeError("Confluence space id was malformed")


def _parse_page_batch(payload: object) -> tuple[list[_ConfluencePage], str | None]:
    if not isinstance(payload, dict):
        raise ConfluenceProbeError("Confluence pages payload was malformed")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ConfluenceProbeError("Confluence pages payload was malformed")
    pages: list[_ConfluencePage] = []
    for item in results:
        if not isinstance(item, dict):
            raise ConfluenceProbeError("Confluence page item was malformed")
        raw_id = item.get("id")
        page_id = str(raw_id) if isinstance(raw_id, int) else raw_id
        title = item.get("title")
        links = item.get("_links")
        webui = links.get("webui") if isinstance(links, dict) else None
        if not (
            isinstance(page_id, str)
            and page_id
            and isinstance(title, str)
            and isinstance(webui, str)
        ):
            raise ConfluenceProbeError("Confluence page item was malformed")
        pages.append(_ConfluencePage(id=page_id, title=title, webui=webui))
    return pages, _extract_next_link(payload.get("_links"))


def _extract_next_link(links: object) -> str | None:
    if not isinstance(links, dict) or "next" not in links:
        # No next link is the terminal signal in v2: this was the last page.
        return None
    nxt = links.get("next")
    if isinstance(nxt, str) and nxt:
        return nxt
    # A next link is indicated (more pages exist) but the cursor is malformed/absent: we cannot
    # continue, so fail closed rather than assume this was the last page.
    raise ConfluenceProbeError("Confluence pagination cursor was malformed")


def _fetch_property(
    base_url: str, page_id: str, auth: tuple[str, str], opener: HttpOpener
) -> str | None:
    payload = _get_json(
        f"{base_url}/wiki/api/v2/pages/{quote(page_id)}/properties?key={_PROPERTY_KEY}",
        auth=auth,
        opener=opener,
    )
    if not isinstance(payload, dict):
        raise ConfluenceProbeError("Confluence property payload was malformed")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ConfluenceProbeError("Confluence property payload was malformed")
    if not results:
        return None
    first = results[0]
    if not isinstance(first, dict):
        raise ConfluenceProbeError("Confluence property item was malformed")
    value = first.get("value")
    if isinstance(value, str) and value:
        return value
    raise ConfluenceProbeError("Confluence property value was malformed")


def _get_json(url: str, *, auth: tuple[str, str], opener: HttpOpener) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": _basic_auth_header(auth),
            "User-Agent": "teamctx-confluence-docs-probe",
        },
    )
    try:
        with opener(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ConfluenceProbeError("Confluence API request failed") from exc
    except URLError as exc:
        raise ConfluenceProbeError(f"Confluence API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ConfluenceProbeError("Confluence API response was not valid JSON") from exc


def _basic_auth_header(auth: tuple[str, str]) -> str:
    raw = f"{auth[0]}:{auth[1]}".encode()
    return f"Basic {base64.b64encode(raw).decode('ascii')}"
