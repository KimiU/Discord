import logging
import time
from typing import Dict, Optional

import discord
from discord.ext import commands, tasks

from manager import unitils
from manager.progression import progress_for
from manager.tracking import SessionSummary, VoiceSnapshot

log = logging.getLogger(__name__)


def humans_in(channel) -> int:
    return sum(1 for m in channel.members if not m.bot)


def snapshot(member: discord.Member) -> Optional[VoiceSnapshot]:
    vs = member.voice
    if vs is None or vs.channel is None:
        return None
    afk_channel = member.guild.afk_channel
    return VoiceSnapshot(
        channel_id=vs.channel.id,
        is_afk_channel=afk_channel is not None and vs.channel.id == afk_channel.id,
        deafened=bool(vs.self_deaf or vs.deaf),
        muted=bool(vs.self_mute or vs.mute),
        humans_in_channel=humans_in(vs.channel),
    )


def key_for(member: discord.Member):
    return (member.guild.id, member.id)


class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = bot.config
        self.tracker = bot.tracker
        self._crowd_announced: Dict[int, float] = {}

    async def cog_load(self):
        self.checkpoint_loop.change_interval(seconds=self.cfg.checkpoint_seconds)
        self.checkpoint_loop.start()

    async def cog_unload(self):
        self.checkpoint_loop.cancel()
        self.tracker.end_all()

    @tasks.loop(seconds=300)
    async def checkpoint_loop(self):
        self.tracker.checkpoint()

    def _track(self, member: discord.Member) -> Optional[SessionSummary]:
        if member.bot:
            return None
        snap = snapshot(member)
        if snap is not None and not self.tracker.is_tracking(key_for(member)):
            # Refresh the stored username when a session starts.
            self.bot.store.get(member.id, member.name)
        return self.tracker.update(key_for(member), member.id, snap)

    @commands.Cog.listener()
    async def on_ready(self):
        """Pick up everyone already in voice (bot (re)started while people were in calls)."""
        present = set()
        for guild in self.bot.guilds:
            for channel in guild.voice_channels + list(guild.stage_channels):
                for member in channel.members:
                    if not member.bot:
                        present.add(key_for(member))
                        self._track(member)
        # Sessions for people who left while the gateway was disconnected.
        for key in [k for k in self.tracker.sessions if k not in present]:
            s = self.tracker.sessions[key]
            self.tracker.update(key, s.user_id, None)
        log.info("Voice tracking synced: %d active session(s)", len(self.tracker.sessions))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        if member.bot:
            return

        summary = self._track(member)

        # Others' state can depend on headcount (count_alone=False), so re-evaluate them too.
        if not self.cfg.rules.count_alone:
            for channel in {before.channel, after.channel} - {None}:
                for other in channel.members:
                    if other.id != member.id:
                        self._track(other)

        if summary is not None:
            await self._post_summary(member, summary)

        if after.channel is not None and before.channel != after.channel:
            await self._maybe_announce_crowd(member.guild, after.channel)

    async def _post_summary(self, member: discord.Member, summary: SessionSummary):
        channel = discord.utils.get(member.guild.text_channels, name=self.cfg.progression_channel)
        if channel is None:
            return
        rec = self.bot.store.get(member.id)
        now = progress_for(rec.active_ms)
        before = progress_for(rec.active_ms - summary.active_ms)
        earned = now.total_xp - before.total_xp

        embed = discord.Embed(title="Progression update", description=member.display_name, color=0x00ff00)
        embed.add_field(name="Call duration", value=unitils.formatDuration(summary.duration_ms), inline=True)
        embed.add_field(name="Active time", value=unitils.formatDuration(summary.active_ms), inline=True)
        embed.add_field(name="AFK (not counted)", value=unitils.formatDuration(summary.afk_ms), inline=True)
        embed.add_field(name="Earned XP", value=f"{earned} XP", inline=True)
        embed.add_field(name="Total time", value=unitils.formatDuration(rec.active_ms), inline=True)
        embed.add_field(name="Progression", value=f"Level: {now.level}\nXP: {now.xp}/{now.xp_needed}", inline=False)
        if now.level > before.level:
            embed.add_field(name="🎉 Level up!", value=f"{before.level} → {now.level}", inline=False)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            log.warning("Could not post progression update: %s", e)

    async def _maybe_announce_crowd(self, guild: discord.Guild, voice_channel):
        count = humans_in(voice_channel)
        if count < self.cfg.crowd_threshold:
            return
        last = self._crowd_announced.get(voice_channel.id, 0)
        if time.monotonic() - last < self.cfg.crowd_cooldown_seconds:
            return
        channel = discord.utils.get(guild.text_channels, name=self.cfg.announce_channel)
        if channel is None:
            return
        self._crowd_announced[voice_channel.id] = time.monotonic()
        await channel.send(
            f"{voice_channel.name}:ssa on nyt enemmän porukkaa kun porijazzeilla! (Eli siis {count})"
        )


async def setup(bot):
    await bot.add_cog(Tracker(bot))
