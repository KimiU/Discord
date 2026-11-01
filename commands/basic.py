from discord.ext import commands


class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Näytä invite-linkki.")
    async def invite(self, ctx):
        await ctx.send(f"Tässä kutsulinkki: {self.bot.config.invite_url}")

    @commands.command(help="Koitas ite..")
    async def tableflip(self, ctx):
        await ctx.send("(╯°□°)╯︵ ┻━┻")
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command(help="(Mod) Poista N viimeisintä viestiä (max 100).")
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def clear(self, ctx, num: int):
        num = max(1, min(num, 100))
        deleted = await ctx.channel.purge(limit=num + 1)  # +1 = the command message itself
        await ctx.send(f"Poistettu {len(deleted) - 1} viestiä.", delete_after=5)

    @commands.command(help="Apua botin käyttöön.")
    async def apua(self, ctx):
        p = self.bot.config.prefix
        await ctx.send(
            f"{p}apua = apua botin käyttöön\n"
            f"{p}level [@nimi] = taso ja aika äänikanavilla (AFK ei lasketa)\n"
            f"{p}leaderboard = TOP 10 nörtit\n"
            f"{p}invite = näytä invite linkki\n"
            f"{p}play <url/haku>, {p}skip, {p}pause, {p}resume, {p}stop, {p}leave = musiikki\n"
            f"{p}tableflip = Koitas ite.."
        )


async def setup(bot):
    await bot.add_cog(Basic(bot))
