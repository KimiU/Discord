from discord.ext import commands


class Basic(commands.Cog):
    def __init__(self, client):
        self.client = client


    # Send invite link
    @commands.command(pass_context=True)
    async def invite(self, ctx):
        await ctx.send("Tässä kutsulinkki: https://discord.gg/nlahoodz")


    # Flip the table
    @commands.command(pass_context=True)
    async def tableflip(self, ctx):
        await ctx.send("(╯°□°)╯︵ ┻━┻")
        await ctx.message.delete()


    # Clear the chat
    @commands.command(pass_context=True)
    async def clear(self, ctx, num):
        await ctx.send('Clearing messages...')
        await ctx.channel.purge(limit=int(num)+2)

    # Help
    @commands.command(pass_context=True)
    async def apua(self, ctx):
        await ctx.send('!apua = apua botin käyttöön \n!level = Näe oma läsnäolo äänikanavilla \n!invite = näytä invite linkki \n!leaderboard = TOP 10 nörtit \n!tableflip = Koitas ite..')

# Setup cog for main.py.
def setup(client):
    client.add_cog(Basic(client))
