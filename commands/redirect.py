"""Configurable channel suggestions, copies and opt-in moves."""
import asyncio
import logging
import time
from copy import copy
from dataclasses import replace
from typing import Optional

import discord
from discord.ext import commands

from manager.redirects import MODES, RedirectRule, RedirectStore

log = logging.getLogger(__name__)


class Redirect(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.store = RedirectStore(bot.config)
        self._last = {}
        self._locks = {}

    async def cog_check(self, ctx):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        if not ctx.author.guild_permissions.manage_guild:
            raise commands.MissingPermissions(["manage_guild"])
        return True

    def _match(self, message):
        for rule in self.store.get(message.guild.id).rules:
            if not rule.enabled:
                continue
            source_id = message.channel.id
            parent_id = getattr(message.channel, "parent_id", None)
            if rule.source_channel_id and rule.source_channel_id not in (source_id, parent_id):
                continue
            if rule.target_channel_id in (source_id, parent_id):
                continue
            target = self.bot.get_channel(rule.target_channel_id)
            if not isinstance(target, discord.TextChannel) or target.guild.id != message.guild.id:
                continue
            permissions = target.permissions_for(message.guild.me)
            author_permissions = target.permissions_for(message.author)
            if not (message.channel.permissions_for(message.guild.me).view_channel
                    and permissions.view_channel and author_permissions.view_channel
                    and author_permissions.send_messages):
                continue
            if rule.matches(message.content):
                return rule, target, permissions
        return None

    async def _suggest(self, message, target):
        await message.reply(f"Tämä aihe sopisi kanavalle {target.mention}. Jatketaanko siellä?",
                            mention_author=False, allowed_mentions=discord.AllowedMentions.none())

    async def _redirect(self, message, target, permissions, mode):
        if mode == "suggest":
            await self._suggest(message, target)
            return
        source_permissions = message.channel.permissions_for(message.guild.me)
        if not permissions.send_messages or not permissions.embed_links:
            await self._suggest(message, target)
            return
        # A public destination must not gain content from a restricted source.
        # Suggesting a channel is sufficient inside private conversations/threads.
        private_thread = isinstance(message.channel, discord.Thread) and message.channel.is_private()
        source_base = message.channel.parent if isinstance(message.channel, discord.Thread) else message.channel
        has_view_deny = any(overwrite.view_channel is False for overwrite in source_base.overwrites.values())
        if (private_thread or not message.channel.permissions_for(message.guild.default_role).view_channel
                or has_view_deny
                or (message.channel.is_nsfw() and not target.is_nsfw())):
            await self._suggest(message, target)
            return
        if (len(message.attachments) > 10
                or any(a.size > message.guild.filesize_limit for a in message.attachments)
                or (message.attachments and not permissions.attach_files)):
            await self._suggest(message, target)
            return
        # Moving must preserve everything. Leave rich/reply context in place if it
        # cannot be reproduced, or if an attachment cannot be uploaded at the destination.
        if mode == "move" and (
            not source_permissions.manage_messages or not source_permissions.read_message_history
            or message.stickers or message.reference
            or message.components or getattr(message, "poll", None)
            or len(message.content) > 2000
        ):
            await self._suggest(message, target)
            return
        embed = discord.Embed(title=f"#{message.channel.name}", color=discord.Color.dark_red(),
                              description=f"[Alkuperäinen viesti]({message.jump_url})")
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        original = (message.content, message.edited_at, tuple(a.id for a in message.attachments))
        files = []
        try:
            # Re-upload copies too: Discord's signed attachment URLs expire.
            # Append individually so a later failure still closes earlier files.
            for attachment in message.attachments:
                files.append(await attachment.to_file(spoiler=attachment.is_spoiler()))
            content = message.content or None
            if len(message.content) > 2000:
                if len(message.content) > 4000:
                    await self._suggest(message, target)
                    return
                embed.description = message.content
                embed.add_field(name="Lähde", value=message.jump_url)
                content = None
            await target.send(content=content, embed=embed, files=files,
                              allowed_mentions=discord.AllowedMentions.none())
        finally:
            for file in files:
                file.close()
        if mode == "move":
            try:
                latest = await message.channel.fetch_message(message.id)
                current = (latest.content, latest.edited_at, tuple(a.id for a in latest.attachments))
                if current != original:
                    log.info("Kept message %s because it was edited during redirect", message.id)
                    return
                await message.delete()
            except discord.HTTPException:
                log.warning("Copied message %s but could not delete its source", message.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.webhook_id or message.guild is None:
            return
        if message.content.startswith(self.bot.config.prefix):
            return
        settings = self.store.get(message.guild.id)
        if not settings.enabled:
            return
        match = self._match(message)
        if match is None:
            return
        rule, target, permissions = match
        key = (message.guild.id, message.channel.id, message.author.id)
        lock = self._locks.setdefault(key, asyncio.Lock())
        try:
            async with lock:
                settings = self.store.get(message.guild.id)
                match = self._match(message) if settings.enabled else None
                if match is None:
                    return
                rule, target, permissions = match
                now = time.monotonic()
                if now - self._last.get(key, float("-inf")) < settings.cooldown_seconds:
                    return
                try:
                    await self._redirect(message, target, permissions, rule.mode or settings.mode)
                except (discord.HTTPException, OSError) as exc:
                    log.warning("Redirect failed for message %s: %s", message.id, exc)
                    return
                self._last[key] = time.monotonic()
                cutoff = time.monotonic() - 86400
                self._last = {k: stamp for k, stamp in self._last.items() if stamp >= cutoff}
        finally:
            if not lock.locked() and not getattr(lock, "_waiters", None):
                self._locks.pop(key, None)

    async def _reply(self, ctx, text):
        await ctx.send(text, allowed_mentions=discord.AllowedMentions.none())

    @commands.group(invoke_without_command=True, help="(Manage Server) Hallitse uudelleenohjauksia.")
    async def redirect(self, ctx):
        await self._list(ctx)

    @redirect.command(name="list")
    async def list_rules(self, ctx):
        await self._list(ctx)

    async def _list(self, ctx):
        settings = self.store.get(ctx.guild.id)
        lines = [f"Redirect: {'on' if settings.enabled else 'off'} | {settings.mode} | "
                 f"cooldown {settings.cooldown_seconds}s"]
        for rule in settings.rules:
            target = self.bot.get_channel(rule.target_channel_id)
            if target is None or target.guild.id != ctx.guild.id:
                continue
            pattern = discord.utils.escape_markdown(rule.pattern)
            source = f"<#{rule.source_channel_id}>" if rule.source_channel_id else "all"
            lines.append(f"`{rule.name}`: {rule.match_type} {pattern} → {target.mention} | "
                         f"{rule.mode or settings.mode} | {'on' if rule.enabled else 'off'} | source: {source}")
        lines.append(f"Ohje: `{ctx.prefix}help redirect`")
        page = ""
        for line in lines:
            if len(page) + len(line) > 1900:
                await self._reply(ctx, page)
                page = ""
            page += line + "\n"
        await self._reply(ctx, page)

    @redirect.command(name="add", help="Lisää/päivitä: nimi #kohde domain|keyword|code|nettix [hakuehto].")
    async def add_rule(self, ctx, name: str, target: discord.TextChannel, match_type: str, *, pattern: str = ""):
        if target.guild.id != ctx.guild.id:
            raise commands.BadArgument("Kohdekanavan täytyy olla samalla palvelimella.")
        perms = target.permissions_for(ctx.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links):
            raise commands.BadArgument("Botti tarvitsee kohteessa View Channel, Send Messages ja Embed Links.")
        existing = next((r for r in self.store.get(ctx.guild.id).rules if r.name == name), None)
        try:
            rule = RedirectRule(name, target.id, match_type, pattern,
                                mode=existing.mode if existing else None,
                                source_channel_id=existing.source_channel_id if existing else None,
                                enabled=existing.enabled if existing else True)
            self.store.put_rule(ctx.guild.id, rule)
        except ValueError as exc:
            raise commands.BadArgument(str(exc)) from exc
        await self._reply(ctx, f"Tallennettu sääntö `{rule.name}` → {target.mention}.")

    @redirect.command(name="remove")
    async def remove_rule(self, ctx, name: str):
        try:
            self.store.remove_rule(ctx.guild.id, name)
        except ValueError as exc:
            raise commands.BadArgument(str(exc)) from exc
        await self._reply(ctx, "Sääntö poistettu.")

    @redirect.command(name="enable")
    async def enable(self, ctx):
        self.store.update(ctx.guild.id, enabled=True)
        await self._reply(ctx, "Uudelleenohjaukset käytössä.")

    @redirect.command(name="disable")
    async def disable(self, ctx):
        self.store.update(ctx.guild.id, enabled=False)
        await self._reply(ctx, "Uudelleenohjaukset pois käytöstä.")

    @redirect.command(name="mode")
    async def mode(self, ctx, mode: str):
        if mode not in MODES:
            raise commands.BadArgument("Valitse suggest, copy tai move.")
        self.store.update(ctx.guild.id, mode=mode)
        await self._reply(ctx, f"Oletustila: {mode}. Sääntökohtaiset asetukset säilyvät.")

    @redirect.command(name="cooldown")
    async def cooldown(self, ctx, seconds: int):
        if not 0 <= seconds <= 86400:
            raise commands.BadArgument("Valitse 0–86400 sekuntia.")
        self.store.update(ctx.guild.id, cooldown_seconds=seconds)
        await self._reply(ctx, f"Odotusaika: {seconds}s per käyttäjä ja kanava.")

    @redirect.command(name="source", help="Rajaa sääntö lähdekanavaan; ilman kanavaa rajaus poistuu.")
    async def source(self, ctx, name: str, channel: Optional[discord.TextChannel] = None):
        if channel is not None and channel.guild.id != ctx.guild.id:
            raise commands.BadArgument("Lähdekanavan täytyy olla samalla palvelimella.")
        await self._change_rule(ctx, name, source_channel_id=channel.id if channel else None)

    @redirect.command(name="rulemode", help="Säännön suggest|copy|move|default -tila.")
    async def rulemode(self, ctx, name: str, mode: str):
        if mode not in (*MODES, "default"):
            raise commands.BadArgument("Valitse suggest, copy, move tai default.")
        await self._change_rule(ctx, name, mode=None if mode == "default" else mode)

    @redirect.command(name="toggle", help="Kytke yksittäinen sääntö on/off.")
    async def toggle(self, ctx, name: str, enabled: bool):
        await self._change_rule(ctx, name, enabled=enabled)

    async def _change_rule(self, ctx, name, **changes):
        try:
            self.store.put_rule(ctx.guild.id, replace(self.store.rule(ctx.guild.id, name), **changes))
        except ValueError as exc:
            raise commands.BadArgument(str(exc)) from exc
        await self._reply(ctx, "Sääntö päivitetty ja tallennettu.")

    @redirect.command(name="test", help="Testaa sääntöjä lähettämättä tai poistamatta viestejä.")
    async def test_rule(self, ctx, *, text: str):
        message = copy(ctx.message)
        message.content = text
        match = self._match(message)
        settings = self.store.get(ctx.guild.id)
        if match:
            rule, target, _ = match
            await self._reply(ctx, f"Osuma: `{rule.name}` → {target.mention} | "
                              f"{rule.mode or settings.mode} | redirect {'on' if settings.enabled else 'off'}")
        else:
            await self._reply(ctx, "Ei osumaa tässä kanavassa.")


async def setup(bot):
    await bot.add_cog(Redirect(bot))
