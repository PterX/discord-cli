"""Query commands — search, stats, today."""

from collections import defaultdict

import click
from rich.console import Console
from rich.table import Table

from ..db import MessageDB

console = Console()


@click.group("query", invoke_without_command=True)
def query_group():
    """Query and analysis commands (registered at top-level)."""
    pass


@query_group.command("search")
@click.argument("keyword")
@click.option("-c", "--channel", help="Filter by channel name")
@click.option("-n", "--limit", default=50, help="Max results")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def search(keyword: str, channel: str | None, limit: int, as_json: bool):
    """Search messages by KEYWORD."""
    import json

    db = MessageDB()
    channel_id = db.resolve_channel_id(channel) if channel else None
    results = db.search(keyword, channel_id=channel_id, limit=limit)
    db.close()

    if not results:
        console.print("[yellow]No messages found.[/yellow]")
        return

    if as_json:
        console.print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
        return

    for msg in results:
        ts = (msg.get("timestamp") or "")[:19]
        sender = msg.get("sender_name") or "Unknown"
        ch_name = msg.get("channel_name") or ""
        content = (msg.get("content") or "")[:200]
        console.print(
            f"[dim]{ts}[/dim] [cyan]#{ch_name}[/cyan] | "
            f"[bold]{sender}[/bold]: {content}"
        )

    console.print(f"\n[dim]Found {len(results)} messages[/dim]")


@query_group.command("stats")
def stats():
    """Show message statistics per channel."""
    db = MessageDB()
    channels = db.get_channels()
    total = db.count()
    db.close()

    table = Table(title=f"Message Stats (Total: {total})")
    table.add_column("Channel ID", style="dim")
    table.add_column("Channel", style="bold")
    table.add_column("Guild", style="cyan")
    table.add_column("Messages", justify="right")
    table.add_column("First", style="dim")
    table.add_column("Last", style="dim")

    for c in channels:
        table.add_row(
            str(c["channel_id"])[-6:] + "…",
            f"#{c['channel_name']}" if c["channel_name"] else "—",
            c.get("guild_name") or "—",
            str(c["msg_count"]),
            (c["first_msg"] or "")[:10],
            (c["last_msg"] or "")[:10],
        )

    console.print(table)


@query_group.command("today")
@click.option("-c", "--channel", help="Filter by channel name")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def today(channel: str | None, as_json: bool):
    """Show today's messages, grouped by channel."""
    import json

    db = MessageDB()
    channel_id = db.resolve_channel_id(channel) if channel else None
    msgs = db.get_today(channel_id=channel_id)
    db.close()

    if not msgs:
        console.print("[yellow]No messages today.[/yellow]")
        return

    if as_json:
        console.print(json.dumps(msgs, ensure_ascii=False, indent=2, default=str))
        return

    # Group by channel
    grouped: dict[str, list[dict]] = defaultdict(list)
    for m in msgs:
        key = f"#{m.get('channel_name') or 'unknown'}"
        if m.get("guild_name"):
            key = f"{m['guild_name']} > {key}"
        grouped[key].append(m)

    for ch_label, ch_msgs in sorted(grouped.items(), key=lambda x: -len(x[1])):
        console.print(f"\n[bold cyan]═══ {ch_label} ({len(ch_msgs)} msgs) ═══[/bold cyan]")
        for m in ch_msgs:
            ts = (m.get("timestamp") or "")[11:19]
            sender = m.get("sender_name") or "Unknown"
            content = (m.get("content") or "")[:200].replace("\n", " ")
            console.print(f"  [dim]{ts}[/dim] [bold]{sender[:15]}[/bold]: {content}")

    console.print(f"\n[green]Total: {len(msgs)} messages today[/green]")
