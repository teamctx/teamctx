from __future__ import annotations

import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import teamctx.runner as runner_mod
from teamctx.connectors.confluence import run_confluence_docs_probe
from teamctx.contract_render import render_broker_answer, render_open_source
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

OBSERVED = "2026-07-03T12:00:00Z"
BASE_URL = "https://example.atlassian.net"
SPACE_KEY = "DEV"


class _FakeResponse:
    def __init__(self, data: object) -> None:
        self._data = data

    def read(self) -> bytes:
        return json.dumps(self._data).encode()

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_: object) -> None:
        pass


def _fake_opener(responses: dict[str, object]):
    def opener(request):  # type: ignore[no-untyped-def]
        url = request.full_url
        best_pattern = ""
        best_data: object = {}
        for pattern, data in responses.items():
            if pattern in url and len(pattern) > len(best_pattern):
                best_pattern = pattern
                best_data = data
        return _FakeResponse(best_data)

    return opener


def _empty_doc(request_context: RequestContext) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def _init_confluence_repo(root: Path, *, docs_root: str | None) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("base\n", encoding="utf-8")
    if docs_root is not None:
        (root / docs_root).mkdir(parents=True, exist_ok=True)
        (root / docs_root / "guide.md").write_text("# nothing declared\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(root, "checkout", "-qb", "work")
    work_start: dict[str, object] = {
        "repo": "acme/widgets",
        "confluence": {"base_url": f"{BASE_URL}/wiki", "space_key": SPACE_KEY},
    }
    if docs_root is not None:
        work_start["docs_root"] = docs_root
    (root / ".teamctx").mkdir()
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )


def _stub_forge_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        runner_mod, "run_github_pr_probe", lambda **kw: _empty_doc(kw["request_context"])
    )
    monkeypatch.setattr(
        runner_mod, "run_github_checks_probe", lambda **kw: _empty_doc(kw["request_context"])
    )


def _patch_confluence_opener(monkeypatch, responses: dict[str, object]) -> None:
    opener = _fake_opener(responses)

    def probe(**kwargs):  # type: ignore[no-untyped-def]
        return run_confluence_docs_probe(opener=opener, **kwargs)

    monkeypatch.setattr(runner_mod, "run_confluence_docs_probe", probe)


def _spaces() -> dict:
    return {"results": [{"id": "123", "key": SPACE_KEY, "name": "Development"}], "_links": {}}


def _one_page(webui: str) -> dict:
    return {
        "results": [
            {
                "id": "42",
                "status": "current",
                "title": "Rounding Policy",
                "_links": {"webui": webui},
            }
        ],
        "_links": {},
    }


def test_confluence_superseded_page_fires_card_with_title_and_webui_url(
    monkeypatch, tmp_path: Path
) -> None:
    _init_confluence_repo(tmp_path, docs_root=None)
    _stub_forge_sources(monkeypatch)
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    _patch_confluence_opener(
        monkeypatch,
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces(),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _one_page(
                "/spaces/DEV/pages/42/Rounding+Policy"
            ),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": {
                "results": [{"id": "9", "key": "teamctx.superseded_by", "value": "docs/new.md"}]
            },
        },
    )

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert inputs.confluence_base_url == BASE_URL
    assert inputs.confluence_space_key == "DEV"
    doc_cards = [c for c in answer.selection.cards if c.reason_code == "doc.superseded"]
    assert len(doc_cards) == 1
    assert "Rounding Policy" in text
    assert "docs/new.md" in text  # names the replacement to rely on
    assert dict(answer.verdicts)["Docs check"].value == "false"

    open_source = render_open_source(doc_cards[0], answer.open_targets)
    assert (
        "open https://example.atlassian.net/wiki/spaces/DEV/pages/42/Rounding+Policy"
        in open_source
    )


def test_confluence_clean_space_reads_real_green_beside_local_docs(
    monkeypatch, tmp_path: Path
) -> None:
    _init_confluence_repo(tmp_path, docs_root="docs")
    _stub_forge_sources(monkeypatch)
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    _patch_confluence_opener(
        monkeypatch,
        {
            "/wiki/api/v2/spaces?keys=DEV": _spaces(),
            "/wiki/api/v2/spaces/123/pages?limit=100&status=current": _one_page(
                "/spaces/DEV/pages/42/Rounding+Policy"
            ),
            "/wiki/api/v2/pages/42/properties?key=teamctx.superseded_by": {"results": []},
        },
    )

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    # both docs sources scanned to the end: the family is complete, no superseded docs.
    assert dict(answer.verdicts)["Docs check"].value == "true"
    assert "the docs you rely on are current" in text
    assert "Not applicable" not in text


def test_confluence_reflex_profile_emits_verbatim_skip_note(monkeypatch, tmp_path: Path) -> None:
    _init_confluence_repo(tmp_path, docs_root=None)
    _stub_forge_sources(monkeypatch)
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")

    def fail_confluence(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Confluence probe must not run in reflex profile: {kwargs}")

    monkeypatch.setattr(runner_mod, "run_confluence_docs_probe", fail_confluence)

    inputs = replace(
        resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path), profile="reflex"
    )
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert (
        "Confluence docs are skipped in the quick pre-edit check; run teamctx work-start for "
        "the full scan." in text
    )
    assert "Looks clear to start." not in text
