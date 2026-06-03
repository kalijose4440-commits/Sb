from __future__ import annotations

from dataclasses import dataclass

from disnake.ext import commands


@dataclass(slots=True)
class CommandErrorHint:
    title: str
    reason: str
    possible_fix: str
    severity: str = "warning"


def classify_command_error(
    error: commands.CommandError,
    *,
    prefix: str,
    command_name: str | None,
) -> CommandErrorHint:
    """Translate command errors into user-facing troubleshooting hints."""

    normalized_name = command_name or "command"

    if isinstance(error, commands.CommandNotFound):
        return CommandErrorHint(
            title="Unknown Command",
            reason="That command name is not registered on this server.",
            possible_fix=f"Run `{prefix}help` and copy a command exactly from the list.",
            severity="info",
        )
    if isinstance(error, commands.MissingPermissions):
        missing = ", ".join(error.missing_permissions)
        return CommandErrorHint(
            title="Missing User Permission",
            reason=f"Your role is missing required permission(s): `{missing}`.",
            possible_fix=(
                "Ask a server admin to grant those permissions or run the command "
                "from a role that has them."
            ),
        )
    if isinstance(error, commands.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        return CommandErrorHint(
            title="Bot Permission Missing",
            reason=f"The bot is missing required permission(s): `{missing}`.",
            possible_fix=(
                "Edit the bot role and channel overrides to include those permissions, "
                "then run the command again."
            ),
        )
    if isinstance(error, commands.MissingRequiredArgument):
        return CommandErrorHint(
            title="Missing Argument",
            reason=f"Required parameter `{error.param.name}` was not provided.",
            possible_fix=f"Run `{prefix}help {normalized_name}` to see exact usage.",
            severity="info",
        )
    if isinstance(error, commands.BadArgument):
        return CommandErrorHint(
            title="Invalid Argument",
            reason="One of the provided values is not in the expected format.",
            possible_fix=f"Run `{prefix}help {normalized_name}` and follow the examples.",
            severity="info",
        )
    if isinstance(error, commands.NoPrivateMessage):
        return CommandErrorHint(
            title="Guild-Only Command",
            reason="That command cannot run in direct messages.",
            possible_fix="Run it inside the target server channel.",
            severity="info",
        )
    if isinstance(error, commands.CommandOnCooldown):
        return CommandErrorHint(
            title="Command Cooldown",
            reason=f"This command is on cooldown for {error.retry_after:.1f}s.",
            possible_fix="Wait for the cooldown period and retry.",
            severity="info",
        )
    if isinstance(error, commands.CheckFailure):
        return CommandErrorHint(
            title="Command Requirement Failed",
            reason="A command guard blocked this request (permission/role/context check).",
            possible_fix=f"Run `{prefix}help {normalized_name}` and verify requirements.",
        )
    if isinstance(error, commands.CommandInvokeError):
        original = error.original
        original_name = type(original).__name__
        return CommandErrorHint(
            title="Runtime Command Failure",
            reason=f"Command execution raised `{original_name}` internally.",
            possible_fix=(
                "Try again in a few seconds. If it keeps failing, verify bot "
                "permissions and required setup (roles/channels/config) for this command."
            ),
            severity="error",
        )

    return CommandErrorHint(
        title="Unexpected Command Error",
        reason=f"Unhandled error type `{type(error).__name__}`.",
        possible_fix="Retry once. If the issue persists, use `help` and report the failing command.",
        severity="error",
    )
