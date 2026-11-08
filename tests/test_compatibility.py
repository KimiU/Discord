"""Offline checks of the installed Discord and music dependency stack."""
import asyncio
import importlib.metadata
from unittest.mock import patch

import discord
import discord.ext.commands
import discord.voice_client
import yt_dlp

from main import EXTENSIONS, NlaBot
from manager.config import Config


def test_extensions_load_and_unload_without_discord_connection(tmp_path):
    """Exercise real Cog registration and cleanup against the installed discord.py."""
    async def exercise():
        bot = NlaBot(Config(
            token="offline.test.token",
            data_dir=str(tmp_path / "users"),
            redirect_rules_file=str(tmp_path / "redirects.json"),
        ))
        async with bot:
            await bot.setup_hook()
            assert set(EXTENSIONS) == set(bot.extensions)
            for command in ("level", "leaderboard", "play", "clear", "redirect"):
                assert bot.get_command(command) is not None
            assert bot.intents.members
            assert bot.intents.message_content
            assert bot.intents.voice_states
        assert not bot.extensions

    asyncio.run(exercise())


def test_voice_dependencies_include_encrypted_voice_support():
    """A plain discord.py install can import successfully but cannot join today's voice calls."""
    assert discord.voice_client.has_nacl
    assert discord.voice_client.has_dave
    assert importlib.metadata.version("davey")


def test_youtube_dependencies_supply_solver_and_local_runtime():
    """The venv must work even when its Scripts directory isn't on the service account's PATH."""
    assert importlib.metadata.version("yt-dlp-ejs")
    with patch.dict("os.environ", {"PATH": ""}):
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            runtime = ydl._js_runtimes["deno"].info
    assert runtime is not None
    assert runtime.supported


def _start(tmp_path, **config):
    async def exercise():
        bot = NlaBot(Config(token="offline.test.token", data_dir=str(tmp_path / "users"),
                            redirect_rules_file=str(tmp_path / "redirects.json"), **config))
        async with bot:
            await bot.setup_hook()
            return bot, set(bot.extensions)
    return asyncio.run(exercise())


def test_broken_optional_feature_does_not_take_voice_tracking_offline(tmp_path):
    (tmp_path / "redirects.json").write_text('{"version": 1, "guilds": {"1": {"enabled": true}}}')
    bot, loaded = _start(tmp_path)
    assert "events.tracker" in loaded and "commands.level" in loaded
    assert "commands.redirect" not in loaded
    assert set(bot.failed_extensions) == {"commands.redirect"}


def test_broken_core_feature_still_stops_startup(tmp_path):
    original = NlaBot.add_cog

    async def add_cog(self, cog, **kwargs):
        if type(cog).__name__ == "Tracker":
            raise RuntimeError("boom")
        return await original(self, cog, **kwargs)

    with patch.object(NlaBot, "add_cog", add_cog):
        try:
            _start(tmp_path)
        except discord.ext.commands.ExtensionFailed as exc:
            assert exc.name == "events.tracker"
        else:
            raise AssertionError("a broken voice tracker must not start silently")


def test_bot_text_can_never_ping_everyone_or_roles(tmp_path):
    bot = NlaBot(Config(token="offline.test.token", data_dir=str(tmp_path / "users")))
    assert bot.allowed_mentions.everyone is False
    assert bot.allowed_mentions.roles is False
