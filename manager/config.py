"""Runtime configuration, read from environment variables (or a .env file).

Never put the bot token in source code. Copy `.env.example` to `.env` and fill it in.
"""
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: Optional[int] = None) -> Optional[int]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class TrackingRules:
    """Decides which voice states count as 'active' (i.e. earn time and XP)."""

    # Self-deafened / server-deafened users can't hear anyone: treat as AFK.
    count_deafened: bool = False
    # Muted users are often just listening, so they count by default.
    count_muted: bool = True
    # Sitting alone in a channel is the easiest way to farm time.
    count_alone: bool = True


@dataclass(frozen=True)
class Config:
    token: str
    prefix: str = "!"
    data_dir: str = "./data/users"
    rules: TrackingRules = TrackingRules()
    # How often in-progress sessions are flushed to disk, so a crash loses at most this much.
    checkpoint_seconds: int = 300
    progression_channel: str = "progression"
    announce_channel: str = "generalpopulation"
    crowd_threshold: int = 7
    crowd_cooldown_seconds: int = 1800
    nettiauto_channel_id: Optional[int] = None
    code_channel_id: Optional[int] = None
    invite_url: str = "https://discord.gg/nlahoodz"
    # Full path to ffmpeg(.exe) if it isn't on the PATH of the account running the bot.
    ffmpeg_path: str = "ffmpeg"
    redirect_enabled: bool = True
    redirect_mode: str = "suggest"
    redirect_cooldown_seconds: int = 300
    redirect_rules_file: str = "./data/redirects.json"
    redirect_rules_json: str = "[]"


def clean_token(raw: str) -> str:
    """Forgive common paste mistakes: surrounding quotes/whitespace and a 'Bot ' prefix."""
    token = raw.strip().strip('"\'').strip()
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def token_problem(token: str) -> Optional[str]:
    """Cheap shape check. Never include the token itself in the message (it ends up in logs)."""
    if token.isdigit():
        return ("it is only digits, so it's probably the Application ID. Use Developer Portal -> "
                "your app -> Bot -> Reset Token.")
    if token.count(".") != 2:
        return (f"a bot token has 3 parts separated by dots, this has {token.count('.') + 1}. "
                "You may have copied the OAuth2 Client Secret or Public Key instead of the Bot token "
                "(Developer Portal -> your app -> Bot -> Reset Token).")
    if any(c.isspace() for c in token):
        return "it contains spaces or line breaks; paste it again on a single line."
    return None


def load_config() -> Config:
    load_dotenv()
    token = clean_token(os.getenv("DISCORD_TOKEN", ""))
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token.")
    problem = token_problem(token)
    if problem:
        raise SystemExit(f"DISCORD_TOKEN looks wrong: {problem}")

    redirect_mode = os.getenv("REDIRECT_MODE", "suggest").strip().lower()
    if redirect_mode not in ("suggest", "copy", "move"):
        raise SystemExit("REDIRECT_MODE must be suggest, copy, or move.")
    try:
        cooldown = _int("REDIRECT_COOLDOWN_SECONDS", 300)
    except ValueError as exc:
        raise SystemExit("REDIRECT_COOLDOWN_SECONDS must be an integer between 0 and 86400.") from exc
    if not 0 <= cooldown <= 86400:
        raise SystemExit("REDIRECT_COOLDOWN_SECONDS must be between 0 and 86400.")

    return Config(
        token=token,
        prefix=os.getenv("COMMAND_PREFIX", "!"),
        data_dir=os.getenv("DATA_DIR", "./data/users"),
        rules=TrackingRules(
            count_deafened=_bool("COUNT_DEAFENED", False),
            count_muted=_bool("COUNT_MUTED", True),
            count_alone=_bool("COUNT_ALONE", True),
        ),
        checkpoint_seconds=_int("CHECKPOINT_SECONDS", 300),
        progression_channel=os.getenv("PROGRESSION_CHANNEL", "progression"),
        announce_channel=os.getenv("ANNOUNCE_CHANNEL", "generalpopulation"),
        crowd_threshold=_int("CROWD_THRESHOLD", 7),
        crowd_cooldown_seconds=_int("CROWD_COOLDOWN_SECONDS", 1800),
        nettiauto_channel_id=_int("NETTIAUTO_CHANNEL_ID"),
        code_channel_id=_int("CODE_CHANNEL_ID"),
        invite_url=os.getenv("INVITE_URL", "https://discord.gg/nlahoodz"),
        ffmpeg_path=os.getenv("FFMPEG_PATH", "").strip() or "ffmpeg",
        redirect_enabled=_bool("REDIRECT_ENABLED", True),
        redirect_mode=redirect_mode,
        redirect_cooldown_seconds=cooldown,
        redirect_rules_file=os.getenv("REDIRECT_RULES_FILE", "./data/redirects.json"),
        redirect_rules_json=os.getenv("REDIRECT_RULES_JSON", "[]"),
    )
