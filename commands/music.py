import os

import youtube_dl
from discord.ext import commands
import discord


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client

    # Music commands - play music from url
    @commands.command(pass_context=True)
    async def play(self, ctx, url: str):
        song_there = os.path.isfile("song.mp3")
        try:
            if song_there:
                os.remove("song.mp3")
        except PermissionError:
            await ctx.send("Wait for the current playing music to end or use the 'stop' command")
            return

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for file in os.listdir("./"):
            if file.endswith(".mp3"):
                os.rename(file, "song.mp3")

        voiceChannel = discord.utils.get(ctx.guild.voice_channels, name='General')
        await voiceChannel.connect()
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        voice.play(discord.FFmpegPCMAudio("./song.mp3"))

    # Music commands - disconnect bot from channel.
    @commands.command(pass_context=True)
    async def leave(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_connected():
            await voice.disconnect()
        else:
            await ctx.send("The bot is not connected to a voice channel.")

    # Music commands - pause the music bot is currently playing.
    @commands.command(pass_context=True)
    async def pause(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
        else:
            await ctx.send("Currently no audio is playing.")

    # Music commands - resume the music bot was playing.
    @commands.command(pass_context=True)
    async def resume(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
        else:
            await ctx.send("The audio is not paused.")

    # Music commands - stop playing current song.
    @commands.command(pass_context=True)
    async def stop(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        voice.stop()


# Setup cog for main.py.
def setup(client):
    client.add_cog(Music(client))
