"""Command line entrypoint for teamctx."""

from __future__ import annotations

import re
from pathlib import Path

import click

from teamctx.benchmark import export_benchmark_pack
from teamctx.context import context_cards
from teamctx.core.cards import find_card
from teamctx.core.fixtures import FixtureError, load_fixture
from teamctx.core.models import Fixture
from teamctx.render import render_baseline_prompt, render_benchmark_prompt, render_context_cards
from teamctx.session import add_card_to_session, read_session
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
    cards = context_cards(fixture, selected_card_ids=selected)
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
