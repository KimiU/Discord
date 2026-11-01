"""Moves Nettix (nettiauto etc.) links and code snippets to their own channels."""
import logging

import discord
from discord.ext import commands

from manager import unitils

log = logging.getLogger(__name__)


class Redirect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = bot.config
        self.rules = [
            (cfg.nettiauto_channel_id, unitils.isNettiauto),
            (cfg.code_channel_id, unitils.isCode),
        ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return
        if message.content.startswith(self.bot.config.prefix):
            return
        for target_id, matches in self.rules:
            if not target_id or message.channel.id == target_id:
                continue
            if not matches(message.content):
                continue
            target = self.bot.get_channel(target_id)
            if target is None:
                log.warning("Redirect channel %s not found", target_id)
                return
            embed = discord.Embed(
                title=f"Redirect from #{message.channel.name}",
                description=message.content[:4000],
                color=discord.Color.dark_red(),
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            try:
                await target.send(embed=embed)
                await message.delete()
            except discord.HTTPException as e:
                log.warning("Redirect failed: %s", e)
            return  # one redirect per message


async def setup(bot):
    await bot.add_cog(Redirect(bot))
