"""Validated redirect rules and atomic, per-server configuration storage."""
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from manager import unitils

MODES = ("suggest", "copy", "move")
MATCH_TYPES = ("domain", "keyword", "code", "nettix")
MAX_RULES = 100
_URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


def _id(value):
    return type(value) is int and 0 < value < 2 ** 64


def _host(value):
    value = value.strip().rstrip(".").lower()
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Use a domain such as example.com.") from exc
    if len(value) > 253 or not re.fullmatch(
        r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value
    ) or any(not part or len(part) > 63 or part.startswith("-") or part.endswith("-")
             for part in value.split(".")):
        raise ValueError("Use a domain such as example.com, without a URL path.")
    return value


def domains_in(content):
    for match in _URL.finditer(content):
        try:
            host = urlsplit(match.group().rstrip(".,;!?)\"]}")).hostname
            if host:
                yield _host(host)
        except ValueError:
            continue


@dataclass(frozen=True)
class RedirectRule:
    name: str
    target_channel_id: int
    match_type: str
    pattern: str = ""
    mode: str | None = None
    source_channel_id: int | None = None
    enabled: bool = True

    def __post_init__(self):
        if not isinstance(self.name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", self.name):
            raise ValueError("Rule names use 1-32 lowercase letters, numbers, _ or -, starting with a letter.")
        if not _id(self.target_channel_id) or (
            self.source_channel_id is not None and not _id(self.source_channel_id)
        ):
            raise ValueError("Channel IDs must be positive integers.")
        if self.match_type not in MATCH_TYPES:
            raise ValueError("Match type must be domain, keyword, code, or nettix.")
        if self.mode is not None and self.mode not in MODES:
            raise ValueError("Mode must be suggest, copy, or move.")
        if type(self.enabled) is not bool or not isinstance(self.pattern, str):
            raise ValueError("Invalid rule enabled flag or pattern.")
        if self.match_type in ("keyword", "domain") and not self.pattern.strip():
            raise ValueError("Domain and keyword rules need a pattern.")
        if len(self.pattern) > 253:
            raise ValueError("Patterns must be at most 253 characters.")
        if self.match_type == "domain":
            object.__setattr__(self, "pattern", _host(self.pattern))
        if self.match_type in ("code", "nettix") and self.pattern:
            raise ValueError("Code and nettix rules do not take a pattern.")

    def matches(self, content):
        if self.match_type == "keyword":
            return self.pattern.casefold() in content.casefold()
        if self.match_type == "code":
            return unitils.isCode(content)
        domains = (self.pattern,) if self.match_type == "domain" else tuple(
            name + ".com" for name in unitils.NETTIX_SITES
        )
        return any(host == domain or host.endswith("." + domain)
                   for host in domains_in(content) for domain in domains)


def parse_rules(items):
    if not isinstance(items, list) or len(items) > MAX_RULES:
        raise ValueError(f"Redirect rules must be a JSON array of at most {MAX_RULES} rules.")
    try:
        rules = tuple(RedirectRule(**item) for item in items)
    except (TypeError, KeyError) as exc:
        raise ValueError("Invalid redirect rule fields.") from exc
    if len({rule.name for rule in rules}) != len(rules):
        raise ValueError("Redirect rule names must be unique.")
    return rules


@dataclass(frozen=True)
class RedirectSettings:
    enabled: bool
    mode: str
    cooldown_seconds: int
    rules: tuple[RedirectRule, ...]

    def __post_init__(self):
        if type(self.enabled) is not bool or self.mode not in MODES:
            raise ValueError("Invalid redirect enabled flag or mode.")
        if type(self.cooldown_seconds) is not int or not 0 <= self.cooldown_seconds <= 86400:
            raise ValueError("Cooldown must be between 0 and 86400 seconds.")


class RedirectStore:
    def __init__(self, config):
        self.path = Path(config.redirect_rules_file)
        defaults = []
        for name, channel_id, match_type in (
            ("nettix", config.nettiauto_channel_id, "nettix"),
            ("code", config.code_channel_id, "code"),
        ):
            if channel_id:
                defaults.append(RedirectRule(name, channel_id, match_type))
        try:
            custom = parse_rules(json.loads(config.redirect_rules_json))
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid REDIRECT_RULES_JSON: {exc}") from exc
        by_name = {rule.name: rule for rule in defaults}
        by_name.update((rule.name, rule) for rule in custom)
        if len(by_name) > MAX_RULES:
            raise ValueError(f"At most {MAX_RULES} redirect rules are allowed, including built-in defaults.")
        self.defaults = RedirectSettings(config.redirect_enabled, config.redirect_mode,
                                         config.redirect_cooldown_seconds, tuple(by_name.values()))
        self._guilds = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if data["version"] != 1 or not isinstance(data["guilds"], dict):
                    raise ValueError("Unsupported redirect configuration format.")
                for guild_id, values in data["guilds"].items():
                    if not guild_id.isdigit() or not _id(int(guild_id)):
                        raise ValueError("Invalid server ID.")
                    self._guilds[int(guild_id)] = RedirectSettings(
                        values["enabled"], values["mode"], values["cooldown_seconds"],
                        parse_rules(values["rules"]),
                    )
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise ValueError(f"Invalid redirect configuration in {self.path}: {exc}") from exc

    def get(self, guild_id):
        return self._guilds.get(guild_id, self.defaults)

    def update(self, guild_id, **changes):
        updated = replace(self.get(guild_id), **changes)
        parse_rules([asdict(rule) for rule in updated.rules])
        guilds = {**self._guilds, guild_id: updated}
        data = {"version": 1, "guilds": {str(key): asdict(value) for key, value in guilds.items()}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)
        self._guilds = guilds  # publish only after a successful write

    def put_rule(self, guild_id, rule):
        rules = list(self.get(guild_id).rules)
        for index, existing in enumerate(rules):
            if existing.name == rule.name:
                rules[index] = rule
                break
        else:
            rules.append(rule)
        self.update(guild_id, rules=tuple(rules))

    def rule(self, guild_id, name):
        for rule in self.get(guild_id).rules:
            if rule.name == name:
                return rule
        raise ValueError(f"Unknown redirect rule: {name}")

    def remove_rule(self, guild_id, name):
        self.rule(guild_id, name)
        self.update(guild_id, rules=tuple(rule for rule in self.get(guild_id).rules if rule.name != name))
