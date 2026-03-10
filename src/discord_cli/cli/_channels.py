"""Helpers for resolving stored channel names safely."""

import click

from ..db import ChannelResolutionError, MessageDB


def resolve_channel_id_or_raise(db: MessageDB, channel: str) -> str:
    """Resolve a stored channel ID or raise a CLI-friendly error."""
    try:
        return db.resolve_channel(channel)["channel_id"]
    except ChannelResolutionError as exc:
        raise click.ClickException(str(exc)) from exc
