from __future__ import annotations

import re

# ruff: noqa: E501

SUPPORTED_LANGUAGES = ("en", "es", "fr", "de", "ru")
DEFAULT_LANGUAGE = "en"

HELP_COMMAND_BY_LANGUAGE: dict[str, str] = {
    "en": "help",
    "es": "ayuda",
    "fr": "aide",
    "de": "hilfe",
    "ru": "pomosh",
}

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "help.dashboard_intro": (
            "Current prefix: `{prefix}`\n"
            "Use `{prefix}{help_command} <category>` for detailed subcommand usage."
        ),
        "help.quick_fix": (
            "Quick fix: run `{prefix}{help_command} {category}` for argument format and checks."
        ),
        "help.unknown_category": "Unknown category `{category}`.",
        "help.available_categories": "Available categories: {categories}",
        "help.subcommands_detail": "Detailed subcommands for `{command}`.",
        "help.command_usage": "Usage: `{usage}`",
        "language.current": "Current server language: `{language}`. Start with `{prefix}{help_command}`.",
        "language.updated": "Server language updated to `{language}`. Start with `{prefix}{help_command}`.",
        "language.invalid": "Unsupported language `{language}`. Supported: {supported}.",
        "language.category_hint": "Manage per-server language preferences.",
        "error.unknown_command.title": "Unknown Command",
        "error.unknown_command.reason": "That command name is not registered on this server.",
        "error.unknown_command.fix": (
            "Run `{prefix}{help_command}` and copy a command exactly from the list."
        ),
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
        "error.missing_argument.fix": (
            "Run `{prefix}{help_command} {command}` to see exact usage."
        ),
        "error.bad_argument.title": "Invalid Argument",
        "error.bad_argument.reason": "One of the provided values is not in the expected format.",
        "error.bad_argument.fix": (
            "Run `{prefix}{help_command} {command}` and follow the examples."
        ),
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
        "error.check_failure.fix": (
            "Run `{prefix}{help_command} {command}` and verify requirements."
        ),
        "error.invoke.title": "Runtime Command Failure",
        "error.invoke.reason": "Command execution raised `{original}` internally.",
        "error.invoke.fix": (
            "Retry in a few seconds. If it persists, verify bot permissions and setup."
        ),
        "error.unexpected.title": "Unexpected Command Error",
        "error.unexpected.reason": "Unhandled error type `{error_type}`.",
        "error.unexpected.fix": (
            "Retry once. If it persists, run `{help_command}` and report the command."
        ),
    },
    "es": {
        "help.dashboard_intro": (
            "Prefijo actual: `{prefix}`\n"
            "Usa `{prefix}{help_command} <categoria>` para ver subcomandos detallados."
        ),
        "help.quick_fix": (
            "Solucion rapida: usa `{prefix}{help_command} {category}` para formato y requisitos."
        ),
        "help.unknown_category": "Categoria desconocida `{category}`.",
        "help.available_categories": "Categorias disponibles: {categories}",
        "help.subcommands_detail": "Subcomandos detallados para `{command}`.",
        "help.command_usage": "Uso: `{usage}`",
        "language.current": "Idioma del servidor: `{language}`. Empieza con `{prefix}{help_command}`.",
        "language.updated": "Idioma cambiado a `{language}`. Empieza con `{prefix}{help_command}`.",
        "language.invalid": "Idioma no soportado `{language}`. Soportados: {supported}.",
    },
    "fr": {
        "help.dashboard_intro": (
            "Prefixe actuel: `{prefix}`\n"
            "Utilise `{prefix}{help_command} <categorie>` pour les sous-commandes."
        ),
        "help.quick_fix": (
            "Correction rapide: utilise `{prefix}{help_command} {category}` pour le format."
        ),
        "help.unknown_category": "Categorie inconnue `{category}`.",
        "help.available_categories": "Categories disponibles: {categories}",
        "help.subcommands_detail": "Sous-commandes detaillees pour `{command}`.",
        "help.command_usage": "Utilisation: `{usage}`",
        "language.current": "Langue du serveur: `{language}`. Commence par `{prefix}{help_command}`.",
        "language.updated": "Langue changee en `{language}`. Commence par `{prefix}{help_command}`.",
        "language.invalid": "Langue non supportee `{language}`. Supportees: {supported}.",
    },
    "de": {
        "help.dashboard_intro": (
            "Aktuelles Prefix: `{prefix}`\n"
            "Nutze `{prefix}{help_command} <kategorie>` fur detaillierte Unterbefehle."
        ),
        "help.quick_fix": (
            "Schnellhilfe: nutze `{prefix}{help_command} {category}` fur Format und Prufungen."
        ),
        "help.unknown_category": "Unbekannte Kategorie `{category}`.",
        "help.available_categories": "Verfugbare Kategorien: {categories}",
        "help.subcommands_detail": "Detaillierte Unterbefehle fur `{command}`.",
        "help.command_usage": "Verwendung: `{usage}`",
        "language.current": "Serversprache: `{language}`. Starte mit `{prefix}{help_command}`.",
        "language.updated": "Serversprache auf `{language}` gesetzt. Starte mit `{prefix}{help_command}`.",
        "language.invalid": "Nicht unterstutzte Sprache `{language}`. Unterstutzt: {supported}.",
    },
    "ru": {
        "help.dashboard_intro": (
            "Tekushchiy prefiks: `{prefix}`\n"
            "Ispolzuy `{prefix}{help_command} <kategoriya>` dlya podkomand."
        ),
        "help.quick_fix": (
            "Bystryy start: zapusti `{prefix}{help_command} {category}` dlya formata i proverok."
        ),
        "help.unknown_category": "Neizvestnaya kategoriya `{category}`.",
        "help.available_categories": "Dostupnye kategorii: {categories}",
        "help.subcommands_detail": "Podrobnye podkomandy dlya `{command}`.",
        "help.command_usage": "Ispolzovanie: `{usage}`",
        "language.current": "Yazyk servera: `{language}`. Nachni s `{prefix}{help_command}`.",
        "language.updated": "Yazyk servera izmenen na `{language}`. Nachni s `{prefix}{help_command}`.",
        "language.invalid": "Yazyk `{language}` ne podderzhivaetsya. Dostupno: {supported}.",
    },
}

# Fill any missing keys from English to keep behavior stable.
for _lang in SUPPORTED_LANGUAGES:
    if _lang == "en":
        continue
    for _key, _value in _MESSAGES["en"].items():
        _MESSAGES[_lang].setdefault(_key, _value)


def normalize_language(language: str | None) -> str:
    if language is None:
        return DEFAULT_LANGUAGE
    candidate = language.lower().strip()
    if candidate in SUPPORTED_LANGUAGES:
        return candidate
    return DEFAULT_LANGUAGE


def help_command_for_language(language: str | None) -> str:
    normalized = normalize_language(language)
    return HELP_COMMAND_BY_LANGUAGE.get(normalized, "help")


def supported_languages_display() -> str:
    return ", ".join(SUPPORTED_LANGUAGES)


def t(locale: str | None, key: str, **kwargs: object) -> str:
    normalized = normalize_language(locale)
    template = _MESSAGES.get(normalized, _MESSAGES["en"]).get(key, _MESSAGES["en"].get(key, key))
    if "help_command" not in kwargs:
        kwargs["help_command"] = help_command_for_language(normalized)
    return template.format(**kwargs)


_RUNTIME_PATTERNS: dict[str, list[tuple[re.Pattern[str], str]]] = {
    "es": [
        (re.compile(r"^This command can only be used in a server\.$"), "Este comando solo se puede usar en un servidor."),
        (re.compile(r"^Join a voice channel first\.$"), "Primero unete a un canal de voz."),
        (re.compile(r"^Queue is empty\.$"), "La cola esta vacia."),
        (re.compile(r"^No track is currently playing\.$"), "No hay una pista reproduciendose ahora."),
        (re.compile(r"^No active track to skip\.$"), "No hay pista activa para saltar."),
        (re.compile(r"^Paused playback\.$"), "Reproduccion pausada."),
        (re.compile(r"^Resumed playback\.$"), "Reproduccion reanudada."),
        (re.compile(r"^Playback is not paused\.$"), "La reproduccion no esta pausada."),
        (re.compile(r"^Skipped current track\.$"), "Pista actual saltada."),
        (re.compile(r"^Stopped playback and cleared queue\.$"), "Reproduccion detenida y cola limpiada."),
        (re.compile(r"^Disconnected and cleared queue\.$"), "Desconectado y cola limpiada."),
    ],
    "fr": [
        (re.compile(r"^This command can only be used in a server\.$"), "Cette commande doit etre utilisee sur un serveur."),
        (re.compile(r"^Join a voice channel first\.$"), "Rejoins un salon vocal d'abord."),
        (re.compile(r"^Queue is empty\.$"), "La file est vide."),
        (re.compile(r"^No track is currently playing\.$"), "Aucune piste en lecture actuellement."),
        (re.compile(r"^No active track to skip\.$"), "Aucune piste active a passer."),
        (re.compile(r"^Paused playback\.$"), "Lecture mise en pause."),
        (re.compile(r"^Resumed playback\.$"), "Lecture reprise."),
        (re.compile(r"^Playback is not paused\.$"), "La lecture n'est pas en pause."),
        (re.compile(r"^Skipped current track\.$"), "Piste actuelle passee."),
        (re.compile(r"^Stopped playback and cleared queue\.$"), "Lecture arretee et file videe."),
        (re.compile(r"^Disconnected and cleared queue\.$"), "Deconnecte et file videe."),
    ],
    "de": [
        (re.compile(r"^This command can only be used in a server\.$"), "Dieser Befehl kann nur auf einem Server genutzt werden."),
        (re.compile(r"^Join a voice channel first\.$"), "Tritt zuerst einem Sprachkanal bei."),
        (re.compile(r"^Queue is empty\.$"), "Die Warteschlange ist leer."),
        (re.compile(r"^No track is currently playing\.$"), "Aktuell wird kein Track abgespielt."),
        (re.compile(r"^No active track to skip\.$"), "Kein aktiver Track zum Uberspringen."),
        (re.compile(r"^Paused playback\.$"), "Wiedergabe pausiert."),
        (re.compile(r"^Resumed playback\.$"), "Wiedergabe fortgesetzt."),
        (re.compile(r"^Playback is not paused\.$"), "Die Wiedergabe ist nicht pausiert."),
        (re.compile(r"^Skipped current track\.$"), "Aktueller Track ubersprungen."),
        (re.compile(r"^Stopped playback and cleared queue\.$"), "Wiedergabe gestoppt und Warteschlange geleert."),
        (re.compile(r"^Disconnected and cleared queue\.$"), "Getrennt und Warteschlange geleert."),
    ],
    "ru": [
        (re.compile(r"^This command can only be used in a server\.$"), "Eta komanda rabotaet tolko na servere."),
        (re.compile(r"^Join a voice channel first\.$"), "Snachala zaydi v golosovoy kanal."),
        (re.compile(r"^Queue is empty\.$"), "Ochered pusta."),
        (re.compile(r"^No track is currently playing\.$"), "Seychas nichego ne vosproizvoditsya."),
        (re.compile(r"^No active track to skip\.$"), "Net aktivnogo treka dlya propuska."),
        (re.compile(r"^Paused playback\.$"), "Vosproizvedenie postavleno na pauzu."),
        (re.compile(r"^Resumed playback\.$"), "Vosproizvedenie prodolzheno."),
        (re.compile(r"^Playback is not paused\.$"), "Vosproizvedenie ne na pauze."),
        (re.compile(r"^Skipped current track\.$"), "Tekushchiy trek propushchen."),
        (re.compile(r"^Stopped playback and cleared queue\.$"), "Vosproizvedenie ostanovleno i ochered ochishchena."),
        (re.compile(r"^Disconnected and cleared queue\.$"), "Otklyuchenie i ochered ochishchena."),
    ],
}


def translate_runtime_text(locale: str | None, text: str) -> str:
    normalized = normalize_language(locale)
    if normalized == "en" or not text:
        return text

    output = text
    for pattern, replacement in _RUNTIME_PATTERNS.get(normalized, []):
        output = pattern.sub(replacement, output)
    return output
