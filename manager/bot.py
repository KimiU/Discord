import discord


# Sending embed message from bot
async def sendMsg(ctx, channel: discord.TextChannel, *msg):
    message = " ".join(msg)
    embed = discord.Embed(title="Redirect from {}".format(ctx.channel.name), color=discord.Color.dark_red())
    embed.add_field(name="{}".format(ctx.author), value="{}".format(message))

    await channel.send(embed=embed)

