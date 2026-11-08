"""Redirect behavior with Discord objects mocked; no token or server is needed."""
import asyncio
import importlib
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from commands.redirect import Redirect
from manager.config import Config
from manager.redirects import RedirectRule, RedirectStore


def run(awaitable):
    return asyncio.run(awaitable)


def config(tmp_path, **changes):
    return Config(token="offline", redirect_rules_file=str(tmp_path / "redirects.json"),
                  nettiauto_channel_id=20, code_channel_id=30, **changes)


def permissions(**changes):
    values = dict(view_channel=True, send_messages=True, embed_links=True,
                  attach_files=True, manage_messages=True, read_message_history=True)
    values.update(changes)
    return SimpleNamespace(**values)


def channel(channel_id, guild, *, kind=discord.TextChannel, **changes):
    result = MagicMock(spec=kind)
    result.id = channel_id
    result.name = f"channel-{channel_id}"
    result.mention = f"<#{channel_id}>"
    result.guild = guild
    result.parent_id = None
    result.overwrites = {}
    result.permissions_for.return_value = permissions(**changes)
    result.is_nsfw.return_value = False
    if kind is discord.Thread:
        result.is_private.return_value = False
    result.send = AsyncMock()
    result.fetch_message = AsyncMock()
    return result


@pytest.fixture
def app(tmp_path):
    guild = SimpleNamespace(id=1, me=object(), default_role=object(), filesize_limit=10_000_000)
    source = channel(10, guild)
    target = channel(20, guild)
    code_target = channel(30, guild)
    channels = {c.id: c for c in (source, target, code_target)}
    bot = SimpleNamespace(config=config(tmp_path), get_channel=channels.get)
    cog = Redirect(bot)
    author = SimpleNamespace(id=100, bot=False, display_name="Friend",
                             display_avatar=SimpleNamespace(url="https://example.com/avatar.png"))

    def message(content="Look: https://www.nettiauto.com/Car/ABC?Key=MiXeD", **changes):
        values = dict(id=123, guild=guild, channel=source, author=author,
                      webhook_id=None, content=content, attachments=[], stickers=[],
                      reference=None, components=[], poll=None, edited_at=None,
                      jump_url="https://discord.com/channels/1/10/123",
                      reply=AsyncMock(), delete=AsyncMock())
        values.update(changes)
        result = SimpleNamespace(**values)
        result.channel.fetch_message.return_value = result
        return result

    return SimpleNamespace(cog=cog, bot=bot, guild=guild, author=author,
                           source=source, target=target, code_target=code_target,
                           channels=channels, message=message)


def assert_no_mentions(kwargs):
    assert kwargs["allowed_mentions"].to_dict() == {"parse": []}


def test_default_suggestion_keeps_original_case_and_attachments(app):
    original = "Look @everyone: https://nettiauto.com/Car/ABC?Key=MiXeD"
    attachment = SimpleNamespace(url="https://example.com/photo.png")
    message = app.message(original, attachments=[attachment])
    run(app.cog.on_message(message))
    assert message.content == original
    assert message.attachments == [attachment]
    message.delete.assert_not_awaited()
    app.target.send.assert_not_awaited()
    message.reply.assert_awaited_once()
    assert app.target.mention in message.reply.call_args.args[0]
    assert message.reply.call_args.kwargs["mention_author"] is False
    assert_no_mentions(message.reply.call_args.kwargs)


def test_copy_preserves_text_case_and_suppresses_mentions(app):
    app.cog.store.update(1, mode="copy")
    original = "@everyone <@12345> https://nettiauto.com/Car/ABC?Key=MiXeD"
    message = app.message(original)
    run(app.cog.on_message(message))
    app.target.send.assert_awaited_once()
    kwargs = app.target.send.call_args.kwargs
    assert kwargs["content"] == original
    assert message.jump_url in kwargs["embed"].description
    assert_no_mentions(kwargs)
    message.delete.assert_not_awaited()
    message.reply.assert_not_awaited()


def test_rule_mode_overrides_default_and_copy_uploads_spoiler_attachment(app):
    app.cog.store.put_rule(1, RedirectRule("nettix", 20, "nettix", mode="copy"))
    file = MagicMock()
    attachment = SimpleNamespace(id=777, size=100, is_spoiler=lambda: True,
                                 to_file=AsyncMock(return_value=file))
    message = app.message(attachments=[attachment])
    run(app.cog.on_message(message))
    assert app.target.send.call_args.kwargs["files"] == [file]
    attachment.to_file.assert_awaited_once_with(spoiler=True)
    file.close.assert_called_once()
    message.delete.assert_not_awaited()


def test_move_uploads_every_attachment_before_deleting_and_closes_files(app):
    app.cog.store.update(1, mode="move")
    events = []
    files = [MagicMock(name=f"file-{i}") for i in range(3)]
    attachments = []
    for i, file in enumerate(files):
        async def download(*, spoiler, index=i, downloaded=file):
            assert spoiler is False
            events.append(f"download-{index}")
            return downloaded
        attachments.append(SimpleNamespace(id=200 + i, size=100, is_spoiler=lambda: False,
                                           to_file=AsyncMock(side_effect=download)))

    async def send(**kwargs):
        assert kwargs["files"] == files
        assert kwargs["content"] == message.content
        assert_no_mentions(kwargs)
        events.append("sent")

    async def delete():
        events.append("deleted")

    app.target.send.side_effect = send
    message = app.message(attachments=attachments, delete=AsyncMock(side_effect=delete))
    run(app.cog.on_message(message))
    assert events == ["download-0", "download-1", "download-2", "sent", "deleted"]
    for file in files:
        file.close.assert_called_once()


@pytest.mark.parametrize("failure", ["attachment", "send"])
def test_move_failure_never_deletes_original_or_uses_cooldown(app, failure):
    app.cog.store.update(1, mode="move")
    file = MagicMock()
    attachments = [SimpleNamespace(id=1, size=1, is_spoiler=lambda: False, to_file=AsyncMock(return_value=file))]
    if failure == "attachment":
        attachments.append(SimpleNamespace(id=2, size=1, is_spoiler=lambda: False,
                                           to_file=AsyncMock(side_effect=OSError("download failed"))))
    else:
        app.target.send.side_effect = discord.HTTPException(
            SimpleNamespace(status=500, reason="Server Error"), "upload failed")
    message = app.message(attachments=attachments)
    run(app.cog.on_message(message))
    message.delete.assert_not_awaited()
    assert app.cog._last == {}
    assert app.cog._locks == {}
    file.close.assert_called_once()
    if failure == "attachment":
        app.target.send.assert_not_awaited()


@pytest.mark.parametrize("condition", ["manage_messages", "read_message_history", "attachment_permission", "oversize", "reply", "poll"])
def test_unsafe_move_falls_back_to_suggestion(app, condition):
    app.cog.store.update(1, mode="move")
    message = app.message()
    if condition == "manage_messages":
        app.source.permissions_for.return_value.manage_messages = False
    elif condition == "read_message_history":
        app.source.permissions_for.return_value.read_message_history = False
    elif condition == "attachment_permission":
        app.target.permissions_for.return_value.attach_files = False
        message.attachments = [SimpleNamespace(size=1, to_file=AsyncMock())]
    elif condition == "oversize":
        message.attachments = [SimpleNamespace(size=app.guild.filesize_limit + 1, to_file=AsyncMock())]
    elif condition == "reply":
        message.reference = object()
    else:
        message.poll = object()
    run(app.cog.on_message(message))
    message.reply.assert_awaited_once()
    app.target.send.assert_not_awaited()
    message.delete.assert_not_awaited()
    for attachment in message.attachments:
        attachment.to_file.assert_not_awaited()


@pytest.mark.parametrize("change", ["content", "edited_at", "attachments", "fetch_failure"])
def test_move_keeps_source_if_edited_or_cannot_verify_it_after_sending(app, change):
    app.cog.store.update(1, mode="move")
    message = app.message()
    if change == "fetch_failure":
        app.source.fetch_message.side_effect = discord.HTTPException(
            SimpleNamespace(status=403, reason="Forbidden"), "cannot read source")
    else:
        changes = {"content": "Updated source", "edited_at": object(),
                   "attachments": [SimpleNamespace(id=999)]}
        app.source.fetch_message.return_value = replace_namespace(message, **{change: changes[change]})
    run(app.cog.on_message(message))
    app.target.send.assert_awaited_once()
    app.source.fetch_message.assert_awaited_once_with(message.id)
    message.delete.assert_not_awaited()


@pytest.mark.parametrize("condition", ["disabled", "rule_disabled", "bot", "webhook", "command", "dm", "other_guild", "target", "target_thread", "wrong_source"])
def test_ignored_messages_have_no_side_effects(app, condition):
    message = app.message()
    if condition == "disabled":
        app.cog.store.update(1, enabled=False)
    elif condition == "rule_disabled":
        app.cog.store.put_rule(1, replace(app.cog.store.rule(1, "nettix"), enabled=False))
    elif condition == "bot":
        message.author = SimpleNamespace(id=200, bot=True)
    elif condition == "webhook":
        message.webhook_id = 555
    elif condition == "command":
        message.content = "!redirect test https://nettiauto.com/ABC"
    elif condition == "dm":
        message.guild = None
    elif condition == "other_guild":
        app.target.guild = SimpleNamespace(id=999)
    elif condition == "target":
        message.channel = app.target
    elif condition == "target_thread":
        message.channel = channel(21, app.guild)
        message.channel.parent_id = app.target.id
    else:
        app.cog.store.put_rule(1, replace(app.cog.store.rule(1, "nettix"), source_channel_id=50))
    run(app.cog.on_message(message))
    message.reply.assert_not_awaited()
    message.delete.assert_not_awaited()
    app.target.send.assert_not_awaited()
    assert app.cog._last == {}


def test_source_rule_applies_to_child_thread(app):
    app.cog.store.put_rule(1, replace(app.cog.store.rule(1, "nettix"), source_channel_id=10))
    thread = channel(11, app.guild)
    thread.parent_id = 10
    message = app.message(channel=thread)
    run(app.cog.on_message(message))
    message.reply.assert_awaited_once()


@pytest.mark.parametrize("mode", ["copy", "move"])
@pytest.mark.parametrize("condition", ["restricted", "role_deny", "private_thread", "nsfw"])
def test_private_or_age_restricted_content_stays_in_source(app, mode, condition):
    app.cog.store.update(1, mode=mode)
    message = app.message()
    if condition == "restricted":
        app.source.permissions_for.side_effect = lambda member: permissions(
            view_channel=member is not app.guild.default_role)
    elif condition == "role_deny":
        app.source.overwrites = {object(): discord.PermissionOverwrite(view_channel=False)}
    elif condition == "private_thread":
        thread = channel(11, app.guild, kind=discord.Thread)
        thread.parent = app.source
        thread.parent_id = app.source.id
        thread.is_private.return_value = True
        message.channel = thread
    else:
        app.source.is_nsfw.return_value = True
    run(app.cog.on_message(message))
    message.reply.assert_awaited_once()
    app.target.send.assert_not_awaited()
    message.delete.assert_not_awaited()


@pytest.mark.parametrize("permission", ["view_channel", "send_messages"])
def test_does_not_route_to_channel_author_cannot_use(app, permission):
    app.target.permissions_for.side_effect = lambda member: permissions(
        **{permission: member is not app.author})
    message = app.message()
    run(app.cog.on_message(message))
    message.reply.assert_not_awaited()
    app.target.send.assert_not_awaited()
    message.delete.assert_not_awaited()


def test_cooldown_is_per_member_and_channel_and_expires(app, monkeypatch):
    clock = [1000.0]
    # Extension load/unload tests replace sys.modules entries. Patch the globals
    # belonging to this fixture's actual listener, without changing asyncio's clock.
    monkeypatch.setitem(Redirect.on_message.__globals__, "time",
                        SimpleNamespace(monotonic=lambda: clock[0]))
    first, repeat = app.message(), app.message()
    other_author = replace_namespace(app.author, id=101)
    other_member = app.message(author=other_author)
    other_channel = app.message(channel=channel(12, app.guild))
    run(app.cog.on_message(first))
    run(app.cog.on_message(repeat))
    run(app.cog.on_message(other_member))
    run(app.cog.on_message(other_channel))
    first.reply.assert_awaited_once()
    repeat.reply.assert_not_awaited()
    other_member.reply.assert_awaited_once()
    other_channel.reply.assert_awaited_once()
    clock[0] += app.bot.config.redirect_cooldown_seconds
    run(app.cog.on_message(repeat))
    repeat.reply.assert_awaited_once()


def replace_namespace(value, **changes):
    return SimpleNamespace(**(vars(value) | changes))


def test_simultaneous_burst_only_sends_one_suggestion(app):
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        first, second, third = app.message(), app.message(), app.message()

        async def held_reply(*args, **kwargs):
            entered.set()
            await release.wait()

        first.reply.side_effect = held_reply
        tasks = [asyncio.create_task(app.cog.on_message(first))]
        await entered.wait()
        tasks.extend(asyncio.create_task(app.cog.on_message(m)) for m in (second, third))
        await asyncio.sleep(0)  # both later messages arrive while the first is sending
        release.set()
        await asyncio.gather(*tasks)
        assert sum(m.reply.await_count for m in (first, second, third)) == 1
        assert app.cog._locks == {}

    run(scenario())


@pytest.mark.parametrize("change", ["disable", "remove", "mode"])
def test_queued_message_uses_current_configuration(app, change):
    app.cog.store.update(1, cooldown_seconds=0)

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        first, queued = app.message(), app.message()

        async def held_reply(*args, **kwargs):
            entered.set()
            await release.wait()

        first.reply.side_effect = held_reply
        first_task = asyncio.create_task(app.cog.on_message(first))
        await entered.wait()
        queued_task = asyncio.create_task(app.cog.on_message(queued))
        await asyncio.sleep(0)
        if change == "disable":
            app.cog.store.update(1, enabled=False)
        elif change == "remove":
            app.cog.store.remove_rule(1, "nettix")
        else:
            app.cog.store.update(1, mode="copy")
        release.set()
        await asyncio.gather(first_task, queued_task)
        first.reply.assert_awaited_once()
        queued.reply.assert_not_awaited()
        assert app.target.send.await_count == (1 if change == "mode" else 0)
        queued.delete.assert_not_awaited()
        assert app.cog._locks == {}

    run(scenario())


@pytest.mark.parametrize("content", [
    "https://nettiauto.com.evil.example/ABC",
    "https://evil.example/nettiauto.com",
    "https://nettiauto.com@evil.example/ABC",
    "https://fake-nettiauto.com/ABC",
    "https://evil.example/?next=https%3A%2F%2Fnettiauto.com",
])
def test_domain_matching_rejects_spoofed_domains(content):
    assert not RedirectRule("cars", 20, "domain", "nettiauto.com").matches(content)
    assert not RedirectRule("nettix", 20, "nettix").matches(content)


@pytest.mark.parametrize("content", [
    "https://nettiauto.com/ABC", "(HTTPS://WWW.NETTIAUTO.COM/Car/ABC).",
    "https://sub.nettiauto.com:443/ABC", "https://nettiauto.com./ABC",
])
def test_domain_matching_accepts_real_domain_and_subdomains(content):
    assert RedirectRule("cars", 20, "domain", "NETTIAUTO.COM").matches(content)


def test_store_persists_changes_and_removed_defaults_without_affecting_other_servers(tmp_path):
    cfg = config(tmp_path)
    store = RedirectStore(cfg)
    store.update(1, enabled=False, mode="copy", cooldown_seconds=42)
    store.remove_rule(1, "nettix")
    custom = RedirectRule("gaming", 99, "keyword", "Game Night", mode="move", source_channel_id=10)
    store.put_rule(1, custom)
    reloaded = RedirectStore(cfg)
    settings = reloaded.get(1)
    assert (settings.enabled, settings.mode, settings.cooldown_seconds) == (False, "copy", 42)
    assert reloaded.rule(1, "gaming") == custom
    assert [rule.name for rule in settings.rules] == ["code", "gaming"]
    assert [rule.name for rule in reloaded.get(2).rules] == ["nettix", "code"]
    assert reloaded.get(2).mode == "suggest"
    assert not (tmp_path / "redirects.json.tmp").exists()


@pytest.mark.parametrize("payload", [
    "not JSON", "[]", '{"version":2,"guilds":{}}',
    '{"version":1,"guilds":{"bad":{}}}',
    '{"version":1,"guilds":{"1":{"enabled":"yes","mode":"copy","cooldown_seconds":1,"rules":[]}}}',
    '{"version":1,"guilds":{"1":{"enabled":true,"mode":"delete","cooldown_seconds":1,"rules":[]}}}',
    '{"version":1,"guilds":{"1":{"enabled":true,"mode":"suggest","cooldown_seconds":-1,"rules":[]}}}',
])
def test_malformed_saved_config_fails_clearly_without_overwriting(tmp_path, payload):
    cfg = config(tmp_path)
    path = tmp_path / "redirects.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid redirect configuration"):
        RedirectStore(cfg)
    assert path.read_text(encoding="utf-8") == payload


@pytest.mark.parametrize("payload", ["{}", "not JSON", '[{"name":"incomplete"}]',
                                      '[{"name":"cars","target_channel_id":20,"match_type":"domain","pattern":"https://example.com/path"}]'])
def test_malformed_environment_rules_fail_before_creating_file(tmp_path, payload):
    cfg = config(tmp_path, redirect_rules_json=payload)
    with pytest.raises(ValueError, match="REDIRECT_RULES_JSON"):
        RedirectStore(cfg)
    assert not (tmp_path / "redirects.json").exists()


def test_custom_rule_replaces_environment_default_by_name(tmp_path):
    payload = json.dumps([dict(name="nettix", target_channel_id=44, match_type="domain",
                               pattern="example.com", mode="copy")])
    store = RedirectStore(config(tmp_path, redirect_rules_json=payload))
    assert len(store.get(1).rules) == 2
    assert store.rule(1, "nettix").target_channel_id == 44
    assert store.rule(1, "nettix").pattern == "example.com"


def test_management_commands_require_server_and_manage_server_permission(app):
    with pytest.raises(commands.NoPrivateMessage):
        run(app.cog.cog_check(SimpleNamespace(guild=None)))
    ctx = SimpleNamespace(guild=app.guild,
                          author=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=False)))
    with pytest.raises(commands.MissingPermissions) as error:
        run(app.cog.cog_check(ctx))
    assert error.value.missing_permissions == ["manage_guild"]
    ctx.author.guild_permissions.manage_guild = True
    assert run(app.cog.cog_check(ctx)) is True


@pytest.fixture
def environment(monkeypatch):
    module = importlib.import_module("manager.config")
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_TOKEN", "offline.fake.token")
    for key in ("REDIRECT_MODE", "REDIRECT_ENABLED", "REDIRECT_COOLDOWN_SECONDS",
                "REDIRECT_RULES_FILE", "REDIRECT_RULES_JSON", "NETTIAUTO_CHANNEL_ID",
                "CODE_CHANNEL_ID", "CHECKPOINT_SECONDS", "CROWD_THRESHOLD",
                "CROWD_COOLDOWN_SECONDS"):
        monkeypatch.delenv(key, raising=False)
    return module


def test_environment_redirect_defaults_and_custom_settings(environment, monkeypatch, tmp_path):
    defaults = environment.load_config()
    assert defaults.redirect_enabled is True
    assert defaults.redirect_mode == "suggest"
    assert defaults.redirect_cooldown_seconds == 300
    monkeypatch.setenv("REDIRECT_ENABLED", "off")
    monkeypatch.setenv("REDIRECT_MODE", " COPY ")
    monkeypatch.setenv("REDIRECT_COOLDOWN_SECONDS", "17")
    monkeypatch.setenv("REDIRECT_RULES_FILE", str(tmp_path / "custom.json"))
    monkeypatch.setenv("REDIRECT_RULES_JSON", "[]")
    loaded = environment.load_config()
    assert loaded.redirect_enabled is False
    assert loaded.redirect_mode == "copy"
    assert loaded.redirect_cooldown_seconds == 17
    assert loaded.redirect_rules_file == str(tmp_path / "custom.json")


@pytest.mark.parametrize("key,value", [
    ("REDIRECT_MODE", "delete"), ("REDIRECT_COOLDOWN_SECONDS", "-1"),
    ("REDIRECT_COOLDOWN_SECONDS", "86401"), ("REDIRECT_COOLDOWN_SECONDS", "not-a-number"),
])
def test_invalid_environment_settings_have_named_errors(environment, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit, match=key):
        environment.load_config()


def test_list_shows_rules_whose_channel_is_missing(app):
    app.cog.store.put_rule(1, RedirectRule("gone", 999, "keyword", "x"))
    ctx = SimpleNamespace(guild=app.guild, prefix="!", send=AsyncMock())
    run(app.cog._list(ctx))
    text = "".join(call.args[0] for call in ctx.send.await_args_list)
    assert "`gone`" in text and "999 ei löydy" in text
    assert "`nettix`" in text and "<#20>" in text
