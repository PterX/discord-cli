# discord-cli

Discord CLI — fetch chat history, search messages, daily sync. Uses Discord HTTP API with user token (read-only).

## Quick Start

```bash
# Install
uv sync

# Set token in .env
cp .env.example .env
# Edit .env — set DISCORD_TOKEN

# List servers
discord dc guilds

# List channels
discord dc channels <guild_id>

# Fetch history
discord dc history <channel_id> -n 1000

# Incremental sync
discord dc sync <channel_id>

# Sync all channels
discord dc sync-all

# Today's messages
discord today
```

## Commands

### Discord (`discord dc ...`)

| Command | Description |
|---------|-------------|
| `dc guilds` | List joined servers |
| `dc channels GUILD` | List text channels in a server |
| `dc history CHANNEL [-n 1000]` | Fetch historical messages |
| `dc sync CHANNEL` | Incremental sync (only new messages) |
| `dc sync-all` | Sync ALL channels in database |
| `dc info GUILD` | Show server info |

### Query

| Command | Description |
|---------|-------------|
| `search KEYWORD [-c CHANNEL]` | Search stored messages |
| `stats` | Show message statistics |
| `today [-c CHANNEL] [--json]` | Show today's messages |

### Data

| Command | Description |
|---------|-------------|
| `export CHANNEL [-f text\|json] [-o FILE]` | Export messages |
| `purge CHANNEL [-y]` | Delete stored messages |

## Setup

1. Get your Discord user token from browser DevTools:
   - Open Discord in browser → F12 → Network tab
   - Send a message or click around
   - Find any request to `discord.com/api` → copy `Authorization` header value
2. Copy `.env.example` to `.env` and paste your token
3. `uv sync` to install dependencies

## Architecture

```
src/discord_cli/
├── cli/
│   ├── main.py          # Click CLI entry point
│   ├── discord_cmds.py  # Discord commands (guilds, channels, sync)
│   ├── query.py         # Query commands (search, stats, today)
│   └── data.py          # Data commands (export, purge)
├── client.py            # httpx Discord API client with rate limiting
├── config.py            # Env var / .env config
└── db.py                # SQLite message store
```

Uses **httpx** (async HTTP) to call Discord REST API v10.
Messages are stored in **SQLite** (`~/Library/Application Support/discord-cli/messages.db`).
