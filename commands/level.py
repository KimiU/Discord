from discord.ext import commands
import discord

from manager import unitils
from manager.user import User


async def async_sort_users(users):
    return sorted(users, key=lambda x: x.getTime(), reverse=True)

class Level(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Leveling command.
    @commands.command(pass_context=True)
    async def level(self, ctx):

        user = User(ctx.message.author)

        lvl = user.getLevel()
        xp = user.getXP()
        max = user.getMaxXP()

        embed = discord.Embed(title=f"Progression", description=f"{ctx.message.author.display_name}", color=0x00ff00)
        
        embed.add_field(name=f"Level {lvl}", value=f"{xp}/{max} XP", inline=False)
        embed.add_field(name="Total time", value=f"{unitils.convertSeconds(user.getTime())}", inline=False)
        
        if user.getCurrentMillis() != 0:
            time = user.getCurrentCallTimeFormatted()
            embed.add_field(name="Current call duration", value=f"{time}", inline=False)
        
        await ctx.send(embed=embed)
        await ctx.message.delete()


    @commands.command()
    async def leaderboard(self, ctx):
        users = await User.get_all_users(self.client)
        sorted_users = await async_sort_users(users)
        #sorted_users = sorted(users, key=lambda x: x.getTime(), reverse=True)


        leaderboard_embed = discord.Embed(
            title="Leaderboard",
            description="Top users by total time spent in voice channels",
            color=0x00ff00,
        )

        for index, user in enumerate(sorted_users[:10], start=1):
            leaderboard_embed.add_field(
                name=f"{index}. {user.username}#{user.tag}",
                value=f"Level: {user.getLevel()} | Time: {user.getTimeFormatted()}",
                inline=False,
            )

        await ctx.send(embed=leaderboard_embed)
        await ctx.message.delete()

# Setup cog for main.py.
def setup(client):
    client.add_cog(Level(client))
