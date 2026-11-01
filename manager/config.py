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


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise SystemExit("DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token.")

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
    )
