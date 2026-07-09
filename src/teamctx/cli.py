"""Command line entrypoint for teamctx."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

import click

from teamctx.clock import utc_now_iso
from teamctx.config_failure import format_config_failure
from teamctx.connectors.declared_authority import DeclaredAuthorityError
from teamctx.connectors.docs import run_docs_supersession_probe
from teamctx.connectors.github import run_github_pr_probe
from teamctx.connectors.github_checks import run_github_checks_probe
from teamctx.connectors.github_issues import run_github_issues_probe
from teamctx.contract_render import (
    render_broker_answer,
    render_open_source,
    render_why,
)
from teamctx.core.broker import BrokerAnswer, broker_answer_from_documents
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.eval.pack import export_eval_pack
from teamctx.eval.scenario import EvalScenarioError
from teamctx.finding_query import (
    AmbiguousFinding,
    FindingSelector,
    FindingSelectorError,
    NoFindingMatch,
    match_finding,
    parse_selector,
)
from teamctx.git_context import (
    detect_repo,
    parse_github_repo,
    repo_relative_path,
    resolve_project_root,
)
from teamctx.onboard import CLAUDE_MD_SNIPPET, _atomic_write, run_onboard
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    ProjectConfigError,
    build_work_start_project_config,
    write_project_config,
)
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs
from teamctx.team_semantics import load_team_authority
from teamctx.tokens import resolve_github_token
from teamctx.work_start import render_work_start, work_start_answer


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="teamctx")
def main() -> None:
    """Deterministic ambient context for software teams."""


@main.group("dev")
def dev() -> None:
    """Diagnostic and developer commands (per-connector probes, eval export)."""


@main.command()
@click.option(
    "--token-env", default="GITHUB_TOKEN", show_default=True,
    help="Name of the env var holding the GitHub token.",
)
def status(token_env: str) -> None:
    """Report teamctx setup in this repo, read-only: config, hook, snippet, credential, and
    a live reachability check. Writes nothing; never a verdict."""

    from teamctx.onboard import run_status

    root = resolve_project_root()
    report = run_status(root, token_env=token_env)
    click.echo(f"teamctx status for {root}:")
    for step in report.steps:
        click.echo(f"  [{_STEP_MARK[step.status]}] {step.name}: {step.detail}")
    click.echo(f"\nNext: {report.next_step}")


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
    help="Folder of design docs to watch for supersession (off unless you set it).",
)
@click.option("--force", is_flag=True, help="Overwrite an existing project config.")
def init_command(repo: str | None, docs_root: str | None, force: bool) -> None:
    """Scaffold the project-local teamctx config for work-start."""

    root = resolve_project_root()
    if repo is not None and parse_github_repo(repo) is None:
        raise click.ClickException(
            f"{repo!r} is not a GitHub repo (owner/name). teamctx only checks GitHub today."
        )
    resolved_repo = parse_github_repo(repo) if repo is not None else detect_repo(root)
    if resolved_repo is None:
        raise click.ClickException(
            "Could not determine the repository: this is not a git repo with a recognizable "
            "'origin' remote. Pass --repo owner/name."
        )
    resolved_docs_root = docs_root  # explicit only; no docs auto-enable (it would over-claim)

    config = build_work_start_project_config(repo=resolved_repo, docs_root=resolved_docs_root)
    config_path = root / DEFAULT_CONFIG_PATH
    try:
        write_project_config(config_path, config, overwrite=force, exclude_defaults=True)
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
    click.echo(
        "Next: run `teamctx work-start --path <file you are about to edit>` before you start "
        "editing."
    )


@dev.command("github-pr-probe")
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

    normalized_repo = parse_github_repo(repo)
    if normalized_repo is None:
        raise click.ClickException(f"{repo!r} is not a GitHub repo (owner/name).")
    repo = normalized_repo
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
    help="Diagnostic override for the GitHub repo owner/name. Normal work-start reads the "
         "git 'origin' remote or committed .teamctx/config.json.",
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
@click.option(
    "--docs-root",
    default=None,
    help="Diagnostic override for the docs root. Normal work-start reads committed "
         ".teamctx/config.json.",
)
@click.option("--ref", default=None, help="Gate ref to read check-runs for (defaults to --branch).")
@click.option(
    "--allow-dirty",
    is_flag=True,
    help="Diagnostic: use working-tree .teamctx config and authority before they are committed.",
)
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
    allow_dirty: bool,
) -> None:
    """Derive unified work-start context: run every connector the inputs allow (collisions +
    gates + linked-issue criteria + relied-on docs), compose, and report cards + honest
    coverage + one verdict per check. Sources not reachable from the inputs stay Unknown."""

    project_root = resolve_project_root()
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
            token=resolve_github_token(token_env),
            root=project_root,
            allow_dirty=allow_dirty,
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        raise click.ClickException(format_config_failure(exc)) from exc
    try:
        output = render_work_start(inputs, observed_at=utc_now_iso(), project_root=project_root)
    except DeclaredAuthorityError as exc:
        raise click.ClickException(format_config_failure(exc)) from exc
    click.echo(output, nl=False)


_SELECTOR_KIND_TO_VERDICT_LABEL: dict[str, str] = {
    "pr": "Conflict check",
    "issue": "Criteria check",
    "doc": "Docs check",
    "gate": "Gate check",
}


def _raise_no_finding_match(sel: FindingSelector, answer: BrokerAnswer) -> NoReturn:
    """Distinguish 'could not check' from 'may have cleared' for honest no-match handling.

    When teamctx never reached a relevant source (its verdict is Unknown), it cannot say whether
    a finding exists; telling the user 'nothing found' would be a false all-clear. Only when every
    relevant check ran can a no-match honestly mean 'it may have cleared'. `path:` is special: a
    path can appear in a collision (Conflict check) or a failing gate (Gate check), so both are
    relevant.
    """

    verdicts = {label: val for label, val in answer.verdicts}
    if sel.kind == "path":
        relevant = ["Conflict check", "Gate check"]
    else:
        label = _SELECTOR_KIND_TO_VERDICT_LABEL.get(sel.kind)
        relevant = [label] if label else []

    unknown = [lbl for lbl in relevant if lbl in verdicts and verdicts[lbl].value == "unknown"]
    if unknown:
        joined = " or ".join(unknown)
        reason = verdicts[unknown[0]].reason
        raise click.ClickException(
            f"teamctx could not check {joined} ({reason}), so it cannot confirm whether a finding"
            f" for `{sel.kind}:{sel.value}` exists. Run `teamctx work-start --path ...` to see"
            f" coverage."
        )
    raise click.ClickException(
        f"No current finding matches `{sel.kind}:{sel.value}`."
        f" It may have cleared since you last ran work-start."
        f" Run `teamctx work-start --path ...` to check current state."
    )


def _resolve_work_start(
    *,
    repo: str | None,
    paths: tuple[str, ...],
    branch: str | None,
    token_env: str,
    include_title: bool,
    issues: tuple[str, ...],
    since: str | None,
    docs_root: str | None,
    ref: str | None,
) -> BrokerAnswer:
    """Shared resolution + broker run for why/open-source commands."""

    project_root = resolve_project_root()
    try:
        inputs = resolve_work_start_inputs(
            paths=paths,
            repo=repo,
            branch=branch,
            docs_root=docs_root,
            issues=issues,
            since=since,
            ref=ref,
            include_titles=include_title,
            token=resolve_github_token(token_env),
            root=project_root,
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        raise click.ClickException(format_config_failure(exc)) from exc
    try:
        return work_start_answer(inputs, observed_at=utc_now_iso(), project_root=project_root)
    except DeclaredAuthorityError as exc:
        raise click.ClickException(format_config_failure(exc)) from exc


def _add_work_start_options(func: Any) -> Any:
    """Apply the shared work-start resolution options to a command (why/open-source)."""

    opts = [
        click.option(
            "--github-repo", "repo", default=None,
            help="Diagnostic override for the GitHub repo owner/name. Normal use reads git "
                 "'origin' or committed .teamctx/config.json.",
        ),
        click.option(
            "--path", "paths", multiple=True, required=True,
            help="A path the work is about to touch.",
        ),
        click.option("--branch", default=None, help="Current branch name."),
        click.option(
            "--token-env", default="GITHUB_TOKEN", show_default=True,
            help="Name of the env var holding the GitHub token.",
        ),
        click.option(
            "--include-title/--omit-title", "include_title", default=False,
            help="Allow PR titles in normalized metadata.",
        ),
        click.option(
            "--issue", "issues", multiple=True, help="A linked issue to check (e.g. #42).",
        ),
        click.option("--since", default=None, help="ISO timestamp for issue change window."),
        click.option(
            "--docs-root",
            default=None,
            help="Diagnostic override for the docs root. Normal use reads committed "
                 ".teamctx/config.json.",
        ),
        click.option("--ref", default=None, help="Gate ref to read check-runs for."),
    ]
    for opt in reversed(opts):
        func = opt(func)
    return func


@main.command("why")
@click.argument("selector")
@_add_work_start_options
def why_command(
    selector: str,
    repo: str | None,
    paths: tuple[str, ...],
    branch: str | None,
    token_env: str,
    include_title: bool,
    issues: tuple[str, ...],
    since: str | None,
    docs_root: str | None,
    ref: str | None,
) -> None:
    """Show full evidence for one finding (e.g. `teamctx why pr:7`).

    SELECTOR is a typed handle: pr:N, issue:REF, path:X, doc:PATH, or gate:NAME.
    Runs the live broker and explains why teamctx flagged that specific finding:
    what it found, why it matters, and what source it came from.
    """

    try:
        sel = parse_selector(selector)
    except FindingSelectorError as exc:
        raise click.ClickException(str(exc)) from exc

    answer = _resolve_work_start(
        repo=repo, paths=paths, branch=branch, token_env=token_env,
        include_title=include_title, issues=issues, since=since, docs_root=docs_root, ref=ref,
    )

    try:
        card = match_finding(answer.selection.cards, sel)
    except AmbiguousFinding as exc:
        raise click.ClickException(str(exc)) from exc
    except NoFindingMatch:
        _raise_no_finding_match(sel, answer)

    click.echo(render_why(card), nl=False)


@main.command("open-source")
@click.argument("selector")
@_add_work_start_options
def open_source_command(
    selector: str,
    repo: str | None,
    paths: tuple[str, ...],
    branch: str | None,
    token_env: str,
    include_title: bool,
    issues: tuple[str, ...],
    since: str | None,
    docs_root: str | None,
    ref: str | None,
) -> None:
    """Show how to open the source for one finding (e.g. `teamctx open-source pr:7`).

    SELECTOR is a typed handle: pr:N, issue:REF, path:X, doc:PATH, or gate:NAME.
    Runs the live broker and prints the command or URL to open the underlying source,
    plus an honest note about body availability.
    """

    try:
        sel = parse_selector(selector)
    except FindingSelectorError as exc:
        raise click.ClickException(str(exc)) from exc

    answer = _resolve_work_start(
        repo=repo, paths=paths, branch=branch, token_env=token_env,
        include_title=include_title, issues=issues, since=since, docs_root=docs_root, ref=ref,
    )

    try:
        card = match_finding(answer.selection.cards, sel)
    except AmbiguousFinding as exc:
        raise click.ClickException(str(exc)) from exc
    except NoFindingMatch:
        _raise_no_finding_match(sel, answer)

    click.echo(render_open_source(card, answer.open_targets), nl=False)


@dev.command("docs-probe")
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

    normalized_repo = parse_github_repo(repo)
    if normalized_repo is None:
        raise click.ClickException(f"{repo!r} is not a GitHub repo (owner/name).")
    repo = normalized_repo
    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"docs-supersession-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=_normalized_paths(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_docs_supersession_probe(
        repo=repo, root=root, request_context=request_context, observed_at=observed_at,
        base_dir=resolve_project_root(),
    )
    click.echo(_work_start_view(document), nl=False)


@dev.command("gate-probe")
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

    normalized_repo = parse_github_repo(repo)
    if normalized_repo is None:
        raise click.ClickException(f"{repo!r} is not a GitHub repo (owner/name).")
    repo = normalized_repo
    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-checks-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=_normalized_paths(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_github_checks_probe(
        repo=repo,
        ref=ref,
        token=resolve_github_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
    )
    click.echo(_work_start_view(document), nl=False)


@dev.command("issue-probe")
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

    normalized_repo = parse_github_repo(repo)
    if normalized_repo is None:
        raise click.ClickException(f"{repo!r} is not a GitHub repo (owner/name).")
    repo = normalized_repo
    observed_at = utc_now_iso()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-issues-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=_normalized_paths(paths),
        linked_issues=list(issues),
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_github_issues_probe(
        repo=repo,
        issues=list(issues),
        since=since,
        token=resolve_github_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
    )
    click.echo(_work_start_view(document), nl=False)


@dev.command("eval-export")
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


@dataclass(frozen=True)
class _JsonMember:
    key: str
    key_start: int
    value_start: int
    value_end: int


@dataclass(frozen=True)
class _JsonElement:
    value_start: int
    value_end: int


_JSON_DECODER = json.JSONDecoder()
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
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help=(
        "Project-local Claude Code settings file "
        "(defaults to <repo-root>/.claude/settings.local.json)."
    ),
)
def install_hook_command(print_only: bool, settings_path: Path | None) -> None:
    """Opt in to the teamctx reflex: add the PreToolUse hook and print the portable snippet."""

    settings_path = settings_path or resolve_project_root() / ".claude" / "settings.local.json"
    if print_only:
        settings, _ = _settings_with_hook(settings_path)
        click.echo(json.dumps(settings, indent=2))
        click.echo("\nAdd this to your CLAUDE.md:\n")
        click.echo(CLAUDE_MD_SNIPPET)
        return

    wrote = install_hook_into_settings(settings_path)
    if wrote:
        click.echo(f"Installed the teamctx reflex hook in {settings_path}.")
    else:
        click.echo(f"The teamctx reflex hook is already present in {settings_path}.")
    click.echo("\nAdd this to your CLAUDE.md:\n")
    click.echo(CLAUDE_MD_SNIPPET)


def _settings_with_hook(settings_path: Path) -> tuple[dict[str, Any], bool]:
    """Load ``settings_path`` and return (settings-with-the-hook, added), without writing. Raises
    click.ClickException on a malformed settings shape. ``added`` is False when already present."""

    settings = _load_settings(settings_path)
    if _has_hook_entry(settings):
        return settings, False
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
    return settings, True


def install_hook_into_settings(settings_path: Path) -> bool:
    """Add the teamctx PreToolUse hook to ``settings_path`` if absent, atomically. Returns True if
    it wrote a change, False if the hook was already present. Raises click.ClickException on a
    malformed settings file (the caller decides whether that aborts). Reused by ``onboard``."""

    settings, added = _settings_with_hook(settings_path)
    if added:
        _atomic_write(settings_path, json.dumps(settings, indent=2) + "\n")
    return added


def remove_hook_from_settings(settings_path: Path) -> bool:
    """Remove canonical teamctx hook entries from ``settings_path`` without rewriting unrelated
    bytes. Returns True when it wrote a migration."""

    if not settings_path.exists():
        return False
    try:
        settings = _load_settings(settings_path)
    except click.ClickException:
        return False
    if not _has_exact_hook_entry(settings):
        return False
    text = settings_path.read_text(encoding="utf-8")
    migrated, removed = _settings_text_without_exact_hook_entries(text)
    if not removed:
        return False
    _atomic_write(settings_path, migrated)
    return True


def _has_exact_hook_entry(settings: dict[str, Any]) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    pre = hooks.get("PreToolUse")
    if not isinstance(pre, list):
        return False
    return any(entry == _HOOK_ENTRY for entry in pre)


def _settings_text_without_exact_hook_entries(text: str) -> tuple[str, bool]:
    changed = False
    while True:
        root = _root_object_members(text)
        if root is None:
            return text, changed
        hooks = _find_member(root, "hooks")
        if hooks is None:
            return _canonical_empty_object_if_needed(text), changed
        hook_members = _object_members_at(text, hooks.value_start)
        if hook_members is None:
            return text, changed
        pre = _find_member(hook_members, "PreToolUse")
        if pre is None:
            settings = json.loads(text)
            current_hooks = settings.get("hooks")
            if isinstance(current_hooks, dict) and current_hooks == {}:
                text = _remove_object_member(text, root, "hooks")
                changed = True
                continue
            return _canonical_empty_object_if_needed(text), changed
        elements = _array_elements_at(text, pre.value_start)
        if elements is None:
            return text, changed

        removed_entry = False
        for index, element in enumerate(elements):
            entry = json.loads(text[element.value_start:element.value_end])
            if entry == _HOOK_ENTRY:
                text = _remove_array_element(text, elements, index)
                changed = True
                removed_entry = True
                break
        if removed_entry:
            continue

        settings = json.loads(text)
        current_hooks = settings.get("hooks")
        current_pre = current_hooks.get("PreToolUse") if isinstance(current_hooks, dict) else None
        if current_pre == []:
            text = _remove_object_member(text, hook_members, "PreToolUse")
            changed = True
            continue
        if isinstance(current_hooks, dict) and current_hooks == {}:
            text = _remove_object_member(text, root, "hooks")
            changed = True
            continue
        return _canonical_empty_object_if_needed(text), changed


def _canonical_empty_object_if_needed(text: str) -> str:
    if json.loads(text) == {}:
        return "{}\n"
    return text


def _skip_ws(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


def _root_object_members(text: str) -> list[_JsonMember] | None:
    root_start = _skip_ws(text, 0)
    return _object_members_at(text, root_start)


def _object_members_at(text: str, object_start: int) -> list[_JsonMember] | None:
    if object_start >= len(text) or text[object_start] != "{":
        return None
    index = _skip_ws(text, object_start + 1)
    members: list[_JsonMember] = []
    if index < len(text) and text[index] == "}":
        return members
    while True:
        key_start = index
        key, key_end = _JSON_DECODER.raw_decode(text, key_start)
        if not isinstance(key, str):
            return None
        colon = _skip_ws(text, key_end)
        if colon >= len(text) or text[colon] != ":":
            return None
        value_start = _skip_ws(text, colon + 1)
        _, value_end = _JSON_DECODER.raw_decode(text, value_start)
        members.append(_JsonMember(key, key_start, value_start, value_end))
        index = _skip_ws(text, value_end)
        if index >= len(text):
            return None
        if text[index] == "}":
            return members
        if text[index] != ",":
            return None
        index = _skip_ws(text, index + 1)


def _array_elements_at(text: str, array_start: int) -> list[_JsonElement] | None:
    if array_start >= len(text) or text[array_start] != "[":
        return None
    index = _skip_ws(text, array_start + 1)
    elements: list[_JsonElement] = []
    if index < len(text) and text[index] == "]":
        return elements
    while True:
        value_start = index
        _, value_end = _JSON_DECODER.raw_decode(text, value_start)
        elements.append(_JsonElement(value_start, value_end))
        index = _skip_ws(text, value_end)
        if index >= len(text):
            return None
        if text[index] == "]":
            return elements
        if text[index] != ",":
            return None
        index = _skip_ws(text, index + 1)


def _find_member(members: list[_JsonMember], key: str) -> _JsonMember | None:
    for member in members:
        if member.key == key:
            return member
    return None


def _remove_array_element(text: str, elements: list[_JsonElement], index: int) -> str:
    element = elements[index]
    if len(elements) == 1:
        return text[:element.value_start] + text[element.value_end:]
    if index < len(elements) - 1:
        return text[:element.value_start] + text[elements[index + 1].value_start:]
    previous_end = elements[index - 1].value_end
    comma = _skip_ws(text, previous_end)
    return text[:comma] + text[element.value_end:]


def _remove_object_member(text: str, members: list[_JsonMember], key: str) -> str:
    index = next(i for i, member in enumerate(members) if member.key == key)
    member = members[index]
    if len(members) == 1:
        return text[:member.key_start] + text[member.value_end:]
    if index < len(members) - 1:
        return text[:member.key_start] + text[members[index + 1].key_start:]
    previous_end = members[index - 1].value_end
    comma = _skip_ws(text, previous_end)
    return text[:comma] + text[member.value_end:]


_STEP_MARK = {
    "wrote": "wrote", "already": "already set", "skipped": "skipped",
    "failed": "FAILED", "noted": "checked", "ok": "ok",
}


@main.command("onboard")
@click.option(
    "--repo", "repo", default=None, help="GitHub repo owner/name. Overrides git 'origin' detection."
)
@click.option("--force", is_flag=True, help="Overwrite an existing .teamctx/config.json.")
@click.option("--dry-run", "dry_run", is_flag=True, help="Preview every step; write nothing.")
@click.option(
    "--yes", is_flag=True, help="Assume non-interactive (accepted; onboard does not prompt today)."
)
def onboard_command(repo: str | None, force: bool, dry_run: bool, yes: bool) -> None:
    """Set up teamctx in this repo: config, reflex hook, CLAUDE.md snippet, and an honest
    credential and reachability report. Idempotent; re-run any time."""

    result = run_onboard(
        resolve_project_root(), repo_override=repo, force=force, dry_run=dry_run
    )
    click.echo("teamctx onboard:" + (" (dry run, nothing written)" if dry_run else ""))
    for step in result.steps:
        click.echo(f"  [{_STEP_MARK[step.status]}] {step.name}: {step.detail}")
    click.echo(f"\nNext: {result.next_step}")
    if not result.ok:
        raise SystemExit(1)


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


def _normalized_paths(paths: tuple[str, ...]) -> list[str]:
    """Normalize a dev probe's raw --path values to repo-relative POSIX (same as the work-start
    resolver), so a caller path matches the broker's repo-relative signal paths."""

    root = resolve_project_root()
    return [repo_relative_path(root, path) for path in paths]


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
        paths=_normalized_paths(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    return run_github_pr_probe(
        repo=repo,
        token=resolve_github_token(token_env),
        request_context=request_context,
        observed_at=observed_at,
        include_titles=include_title,
    )


def _work_start_view(document: CoreContractDocument) -> str:
    declarations = load_team_authority(resolve_project_root()).declarations
    answer = broker_answer_from_documents(document.request_context, [document], declarations)
    return render_broker_answer(answer)


if __name__ == "__main__":
    main()
