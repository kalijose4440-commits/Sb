from __future__ import annotations

import asyncio

import disnake
from disnake.ext import commands

from bot.core.command_aliases import command_aliases_for, register_multilingual_aliases


class _AliasDemoCog(commands.Cog):
    @commands.group(name="music", invoke_without_command=True)
    async def music_group(self, _ctx: commands.Context) -> None:
        return None

    @music_group.command(name="play")
    async def music_play(self, _ctx: commands.Context, *, _source: str) -> None:
        return None


def test_command_aliases_cover_requested_languages() -> None:
    aliases = command_aliases_for("music")
    assert "musica" in aliases
    assert "musique" in aliases
    assert "musik" in aliases
    assert "muzyka" in aliases


def test_register_multilingual_aliases_adds_group_and_subcommand_names() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=disnake.Intents.none())
    bot.add_cog(_AliasDemoCog())

    added = register_multilingual_aliases(bot, ("music",))
    assert added >= 2

    localized_group = bot.get_command("musica")
    assert isinstance(localized_group, commands.Group)
    assert localized_group is bot.get_command("music")
    assert localized_group.get_command("reproducir") is localized_group.get_command("play")
    loop.run_until_complete(bot.close())
    loop.close()
    asyncio.set_event_loop(None)
