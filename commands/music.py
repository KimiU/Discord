"""Simple per-server music queue. Streams audio with yt-dlp + FFmpeg (no files on disk).

Requires FFmpeg on PATH. youtube_dl is dead; yt-dlp is its maintained fork.
"""
import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",  # lets `!play some song name` work, not only URLs
}
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    stream_url: str
    page_url: str


def _extract(query: str) -> Track:
    import yt_dlp  # imported lazily so the bot runs even if music isn't used

    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        info = ydl.extract_info(query, download=False)
    if "entries" in info:  # search result
        info = info["entries"][0]
    return Track(info.get("title", query), info["url"], info.get("webpage_url", query))


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues: Dict[int, Deque[Track]] = {}

    def _queue(self, guild_id: int) -> Deque[Track]:
        return self.queues.setdefault(guild_id, deque())

    def _play_next(self, guild: discord.Guild, text_channel):
        vc = guild.voice_client
        queue = self._queue(guild.id)
        if vc is None or not vc.is_connected() or not queue:
            return
        track = queue.popleft()

        def after(err):
            if err:
                log.warning("Playback error: %s", err)
            self.bot.loop.call_soon_threadsafe(self._play_next, guild, text_channel)

        vc.play(discord.FFmpegPCMAudio(track.stream_url, **FFMPEG_OPTS), after=after)
        asyncio.run_coroutine_threadsafe(text_channel.send(f"▶️ Nyt soi: **{track.title}**"), self.bot.loop)

    @commands.command(help="Soita URL tai hakusana. Liittyy omalle äänikanavallesi.")
    @commands.guild_only()
    async def play(self, ctx, *, query: str):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("Liity ensin äänikanavalle.")
            return
        channel = ctx.author.voice.channel
        vc = ctx.voice_client
        if vc is None:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        async with ctx.typing():
            try:
                track = await asyncio.to_thread(_extract, query)
            except Exception as e:
                await ctx.send(f"En löytänyt/voinut soittaa: {e}")
                return

        self._queue(ctx.guild.id).append(track)
        if vc.is_playing() or vc.is_paused():
            await ctx.send(f"Jonossa: **{track.title}**")
        else:
            self._play_next(ctx.guild, ctx.channel)

    @commands.command(help="Ohita nykyinen kappale.")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()  # `after` callback starts the next track
        else:
            await ctx.send("Mikään ei soi.")

    @commands.command(help="Näytä jono.")
    async def queue(self, ctx):
        q = self._queue(ctx.guild.id) if ctx.guild else []
        if not q:
            await ctx.send("Jono on tyhjä.")
            return
        await ctx.send("\n".join(f"{i}. {t.title}" for i, t in enumerate(list(q)[:10], start=1)))

    @commands.command(help="Tauko.")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
        else:
            await ctx.send("Currently no audio is playing.")

    @commands.command(help="Jatka.")
    async def resume(self, ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
        else:
            await ctx.send("The audio is not paused.")

    @commands.command(help="Pysäytä ja tyhjennä jono.")
    async def stop(self, ctx):
        if ctx.guild:
            self._queue(ctx.guild.id).clear()
        if ctx.voice_client:
            ctx.voice_client.stop()

    @commands.command(help="Botti poistuu äänikanavalta.")
    async def leave(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_connected():
            self._queue(ctx.guild.id).clear()
            await ctx.voice_client.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")


async def setup(bot):
    await bot.add_cog(Music(bot))
