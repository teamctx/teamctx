"""Command line entrypoint for teamctx."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

import click

from teamctx.benchmark import export_benchmark_pack
from teamctx.claude_benchmark import AgentVariant, SourceAccessMode, run_claude_agent_suite
from teamctx.claude_quality import assess_claude_run_dir
from teamctx.context import agent_prompt_cards, context_cards
from teamctx.core.cards import find_card
from teamctx.core.fixtures import FixtureError, load_fixture
from teamctx.core.models import Fixture
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


@main.command("context")
@click.option(
    "--fixture",
    "fixture_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
@click.option("--session", "session_id", default=None, help="Include cards used in a session.")
@click.option("--include-relevance", multiple=True, help="Include cards for a relevance tag.")
def context_command(
    fixture_path: Path,
    session_id: str | None,
    include_relevance: tuple[str, ...],
) -> None:
    """Render prototype working context from a fixture."""

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
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
def why_command(card_id: str, fixture_path: Path) -> None:
    """Show why a prototype card appears."""

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
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Prototype fixture path.",
)
def open_source_command(ref_id: str, fixture_path: Path) -> None:
    """Open a source body when policy allows it."""

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
    type=click.Choice(["full", "none", "status_only"]),
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


def _scenario_aliases(fixture: Fixture) -> set[str]:
    aliases = {fixture.fixture_id}
    aliases.add(re.sub(r"-v\d+$", "", fixture.fixture_id))
    return aliases


def _load_or_raise(path: Path) -> Fixture:
    try:
        return load_fixture(path)
    except FixtureError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    main()
