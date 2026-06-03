from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, cast

import disnake
from disnake.ext import commands
from disnake.interactions.application_command import ApplicationCommandInteraction

from bot.cogs.base_cog import BaseCog


@dataclass(slots=True)
class MusicTrack:
    source: str
    title: str
    requested_by: int


@dataclass(slots=True)
class GuildMusicState:
    queue: list[MusicTrack] = field(default_factory=list)
    now_playing: MusicTrack | None = None
    volume: float = 0.5


class MusicCog(BaseCog):
    """Voice and queue controls for basic music playback."""

    def __init__(self, bot: commands.InteractionBot, session_factory) -> None:
        super().__init__(bot=bot, session_factory=session_factory)
        self._states: dict[int, GuildMusicState] = {}

    def _state_for(self, guild_id: int) -> GuildMusicState:
        state = self._states.get(guild_id)
        if state is None:
            state = GuildMusicState()
            self._states[guild_id] = state
        return state

    async def _ensure_voice(
        self,
        interaction: ApplicationCommandInteraction,
    ) -> tuple[disnake.VoiceClient, GuildMusicState] | None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return None

        if not isinstance(interaction.author, disnake.Member) or interaction.author.voice is None:
            await interaction.response.send_message(
                "Join a voice channel first.",
                ephemeral=True,
            )
            return None

        channel = interaction.author.voice.channel
        if channel is None:
            await interaction.response.send_message(
                "Could not resolve your voice channel.",
                ephemeral=True,
            )
            return None

        voice_client = interaction.guild.voice_client
        if voice_client is None:
            voice_client = await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        return voice_client, self._state_for(interaction.guild_id)

    @commands.slash_command(name="music", description="Music playback controls")
    async def music(self, interaction: ApplicationCommandInteraction) -> None:
        await self.send_subcommand_help(
            interaction,
            group_name="music",
            slash_examples=[
                "music join",
                "music play",
                "music pause",
                "music resume",
                "music skip",
                "music stop",
                "music queue",
                "music volume",
                "music nowplaying",
                "music leave",
            ],
            prefix_examples=[
                "music join",
                "music play",
                "music pause",
                "music resume",
                "music skip",
                "music stop",
                "music queue",
                "music volume",
                "music nowplaying",
                "music leave",
            ],
        )

    @music.sub_command(name="join", description="Join your current voice channel")
    async def join(self, interaction: ApplicationCommandInteraction) -> None:
        resolved = await self._ensure_voice(interaction)
        if resolved is None:
            return
        voice_client, _state = resolved
        await interaction.response.send_message(
            f"Connected to `{voice_client.channel}`.",
            ephemeral=True,
        )

    @music.sub_command(name="leave", description="Disconnect from voice and clear queue")
    async def leave(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        voice_client = interaction.guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect(force=True)

        state = self._state_for(interaction.guild_id)
        state.queue.clear()
        state.now_playing = None
        await interaction.response.send_message("Disconnected and cleared queue.", ephemeral=True)

    @music.sub_command(name="play", description="Queue and play an audio source URL")
    async def play(self, interaction: ApplicationCommandInteraction, source: str) -> None:
        resolved = await self._ensure_voice(interaction)
        if resolved is None or interaction.guild_id is None:
            return

        voice_client, state = resolved
        track = MusicTrack(
            source=source.strip(),
            title=source.strip(),
            requested_by=interaction.author.id,
        )
        state.queue.append(track)

        if not voice_client.is_playing() and not voice_client.is_paused() and state.now_playing is None:
            await self._play_next(interaction.guild, voice_client, state)

        await interaction.response.send_message(
            f"Queued track: `{track.title}` (position `{len(state.queue)}`).",
            ephemeral=True,
        )

    async def _play_next(
        self,
        guild: disnake.Guild,
        voice_client: disnake.VoiceClient,
        state: GuildMusicState,
    ) -> None:
        if not state.queue:
            state.now_playing = None
            return

        track = state.queue.pop(0)
        state.now_playing = track

        audio_source = disnake.PCMVolumeTransformer(
            disnake.FFmpegPCMAudio(track.source),
            volume=state.volume,
        )

        def _after_play(error: Exception | None) -> None:
            if error is not None:
                logger = getattr(self.bot, "logger", None)
                if logger is not None:
                    logger.warning("music_playback_error", extra={"error": str(error)})
            asyncio.run_coroutine_threadsafe(
                self._play_next(guild, voice_client, state),
                self.bot.loop,
            )

        voice_client.play(audio_source, after=_after_play)

    @music.sub_command(name="pause", description="Pause playback")
    async def pause(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.guild.voice_client is None:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Paused playback.", ephemeral=True)
            return
        await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    @music.sub_command(name="resume", description="Resume paused playback")
    async def resume(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.guild.voice_client is None:
            await interaction.response.send_message("Nothing is paused right now.", ephemeral=True)
            return
        voice_client = interaction.guild.voice_client
        if voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Resumed playback.", ephemeral=True)
            return
        await interaction.response.send_message("Playback is not paused.", ephemeral=True)

    @music.sub_command(name="skip", description="Skip the current track")
    async def skip(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        voice_client = interaction.guild.voice_client
        if voice_client is None or not (voice_client.is_playing() or voice_client.is_paused()):
            await interaction.response.send_message("No active track to skip.", ephemeral=True)
            return

        voice_client.stop()
        await interaction.response.send_message("Skipped current track.", ephemeral=True)

    @music.sub_command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild is None or interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        state = self._state_for(interaction.guild_id)
        state.queue.clear()
        state.now_playing = None

        voice_client = interaction.guild.voice_client
        if voice_client is not None and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()

        await interaction.response.send_message("Stopped playback and cleared queue.", ephemeral=True)

    @music.sub_command(name="queue", description="Show upcoming tracks")
    async def queue(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        state = self._state_for(interaction.guild_id)
        if not state.queue and state.now_playing is None:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return

        lines: list[str] = []
        if state.now_playing is not None:
            lines.append(f"Now playing: `{state.now_playing.title}`")
        for index, track in enumerate(state.queue[:10], start=1):
            lines.append(f"`{index}.` {track.title}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    @music.sub_command(name="volume", description="Set playback volume percent")
    async def volume(
        self,
        interaction: ApplicationCommandInteraction,
        percent: int = commands.Param(default=50, ge=1, le=200),
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        state = self._state_for(interaction.guild_id)
        state.volume = percent / 100

        voice_client = interaction.guild.voice_client if interaction.guild is not None else None
        if voice_client is not None and voice_client.source is not None:
            voice_source = cast(disnake.PCMVolumeTransformer, voice_client.source)
            voice_source.volume = state.volume

        await interaction.response.send_message(
            f"Volume set to `{percent}%`.",
            ephemeral=True,
        )

    @music.sub_command(name="nowplaying", description="Show current track")
    async def nowplaying(self, interaction: ApplicationCommandInteraction) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True,
            )
            return

        state = self._state_for(interaction.guild_id)
        if state.now_playing is None:
            await interaction.response.send_message("No track is currently playing.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Now playing: `{state.now_playing.title}`",
            ephemeral=True,
        )


def setup(bot: commands.InteractionBot) -> None:
    bridge = cast(Any, bot).bridge
    bot.add_cog(MusicCog(bot=bot, session_factory=bridge.session_factory))
