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

from teamctx.clock import parse_since
from teamctx.discover import derive_issues, derive_since
from teamctx.git_context import (
    ForgeProvider,
    detect_branch,
    detect_forge_repo,
    parse_github_repo,
    parse_gitlab_repo,
    repo_relative_path,
)
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


def resolve_github_repo(
    explicit: str | None, config_repo: str | None, detected: str | None
) -> tuple[str | None, str | None]:
    """The github.com owner/name to use, by the one precedence every surface shares:
    explicit > config > git-detect (truthy, so an empty string is treated as absent), validated via
    ``parse_github_repo``. Returns ``(repo, None)`` or ``(None, error_message)``. This is THE single
    source of repo resolution, so a setup command (onboard) cannot drift from what work-start
    resolves; both call this with their own explicit/config/detected inputs."""

    detected_forge: tuple[str, ForgeProvider] | None = (detected, "github") if detected else None
    resolved, error = resolve_forge_repo(explicit, config_repo, "github", detected_forge)
    if resolved is None:
        return None, error
    return resolved[0], None


def resolve_forge_repo(
    explicit: str | None,
    config_repo: str | None,
    config_forge: ForgeProvider | None,
    detected: tuple[str, ForgeProvider] | None,
) -> tuple[tuple[str, ForgeProvider] | None, str | None]:
    """Provider-aware repo resolution.

    Repo precedence stays ``explicit > config > git-detect``. Forge precedence is independent:
    ``config.forge > detected-forge > github``. The selected repo string is then parsed under the
    resolved forge, so a committed forge setting is authoritative even when the git origin host
    differs.
    """

    resolved_forge = config_forge or (detected[1] if detected is not None else "github")
    raw_repo = explicit or config_repo or (detected[0] if detected is not None else None)
    if not raw_repo:
        return None, _REPO_UNRESOLVED
    normalized = _parse_repo_for_forge(raw_repo, resolved_forge)
    if normalized is None:
        return None, _repo_parse_error(raw_repo, resolved_forge)
    return (normalized, resolved_forge), None


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

    resolved, repo_error = resolve_forge_repo(
        repo,
        _config_repo(config),
        _config_forge(config),
        detect_forge_repo(root),
    )
    if resolved is None:
        raise WorkStartResolutionError(repo_error or _REPO_UNRESOLVED)
    resolved_repo, resolved_forge = resolved

    resolved_issues = tuple(issues)
    resolved_since = since
    provenance: list[tuple[str, str]] = []
    issues_capped = False

    if not resolved_issues:
        derived = derive_issues(root)
        resolved_issues = tuple(issue_ref for issue_ref, _ in derived.issues)
        provenance.extend((f"issue:{issue_ref}", source) for issue_ref, source in derived.issues)
        issues_capped = derived.capped

    if resolved_since is None:
        derived_since = derive_since(root)
        if derived_since is not None:
            resolved_since, source = derived_since
            provenance.append(("since", source))
    else:
        try:
            parse_since(resolved_since)
        except ValueError as exc:
            raise WorkStartResolutionError(str(exc)) from exc

    return WorkStartInputs(
        repo=resolved_repo,
        paths=tuple(repo_relative_path(root, path) for path in paths),
        branch=branch or detect_branch(root),
        task=task,
        token=token,
        include_titles=include_titles,
        issues=resolved_issues,
        since=resolved_since,
        input_provenance=tuple(provenance),
        derived_issues_capped=issues_capped,
        docs_root=docs_root or _config_docs_root(config),
        ref=ref,
        forge=resolved_forge,
    )


def _load_work_start_config(root: Path, config_path: Path | None) -> WorkStartConfig | None:
    path = config_path if config_path is not None else root / DEFAULT_CONFIG_PATH
    project = maybe_load_project_config(path)
    return project.work_start if project is not None else None


def _config_repo(config: WorkStartConfig | None) -> str | None:
    return config.repo if config is not None else None


def _config_forge(config: WorkStartConfig | None) -> ForgeProvider | None:
    return config.forge if config is not None else None


def _config_docs_root(config: WorkStartConfig | None) -> str | None:
    return config.docs_root if config is not None else None


def _parse_repo_for_forge(repo: str, forge: ForgeProvider) -> str | None:
    if forge == "github":
        return parse_github_repo(repo)
    return parse_gitlab_repo(repo)


def _repo_parse_error(raw_repo: str, forge: ForgeProvider) -> str:
    if forge == "github":
        return (
            f"{raw_repo!r} is not a GitHub repo (owner/name). teamctx only checks GitHub today; "
            "pass a github.com repo with --github-repo or work_start.repo."
        )
    return (
        f"{raw_repo!r} is not a GitLab repo (group/project). Pass a gitlab.com repo with "
        "work_start.repo and work_start.forge."
    )
