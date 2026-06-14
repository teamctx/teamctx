"""Command line entrypoint for teamctx."""

from __future__ import annotations

import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="teamctx")
def main() -> None:
    """Deterministic ambient context for software teams."""


@main.command()
def status() -> None:
    """Show local teamctx status."""

    click.echo("teamctx is initialized. No sources are configured yet.")

