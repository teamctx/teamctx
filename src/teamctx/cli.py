"""Command line entrypoint for teamctx."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import click

from teamctx.benchmark import export_benchmark_pack
from teamctx.claude_benchmark import AgentVariant, SourceAccessMode, run_claude_agent_suite
from teamctx.claude_quality import assess_claude_run_dir
from teamctx.connectors.github import run_github_pr_probe
from teamctx.context import agent_prompt_cards, context_cards
from teamctx.contract_documents import (
    ContractDocumentError,
    load_contract_document,
    write_contract_document,
)
from teamctx.contract_render import (
    render_contract_context,
    render_contract_open_source,
    render_contract_why,
    render_selection,
)
from teamctx.core.cards import find_card
from teamctx.core.contracts import CoreContractDocument, RequestContext
from teamctx.core.evaluate import evaluate
from teamctx.core.models import Fixture
from teamctx.core.select import CARD_KINDS, select_context
from teamctx.fixtures import FixtureError, load_fixture
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_OUTPUT_PATH,
    ProjectConfig,
    ProjectConfigError,
    build_project_config,
    maybe_load_project_config,
    write_project_config,
)
from teamctx.render import render_baseline_prompt, render_benchmark_prompt, render_context_cards
from teamctx.session import add_card_to_session, read_session
from teamctx.source_open import SourceOpenError, render_open_source
from teamctx.why import render_why


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="teamctx")
def main() -> None:
    """Deterministic ambient context for software teams."""


@main.command()
def status() -> None:
    """Show local teamctx status."""

    click.echo("teamctx is initialized. No sources are configured yet.")


@main.command("init")
@click.option("--github-repo", required=True, help="GitHub repository in owner/name form.")
@click.option("--token-env", default="GITHUB_TOKEN", show_default=True, help="Token env var name.")
@click.option(
    "--include-title/--omit-title",
    default=False,
    show_default=True,
    help="Whether PR titles are allowed in normalized metadata.",
)
@click.option(
    "--output",
    "output_path",
    default=Path(DEFAULT_OUTPUT_PATH),
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Where refresh writes the local context document.",
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
def init_command(
    github_repo: str,
    token_env: str,
    include_title: bool,
    output_path: Path,
    config_path: Path,
    force: bool,
) -> None:
    """Create a project-local TeamCtx config."""

    config = build_project_config(
        github_repo=github_repo,
        token_env=token_env,
        include_title=include_title,
        default_output=str(output_path),
    )
    try:
        write_project_config(config_path, config, overwrite=force)
    except ProjectConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Wrote project config at {config_path}")
    click.echo(f"Default context output: {output_path}")


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
@click.option("--github-repo", "repo", required=True, help="GitHub repository in owner/name form.")
@click.option(
    "--path", "paths", multiple=True, required=True, help="A path the work is about to touch."
)
@click.option("--branch", default=None, help="Current branch name.")
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
def work_start_command(
    repo: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
    include_title: bool,
) -> None:
    """Derive work-start context (collision cards + honest coverage) from GitHub PR metadata."""

    document = _github_contract_document(
        repo=repo,
        paths=paths,
        branch=branch,
        task=task,
        token_env=token_env,
        include_title=include_title,
    )
    selection = select_context(
        document.request_context, document.source_signals, document.source_statuses
    )
    verdicts = tuple(
        (
            kind.verdict_label,
            evaluate(
                kind.query(document.request_context), selection.claim_cards, selection.closure
            ),
        )
        for kind in CARD_KINDS
    )
    click.echo(render_selection(selection, verdicts), nl=False)


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
    "--fixture",
    "fixture_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
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
@click.option("--session", "session_id", default=None, help="Include cards used in a session.")
@click.option("--include-relevance", multiple=True, help="Include cards for a relevance tag.")
def context_command(
    fixture_path: Path | None,
    contract_path: Path | None,
    config_path: Path,
    session_id: str | None,
    include_relevance: tuple[str, ...],
) -> None:
    """Render working context."""

    _raise_if_both_context_inputs(fixture_path, contract_path)
    if contract_path is None and fixture_path is None:
        contract_path = _default_contract_path_or_raise(config_path)

    if contract_path is not None:
        document = _load_contract_or_raise(contract_path)
        click.echo(render_contract_context(document), nl=False)
        return

    if fixture_path is None:
        raise click.ClickException("Provide --fixture or --contract.")

    fixture = _load_or_raise(fixture_path)
    selected = read_session(session_id).card_ids if session_id else []
    cards = context_cards(
        fixture,
        selected_card_ids=selected,
        relevance_tags=include_relevance,
    )
    click.echo(render_context_cards(cards), nl=False)


@main.command("why")
@click.argument("card_id")
@click.option(
    "--fixture",
    "fixture_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
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
def why_command(
    card_id: str,
    fixture_path: Path | None,
    contract_path: Path | None,
    config_path: Path,
) -> None:
    """Show why a context card appears."""

    _raise_if_both_context_inputs(fixture_path, contract_path)
    if contract_path is None and fixture_path is None:
        contract_path = _default_contract_path_or_raise(config_path)

    if contract_path is not None:
        document = _load_contract_or_raise(contract_path)
        try:
            click.echo(render_contract_why(document, card_id), nl=False)
        except KeyError as exc:
            raise click.ClickException(f"Unknown card id: {card_id}") from exc
        return

    if fixture_path is None:
        raise click.ClickException("Provide --fixture or --contract.")

    fixture = _load_or_raise(fixture_path)
    try:
        click.echo(render_why(fixture, card_id), nl=False)
    except KeyError as exc:
        raise click.ClickException(f"Unknown card id: {card_id}") from exc


@main.command("open-source")
@click.argument("ref_id")
@click.option(
    "--fixture",
    "fixture_path",
    required=False,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
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
def open_source_command(
    ref_id: str,
    fixture_path: Path | None,
    contract_path: Path | None,
    config_path: Path,
) -> None:
    """Open a source body when policy allows it."""

    _raise_if_both_context_inputs(fixture_path, contract_path)
    if contract_path is None and fixture_path is None:
        contract_path = _default_contract_path_or_raise(config_path)

    if contract_path is not None:
        document = _load_contract_or_raise(contract_path)
        try:
            click.echo(render_contract_open_source(document, ref_id), nl=False)
        except KeyError as exc:
            raise click.ClickException(f"Unknown source or card id: {ref_id}") from exc
        return

    if fixture_path is None:
        raise click.ClickException("Provide --fixture or --contract.")

    fixture = _load_or_raise(fixture_path)
    try:
        click.echo(render_open_source(fixture, ref_id), nl=False)
    except SourceOpenError as exc:
        raise click.ClickException(str(exc)) from exc


@main.command("use")
@click.argument("card_id")
@click.option("--session", "session_id", required=True, help="Session id.")
@click.option(
    "--fixture",
    "fixture_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
def use_command(card_id: str, session_id: str, fixture_path: Path) -> None:
    """Use a prototype card in this session."""

    fixture = _load_or_raise(fixture_path)
    try:
        find_card(fixture, card_id)
    except KeyError as exc:
        raise click.ClickException(f"Unknown card id: {card_id}") from exc

    add_card_to_session(session_id, card_id)
    click.echo("Added context for this session.")


@main.command("benchmark-prompt")
@click.option("--scenario", default=None, help="Optional scenario id consistency check.")
@click.option(
    "--variant",
    type=click.Choice(["baseline", "context"]),
    required=True,
    help="Prompt variant.",
)
@click.option(
    "--fixture",
    "fixture_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
@click.option("--session", "session_id", default=None, help="Include cards used in a session.")
def benchmark_prompt_command(
    scenario: str | None,
    variant: str,
    fixture_path: Path,
    session_id: str | None,
) -> None:
    """Render a prototype benchmark prompt."""

    fixture = _load_or_raise(fixture_path)
    if scenario is not None and scenario not in _scenario_aliases(fixture):
        raise click.ClickException(
            f"Scenario {scenario!r} does not match fixture {fixture.fixture_id!r}"
        )
    if variant == "baseline":
        click.echo(render_baseline_prompt(fixture), nl=False)
        return

    selected = read_session(session_id).card_ids if session_id else []
    cards = agent_prompt_cards(fixture, selected_card_ids=selected)
    click.echo(render_benchmark_prompt(fixture, cards), nl=False)


@main.command("benchmark-export")
@click.option(
    "--fixtures-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of benchmark fixture JSON files.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write generated prompt files.",
)
def benchmark_export_command(fixtures_dir: Path, output_dir: Path) -> None:
    """Export baseline/context prompt files from benchmark fixtures."""

    try:
        exports = export_benchmark_pack(fixtures_dir, output_dir)
    except (FixtureError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Exported {len(exports)} benchmark scenarios to {output_dir}")


@main.command("claude-agent-benchmark")
@click.option(
    "--fixtures-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of benchmark fixture JSON files.",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory to write Claude agent run artifacts.",
)
@click.option("--scenario", "scenario_ids", multiple=True, help="Fixture id to run.")
@click.option("--model", "models", multiple=True, default=("sonnet",), help="Claude model alias.")
@click.option(
    "--variant",
    type=click.Choice(["baseline", "context", "both"]),
    default="both",
    show_default=True,
    help="Prompt variant to run.",
)
@click.option("--max-budget-usd", default=0.25, show_default=True, type=float, help="Per-run cap.")
@click.option(
    "--source-access",
    type=click.Choice(["full", "none", "status_only", "status_open"]),
    default="full",
    show_default=True,
    help="Whether benchmark source snapshots are available in the disposable workspace.",
)
def claude_agent_benchmark_command(
    fixtures_dir: Path,
    output_dir: Path,
    scenario_ids: tuple[str, ...],
    models: tuple[str, ...],
    variant: str,
    max_budget_usd: float,
    source_access: str,
) -> None:
    """Run Claude Code against disposable benchmark repositories."""

    variants: tuple[AgentVariant, ...] = (
        ("baseline", "context") if variant == "both" else (cast(AgentVariant, variant),)
    )

    runs = run_claude_agent_suite(
        fixtures_dir,
        output_dir,
        models=models,
        variants=variants,
        scenario_ids=scenario_ids,
        max_budget_usd=max_budget_usd,
        source_access=cast(SourceAccessMode, source_access),
    )
    assessments = assess_claude_run_dir(fixtures_dir, output_dir)
    total_cost = sum(run.metrics.total_cost_usd for run in runs)
    review_count = sum(1 for item in assessments if item.quality_level == "review")
    fail_count = sum(1 for item in assessments if item.quality_level == "fail")
    click.echo(
        f"Ran {len(runs)} Claude agent benchmark runs to {output_dir} "
        f"(reported cost: ${total_cost:.6f}; review: {review_count}; fail: {fail_count})"
    )


@main.command("claude-agent-assess")
@click.option(
    "--fixtures-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory of benchmark fixture JSON files.",
)
@click.option(
    "--run-dir",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing Claude agent run artifacts.",
)
def claude_agent_assess_command(fixtures_dir: Path, run_dir: Path) -> None:
    """Assess saved Claude Code benchmark artifacts."""

    assessments = assess_claude_run_dir(fixtures_dir, run_dir)
    review_count = sum(1 for item in assessments if item.quality_level == "review")
    fail_count = sum(1 for item in assessments if item.quality_level == "fail")
    click.echo(
        f"Assessed {len(assessments)} Claude agent benchmark runs in {run_dir} "
        f"(review: {review_count}; fail: {fail_count})"
    )


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
            "Run `teamctx refresh`, or provide --fixture or --contract."
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
    observed_at = _utc_now_string()
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
        token=os.environ.get(token_env),
        request_context=request_context,
        observed_at=observed_at,
        include_titles=include_title,
    )


def _load_contract_or_raise(path: Path) -> CoreContractDocument:
    try:
        return load_contract_document(path)
    except ContractDocumentError as exc:
        raise click.ClickException(str(exc)) from exc


def _raise_if_both_context_inputs(fixture_path: Path | None, contract_path: Path | None) -> None:
    if fixture_path is not None and contract_path is not None:
        raise click.ClickException("Provide only one of --fixture or --contract.")


def _scenario_aliases(fixture: Fixture) -> set[str]:
    aliases = {fixture.fixture_id}
    aliases.add(re.sub(r"-v\d+$", "", fixture.fixture_id))
    return aliases


def _load_or_raise(path: Path) -> Fixture:
    try:
        return load_fixture(path)
    except FixtureError as exc:
        raise click.ClickException(str(exc)) from exc


def _utc_now_string() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
