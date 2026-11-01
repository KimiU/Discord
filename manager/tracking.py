"""Voice time tracking that does NOT credit AFK time.

A voice session is split into *segments*. Each segment is either active or AFK, and is
re-evaluated on every voice state change (moved to the AFK channel, deafened/undeafened,
someone joining/leaving when `count_alone` is off, ...). Only active segments add to a
user's total time / XP.

This module has no discord.py dependency, so it is unit-testable.
"""
import time
from dataclasses import dataclass
from typing import Callable, Dict, Hashable, Optional

from manager.config import TrackingRules


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass(frozen=True)
class VoiceSnapshot:
    """The parts of a member's voice state that matter for tracking."""

    channel_id: int
    is_afk_channel: bool = False
    deafened: bool = False
    muted: bool = False
    humans_in_channel: int = 1  # non-bot members in the channel, including this one


def is_active(snap: VoiceSnapshot, rules: TrackingRules) -> bool:
    if snap.is_afk_channel:
        return False
    if snap.deafened and not rules.count_deafened:
        return False
    if snap.muted and not rules.count_muted:
        return False
    if snap.humans_in_channel < 2 and not rules.count_alone:
        return False
    return True


@dataclass
class Session:
    user_id: int
    started_ms: int
    segment_start_ms: int
    segment_active: bool
    active_ms: int = 0
    afk_ms: int = 0


@dataclass(frozen=True)
class SessionSummary:
    user_id: int
    duration_ms: int
    active_ms: int
    afk_ms: int


# credit(user_id, active_ms, afk_ms) -> persists the time somewhere.
CreditFn = Callable[[int, int, int], None]


class SessionTracker:
    def __init__(self, rules: TrackingRules, credit: CreditFn, clock: Callable[[], int] = now_ms):
        self.rules = rules
        self._credit = credit
        self._clock = clock
        self.sessions: Dict[Hashable, Session] = {}

    def _close_segment(self, s: Session, now: int) -> None:
        elapsed = max(0, now - s.segment_start_ms)
        if elapsed:
            if s.segment_active:
                s.active_ms += elapsed
                self._credit(s.user_id, elapsed, 0)
            else:
                s.afk_ms += elapsed
                self._credit(s.user_id, 0, elapsed)
        s.segment_start_ms = now

    def update(self, key: Hashable, user_id: int, snap: Optional[VoiceSnapshot]) -> Optional[SessionSummary]:
        """Feed the member's current voice state (None = not in voice).

        Returns a summary when a session ends, otherwise None.
        """
        now = self._clock()
        s = self.sessions.get(key)

        if snap is None:
            if s is None:
                return None
            self._close_segment(s, now)
            del self.sessions[key]
            return SessionSummary(s.user_id, now - s.started_ms, s.active_ms, s.afk_ms)

        active = is_active(snap, self.rules)
        if s is None:
            self.sessions[key] = Session(user_id, now, now, active)
        elif active != s.segment_active:
            self._close_segment(s, now)
            s.segment_active = active
        return None

    def checkpoint(self) -> None:
        """Credit all in-progress segments so a crash/restart loses at most one interval."""
        now = self._clock()
        for s in self.sessions.values():
            self._close_segment(s, now)

    def is_tracking(self, key: Hashable) -> bool:
        return key in self.sessions

    def current(self, key: Hashable) -> Optional[Session]:
        """In-progress session including the not-yet-credited open segment (read-only copy)."""
        s = self.sessions.get(key)
        if s is None:
            return None
        open_ms = max(0, self._clock() - s.segment_start_ms)
        return Session(
            s.user_id, s.started_ms, s.segment_start_ms, s.segment_active,
            s.active_ms + (open_ms if s.segment_active else 0),
            s.afk_ms + (0 if s.segment_active else open_ms),
        )

    def pending_active_ms(self, key: Hashable) -> int:
        """Active time in the open segment that hasn't been credited to storage yet."""
        s = self.sessions.get(key)
        if s is None or not s.segment_active:
            return 0
        return max(0, self._clock() - s.segment_start_ms)

    def end_all(self) -> None:
        for key in list(self.sessions):
            s = self.sessions[key]
            self.update(key, s.user_id, None)
