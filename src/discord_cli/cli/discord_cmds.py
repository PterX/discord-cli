"""Discord subcommands — guilds, channels, history, sync, sync-all."""

import asyncio

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..client import datetime_to_snowflake, fetch_messages, get_client, get_guild_info, list_channels, list_guilds
from ..db import MessageDB

console = Console()


@click.group("dc")
def discord_group():
    """Discord operations — list servers, fetch history, sync."""
    pass


@discord_group.command("guilds")
def dc_guilds():
    """List joined Discord servers."""

    async def _run():
        async with get_client() as client:
            return await list_guilds(client)

    guilds = asyncio.run(_run())
    table = Table(title="Discord Servers")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Owner", justify="center")

    for g in guilds:
        table.add_row(g["id"], g["name"], "✓" if g["owner"] else "")

    console.print(table)
    console.print(f"\nTotal: {len(guilds)} servers")


@discord_group.command("channels")
@click.argument("guild")
def dc_channels(guild: str):
    """List text channels in a GUILD (server ID or name)."""

    async def _run():
        async with get_client() as client:
            # If guild looks like a name, search for it
            guild_id = guild
            if not guild.isdigit():
                guilds = await list_guilds(client)
                match = next(
                    (g for g in guilds if guild.lower() in g["name"].lower()),
                    None,
                )
                if not match:
                    console.print(f"[red]Guild '{guild}' not found.[/red]")
                    return []
                guild_id = match["id"]
                console.print(f"[dim]Resolved to: {match['name']} ({guild_id})[/dim]")

            return await list_channels(client, guild_id)

    channels = asyncio.run(_run())
    if not channels:
        return

    table = Table(title="Text Channels")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Topic", max_width=50)

    for ch in channels:
        table.add_row(ch["id"], f"#{ch['name']}", (ch.get("topic") or "")[:50])

    console.print(table)
    console.print(f"\nTotal: {len(channels)} text channels")


@discord_group.command("history")
@click.argument("channel")
@click.option("-n", "--limit", default=1000, help="Max messages to fetch")
@click.option("--guild-name", help="Guild name to store with messages")
@click.option("--channel-name", help="Channel name to store with messages")
def dc_history(channel: str, limit: int, guild_name: str | None, channel_name: str | None):
    """Fetch historical messages from CHANNEL (channel ID)."""

    async def _run():
        db = MessageDB()
        try:
            async with get_client() as client:
                # Try to get channel info for naming
                ch_name = channel_name
                g_name = guild_name

                if not ch_name:
                    try:
                        ch_info = await client.get(f"/channels/{channel}")
                        if ch_info.status_code == 200:
                            ch_data = ch_info.json()
                            ch_name = ch_data.get("name", channel)
                            if not g_name and ch_data.get("guild_id"):
                                g_info = await get_guild_info(client, ch_data["guild_id"])
                                if g_info:
                                    g_name = g_info["name"]
                    except Exception:
                        pass

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"Fetching messages from {ch_name or channel}...", total=None)

                    messages = await fetch_messages(client, channel, limit=limit)
                    progress.update(task, description=f"Fetched {len(messages)} messages")

                # Enrich with guild/channel names
                for msg in messages:
                    msg["guild_name"] = g_name
                    msg["channel_name"] = ch_name

                inserted = db.insert_batch(messages)
                return len(messages), inserted
        finally:
            db.close()

    total, inserted = asyncio.run(_run())
    console.print(
        f"\n[green]✓[/green] Fetched {total} messages, stored {inserted} new"
    )


@discord_group.command("sync")
@click.argument("channel")
@click.option("-n", "--limit", default=5000, help="Max messages per sync")
def dc_sync(channel: str, limit: int):
    """Incremental sync — fetch only new messages from CHANNEL."""
    db = MessageDB()
    last_id = db.get_last_msg_id(channel)
    if last_id:
        console.print(f"Syncing from msg_id > {last_id}...")

    async def _run():
        try:
            async with get_client() as client:
                # Get channel info
                ch_name = None
                g_name = None
                try:
                    ch_info = await client.get(f"/channels/{channel}")
                    if ch_info.status_code == 200:
                        ch_data = ch_info.json()
                        ch_name = ch_data.get("name")
                        if ch_data.get("guild_id"):
                            g_info = await get_guild_info(client, ch_data["guild_id"])
                            if g_info:
                                g_name = g_info["name"]
                except Exception:
                    pass

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    task_id = progress.add_task(f"Syncing {ch_name or channel}...", total=None)

                    messages = await fetch_messages(
                        client, channel, limit=limit, after=last_id
                    )
                    progress.update(task_id, description=f"Fetched {len(messages)} new messages")

                for msg in messages:
                    msg["guild_name"] = g_name
                    msg["channel_name"] = ch_name

                inserted = db.insert_batch(messages)
                return len(messages), inserted
        finally:
            db.close()

    total, inserted = asyncio.run(_run())
    console.print(f"\n[green]✓[/green] Synced {total} messages, stored {inserted} new")


@discord_group.command("sync-all")
@click.option("-n", "--limit", default=5000, help="Max messages per channel")
def dc_sync_all(limit: int):
    """Sync ALL channels in the database."""
    db = MessageDB()
    channels = db.get_channels()
    if not channels:
        console.print("[yellow]No channels in database. Run 'discord dc history' first.[/yellow]")
        db.close()
        return

    console.print(f"Syncing {len(channels)} channels...")

    async def _run():
        try:
            async with get_client() as client:
                results: dict[str, int] = {}

                for ch in channels:
                    ch_id = ch["channel_id"]
                    ch_name = ch.get("channel_name") or ch_id

                    last_id = db.get_last_msg_id(ch_id)
                    try:
                        messages = await fetch_messages(
                            client, ch_id, limit=limit, after=last_id
                        )

                        # Preserve existing names
                        for msg in messages:
                            msg["guild_name"] = ch.get("guild_name")
                            msg["channel_name"] = ch.get("channel_name")

                        inserted = db.insert_batch(messages)
                        results[ch_name] = inserted

                        if inserted > 0:
                            console.print(
                                f"  [green]✓[/green] {ch_name}: +{inserted}"
                            )
                        else:
                            console.print(f"  [dim]✓ {ch_name}: no new messages[/dim]")

                    except Exception as e:
                        console.print(f"  [red]✗ {ch_name}: {e}[/red]")
                        results[ch_name] = 0

                return results
        finally:
            db.close()

    results = asyncio.run(_run())
    total_new = sum(results.values())
    console.print(f"\n[green]✓[/green] Synced {total_new} new messages across {len(results)} channels")


@discord_group.command("info")
@click.argument("guild")
def dc_info(guild: str):
    """Show detailed info about a GUILD (server)."""

    async def _run():
        async with get_client() as client:
            return await get_guild_info(client, guild)

    info = asyncio.run(_run())
    if not info:
        console.print(f"[red]Could not find guild: {guild}[/red]")
        return

    table = Table(title="Guild Info", show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    for k, v in info.items():
        table.add_row(k, str(v) if v is not None else "—")

    console.print(table)
