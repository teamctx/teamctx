"""Row 22: One declared file source feeds two declared checks, including HEAD refusal."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from emulation.actors import (
    DEFAULT_SLUG,
    SubprocessEnv,
    build_lab_repo,
    commit_files,
    run_cli,
    write_file,
)
from emulation.evidence import Expectation, RowResult, passed_or_failed
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

ROW_ID = "22"
TITLE = "Declared file source feeds two checks"

_PATH = "src/app.py"
_RECORD = "records/release.json"
_OBSERVED_AT = "2026-07-08T12:00:00Z"


def _config(*, include_disabled: bool) -> str:
    checks: dict[str, object] = {
        "x_release_block": {
            "enabled": True,
            "lane": "important",
            "profile": "full",
            "consumes": "x_release_record",
            "claim": "release record says the change is blocked",
            "match": {"op": "equality", "field": "state", "value": "blocked"},
            "copy": {
                "finding": "Release record is blocked.",
                "clear": "release record is open",
                "couldnt_check": "release record could not be checked",
                "not_enabled": "release record",
            },
            "identity": ["name"],
        },
        "x_release_cutoff": {
            "enabled": True,
            "lane": "important",
            "profile": "full",
            "consumes": "x_release_record",
            "claim": "release cutoff has passed",
            "match": {
                "op": "threshold",
                "left": "request.requested_at",
                "comparator": ">",
                "right": "cutoff_at",
            },
            "copy": {
                "finding": "Release cutoff has passed.",
                "clear": "release cutoff has not passed",
                "couldnt_check": "release cutoff could not be checked",
                "not_enabled": "release cutoff",
            },
            "identity": ["name"],
        },
    }
    if include_disabled:
        checks["x_release_note"] = {
            "enabled": False,
            "lane": "fyi",
            "profile": "full",
            "consumes": "x_release_record",
            "claim": "release note is present",
            "match": {"op": "presence", "field": "note"},
            "copy": {
                "finding": "Release note is present.",
                "clear": "release note is absent",
                "couldnt_check": "release note could not be checked",
                "not_enabled": "release note",
            },
            "identity": ["name"],
        }
    return json.dumps(
        {
            "schema_version": "teamctx.project_config.v0",
            "work_start": {"repo": DEFAULT_SLUG},
            "declared_sources": {
                "x_release_record": {
                    "kind": "file",
                    "path": _RECORD,
                    "schema_map": {
                        "name": "/name",
                        "state": "/state",
                        "cutoff_at": "/cutoff_at",
                        "note": "/note",
                    },
                }
            },
            "checks": checks,
        }
    )


def _record() -> str:
    return json.dumps(
        {
            "name": "release-one",
            "state": "blocked",
            "cutoff_at": "2026-07-08T00:00:00Z",
            "note": "plain note",
            "unmapped": "not rendered",
        }
    )


def _closure_evidence(repo_root: Path) -> str:
    inputs = resolve_work_start_inputs(paths=(_PATH,), root=repo_root)
    answer = work_start_answer(
        inputs, observed_at=_OBSERVED_AT, project_root=repo_root
    )
    lines: list[str] = []
    for entry in answer.selection.closure:
        if not entry.check_id.startswith("x_"):
            continue
        docs = ",".join(entry.consumed_document_ids) or "none"
        lines.append(f"{entry.check_id}: {entry.closure_status}: {docs}")
    declared_docs = [
        doc for doc in answer.source_documents if doc.document_id == "doc_declared_x_release_record"
    ]
    lines.append(f"declared document count: {len(declared_docs)}")
    return "\n".join(lines)


def _success_half(tmp: Path) -> str:
    repo = build_lab_repo(tmp / "success", branch="42-declared", files={_PATH: "x\n"})
    write_file(repo.root, ".teamctx/config.json", _config(include_disabled=True))
    write_file(repo.root, _RECORD, _record())
    commit_files(repo.root, ".teamctx/config.json", _RECORD, message="declared record")
    run = run_cli(
        ["work-start", "--path", _PATH],
        cwd=repo.root,
        env=SubprocessEnv(),
    )
    return run.output + "\nClosure\n" + _closure_evidence(repo.root) + "\n"


def _failure_half(tmp: Path) -> str:
    repo = build_lab_repo(tmp / "failure", branch="42-declared", files={_PATH: "x\n"})
    write_file(repo.root, ".teamctx/config.json", _config(include_disabled=False))
    commit_files(repo.root, ".teamctx/config.json", message="declared config")
    write_file(repo.root, _RECORD, _record())
    run = run_cli(
        ["work-start", "--path", _PATH],
        cwd=repo.root,
        env=SubprocessEnv(),
    )
    return run.output + "\nClosure\n" + _closure_evidence(repo.root) + "\n"


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        success = _success_half(tmp)
        failure = _failure_half(tmp)

    reason = "commit records/release.json to activate declared file source x_release_record"
    actual = "Success\n" + success + "\nFailure\n" + failure
    return passed_or_failed(
        ROW_ID,
        TITLE,
        actual,
        Expectation(
            must_match=(
                "Success",
                "Release record is blocked.",
                "Release cutoff has passed.",
                "Not enabled by the team: open PRs, spec changes, docs, failing checks, "
                "release note (enable in .teamctx/config.json).",
                "x_release_block: complete: doc_declared_x_release_record",
                "x_release_cutoff: complete: doc_declared_x_release_record",
                "x_release_note: disabled-by-team: none",
                "declared document count: 1",
                "Failure",
                (
                    "Couldn't check: release record could not be checked "
                    f"({reason}); release cutoff could not be checked ({reason})."
                ),
                "x_release_block: incomplete[stale-dep]: doc_declared_x_release_record",
                "x_release_cutoff: incomplete[stale-dep]: doc_declared_x_release_record",
            ),
            must_absent=(
                "not rendered",
                "Release note is present.",
            ),
        ),
    )


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
