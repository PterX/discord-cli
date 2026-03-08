"""discord-cli — CLI entry point."""

import click

from .data import data_group
from .discord_cmds import discord_group
from .query import query_group


@click.group()
@click.version_option(package_name="discord-cli")
def cli():
    """discord — CLI for fetching Discord chat history and searching messages."""
    pass


# Register sub-groups
cli.add_command(discord_group, "dc")

# Register top-level query commands
for name, cmd in query_group.commands.items():
    cli.add_command(cmd, name)

# Register top-level data commands
for name, cmd in data_group.commands.items():
    cli.add_command(cmd, name)
