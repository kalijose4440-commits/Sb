from __future__ import annotations

from dataclasses import dataclass

from disnake.ext import commands

from bot.core.i18n import t


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
    language: str,
) -> CommandErrorHint:
    """Translate command errors into user-facing troubleshooting hints."""

    normalized_name = command_name or "command"

    if isinstance(error, commands.CommandNotFound):
        return CommandErrorHint(
            title=t(language, "error.unknown_command.title"),
            reason=t(language, "error.unknown_command.reason"),
            possible_fix=t(language, "error.unknown_command.fix", prefix=prefix),
            severity="info",
        )
    if isinstance(error, commands.MissingPermissions):
        missing = ", ".join(error.missing_permissions)
        return CommandErrorHint(
            title=t(language, "error.missing_user_perms.title"),
            reason=t(language, "error.missing_user_perms.reason", permissions=missing),
            possible_fix=t(language, "error.missing_user_perms.fix"),
        )
    if isinstance(error, commands.BotMissingPermissions):
        missing = ", ".join(error.missing_permissions)
        return CommandErrorHint(
            title=t(language, "error.missing_bot_perms.title"),
            reason=t(language, "error.missing_bot_perms.reason", permissions=missing),
            possible_fix=t(language, "error.missing_bot_perms.fix"),
        )
    if isinstance(error, commands.MissingRequiredArgument):
        return CommandErrorHint(
            title=t(language, "error.missing_argument.title"),
            reason=t(language, "error.missing_argument.reason", argument=error.param.name),
            possible_fix=t(
                language,
                "error.missing_argument.fix",
                prefix=prefix,
                command=normalized_name,
            ),
            severity="info",
        )
    if isinstance(error, commands.BadArgument):
        return CommandErrorHint(
            title=t(language, "error.bad_argument.title"),
            reason=t(language, "error.bad_argument.reason"),
            possible_fix=t(
                language,
                "error.bad_argument.fix",
                prefix=prefix,
                command=normalized_name,
            ),
            severity="info",
        )
    if isinstance(error, commands.NoPrivateMessage):
        return CommandErrorHint(
            title=t(language, "error.no_private_message.title"),
            reason=t(language, "error.no_private_message.reason"),
            possible_fix=t(language, "error.no_private_message.fix"),
            severity="info",
        )
    if isinstance(error, commands.CommandOnCooldown):
        return CommandErrorHint(
            title=t(language, "error.cooldown.title"),
            reason=t(language, "error.cooldown.reason", retry_after=f"{error.retry_after:.1f}"),
            possible_fix=t(language, "error.cooldown.fix"),
            severity="info",
        )
    if isinstance(error, commands.CheckFailure):
        return CommandErrorHint(
            title=t(language, "error.check_failure.title"),
            reason=t(language, "error.check_failure.reason"),
            possible_fix=t(
                language,
                "error.check_failure.fix",
                prefix=prefix,
                command=normalized_name,
            ),
        )
    if isinstance(error, commands.CommandInvokeError):
        original_name = type(error.original).__name__
        return CommandErrorHint(
            title=t(language, "error.invoke.title"),
            reason=t(language, "error.invoke.reason", original=original_name),
            possible_fix=t(language, "error.invoke.fix"),
            severity="error",
        )

    return CommandErrorHint(
        title=t(language, "error.unexpected.title"),
        reason=t(language, "error.unexpected.reason", error_type=type(error).__name__),
        possible_fix=t(language, "error.unexpected.fix"),
        severity="error",
    )
