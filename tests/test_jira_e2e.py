from __future__ import annotations

import json
import os
import subprocess
from itertools import count
from pathlib import Path
from urllib.request import Request

import teamctx.runner as runner_mod
from teamctx.connectors.jira import run_jira_issues_probe
from teamctx.contract_render import render_broker_answer
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

OBSERVED = "2026-07-03T12:00:00Z"
BASE_URL = "https://jira.example.test"
_EMPTY_DOC_COUNTER = count()


class _Resp:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *_: object) -> None:
        pass


class _Opener:
    def __init__(self, *responses: _Resp) -> None:
        self.responses = list(responses)
        self.requests: list[Request] = []

    def __call__(self, request: Request) -> _Resp:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError(f"unexpected request: {request.full_url}")
        return self.responses.pop(0)


def _empty_doc(request_context: RequestContext) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        document_id=f"doc_empty_jira_e2e_{next(_EMPTY_DOC_COUNTER)}",
        document_type="test_empty",
        request_context=request_context,
        source_signals=[],
        source_statuses=[],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )
    return result.stdout.strip()


def _init_jira_repo(root: Path, *, configure_jira: bool) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    target = root / "src" / "app.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text("base\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(
        root,
        "commit",
        "-qm",
        "base",
        env={
            "GIT_AUTHOR_DATE": "2026-07-01T09:15:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-01T09:15:00+00:00",
        },
    )
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(root, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    _git(root, "checkout", "-qb", "PROJ-123-fix")
    target.write_text("work\n", encoding="utf-8")
    _git(
        root,
        "commit",
        "-am",
        "work",
        env={
            "GIT_AUTHOR_DATE": "2026-07-02T10:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-02T10:00:00+00:00",
        },
    )
    work_start: dict[str, object] = {"repo": "acme/widgets"}
    if configure_jira:
        work_start["jira"] = {"base_url": f"{BASE_URL}/"}
    (root / ".teamctx").mkdir()
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )
    _git(root, "add", ".teamctx/config.json")
    _git(root, "commit", "-qm", "config")


def _stub_non_jira_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        runner_mod,
        "run_github_pr_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )
    monkeypatch.setattr(
        runner_mod,
        "run_github_checks_probe",
        lambda **kw: _empty_doc(kw["request_context"]),
    )


def test_jira_e2e_branch_key_changed_description_fires_with_display_and_provenance(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_jira_repo(tmp_path, configure_jira=True)
    _stub_non_jira_sources(monkeypatch)
    monkeypatch.setenv("ATLASSIAN_EMAIL", "person@example.com")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "token")
    opener = _Opener(
        _Resp(
            {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Acceptance criteria",
                    "status": {"name": "In Progress"},
                    "labels": [],
                    "updated": "2026-07-02T10:00:00.000+0000",
                },
            }
        ),
        _Resp(
            {
                "isLast": True,
                "values": [
                    {
                        "created": "2026-07-02T09:30:00.000+0000",
                        "items": [{"field": "description"}],
                    }
                ],
            }
        ),
    )

    def jira_probe(**kwargs):  # type: ignore[no-untyped-def]
        return run_jira_issues_probe(opener=opener, **kwargs)

    monkeypatch.setattr(runner_mod, "run_jira_issues_probe", jira_probe)

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    criteria_cards = [
        card for card in answer.selection.cards if card.reason_code == "criteria.changed"
    ]
    assert inputs.issues == ("PROJ-123",)
    assert inputs.since == "2026-07-01T09:15:00Z"
    assert answer.request.input_provenance["issue:PROJ-123"] == "your branch name"
    assert criteria_cards[0].source_display == "Jira PROJ-123: Acceptance criteria"
    assert "Jira PROJ-123 updated: description updated" in text
    assert dict(answer.verdicts)["Criteria check"].value == "false"
    assert [request.full_url for request in opener.requests] == [
        f"{BASE_URL}/rest/api/3/issue/PROJ-123?fields=summary,status,labels,updated",
        f"{BASE_URL}/rest/api/3/issue/PROJ-123/changelog?maxResults=100",
    ]


def test_jira_e2e_unconfigured_branch_key_reports_disabled_note_and_never_clear(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_jira_repo(tmp_path, configure_jira=False)
    _stub_non_jira_sources(monkeypatch)

    def fail_jira(**kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError(f"Jira probe should not run without Jira config: {kwargs}")

    monkeypatch.setattr(runner_mod, "run_jira_issues_probe", fail_jira)

    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=tmp_path)
    answer = work_start_answer(inputs, observed_at=OBSERVED, project_root=tmp_path)
    text = render_broker_answer(answer)

    assert inputs.issues == ("PROJ-123",)
    assert "issue PROJ-123 looks like a Jira issue, but no Jira is configured" in text
    assert "Looks clear to start." not in text
    assert dict(answer.verdicts)["Criteria check"].value == "unknown"
