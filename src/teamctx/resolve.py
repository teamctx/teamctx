"""Resolve a work-start request's inputs from the caller, project config, and git.

Both transports (the CLI and the MCP tool) call ``resolve_work_start_inputs`` before running
the broker, so they resolve identically. Precedence per field is
``explicit > .teamctx/config.json > git-detection > honest-absent``. Branch is never read from
config (it is volatile). A repository that cannot be resolved from any source raises
``WorkStartResolutionError``: there is nothing to check, so that is a setup error, not a
coverage gap.
"""

from __future__ import annotations

from pathlib import Path

from teamctx.git_context import detect_branch, detect_repo, parse_github_repo
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    WorkStartConfig,
    maybe_load_project_config,
)
from teamctx.runner import WorkStartInputs

_REPO_UNRESOLVED = (
    "could not determine the repository: not in a git repo with a recognizable 'origin' "
    "remote, and no work_start.repo in .teamctx/config.json. Pass the repo explicitly "
    "(--github-repo / repo=)."
)


class WorkStartResolutionError(ValueError):
    """Raised when a required work-start input (the repository) cannot be resolved."""


def resolve_work_start_inputs(
    *,
    paths: tuple[str, ...],
    repo: str | None = None,
    branch: str | None = None,
    docs_root: str | None = None,
    task: str = "Start work.",
    issues: tuple[str, ...] = (),
    since: str | None = None,
    ref: str | None = None,
    include_titles: bool = False,
    token: str | None = None,
    root: Path,
    config_path: Path | None = None,
) -> WorkStartInputs:
    config = _load_work_start_config(root, config_path)

    raw_repo = repo or _config_repo(config) or detect_repo(root)
    if raw_repo is None:
        raise WorkStartResolutionError(_REPO_UNRESOLVED)
    resolved_repo = parse_github_repo(raw_repo)
    if resolved_repo is None:
        raise WorkStartResolutionError(
            f"{raw_repo!r} is not a GitHub repo (owner/name). teamctx only checks GitHub today; "
            "pass a github.com repo with --github-repo or work_start.repo."
        )

    return WorkStartInputs(
        repo=resolved_repo,
        paths=tuple(paths),
        branch=branch or detect_branch(root),
        task=task,
        token=token,
        include_titles=include_titles,
        issues=tuple(issues),
        since=since,
        docs_root=docs_root or _config_docs_root(config),
        ref=ref,
    )


def _load_work_start_config(root: Path, config_path: Path | None) -> WorkStartConfig | None:
    path = config_path if config_path is not None else root / DEFAULT_CONFIG_PATH
    project = maybe_load_project_config(path)
    return project.work_start if project is not None else None


def _config_repo(config: WorkStartConfig | None) -> str | None:
    return config.repo if config is not None else None


def _config_docs_root(config: WorkStartConfig | None) -> str | None:
    return config.docs_root if config is not None else None
