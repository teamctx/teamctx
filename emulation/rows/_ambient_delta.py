from __future__ import annotations

from pathlib import Path
from typing import Any

from emulation.actors import DEFAULT_SLUG, LabRepo, build_lab_repo
from emulation.ambient_helpers import load_ambient_state
from emulation.mockgh import Fixtures, check_runs_payload, graphql_page, pr_node

DELTA_FILE = "src/a.py"
DELTA_BRANCH = "feature"
DELTA_SESSION = "delta-session"


def build_delta_repo(root: Path) -> LabRepo:
    return build_lab_repo(root, branch=DELTA_BRANCH, files={DELTA_FILE: "x\n"})


def clear_fixtures() -> Fixtures:
    return Fixtures(graphql_pages=[graphql_page([])], check_runs=check_runs_payload([]))


def collision_fixtures(number: int = 7) -> Fixtures:
    return Fixtures(
        graphql_pages=[
            graphql_page([
                pr_node(number, [DELTA_FILE], head_ref="feat/other", head_repo=DEFAULT_SLUG)
            ])
        ],
        check_runs=check_runs_payload([]),
    )


def replace_with_collision(fixtures: Fixtures, *, number: int = 7) -> None:
    fixtures.graphql_pages = collision_fixtures(number).graphql_pages
    fixtures.check_runs = check_runs_payload([])


def replace_with_clear(fixtures: Fixtures) -> None:
    fixtures.graphql_pages = [graphql_page([])]
    fixtures.check_runs = check_runs_payload([])


def only_baseline(state_dir: Path, session_id: str) -> dict[str, Any]:
    state = load_ambient_state(state_dir, session_id)
    baselines = state["baselines"]
    if not isinstance(baselines, dict) or len(baselines) != 1:
        raise RuntimeError("expected exactly one ambient baseline")
    baseline = next(iter(baselines.values()))
    if not isinstance(baseline, dict):
        raise RuntimeError("ambient baseline was not an object")
    return baseline
