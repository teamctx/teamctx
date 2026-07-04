import json
from urllib.error import HTTPError, URLError

from teamctx.connectors.confluence import run_confluence_docs_probe
from teamctx.core.contracts import RequestContext

OBSERVED = "2026-07-03T12:00:00Z"
BASE_URL = "https://example.atlassian.net"
SPACE_KEY = "DEV"


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="test",
        repo="acme/widgets",
        task="test",
        paths=["src/app.py"],
        linked_issues=[],
        requested_at=OBSERVED,
        requesting_principal=None,
    )


class _FakeResponse:
    def __init__(self, data: object) -> None:
        self._data = data

    def read(self) -> bytes:
        return json.dumps(self._data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


def _fake_opener(responses: dict[str, object]):
    requests = []

    def opener(request):
        requests.append(request)
        url = request.full_url
        best_pattern = ""
        best_data: object = {}
        for pattern, data in responses.items():
            if pattern in url and len(pattern) > len(best_pattern):
                best_pattern = pattern
                best_data = data
        if isinstance(best_data, BaseException):
            raise best_data
        return _FakeResponse(best_data)

    opener.requests = requests
    return opener


def _http_error(status: int) -> HTTPError:
    return HTTPError(BASE_URL, status, "boom", hdrs=None, fp=None)


def _spaces(space_id: object = "123") -> dict:
    return {"results": [{"id": space_id, "key": SPACE_KEY, "name": "Development"}], "_links": {}}


def _pages(*pages: dict, next_link: object = "__absent__") -> dict:
    links: dict[str, object] = {} if next_link == "__absent__" else {"next": next_link}
    return {"results": list(pages), "_links": links}


def _page(page_id: str = "42", title: str = "Rounding Policy", webui: object = None) -> dict:
    return {
        "id": page_id,
        "status": "current",
        "title": title,
        "_links": {"webui": webui if webui is not None else f"/spaces/DEV/pages/{page_id}/Title"},
    }


def _property(value: object = "docs/new.md") -> dict:
    return {"results": [{"id": "999", "key": "teamctx.superseded_by", "value": value}]}


def _no_property() -> dict:
    return {"results": []}


def test_probe_without_auth_returns_verbatim_no_credential_copy() -> None:
    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=None,
        request_context=_request(),
        observed_at=OBSERVED,
        opener=_fake_opener({}),
    )

    assert doc.source_statuses[0].source_id == "confluence_pages"
    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "Confluence is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL "
        "and ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE)."
    )
    assert doc.source_signals == []


def test_space_not_found_is_unavailable_never_clean_scan() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": {"results": [], "_links": {}}})

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "the configured Confluence space couldn't be found with current access."
    )
    assert doc.source_signals == []
    # The zero-page space never issued a pages request: it fails closed at resolution.
    assert len(opener.requests) == 1


def test_superseded_page_yields_doc_with_title_and_webui_url() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(
                _page(page_id="42", title="Rounding Policy", webui="/spaces/DEV/pages/42/Rounding")
            ),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _property("docs/new.md"),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert len(doc.source_signals) == 1
    signal = doc.source_signals[0]
    assert signal.signal_type == "doc_superseded"
    assert signal.source_family == "docs"
    assert signal.scope["repo"] == "acme/widgets"
    assert signal.scope["doc"] == "Rounding Policy"
    assert signal.scope["superseded_by"] == "docs/new.md"
    assert signal.scope["url"] == (
        "https://example.atlassian.net/wiki/spaces/DEV/pages/42/Rounding"
    )
    assert doc.source_statuses[0].status == "fresh"
    assert [request.full_url for request in opener.requests] == [
        f"{BASE_URL}/wiki/api/v2/spaces?keys=DEV",
        f"{BASE_URL}/wiki/api/v2/spaces/123/pages?limit=100&status=current",
        f"{BASE_URL}/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by",
    ]
    assert opener.requests[0].get_header("Accept") == "application/json"
    assert opener.requests[0].get_header("Authorization", "").startswith("Basic ")


def test_page_without_property_is_not_superseded_and_scan_is_fresh() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(_page("42")),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _no_property(),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "fresh"


def test_property_fetch_http_failure_makes_source_stale_never_skip() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(_page("42")),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _http_error(500),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "A page's supersession marker couldn't be read; the docs scan is not complete."
    )


def test_malformed_property_value_makes_source_stale() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(_page("42")),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _property(value=99),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "A page's supersession marker couldn't be read; the docs scan is not complete."
    )


def test_property_failure_still_surfaces_docs_found_before_it() -> None:
    # A superseded doc read on an earlier page still fires; the later property failure only marks
    # the source stale (never hides a real "verify before relying" finding).
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(
                _page("10", title="Old A"), _page("20", title="Old B")
            ),
            "/wiki/api/v2/pages/10/properties?key=teamctx.superseded_by": _property("docs/a.md"),
            "/wiki/api/v2/pages/20/properties?key=teamctx.superseded_by": _http_error(500),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert [s.scope["doc"] for s in doc.source_signals] == ["Old A"]


def test_pagination_follows_next_link_and_surfaces_both_pages() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(
                _page("10", title="Old A"),
                next_link="/wiki/api/v2/spaces/123/pages?cursor=NEXT&limit=100&status=current",
            ),
            "cursor=NEXT": _pages(_page("20", title="Old B")),
            "/wiki/api/v2/pages/10/properties?key=teamctx.superseded_by": _property("docs/a.md"),
            "/wiki/api/v2/pages/20/properties?key=teamctx.superseded_by": _property("docs/b.md"),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert sorted(s.scope["doc"] for s in doc.source_signals) == ["Old A", "Old B"]
    assert doc.source_statuses[0].status == "fresh"
    assert (
        f"{BASE_URL}/wiki/api/v2/spaces/123/pages?cursor=NEXT&limit=100&status=current"
        in [r.full_url for r in opener.requests]
    )


def test_malformed_cursor_with_more_pages_is_unavailable_never_assume_last_page() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(
                _page("10"), next_link=12345  # not a string: cursor is malformed
            ),
            "/wiki/api/v2/pages/10/properties?key=teamctx.superseded_by": _no_property(),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "Confluence is unavailable with current access."
    )
    assert doc.source_signals == []


def test_budget_hit_is_stale_with_verbatim_copy() -> None:
    # 500 pages read with a next link still present -> budget hit -> stale, never complete.
    class _BudgetOpener:
        def __init__(self) -> None:
            self.requests: list[object] = []

        def __call__(self, request):
            self.requests.append(request)
            url = request.full_url
            if "keys=DEV" in url:
                return _FakeResponse(_spaces("123"))
            if "/properties?" in url:
                return _FakeResponse(_no_property())
            # every pages batch returns a full page of 100 and always another cursor after it
            pages = [_page(str(i)) for i in range(100)]
            nxt = "/wiki/api/v2/spaces/123/pages?cursor=MORE&limit=100&status=current"
            return _FakeResponse(_pages(*pages, next_link=nxt))

    opener = _BudgetOpener()

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "stale"
    assert doc.source_statuses[0].safe_user_message == (
        "Checked the first 500 pages of the space; more exist, so this is not a complete check."
    )


def test_http_error_on_spaces_is_unavailable_with_current_access() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": _http_error(401)})

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_statuses[0].safe_user_message == (
        "Confluence is unavailable with current access."
    )


def test_network_error_on_pages_is_unavailable() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": URLError("boom"),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"
    assert doc.source_signals == []


def test_malformed_pages_payload_is_unavailable() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": "nope"},
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"


def test_malformed_space_id_is_unavailable() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": _spaces(space_id=None)})

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"


def test_malformed_page_item_is_unavailable() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _pages(
                {"id": "42", "title": 99, "_links": {"webui": "/x"}}
            ),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"


def test_non_json_response_is_unavailable() -> None:
    class _Garbage:
        def read(self) -> bytes:
            return b"not json"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    def opener(request):  # type: ignore[no-untyped-def]
        return _Garbage()

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "unavailable"


def test_spaces_payload_not_a_dict_is_unavailable() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": ["not", "a", "dict"]})
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "unavailable"


def test_spaces_results_not_a_list_is_unavailable() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": {"results": "nope"}})
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "unavailable"


def test_space_item_not_a_dict_is_unavailable() -> None:
    opener = _fake_opener({"/wiki/api/v2/spaces?keys=DEV": {"results": ["nope"]}})
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "unavailable"


def test_integer_space_id_is_accepted() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces(space_id=123),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": [_page("42")]},
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _no_property(),
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "fresh"


def test_pages_payload_not_a_dict_is_unavailable() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": ["nope"],
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "unavailable"


def test_page_result_item_not_a_dict_is_unavailable() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": ["nope"]},
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "unavailable"


def test_property_payload_not_a_dict_makes_source_stale() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": [_page("42")]},
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": ["nope"],
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "stale"


def test_property_results_not_a_list_makes_source_stale() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": [_page("42")]},
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": {"results": "nope"},
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "stale"


def test_property_item_not_a_dict_makes_source_stale() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {"results": [_page("42")]},
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": {"results": ["nope"]},
        }
    )
    doc = run_confluence_docs_probe(
        base_url=BASE_URL, space_key=SPACE_KEY, auth=("p@e.com", "t"),
        request_context=_request(), observed_at=OBSERVED, opener=opener,
    )
    assert doc.source_statuses[0].status == "stale"


def test_absent_next_link_terminates_cleanly_fresh() -> None:
    opener = _fake_opener(
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces("123"),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": {
                "results": [_page("42")]
            },  # no _links at all
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": _no_property(),
        }
    )

    doc = run_confluence_docs_probe(
        base_url=BASE_URL,
        space_key=SPACE_KEY,
        auth=("person@example.com", "token"),
        request_context=_request(),
        observed_at=OBSERVED,
        opener=opener,
    )

    assert doc.source_statuses[0].status == "fresh"
    assert doc.source_signals == []
