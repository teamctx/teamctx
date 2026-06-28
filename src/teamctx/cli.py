"""Command line entrypoint for teamctx."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import click

from teamctx.clock import utc_now_iso
from teamctx.connectors.declared_authority import load_declared_authority
from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.connectors.github import run_github_pr_probe
from teamctx.connectors.github_checks import run_github_checks_probe
from teamctx.connectors.github_issues import run_github_issues_probe
from teamctx.contract_documents import (
    ContractDocumentError,
    load_contract_document,
    write_contract_document,
)
from teamctx.contract_render import (
    render_broker_answer,
    render_contract_context,
    render_contract_open_source,
    render_contract_why,
)
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.eval.pack import export_eval_pack
from teamctx.eval.scenario import EvalScenarioError
from teamctx.git_context import detect_repo
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_PATH,
    ProjectConfig,
    ProjectConfigError,
    build_work_start_project_config,
    maybe_load_project_config,
    write_project_config,
)
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs
from teamctx.tokens import resolve_token
from teamctx.work_start import render_work_start


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="teamctx")
def main() -> None:
    """Deterministic ambient context for software teams."""


@main.command()
def status() -> None:
    """Show local teamctx status."""

    click.echo("teamctx is initialized. No sources are configured yet.")


@main.command("init")
@click.option(
    "--repo",
    "repo",
    default=None,
    help="Repository in owner/name form. Auto-detected from the git 'origin' remote if omitted.",
)
@click.option(
    "--docs-root",
    "docs_root",
    default=None,
    help="Folder of design docs to watch for supersession. Auto-detected from a 'docs' folder.",
)
@click.option(
    "--config",
    "config_path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project config path.",
)
@click.option("--force", is_flag=True, help="Overwrite an existing project config.")
def init_command(repo: str | None, docs_root: str | None, config_path: Path, force: bool) -> None:
    """Scaffold the project-local teamctx config for work-start."""

    root = Path.cwd()
    resolved_repo = repo or detect_repo(root)
    if resolved_repo is None:
        raise click.ClickException(
            "Could not determine the repository: this is not a git repo with a recognizable "
            "'origin' remote. Pass --repo owner/name."
        )
    resolved_docs_root = docs_root if docs_root is not None else _detect_docs_root(root)

    config = build_work_start_project_config(repo=resolved_repo, docs_root=resolved_docs_root)
    try:
        write_project_config(config_path, config, overwrite=force)
    except ProjectConfigError as exc:
        raise click.ClickException(f"{exc} Pass --force to overwrite.") from exc

    click.echo(f"Wrote {config_path} for {resolved_repo}.")
    if resolved_docs_root:
        click.echo(f"  Docs root: {resolved_docs_root} (teamctx will flag superseded docs there).")
    else:
        click.echo(
            "  Docs root: not set. If you keep design docs in a folder, add a docs_root to the "
            "config so teamctx can flag superseded ones."
        )
    click.echo(
        "  GitHub access: set GITHUB_TOKEN, or GITHUB_TOKEN_FILE with a path to a token file, so "
        "teamctx can see open PRs and failing checks. Without it those read as 'couldn't check', "
        "never a false all-clear."
    )
    click.echo("Next: run `teamctx work-start` before you start editing.")


@main.command("github-pr-probe")
@click.option("--repo", required=True, help="GitHub repository in owner/name form.")
@click.option("--path", "paths", multiple=True, required=True, help="Current task file path.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Probe GitHub PR metadata.", show_default=True, help="Task text.")
@click.option("--token-env", default="GITHUB_TOKEN", show_default=True, help="Token env var name.")
@click.option(
    "--include-title/--omit-title",
    default=False,
    show_default=True,
    help="Whether PR titles are allowed in normalized metadata.",
)
def github_pr_probe_command(
    repo: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
    include_title: bool,
) -> None:
    """Emit Core Contract V0 context from GitHub PR metadata."""

    document = _github_contract_document(
        repo=repo,
        paths=paths,
        branch=branch,
        task=task,
        token_env=token_env,
        include_title=include_title,
    )
    click.echo(json.dumps(document.model_dump(mode="json"), indent=2), nl=True)


@main.command("work-start")
@click.option(
    "--github-repo", "repo", default=None,
    help="GitHub repo owner/name. Optional: auto-detected from the git 'origin' remote or "
         ".teamctx/config.json when omitted.",
)
@click.option(
    "--path", "paths", multiple=True, required=True, help="A path the work is about to touch."
)
@click.option("--branch", default=None, help="Current branch name (also the default gate ref).")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
@click.option(
    "--token-env",
    default="GITHUB_TOKEN",
    show_default=True,
    help="Name of the env var holding the GitHub token.",
)
@click.option(
    "--include-title/--omit-title", default=False, help="Allow PR titles in normalized metadata."
)
@click.option("--issue", "issues", multiple=True, help="A linked issue to check (e.g. #42).")
@click.option("--since", default=None, help="ISO timestamp: issue changes after this are surfaced.")
@click.option("--docs-root", default=None, help="Docs root to scan for supersession frontmatter.")
@click.option("--ref", default=None, help="Gate ref to read check-runs for (defaults to --branch).")
def work_start_command(
    repo: str | None,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
    include_title: bool,
    issues: tuple[str, ...],
    since: str | None,
    docs_root: str | None,
    ref: str | None,
) -> None:
    """Derive unified work-start context: run every connector the inputs allow (collisions +
    gates + linked-issue criteria + relied-on docs), compose, and report cards + honest
    coverage + one verdict per check. Sources not reachable from the inputs stay Unknown."""

    try:
        inputs = resolve_work_start_inputs(
            paths=paths,
            repo=repo,
            branch=branch,
            docs_root=docs_root,
            task=task,
            issues=issues,
            since=since,
            ref=ref,
            include_titles=include_title,
            token=resolve_token(token_env),
            root=Path.cwd(),
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(
        render_work_start(inputs, observed_at=utc_now_iso(), project_root=Path.cwd()),
        nl=False,
    )


@main.command("docs-probe")
@click.option("--repo", required=True, help="Repository in owner/name form (scope only; no fetch).")
@click.option("--root", required=True, help="Docs root to scan for supersession frontmatter.")
@click.option("--path", "paths", multiple=True, required=True, help="A doc the work relies on.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
def docs_probe_command(
    repo: str,
    root: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
) -> None:
    """Derive doc-superseded context (declared-frontmatter) for the relied-on docs."""

    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"docs-supersession-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_docs_supersession_probe(
        repo=repo, root=root, request_context=request_context, observed_at=observed_at
    )
    click.echo(_work_start_view(document), nl=False)


@main.command("gate-probe")
@click.option("--repo", required=True, help="GitHub repository in owner/name form.")
@click.option("--ref", required=True, help="Git ref (branch or SHA) to read check-runs for.")
@click.option("--path", "paths", multiple=True, required=True,
              help="A path the work is about to touch.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
@click.option("--token-env", default="GITHUB_TOKEN", show_default=True, help="Token env var name.")
def gate_probe_command(
    repo: str,
    ref: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
) -> None:
    """Derive missed-gate context from failing GitHub check-runs."""

    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-checks-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_github_checks_probe(
        repo=repo,
        ref=ref,
        token=resolve_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
    )
    click.echo(_work_start_view(document), nl=False)


@main.command("issue-probe")
@click.option("--repo", required=True, help="GitHub repository in owner/name form.")
@click.option("--issue", "issues", multiple=True, required=True, help="Linked issue (e.g. #42).")
@click.option("--since", required=True, help="ISO timestamp: only surface changes after this time.")
@click.option("--path", "paths", multiple=True, required=True,
              help="A path the work is about to touch.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
@click.option("--token-env", default="GITHUB_TOKEN", show_default=True, help="Token env var name.")
def issue_probe_command(
    repo: str,
    issues: tuple[str, ...],
    since: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
) -> None:
    """Derive criteria-changed context from GitHub Issue movement."""

    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-issues-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=list(issues),
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_github_issues_probe(
        repo=repo,
        issues=list(issues),
        since=since,
        token=resolve_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
    )
    click.echo(_work_start_view(document), nl=False)


@main.command("refresh")
@click.option("--github-repo", "repo", default=None, help="GitHub repository in owner/name form.")
@click.option("--path", "paths", multiple=True, required=True, help="Current task file path.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Refresh TeamCtx context.", show_default=True, help="Task text.")
@click.option("--token-env", default=None, help="Token env var name.")
@click.option(
    "--include-title/--omit-title",
    default=None,
    help="Whether PR titles are allowed in normalized metadata.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Where to write the Core Contract document.",
)
@click.option(
    "--config",
    "config_path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project config path.",
)
def refresh_command(
    repo: str | None,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str | None,
    include_title: bool | None,
    output_path: Path | None,
    config_path: Path,
) -> None:
    """Refresh local TeamCtx context from configured source metadata."""

    config = _maybe_load_project_config_or_raise(config_path)
    refresh_options = _resolve_refresh_options(
        config=config,
        repo=repo,
        token_env=token_env,
        include_title=include_title,
        output_path=output_path,
    )
    document = _github_contract_document(
        repo=refresh_options.repo,
        paths=paths,
        branch=branch,
        task=task,
        token_env=refresh_options.token_env,
        include_title=refresh_options.include_title,
    )
    try:
        write_contract_document(refresh_options.output_path, document)
    except ContractDocumentError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Refreshed context at {refresh_options.output_path}")


@main.command("context")
@click.option(
    "--contract",
    "contract_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Core Contract document path.",
)
@click.option(
    "--config",
    "config_path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project config path for default local context lookup.",
)
def context_command(contract_path: Path | None, config_path: Path) -> None:
    """Render working context from a Core Contract document."""

    if contract_path is None:
        contract_path = _default_contract_path_or_raise(config_path)
    document = _load_contract_or_raise(contract_path)
    click.echo(render_contract_context(document), nl=False)


@main.command("why")
@click.argument("card_id")
@click.option(
    "--contract",
    "contract_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Core Contract document path.",
)
@click.option(
    "--config",
    "config_path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project config path for default local context lookup.",
)
def why_command(card_id: str, contract_path: Path | None, config_path: Path) -> None:
    """Show why a context card appears."""

    if contract_path is None:
        contract_path = _default_contract_path_or_raise(config_path)
    document = _load_contract_or_raise(contract_path)
    try:
        click.echo(render_contract_why(document, card_id), nl=False)
    except KeyError as exc:
        raise click.ClickException(f"Unknown card id: {card_id}") from exc


@main.command("open-source")
@click.argument("ref_id")
@click.option(
    "--contract",
    "contract_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Core Contract document path.",
)
@click.option(
    "--config",
    "config_path",
    default=DEFAULT_CONFIG_PATH,
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project config path for default local context lookup.",
)
def open_source_command(ref_id: str, contract_path: Path | None, config_path: Path) -> None:
    """Open a source body when policy allows it."""

    if contract_path is None:
        contract_path = _default_contract_path_or_raise(config_path)
    document = _load_contract_or_raise(contract_path)
    try:
        click.echo(render_contract_open_source(document, ref_id), nl=False)
    except KeyError as exc:
        raise click.ClickException(f"Unknown source or card id: {ref_id}") from exc


@main.command("eval-export")
@click.option(
    "--scenarios-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of eval scenario JSON files (contracts model).",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write the A/B prompt pack.",
)
def eval_export_command(scenarios_dir: Path, output_dir: Path) -> None:
    """Export an A/B prompt pack: the context arm is built by the real engine (broker_answer)."""

    try:
        exports = export_eval_pack(scenarios_dir, output_dir)
    except (EvalScenarioError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Exported {len(exports)} eval scenarios to {output_dir}")


_HOOK_MATCHER = "Edit|Write|MultiEdit"
_HOOK_ENTRY = {"matcher": _HOOK_MATCHER, "hooks": [{"type": "command", "command": "teamctx-hook"}]}
_CLAUDE_MD_SNIPPET = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open PRs touching your files, failing checks, changed specs, and "
    "superseded docs. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)


@main.command("install-hook")
@click.option(
    "--print",
    "print_only",
    is_flag=True,
    help="Show the resulting settings and snippet; write nothing.",
)
@click.option(
    "--settings",
    "settings_path",
    default=Path(".claude/settings.json"),
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project-local Claude Code settings file.",
)
def install_hook_command(print_only: bool, settings_path: Path) -> None:
    """Opt in to the teamctx reflex: add the PreToolUse hook and print the portable snippet."""

    settings = _load_settings(settings_path)
    if not _has_hook_entry(settings):
        hooks = settings.get("hooks")
        if "hooks" in settings and not isinstance(hooks, dict):
            raise click.ClickException(
                f"{settings_path}: its 'hooks' value isn't a JSON object. "
                "Fix or remove that key and re-run."
            )
        pre = (hooks or {}).get("PreToolUse")
        if pre is not None and not isinstance(pre, list):
            raise click.ClickException(
                f"{settings_path}: 'hooks.PreToolUse' isn't a list. Fix or remove it and re-run."
            )
        settings.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
            copy.deepcopy(_HOOK_ENTRY)
        )

    if print_only:
        click.echo(json.dumps(settings, indent=2))
        click.echo("\nAdd this to your CLAUDE.md:\n")
        click.echo(_CLAUDE_MD_SNIPPET)
        return

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    click.echo(f"Installed the teamctx reflex hook in {settings_path}.")
    click.echo("\nAdd this to your CLAUDE.md:\n")
    click.echo(_CLAUDE_MD_SNIPPET)


def _load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"Could not read {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path} is not a JSON object.")
    return loaded


def _has_hook_entry(settings: dict[str, Any]) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    pre = hooks.get("PreToolUse")
    if not isinstance(pre, list):
        return False
    for entry in pre:
        if not isinstance(entry, dict):
            continue
        if entry.get("matcher") == _HOOK_MATCHER and any(
            isinstance(c, dict) and c.get("command") == "teamctx-hook"
            for c in entry.get("hooks", [])
        ):
            return True
    return False


class RefreshOptions:
    def __init__(
        self,
        *,
        repo: str,
        token_env: str,
        include_title: bool,
        output_path: Path,
    ) -> None:
        self.repo = repo
        self.token_env = token_env
        self.include_title = include_title
        self.output_path = output_path


def _resolve_refresh_options(
    *,
    config: ProjectConfig | None,
    repo: str | None,
    token_env: str | None,
    include_title: bool | None,
    output_path: Path | None,
) -> RefreshOptions:
    github_config = config.github if config is not None else None
    resolved_repo = repo or (github_config.repo if github_config is not None else None)
    if resolved_repo is None:
        raise click.ClickException("Provide --github-repo or configure github.repo.")

    resolved_token_env = token_env or (
        github_config.token_env if github_config is not None else "GITHUB_TOKEN"
    )
    resolved_include_title = (
        include_title
        if include_title is not None
        else bool(github_config and github_config.include_title)
    )
    resolved_output_path = output_path or Path(
        config.default_output if config is not None else ".teamctx/context.json"
    )
    return RefreshOptions(
        repo=resolved_repo,
        token_env=resolved_token_env,
        include_title=resolved_include_title,
        output_path=resolved_output_path,
    )


def _maybe_load_project_config_or_raise(path: Path) -> ProjectConfig | None:
    try:
        return maybe_load_project_config(path)
    except ProjectConfigError as exc:
        raise click.ClickException(str(exc)) from exc


def _default_contract_path_or_raise(config_path: Path) -> Path:
    config = _maybe_load_project_config_or_raise(config_path)
    contract_path = Path(config.default_output if config is not None else DEFAULT_OUTPUT_PATH)
    if not contract_path.exists():
        raise click.ClickException(
            f"No local TeamCtx context at {contract_path}. "
            "Run `teamctx refresh`, or provide --contract."
        )
    return contract_path


def _github_contract_document(
    *,
    repo: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
    include_title: bool,
) -> CoreContractDocument:
    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-pr-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    return run_github_pr_probe(
        repo=repo,
        token=resolve_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
        include_titles=include_title,
    )


def _work_start_view(document: CoreContractDocument) -> str:
    declarations = load_declared_authority(Path(".teamctx/authority.json"))
    answer = broker_answer(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
    return render_broker_answer(answer)


def _load_contract_or_raise(path: Path) -> CoreContractDocument:
    try:
        return load_contract_document(path)
    except ContractDocumentError as exc:
        raise click.ClickException(str(exc)) from exc


def _detect_docs_root(root: Path) -> str | None:
    return "docs" if (root / "docs").is_dir() else None


if __name__ == "__main__":
    main()
