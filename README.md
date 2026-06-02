# Sb - Premium Disnake + FastAPI + PostgreSQL Bot

Production-grade Discord bot scaffold with:

- **Disnake** slash commands and modular Cog architecture
- **FastAPI** dashboard backend for real-time config
- **PostgreSQL + async SQLAlchemy** persistence
- **Premium automation modules** (welcome, security, ACL, tickets, automod, reaction roles, announcements, analytics)
- **Rich rotating presence** with dynamic placeholders
- **Docker** deployment support
- **Structured logging, type hints, lint/type/test workflow**

## Quick Start

```bash
cp .env.example .env
make setup-dev
make test
make run
```

You can keep `DISCORD_TOKEN` as a placeholder until you are ready to launch.

## Feature Modules

### Core / Admin
- `/settings`
- `/setprefix`
- `/setstatus`

### Utility
- `/ping`
- `/botinfo`
- `/serverinfo`
- `/userinfo`
- `/runtime`

### Moderation
- `/purge`
- `/kick`
- `/ban`
- `/unban`

### Premium: Welcome
- `/welcome status`
- `/welcome setchannel`
- `/welcome message`
- `/welcome enable`
- `/welcome disable`
- `/welcome preview`

### Premium: Security
- `/security status`
- `/security configure`
- `/security enable`
- `/security disable`

`/security configure` supports automated mitigation actions:
- `none`
- `verification_high` (temporarily raises guild verification level and auto-restores)

### Premium: ACL
- `/acl allow`
- `/acl revoke`
- `/acl list`

ACL rules are role-based allow-lists by slash command qualified name (e.g. `ticket open`).

### Premium: Tickets
- `/ticket open`
- `/ticket close`
- `/ticket escalate`
- `/ticket transcript`
- `/ticket add`
- `/ticket remove`
- `/ticket list`

Ticket close/transcript can generate and persist transcript snapshots.

### Premium: Automod
- `/automod add`
- `/automod remove`
- `/automod toggle`
- `/automod list`

### Premium: Reaction Roles
- `/reactionrole bind`
- `/reactionrole unbind`
- `/reactionrole list`

### Premium: Announcements
- `/announce create`
- `/announce toggle`
- `/announce list`
- `/announce runnow`

### Premium: Analytics
- `/analytics topcommands`
- `/analytics topusers`

## Rich Presence

Configured via `PRESENCE_TEMPLATES` and `PRESENCE_ROTATION_SECONDS`.

Template format:

```text
activity::text::status
```

- `activity`: `playing`, `watching`, `listening`, `competing`
- `status`: `online`, `idle`, `dnd`, `invisible`
- placeholders in `text`: `{guilds}`, `{users}`, `{uptime}`

Example:

```text
watching::{users} members::idle
```

## API Endpoints

### Base settings
- `GET /api/v1/settings/{guild_id}`
- `PATCH /api/v1/settings/{guild_id}`
- `DELETE /api/v1/settings/{guild_id}`

### Premium controls
- `GET/POST/DELETE /api/v1/premium/{guild_id}/automod/keywords`
- `GET/POST/PATCH /api/v1/premium/{guild_id}/announcements`
- `GET/POST/DELETE /api/v1/premium/{guild_id}/reaction-roles`
- `GET /api/v1/premium/{guild_id}/tickets/open`
- `PATCH /api/v1/premium/{guild_id}/tickets/{ticket_id}/escalate`
- `GET /api/v1/premium/{guild_id}/tickets/{ticket_id}/transcripts`
- `GET/PATCH /api/v1/premium/{guild_id}/welcome`
- `GET/PATCH /api/v1/premium/{guild_id}/security`
- `GET/POST/DELETE /api/v1/premium/{guild_id}/acl`

## Quality Workflow

```bash
make lint
make typecheck
make test
make check
```

## Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```
