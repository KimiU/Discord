"""Level/XP maths. 1 XP per minute of *active* voice time.

Level and XP are derived from total active time, so there is a single source of truth:
fixing someone's time (e.g. `!settime`) automatically fixes their level too.
"""
from dataclasses import dataclass

BASE_XP = 250
XP_PER_LEVEL = 50
MS_PER_XP = 60_000


def xp_needed(level: int) -> int:
    """XP needed to go from `level` to `level + 1`."""
    return BASE_XP + XP_PER_LEVEL * level


@dataclass(frozen=True)
class Progress:
    level: int
    xp: int
    xp_needed: int
    total_xp: int


def progress_for(active_ms: int) -> Progress:
    total_xp = max(0, int(active_ms)) // MS_PER_XP
    level, remaining = 1, total_xp
    while remaining >= xp_needed(level):
        remaining -= xp_needed(level)
        level += 1
    return Progress(level=level, xp=remaining, xp_needed=xp_needed(level), total_xp=total_xp)
