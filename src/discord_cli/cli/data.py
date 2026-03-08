"""Data commands — export, purge."""

import json

import click
from rich.console import Console

from ..db import MessageDB

console = Console()


@click.group("data", invoke_without_command=True)
def data_group():
    """Data management commands (registered at top-level)."""
    pass


@data_group.command("export")
@click.argument("channel")
@click.option("-f", "--format", "fmt", type=click.Choice(["text", "json"]), default="text")
@click.option("-o", "--output", "output_file", help="Output file path")
@click.option("--hours", type=int, help="Only export last N hours")
def export(channel: str, fmt: str, output_file: str | None, hours: int | None):
    """Export messages from CHANNEL to text or JSON."""
    db = MessageDB()
    channel_id = db.resolve_channel_id(channel)

    if channel_id is None:
        console.print(f"[red]Channel '{channel}' not found in database.[/red]")
        db.close()
        return

    if hours:
        msgs = db.get_recent(channel_id=channel_id, hours=hours, limit=100000)
    else:
        msgs = db.get_recent(channel_id=channel_id, hours=None, limit=100000)
    db.close()

    if not msgs:
        console.print(f"[yellow]No messages found for '{channel}'.[/yellow]")
        return

    if fmt == "json":
        content = json.dumps(msgs, ensure_ascii=False, indent=2, default=str)
    else:
        lines = []
        for msg in msgs:
            ts = (msg.get("timestamp") or "")[:19]
            sender = msg.get("sender_name") or "Unknown"
            text = msg.get("content") or ""
            lines.append(f"[{ts}] {sender}: {text}")
        content = "\n".join(lines)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[green]✓[/green] Exported {len(msgs)} messages to {output_file}")
    else:
        console.print(content)


@data_group.command("purge")
@click.argument("channel")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation")
def purge(channel: str, yes: bool):
    """Delete all stored messages for CHANNEL."""
    db = MessageDB()
    channel_id = db.resolve_channel_id(channel)

    if channel_id is None:
        console.print(f"[red]Channel '{channel}' not found in database.[/red]")
        db.close()
        return

    if not yes:
        count = db.count(channel_id)
        if not click.confirm(f"Delete {count} messages from channel {channel_id}?"):
            db.close()
            return

    deleted = db.delete_channel(channel_id)
    db.close()
    console.print(f"[green]✓[/green] Deleted {deleted} messages")
