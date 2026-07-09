"""The one composed CONFLICT scenario shared by row 10 (transports agree) and row 11 (replay).

A conflict is used deliberately: the hook speaks conflict, so cross-transport agreement is
non-vacuous (all three transports have something to say and must say the same thing). One open PR
on a different branch touches the file the actor is about to edit; the gate is clear so the
conflict is the single subject.
"""

from __future__ import annotations

from pathlib import Path

from emulation.actors import DEFAULT_SLUG, LabRepo, build_lab_repo
from emulation.mockgh import Fixtures, check_runs_payload, graphql_page, pr_node

CONFLICT_BRANCH = "feat/x"
CONFLICT_FILE = "src/a.py"
CONFLICT_PR = 7


def conflict_fixtures() -> Fixtures:
    node = pr_node(
        CONFLICT_PR, [CONFLICT_FILE], head_ref="feat/other", head_repo=DEFAULT_SLUG
    )
    return Fixtures(graphql_pages=[graphql_page([node])], check_runs=check_runs_payload([]))


def build_conflict_repo(root: Path) -> LabRepo:
    return build_lab_repo(root, branch=CONFLICT_BRANCH, files={CONFLICT_FILE: "x\n"})
