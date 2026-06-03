from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "es", "fr", "de", "ru")
DEFAULT_LANGUAGE = "en"

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "help.dashboard_intro": (
            "Current prefix: `{prefix}`\n"
            "Use `{prefix}help <category>` for detailed subcommand usage."
        ),
        "help.quick_fix": (
            "Quick fix: run `{prefix}help {category}` for argument format and checks."
        ),
        "help.unknown_category": "Unknown category `{category}`.",
        "help.available_categories": "Available categories: {categories}",
        "help.subcommands_detail": "Detailed subcommands for `{command}`.",
        "help.command_usage": "Usage: `{usage}`",
        "language.current": "Current server language: `{language}`.",
        "language.updated": "Server language updated to `{language}`.",
        "language.invalid": "Unsupported language `{language}`. Supported: {supported}.",
        "language.category_hint": "Manage per-server language preferences.",
        "error.unknown_command.title": "Unknown Command",
        "error.unknown_command.reason": "That command name is not registered on this server.",
        "error.unknown_command.fix": "Run `{prefix}help` and copy a command exactly from the list.",
        "error.missing_user_perms.title": "Missing User Permission",
        "error.missing_user_perms.reason": (
            "Your role is missing required permission(s): `{permissions}`."
        ),
        "error.missing_user_perms.fix": (
            "Ask a server admin to grant those permissions or use a role with access."
        ),
        "error.missing_bot_perms.title": "Bot Permission Missing",
        "error.missing_bot_perms.reason": (
            "The bot is missing required permission(s): `{permissions}`."
        ),
        "error.missing_bot_perms.fix": (
            "Update the bot role/channel permissions, then retry the command."
        ),
        "error.missing_argument.title": "Missing Argument",
        "error.missing_argument.reason": "Required parameter `{argument}` was not provided.",
        "error.missing_argument.fix": "Run `{prefix}help {command}` to see exact usage.",
        "error.bad_argument.title": "Invalid Argument",
        "error.bad_argument.reason": "One of the provided values is not in the expected format.",
        "error.bad_argument.fix": "Run `{prefix}help {command}` and follow the examples.",
        "error.no_private_message.title": "Guild-Only Command",
        "error.no_private_message.reason": "That command cannot run in direct messages.",
        "error.no_private_message.fix": "Run it inside the target server channel.",
        "error.cooldown.title": "Command Cooldown",
        "error.cooldown.reason": "This command is on cooldown for {retry_after}s.",
        "error.cooldown.fix": "Wait for the cooldown period and retry.",
        "error.check_failure.title": "Command Requirement Failed",
        "error.check_failure.reason": (
            "A command guard blocked this request (permission/role/context check)."
        ),
        "error.check_failure.fix": "Run `{prefix}help {command}` and verify requirements.",
        "error.invoke.title": "Runtime Command Failure",
        "error.invoke.reason": "Command execution raised `{original}` internally.",
        "error.invoke.fix": (
            "Retry in a few seconds. If it persists, verify bot permissions and setup."
        ),
        "error.unexpected.title": "Unexpected Command Error",
        "error.unexpected.reason": "Unhandled error type `{error_type}`.",
        "error.unexpected.fix": "Retry once. If it persists, run `help` and report the command.",
    },
}

# Reuse English strings for non-English locales initially; localized coverage can
# grow incrementally without breaking fallback behavior.
for _lang in ("es", "fr", "de", "ru"):
    _MESSAGES[_lang] = dict(_MESSAGES["en"])


def normalize_language(language: str | None) -> str:
    if language is None:
        return DEFAULT_LANGUAGE
    candidate = language.lower().strip()
    if candidate in SUPPORTED_LANGUAGES:
        return candidate
    return DEFAULT_LANGUAGE


def supported_languages_display() -> str:
    return ", ".join(SUPPORTED_LANGUAGES)


def t(language: str | None, key: str, **kwargs: object) -> str:
    normalized = normalize_language(language)
    template = _MESSAGES.get(normalized, _MESSAGES["en"]).get(key, _MESSAGES["en"].get(key, key))
    return template.format(**kwargs)
