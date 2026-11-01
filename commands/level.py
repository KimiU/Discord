from typing import Optional

import discord
from discord.ext import commands

from manager import unitils
from manager.progression import progress_for


class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Näytä oma (tai toisen) taso ja aika äänikanavilla.")
    async def level(self, ctx, member: Optional[discord.Member] = None):
        member = member or ctx.author
        self.bot.tracker.checkpoint()  # flush in-progress time so numbers are up to date
        rec = self.bot.store.get(member.id, member.name)
        p = progress_for(rec.active_ms)
        rank = self.bot.store.rank_of(member.id)

        embed = discord.Embed(title="Progression", description=member.display_name, color=0x00ff00)
        embed.add_field(name=f"Level {p.level}", value=f"{p.xp}/{p.xp_needed} XP", inline=False)
        embed.add_field(name="Total time", value=unitils.formatDuration(rec.active_ms), inline=True)
        embed.add_field(name="AFK (not counted)", value=unitils.formatDuration(rec.afk_ms), inline=True)
        if rank:
            embed.add_field(name="Rank", value=f"#{rank}", inline=True)

        session = self.bot.tracker.current((ctx.guild.id, member.id)) if ctx.guild else None
        if session is not None:
            state = "active" if session.segment_active else "AFK – not counting"
            embed.add_field(
                name="Current call",
                value=f"{unitils.formatDuration(session.active_ms)} active, "
                      f"{unitils.formatDuration(session.afk_ms)} AFK ({state})",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(help="TOP 10 aktiivisinta äänikanavilla.")
    async def leaderboard(self, ctx):
        self.bot.tracker.checkpoint()
        embed = discord.Embed(
            title="Leaderboard",
            description="Top users by active time in voice channels (AFK excluded)",
            color=0x00ff00,
        )
        for i, rec in enumerate(self.bot.store.top(10), start=1):
            member = ctx.guild.get_member(rec.id) if ctx.guild else None
            name = member.display_name if member else (rec.username or str(rec.id))
            p = progress_for(rec.active_ms)
            embed.add_field(
                name=f"{i}. {name}",
                value=f"Level: {p.level} | Time: {unitils.formatDuration(rec.active_ms)}",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(help="(Admin) Aseta käyttäjän aktiivinen aika tunteina. Esim: !settime @nimi 120")
    @commands.has_permissions(administrator=True)
    async def settime(self, ctx, member: discord.Member, hours: float):
        if hours < 0:
            await ctx.send("Hours must be >= 0.")
            return
        self.bot.tracker.checkpoint()
        rec = self.bot.store.get(member.id, member.name)
        old = rec.active_ms
        rec.active_ms = int(hours * 3_600_000)
        self.bot.store.save(rec)
        await ctx.send(
            f"{member.display_name}: {unitils.formatDuration(old)} → {unitils.formatDuration(rec.active_ms)} "
            f"(level {progress_for(rec.active_ms).level})"
        )


async def setup(bot):
    await bot.add_cog(Level(bot))
