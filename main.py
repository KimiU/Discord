import logging
import os

# Verify TLS certificates with the operating system's trust store (Windows certificate store,
# macOS keychain). Plain Python only trusts roots already present in the store, which fails on
# fresh Windows servers with CERTIFICATE_VERIFY_FAILED. Must run before discord/aiohttp import,
# because aiohttp builds its SSL contexts at import time.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import discord  # noqa: E402
from discord.ext import commands  # noqa: E402

from manager.config import Config, load_config
from manager.storage import UserStore
from manager.tracking import SessionTracker

EXTENSIONS = (
    "commands.basic",
    "commands.level",
    "commands.music",
    "commands.redirect",
    "events.tracker",
)

log = logging.getLogger("nlabot")


class NlaBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.members = True          # privileged: enable "Server Members Intent" in the dev portal
        intents.message_content = True  # privileged: enable "Message Content Intent" in the dev portal
        intents.voice_states = True
        super().__init__(command_prefix=config.prefix, intents=intents)

        self.config = config
        self.store = UserStore(config.data_dir)
        self.tracker = SessionTracker(config.rules, self._credit)

    def _credit(self, user_id: int, active_ms: int, afk_ms: int) -> None:
        rec = self.store.get(user_id)
        rec.active_ms += active_ms
        rec.afk_ms += afk_ms
        self.store.save(rec)

    def reset_all_time(self) -> int:
        """Zero everyone's active/AFK time. Calls in progress keep running and count from now."""
        self.tracker.checkpoint()  # close open segments first, so pre-reset time isn't credited after
        return self.store.reset_all()

    async def setup_hook(self):
        for ext in EXTENSIONS:
            await self.load_extension(ext)

    async def on_ready(self):
        for guild in self.guilds:
            log.info("Server - %s (name: %s)", guild.id, guild.name)
        log.info("%s is in %d guild(s).", self.user, len(self.guilds))

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
            await ctx.send("Ei oikeuksia tähän komentoon.")
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send(f"Väärät parametrit. Käyttö: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("Tämä komento toimii vain palvelimella.")
        else:
            log.error("Command %s failed", ctx.command, exc_info=error)
            await ctx.send("Jokin meni pieleen.")

    async def close(self):
        # Credit everyone's in-progress time before shutting down.
        self.tracker.end_all()
        await super().close()


def main():
    config = load_config()
    # Lets the Windows scripts stop/restart exactly this process.
    with open("bot.pid", "w") as f:
        f.write(str(os.getpid()))
    bot = NlaBot(config)
    bot.run(config.token, log_level=logging.INFO, root_logger=True)


if __name__ == "__main__":
    main()
