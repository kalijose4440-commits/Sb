# Sb - Disnake + FastAPI + PostgreSQL Bot

Production-oriented Discord bot scaffold with:

- **Disnake** for slash-command based bot interactions
- **FastAPI** dashboard backend for real-time settings management
- **PostgreSQL + async SQLAlchemy** persistence
- **Docker** deployment support
- **Structured JSON logging**, type hints, and async-first architecture

## Project Layout

```text
src/bot/
  api/         # FastAPI app, routes, schemas
  bridge/      # Real-time runtime bridge state
  cogs/        # Modular command cogs
  core/        # Config, logging, lifecycle helpers
  db/          # SQLAlchemy base/models/repositories/session
  bot.py       # Main entrypoint
```

## Quick Start (Cloud/Local)

1. Copy env file:

```bash
cp .env.example .env
```

2. Install dependencies (including dev tooling):

```bash
make setup-dev
```

3. Run tests:

```bash
make test
```

4. Run bot + API service:

```bash
make run
```

## Environment Variables

See `.env.example`.

Important values:

- `DISCORD_TOKEN`
- `DATABASE_URL`
- `API_HOST`, `API_PORT`
- `DEFAULT_PREFIX`, `DEFAULT_STATUS`
- `BOT_ACTIVITY`

## Command Suite

### Admin / Settings

- `/settings` - View current guild settings
- `/setprefix <prefix>` - Update guild prefix (Manage Server)
- `/setstatus <status>` - Update guild status label (Manage Server)

### Utility

- `/ping` - Heartbeat latency
- `/botinfo` - Runtime stats and uptime
- `/serverinfo` - Guild summary
- `/userinfo [member]` - Member profile details
- `/runtime` - Current bridge runtime snapshot

### Moderation

- `/purge <amount>` - Bulk-delete up to 100 messages (Manage Messages)
- `/kick <member> [reason]` - Kick member (Kick Members)
- `/ban <member> [reason]` - Ban member (Ban Members)
- `/unban <user_id> [reason]` - Unban by user id (Ban Members)

## Quality Tooling

- Lint: `make lint`
- Format: `make format`
- Type check: `make typecheck`
- Full checks: `make check`

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

This launches:

- bot/API container
- PostgreSQL 16 container
