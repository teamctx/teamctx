"""Committed team-semantics reads for config and authority files.

Normal surfaces read team semantics from the committed HEAD blob, not the working tree. This is
an I/O edge: it shells out to git and feeds parsed data into the deterministic broker path.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from teamctx.config_failure import (
    ALLOW_DIRTY_CONFIG_BANNER,
    COMMIT_CONFIG_TO_ACTIVATE_LINE,
    CONFIG_DIRTY_NOTE,
)
from teamctx.connectors.declared_authority import (
    parse_declared_authority_bytes,
)
from teamctx.core.authority import AuthorityDecl
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    ProjectConfig,
    parse_project_config_bytes,
)
from teamctx.work_start_paths import DEFAULT_AUTHORITY_PATH

SemanticsState = Literal[
    "committed_clean",
    "committed_dirty",
    "uncommitted_refused",
    "no_git_or_no_head_refused",
    "allow_dirty",
]


@dataclass(frozen=True)
class SemanticsFile:
    rel_path: str
    state: SemanticsState
    data: bytes | None
    working_tree_exists: bool = False

    @property
    def key_bytes(self) -> bytes:
        return self.data or b""


@dataclass(frozen=True)
class TeamProjectConfig:
    config: ProjectConfig | None
    file: SemanticsFile


@dataclass(frozen=True)
class TeamAuthority:
    declarations: list[AuthorityDecl]
    file: SemanticsFile


def load_team_project_config(root: Path, *, allow_dirty: bool = False) -> TeamProjectConfig:
    file = read_team_semantics_file(root, DEFAULT_CONFIG_PATH.as_posix(), allow_dirty=allow_dirty)
    if file.data is None:
        return TeamProjectConfig(config=None, file=file)
    config = parse_project_config_bytes(file.data, _display_source(root, file))
    return TeamProjectConfig(config=config, file=file)


def load_team_authority(root: Path, *, allow_dirty: bool = False) -> TeamAuthority:
    file = read_team_semantics_file(
        root, DEFAULT_AUTHORITY_PATH.as_posix(), allow_dirty=allow_dirty
    )
    if file.data is None:
        return TeamAuthority(declarations=[], file=file)
    declarations = parse_declared_authority_bytes(file.data, _display_source(root, file))
    return TeamAuthority(declarations=declarations, file=file)


def read_team_semantics_file(
    root: Path, rel_path: str, *, allow_dirty: bool = False
) -> SemanticsFile:
    if allow_dirty:
        working = _read_working_tree_bytes(root, rel_path)
        return SemanticsFile(
            rel_path=rel_path,
            state="allow_dirty",
            data=working,
            working_tree_exists=working is not None,
        )

    working = _read_working_tree_bytes(root, rel_path)
    if not _has_head(root):
        return SemanticsFile(
            rel_path=rel_path,
            state="no_git_or_no_head_refused",
            data=None,
            working_tree_exists=working is not None,
        )

    committed = _show_head_blob(root, rel_path)
    if committed is None:
        if working is not None:
            return SemanticsFile(
                rel_path=rel_path,
                state="uncommitted_refused",
                data=None,
                working_tree_exists=True,
            )
        return SemanticsFile(rel_path=rel_path, state="committed_clean", data=None)

    state: SemanticsState = "committed_clean" if working == committed else "committed_dirty"
    return SemanticsFile(
        rel_path=rel_path,
        state=state,
        data=committed,
        working_tree_exists=working is not None,
    )


def semantics_notices(
    *,
    config: SemanticsFile | None = None,
    authority: SemanticsFile | None = None,
    allow_dirty: bool = False,
) -> tuple[str, ...]:
    notices: list[str] = []
    if allow_dirty:
        notices.append(ALLOW_DIRTY_CONFIG_BANNER)
    if config is not None and config.working_tree_exists and config.state in {
        "uncommitted_refused",
        "no_git_or_no_head_refused",
    }:
        notices.append(COMMIT_CONFIG_TO_ACTIVATE_LINE)
    if (config is not None and config.state == "committed_dirty") or (
        authority is not None and authority.state == "committed_dirty"
    ):
        notices.append(CONFIG_DIRTY_NOTE)
    return _dedupe(notices)


def _display_source(root: Path, file: SemanticsFile) -> str:
    source = str(root / file.rel_path)
    if file.state == "allow_dirty":
        return source
    return f"{source} (HEAD)"


def _dedupe(lines: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(lines))


def _read_working_tree_bytes(root: Path, rel_path: str) -> bytes | None:
    try:
        return (root / rel_path).read_bytes()
    except OSError:
        return None


def _has_head(root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return True


def _show_head_blob(root: Path, rel_path: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{rel_path}"],
            capture_output=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout
