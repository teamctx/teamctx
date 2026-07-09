from __future__ import annotations

import json
import os
import stat
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from teamctx.ambient import (
    Baseline,
    BaselineMaterial,
    CheckMaterial,
    Delta,
    FindingMaterial,
    ambient_interval_seconds,
    ambient_state_dir,
    build_delta_document,
    compute_baseline_material,
    compute_deltas,
    compute_key,
    decide,
    deltas_from_signals,
    finding_key,
    load_baseline,
    store_baseline,
)
from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal


def _baseline(
    *,
    key: str = "key-1",
    digest: str = "digest-1",
    class_of_answer: str = "GOOD",
    last_network_check_at: float = 1000.0,
    last_spoken_at: float = 1000.0,
    material: BaselineMaterial | None = None,
) -> Baseline:
    return Baseline(
        key=key,
        content_digest=digest,
        class_of_answer=class_of_answer,
        last_network_check_at=last_network_check_at,
        last_spoken_at=last_spoken_at,
        material=material if material is not None else BaselineMaterial(),
    )


def test_load_missing_baseline_is_none(tmp_path: Path) -> None:
    assert load_baseline(tmp_path / ".teamctx" / "ambient", "sess-1", "key-1") is None


def test_store_and_load_baseline_round_trips_with_0600_mode(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    baseline = _baseline()

    store_baseline(state_dir, "sess-1", baseline, now=1000.0, project_root=tmp_path)

    assert load_baseline(state_dir, "sess-1", "key-1") == baseline
    mode = stat.S_IMODE((state_dir / "sess-1.json").stat().st_mode)
    assert mode == 0o600


def test_load_baseline_is_isolated_by_key_and_session(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    store_baseline(state_dir, "sess-1", _baseline(key="key-1"), now=1000.0)
    store_baseline(state_dir, "sess-2", _baseline(key="key-1"), now=1000.0)

    assert load_baseline(state_dir, "sess-1", "key-1") == _baseline(key="key-1")
    assert load_baseline(state_dir, "sess-1", "key-2") is None
    assert load_baseline(state_dir, "sess-3", "key-1") is None


def test_corrupt_state_file_is_none_and_next_store_overwrites(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    (state_dir / "sess-1.json").write_text("{not-json", encoding="utf-8")

    assert load_baseline(state_dir, "sess-1", "key-1") is None

    baseline = _baseline()
    store_baseline(state_dir, "sess-1", baseline, now=1000.0)
    assert load_baseline(state_dir, "sess-1", "key-1") == baseline


def test_v0_state_file_reads_as_no_baseline_after_the_schema_bump(tmp_path: Path) -> None:
    # A well-formed v0 file (the A-2a shape, before delta material) is a different schema and must
    # read as no-baseline; the next write overwrites it with a v1 file.
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    (state_dir / "sess-1.json").write_text(
        json.dumps({
            "schema_version": "teamctx.ambient_state.v0",
            "session_id": "sess-1",
            "baselines": {
                "key-1": {
                    "key": "key-1",
                    "content_digest": "digest-1",
                    "class_of_answer": "GOOD",
                    "last_network_check_at": 1000.0,
                    "last_spoken_at": 1000.0,
                }
            },
        }),
        encoding="utf-8",
    )

    assert load_baseline(state_dir, "sess-1", "key-1") is None


def test_v1_state_file_reads_as_no_baseline_after_the_closure_schema_bump(
    tmp_path: Path,
) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    (state_dir / "sess-1.json").write_text(
        json.dumps({
            "schema_version": "teamctx.ambient_state.v1",
            "session_id": "sess-1",
            "baselines": {
                "key-1": {
                    "key": "key-1",
                    "content_digest": "digest-1",
                    "class_of_answer": "GOOD",
                    "last_network_check_at": 1000.0,
                    "last_spoken_at": 1000.0,
                    "material": {
                        "checks": [
                            {
                                "check": "conflict",
                                "status": "clear",
                                "note": None,
                                "findings": [],
                            }
                        ]
                    },
                }
            },
        }),
        encoding="utf-8",
    )

    assert load_baseline(state_dir, "sess-1", "key-1") is None


def test_material_round_trips_through_store_and_load(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    material = BaselineMaterial(
        checks=(
            CheckMaterial(
                check="conflict",
                status="found",
                note=None,
                findings=(
                    FindingMaterial(
                        key="conflict:7",
                        source_display="GitHub PR #7",
                        paths=("src/app.py",),
                    ),
                ),
            ),
            CheckMaterial(check="gate", status="unreachable", note="couldn't reach GitHub"),
        )
    )
    baseline = _baseline(material=material)

    store_baseline(state_dir, "sess-1", baseline, now=1000.0, project_root=tmp_path)

    assert load_baseline(state_dir, "sess-1", "key-1") == baseline


def test_corrupt_material_shape_is_read_as_no_baseline(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    (state_dir / "sess-1.json").write_text(
        json.dumps({
            "schema_version": "teamctx.ambient_state.v2",
            "session_id": "sess-1",
            "baselines": {
                "key-1": {
                    "key": "key-1",
                    "content_digest": "digest-1",
                    "class_of_answer": "GOOD",
                    "last_network_check_at": 1000.0,
                    "last_spoken_at": 1000.0,
                    "material": {"checks": "not-a-list"},
                }
            },
        }),
        encoding="utf-8",
    )

    assert load_baseline(state_dir, "sess-1", "key-1") is None


def _request(paths: tuple[str, ...] = ("src/app.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0", request_id="t", repo="acme/widgets",
        branch="feature", task="work", paths=list(paths), linked_issues=[],
        requested_at="2026-07-04T00:00:00Z", requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0", id="sig_pr_7", signal_type="collision",
        source_family="git_hosting",
        scope={"provider": "github", "repo": "acme/widgets", "pr_number": 7,
               "files": ["src/app.py"]},
        evidence_summary="Open PR #7 changed src/app.py.", source_display="GitHub PR #7",
        freshness="fresh", confidence="high", visibility="visible",
        created_at="2026-07-04T00:00:00Z", observed_at="2026-07-04T00:00:00Z",
        expires_at="next_refresh", policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh(family: str) -> object:
    return source_status(
        source_id=f"{family}-probe", source_family=family, scope={"repo": "acme/widgets"},
        status="fresh", observed_at="2026-07-04T00:00:00Z", safe_user_message="checked",
        visibility="silent", policy_reason="status only",
    )


def test_compute_baseline_material_captures_status_and_finding_identity() -> None:
    answer = broker_answer(_request(), [_collision_signal()], [_fresh("git_hosting")])

    material = compute_baseline_material(answer)

    by_check = {c.check: c for c in material.checks}
    assert by_check["conflict"].status == "found"
    assert by_check["conflict"].findings == (
        FindingMaterial(key="conflict:7", source_display="GitHub PR #7", paths=("src/app.py",)),
    )
    assert by_check["gate"].status == "not_configured"
    assert by_check["gate"].findings == ()


def test_finding_key_is_stable_per_check_identity_field() -> None:
    assert finding_key("conflict", {"pr_number": 7}) == "conflict:7"
    assert finding_key("criteria", {"issue": "#12"}) == "criteria:#12"
    assert finding_key("docs", {"doc": "spec.md"}) == "docs:spec.md"
    assert finding_key("gate", {"gate": "build"}) == "gate:build"


def _pr(number: int, paths: tuple[str, ...] = ("src/app.py",)) -> FindingMaterial:
    return FindingMaterial(
        key=f"conflict:{number}", source_display=f"GitHub PR #{number}", paths=paths
    )


def _check(check: str, status: str, *findings: FindingMaterial, note: str | None = None) -> (
    CheckMaterial
):
    return CheckMaterial(check=check, status=status, note=note, findings=findings)


def test_no_baseline_yields_no_deltas() -> None:
    assert compute_deltas(None, BaselineMaterial((_check("conflict", "found", _pr(7)),))) == ()


def test_appear_per_check() -> None:
    conflict = compute_deltas(
        BaselineMaterial((_check("conflict", "clear"),)),
        BaselineMaterial((_check("conflict", "found", _pr(7)),)),
    )
    assert conflict == (Delta("appear", "conflict", _pr(7)),)

    gate_finding = FindingMaterial(key="gate:build", source_display="CI: build", gate="build")
    gate = compute_deltas(
        BaselineMaterial((_check("gate", "clear"),)),
        BaselineMaterial((_check("gate", "found", gate_finding),)),
    )
    assert gate == (Delta("appear", "gate", gate_finding),)


def test_disappear_per_check() -> None:
    result = compute_deltas(
        BaselineMaterial((_check("conflict", "found", _pr(7)),)),
        BaselineMaterial((_check("conflict", "clear"),)),
    )
    assert result == (Delta("disappear", "conflict", _pr(7)),)


def test_transition_when_a_gap_closes() -> None:
    result = compute_deltas(
        BaselineMaterial((_check("gate", "unreachable"),)),
        BaselineMaterial((_check("gate", "clear"),)),
    )
    assert result == (Delta("transition", "gate", FindingMaterial(key="gate:__source__")),)


def test_coverage_shrank_when_verified_becomes_unreachable() -> None:
    result = compute_deltas(
        BaselineMaterial((_check("conflict", "clear"),)),
        BaselineMaterial((_check("conflict", "unreachable", note="couldn't reach GitHub"),)),
    )
    assert result == (
        Delta(
            "coverage_shrank",
            "conflict",
            FindingMaterial(key="conflict:__source__"),
            note="couldn't reach GitHub",
        ),
    )


def test_reopened_pr_re_speaks_as_a_fresh_appearance() -> None:
    present = BaselineMaterial((_check("conflict", "found", _pr(7)),))
    absent = BaselineMaterial((_check("conflict", "clear"),))

    assert compute_deltas(present, absent) == (Delta("disappear", "conflict", _pr(7)),)
    assert compute_deltas(absent, present) == (Delta("appear", "conflict", _pr(7)),)


def test_same_finding_across_runs_is_no_delta() -> None:
    present = BaselineMaterial((_check("conflict", "found", _pr(7)),))
    assert compute_deltas(present, present) == ()


def test_swapped_finding_is_a_disappear_and_an_appear() -> None:
    result = compute_deltas(
        BaselineMaterial((_check("conflict", "found", _pr(7)),)),
        BaselineMaterial((_check("conflict", "found", _pr(8)),)),
    )
    assert result == (Delta("appear", "conflict", _pr(8)), Delta("disappear", "conflict", _pr(7)))


def test_delta_signals_round_trip_through_mint_and_read() -> None:
    deltas = (
        Delta("appear", "conflict", _pr(7)),
        Delta(
            "disappear", "gate",
            FindingMaterial(key="gate:build", source_display="CI: build", gate="build"),
        ),
        Delta(
            "coverage_shrank", "conflict", FindingMaterial(key="conflict:__source__"),
            note="couldn't reach GitHub",
        ),
    )

    document = build_delta_document(_request(), deltas, observed_at="2026-07-04T00:00:00Z")

    assert all(s.signal_type == "changed_since_start" for s in document.source_signals)
    assert deltas_from_signals(document.source_signals) == deltas


def test_delta_signals_never_derive_a_card_verdict_or_closure() -> None:
    deltas = (Delta("appear", "conflict", _pr(7)),)
    document = build_delta_document(_request(), deltas, observed_at="2026-07-04T00:00:00Z")

    answer = broker_answer(_request(), document.source_signals, [_fresh("git_hosting")])

    # the changed_since_start signal rides in source_signals but derives no card and no closure
    # entry (no CardKind), so the kind stays the current world.
    assert answer.selection.cards == ()
    assert deltas_from_signals(answer.source_signals) == deltas


def test_deltas_from_signals_ignores_non_delta_signals() -> None:
    assert deltas_from_signals([_collision_signal()]) == ()


def test_wrong_shape_or_version_is_none(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    (state_dir / "sess-1.json").write_text(
        json.dumps({"schema_version": "old", "baselines": {}}),
        encoding="utf-8",
    )
    (state_dir / "sess-2.json").write_text(
        json.dumps({"schema_version": "teamctx.ambient_state.v0", "baselines": []}),
        encoding="utf-8",
    )

    assert load_baseline(state_dir, "sess-1", "key-1") is None
    assert load_baseline(state_dir, "sess-2", "key-1") is None


def test_store_preserves_other_keys_in_the_session_file(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    store_baseline(state_dir, "sess-1", _baseline(key="a"), now=1000.0)
    store_baseline(state_dir, "sess-1", _baseline(key="b", digest="digest-b"), now=1001.0)

    assert load_baseline(state_dir, "sess-1", "a") == _baseline(key="a")
    assert load_baseline(state_dir, "sess-1", "b") == _baseline(key="b", digest="digest-b")


def test_store_evicts_session_files_older_than_seven_days(tmp_path: Path) -> None:
    state_dir = tmp_path / ".teamctx" / "ambient"
    state_dir.mkdir(parents=True)
    stale = state_dir / "stale.json"
    fresh = state_dir / "fresh.json"
    stale.write_text("{}", encoding="utf-8")
    fresh.write_text("{}", encoding="utf-8")
    os.utime(stale, (1000.0, 1000.0))
    os.utime(fresh, (1000.0 + 6 * 86400, 1000.0 + 6 * 86400))

    store_baseline(state_dir, "sess-1", _baseline(), now=1000.0 + 8 * 86400)

    assert not stale.exists()
    assert fresh.exists()


def test_store_ensures_ambient_state_is_ignored_on_first_write(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)

    state_dir = tmp_path / ".teamctx" / "ambient"
    store_baseline(state_dir, "sess-1", _baseline(), now=1000.0, project_root=tmp_path)

    gitignore = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".teamctx/ambient/" in gitignore
    result = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--no-index", ".teamctx/ambient/sess-1.json"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


def test_compute_key_is_order_independent_for_path_and_issue_sets() -> None:
    a = compute_key(
        repo="acme/widgets",
        forge="github",
        branch="feature",
        paths=("src/b.py", "./src/a.py", "src/a.py"),
        issues=("#2", "#1"),
        since="2026-07-01T00:00:00Z",
        docs_root="docs",
        profile="reflex",
        token_present=True,
        config_bytes=b"config",
        authority_bytes=b"authority",
        version="0.0.0",
    )
    b = compute_key(
        repo="acme/widgets",
        forge="github",
        branch="feature",
        paths=("src/a.py", "src/b.py"),
        issues=("#1", "#2"),
        since="2026-07-01T00:00:00Z",
        docs_root="docs",
        profile="reflex",
        token_present=True,
        config_bytes=b"config",
        authority_bytes=b"authority",
        version="0.0.0",
    )

    assert a == b


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repo", "acme/other"),
        ("forge", "gitlab"),
        ("branch", "other-branch"),
        ("paths", ("src/a.py", "src/b.py", "src/c.py")),
        ("issues", ("#1", "#3")),
        ("since", "2026-07-02T00:00:00Z"),
        ("docs_root", "handbook"),
        ("profile", "full"),
        ("token_present", False),
        ("config_bytes", b"changed config"),
        ("authority_bytes", b"changed authority"),
        ("version", "0.0.1"),
    ],
)
def test_compute_key_isolates_every_pinned_input(field: str, value: object) -> None:
    kwargs: dict[str, object] = {
        "repo": "acme/widgets",
        "forge": "github",
        "branch": "feature",
        "paths": ("src/a.py", "src/b.py"),
        "issues": ("#1", "#2"),
        "since": "2026-07-01T00:00:00Z",
        "docs_root": "docs",
        "profile": "reflex",
        "token_present": True,
        "config_bytes": b"config",
        "authority_bytes": b"authority",
        "version": "0.0.0",
    }
    base = compute_key(**kwargs)  # type: ignore[arg-type]
    kwargs[field] = value

    assert base != compute_key(**kwargs)  # type: ignore[arg-type]


def test_env_overrides_are_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("TEAMCTX_AMBIENT_STATE", raising=False)
    assert ambient_state_dir(tmp_path) == tmp_path / ".teamctx" / "ambient"

    monkeypatch.setenv("TEAMCTX_AMBIENT_STATE", str(tmp_path / "state-a"))
    assert ambient_state_dir(tmp_path) == tmp_path / "state-a"

    monkeypatch.setenv("TEAMCTX_AMBIENT_STATE", str(tmp_path / "state-b"))
    assert ambient_state_dir(tmp_path) == tmp_path / "state-b"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, 90),
        ("120", 120),
        ("29", 30),
        ("not-int", 90),
    ],
)
def test_interval_default_and_floor_are_read_at_call_time(
    monkeypatch: pytest.MonkeyPatch, raw: str | None, expected: int
) -> None:
    if raw is None:
        monkeypatch.delenv("TEAMCTX_AMBIENT_INTERVAL_SECONDS", raising=False)
    else:
        monkeypatch.setenv("TEAMCTX_AMBIENT_INTERVAL_SECONDS", raw)

    assert ambient_interval_seconds() == expected


def test_decide_none_baseline_speaks_full() -> None:
    assert decide(None, now=1000.0, interval=90, content_digest="d", class_of_answer="GOOD") == (
        "speak_full"
    )


@pytest.mark.parametrize("answer_class", ["GOOD", "GAP-KNOWN"])
def test_decide_same_baseline_inside_interval_is_silent(answer_class: str) -> None:
    baseline = _baseline(class_of_answer=answer_class, last_network_check_at=1000.0)
    assert decide(
        baseline,
        now=1089.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="NONE",
    ) == "silent"


def test_decide_interval_expired_requires_recheck_before_speaking() -> None:
    baseline = _baseline(last_network_check_at=1000.0)
    assert decide(
        baseline,
        now=1090.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="NONE",
    ) == "recheck_due"


@pytest.mark.parametrize(
    ("digest", "answer_class"),
    [
        ("digest-2", "GOOD"),
        ("digest-1", "GAP-KNOWN"),
    ],
)
def test_decide_observed_content_or_class_transition_speaks(
    digest: str, answer_class: str
) -> None:
    baseline = _baseline(class_of_answer="GOOD", last_network_check_at=1000.0)
    assert decide(
        baseline,
        now=1001.0,
        interval=90,
        content_digest=digest,
        class_of_answer=answer_class,
    ) == "speak_full"


def test_decide_same_good_after_recheck_is_silent() -> None:
    baseline = _baseline(class_of_answer="GOOD", last_network_check_at=1000.0)
    assert decide(
        baseline,
        now=1090.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="GOOD",
    ) == "silent"


def test_decide_same_gap_after_recheck_restates_only_after_max_period() -> None:
    baseline = _baseline(
        class_of_answer="GAP-KNOWN",
        last_network_check_at=1000.0,
        last_spoken_at=1000.0,
    )

    assert decide(
        baseline,
        now=1090.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="GAP-KNOWN",
    ) == "silent"
    assert decide(
        baseline,
        now=1900.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="GAP-KNOWN",
    ) == "speak_full"


def test_decide_restatement_period_rides_a_long_interval() -> None:
    baseline = _baseline(
        class_of_answer="GAP-KNOWN",
        last_network_check_at=1000.0,
        last_spoken_at=1000.0,
    )

    assert decide(
        baseline,
        now=1900.0,
        interval=3600,
        content_digest=baseline.content_digest,
        class_of_answer="GAP-KNOWN",
    ) == "silent"
    assert decide(
        baseline,
        now=4600.0,
        interval=3600,
        content_digest=baseline.content_digest,
        class_of_answer="GAP-KNOWN",
    ) == "speak_full"


def test_decide_stored_none_class_is_not_a_silent_baseline() -> None:
    baseline = replace(_baseline(), class_of_answer="NONE")
    assert decide(
        baseline,
        now=1001.0,
        interval=90,
        content_digest=baseline.content_digest,
        class_of_answer="NONE",
    ) == "speak_full"
