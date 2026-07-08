from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from teamctx.connectors.declared_file import MAX_DECLARED_FILE_BYTES
from teamctx.contract_render import render_broker_answer
from teamctx.project_config import (
    ProjectConfigError,
    load_project_config,
    parse_project_config_text,
)
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

OBSERVED_AT = "2026-07-08T12:00:00Z"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
    _git(root, "add", "src/app.py")
    _git(root, "commit", "-qm", "base")
    _git(root, "remote", "add", "origin", "git@github.com:acme/widgets.git")


def _config(*, include_disabled: bool = True) -> dict[str, object]:
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
    return {
        "schema_version": "teamctx.project_config.v0",
        "work_start": {"repo": "acme/widgets"},
        "declared_sources": {
            "x_release_record": {
                "kind": "file",
                "path": "records/release.json",
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


def _write_config(root: Path, body: dict[str, object]) -> None:
    (root / ".teamctx").mkdir()
    (root / ".teamctx" / "config.json").write_text(json.dumps(body), encoding="utf-8")


def _write_record(root: Path, body: dict[str, object]) -> None:
    (root / "records").mkdir(exist_ok=True)
    (root / "records" / "release.json").write_text(json.dumps(body), encoding="utf-8")


def _answer(root: Path):
    inputs = resolve_work_start_inputs(paths=("src/app.py",), root=root)
    return work_start_answer(inputs, observed_at=OBSERVED_AT, project_root=root)


def test_declared_file_source_feeds_two_declared_checks_from_one_document(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config())
    _write_record(
        tmp_path,
        {
            "name": "release-one",
            "state": "blocked",
            "cutoff_at": "2026-07-08T00:00:00Z",
            "note": "plain note",
            "unmapped": "must not cross",
        },
    )
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    answer = _answer(tmp_path)
    text = render_broker_answer(answer)

    assert "Release record is blocked." in text
    assert "Release cutoff has passed." in text
    assert "release note (enable in .teamctx/config.json)." in text
    assert "must not cross" not in text
    declared_closure = {
        entry.check_id: entry
        for entry in answer.selection.closure
        if entry.check_id.startswith("x_")
    }
    assert declared_closure["x_release_block"].closure_status == "complete"
    assert declared_closure["x_release_cutoff"].closure_status == "complete"
    assert declared_closure["x_release_note"].closure_status == "disabled-by-team"
    assert declared_closure["x_release_block"].consumed_document_ids == (
        "doc_declared_x_release_record",
    )
    assert declared_closure["x_release_cutoff"].consumed_document_ids == (
        "doc_declared_x_release_record",
    )
    fetched = [
        doc for doc in answer.source_documents if doc.document_id == "doc_declared_x_release_record"
    ]
    assert len(fetched) == 1


def test_declared_record_present_only_in_worktree_is_refused_for_both_checks(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    _git(tmp_path, "add", ".teamctx/config.json")
    _git(tmp_path, "commit", "-qm", "config")
    _write_record(
        tmp_path,
        {
            "name": "release-one",
            "state": "blocked",
            "cutoff_at": "2026-07-08T00:00:00Z",
        },
    )

    answer = _answer(tmp_path)
    text = render_broker_answer(answer)

    reason = "commit records/release.json to activate declared file source x_release_record"
    assert (
        "Couldn't check: release record could not be checked "
        f"({reason}); release cutoff could not be checked ({reason})."
    ) in text
    declared_closure = {
        entry.check_id: entry
        for entry in answer.selection.closure
        if entry.check_id.startswith("x_")
    }
    assert declared_closure["x_release_block"].closure_status == "incomplete[stale-dep]"
    assert declared_closure["x_release_cutoff"].closure_status == "incomplete[stale-dep]"
    assert declared_closure["x_release_block"].consumed_document_ids == (
        "doc_declared_x_release_record",
    )
    assert declared_closure["x_release_cutoff"].consumed_document_ids == (
        "doc_declared_x_release_record",
    )


def test_declared_match_missing_mapped_field_is_per_check_unknown(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    _write_record(
        tmp_path,
        {"name": "release-one", "cutoff_at": "2026-07-08T00:00:00Z"},
    )
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    answer = _answer(tmp_path)
    text = render_broker_answer(answer)

    assert "release record could not be checked (field state is missing)" in text
    assert "Release cutoff has passed." in text
    closures = {entry.check_id: entry.closure_status for entry in answer.selection.closure}
    assert closures["x_release_block"] == "incomplete[stale-dep]"
    assert closures["x_release_cutoff"] == "complete"


def test_declared_record_duplicate_keys_are_rejected_at_fetch(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    (tmp_path / "records").mkdir()
    (tmp_path / "records" / "release.json").write_text(
        '{"name":"release-one","state":"open","state":"blocked"}',
        encoding="utf-8",
    )
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    text = render_broker_answer(_answer(tmp_path))

    assert "duplicate object key 'state'" in text
    assert "Release record is blocked." not in text


def test_declared_time_operand_malformed_is_per_check_unknown(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    _write_record(
        tmp_path,
        {"name": "release-one", "state": "open", "cutoff_at": "not-a-time"},
    )
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    text = render_broker_answer(_answer(tmp_path))

    assert "release cutoff could not be checked (time operand cutoff_at is malformed)" in text
    assert "release record is open" in text


def test_declared_source_symlink_is_refused(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    (tmp_path / "records").mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text('{"name":"release-one","state":"blocked"}', encoding="utf-8")
    try:
        (tmp_path / "records" / "release.json").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported here")
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    text = render_broker_answer(_answer(tmp_path))

    assert "not a symlink" in text
    assert "Release record is blocked." not in text


def test_declared_source_size_cap_is_refused(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _write_config(tmp_path, _config(include_disabled=False))
    (tmp_path / "records").mkdir()
    oversized = '{"name":"' + ("a" * MAX_DECLARED_FILE_BYTES) + '"}'
    (tmp_path / "records" / "release.json").write_text(oversized, encoding="utf-8")
    _git(tmp_path, "add", ".teamctx/config.json", "records/release.json")
    _git(tmp_path, "commit", "-qm", "declared checks")

    text = render_broker_answer(_answer(tmp_path))

    assert "is too large; maximum is" in text


def test_declared_url_source_fails_loud_in_this_version(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "declared_sources": {
                    "x_remote_record": {
                        "kind": "url",
                        "schema_map": {"state": "/state"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProjectConfigError, match="URL declared sources are not supported"):
        load_project_config(config_path)


def test_config_duplicate_keys_are_rejected() -> None:
    with pytest.raises(ProjectConfigError, match="duplicate object key 'checks'"):
        parse_project_config_text(
            '{"schema_version":"teamctx.project_config.v0","checks":{},"checks":{}}',
            "inline",
        )


def test_declared_check_shadowing_builtin_copy_is_rejected(tmp_path: Path) -> None:
    body = _config(include_disabled=False)
    checks = body["checks"]
    assert isinstance(checks, dict)
    check = checks["x_release_block"]
    assert isinstance(check, dict)
    copy = check["copy"]
    assert isinstance(copy, dict)
    copy["clear"] = "no failing checks found"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(ProjectConfigError, match="reserved built-in copy"):
        load_project_config(config_path)


def test_declared_source_and_check_id_collision_is_rejected(tmp_path: Path) -> None:
    body = _config(include_disabled=False)
    checks = body["checks"]
    assert isinstance(checks, dict)
    checks["x_release_record"] = checks.pop("x_release_block")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(body), encoding="utf-8")

    with pytest.raises(ProjectConfigError, match="collides"):
        load_project_config(config_path)
