from discord.ext import commands


class Tracker(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Discord call time tracker command.
    @commands.command(pass_context=True)
    async def info(self, ctx):
        await ctx.send("Call time tracker on progress.")


# Setup cog for main.py.
def setup(client):
    client.add_cog(Tracker(client))
