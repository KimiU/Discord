import json

from manager import unitils
from manager.config import TrackingRules
from manager.progression import progress_for, xp_needed
from manager.storage import UserStore
from manager.tracking import SessionTracker, VoiceSnapshot, is_active

MIN = 60_000


class Clock:
    def __init__(self):
        self.t = 1_000_000

    def __call__(self):
        return self.t

    def advance(self, minutes):
        self.t += minutes * MIN


def make(rules=TrackingRules()):
    credited = {"active": 0, "afk": 0}

    def credit(uid, a, f):
        credited["active"] += a
        credited["afk"] += f

    clock = Clock()
    return SessionTracker(rules, credit, clock), clock, credited


ACTIVE = VoiceSnapshot(channel_id=1, humans_in_channel=2)
AFK_CH = VoiceSnapshot(channel_id=99, is_afk_channel=True)
DEAF = VoiceSnapshot(channel_id=1, deafened=True, humans_in_channel=2)


def test_afk_channel_time_is_not_counted():
    t, clock, c = make()
    t.update("k", 1, ACTIVE)
    clock.advance(30)
    t.update("k", 1, AFK_CH)      # moved to AFK channel
    clock.advance(240)            # 4 hours idle
    s = t.update("k", 1, None)    # disconnected
    assert c["active"] == 30 * MIN
    assert c["afk"] == 240 * MIN
    assert (s.duration_ms, s.active_ms, s.afk_ms) == (270 * MIN, 30 * MIN, 240 * MIN)


def test_return_from_afk_resumes_counting():
    t, clock, c = make()
    t.update("k", 1, ACTIVE)
    clock.advance(10)
    t.update("k", 1, DEAF)
    clock.advance(60)
    t.update("k", 1, ACTIVE)
    clock.advance(5)
    t.update("k", 1, None)
    assert c["active"] == 15 * MIN and c["afk"] == 60 * MIN


def test_joining_directly_into_afk_channel_counts_nothing():
    t, clock, c = make()
    t.update("k", 1, AFK_CH)
    clock.advance(600)
    t.update("k", 1, None)
    assert c["active"] == 0


def test_leave_without_session_is_noop():
    # The old code computed now - 0 when the bot missed the join -> decades of fake time.
    t, clock, c = make()
    assert t.update("k", 1, None) is None
    assert c["active"] == 0


def test_checkpoint_credits_without_double_counting():
    t, clock, c = make()
    t.update("k", 1, ACTIVE)
    clock.advance(5)
    t.checkpoint()
    assert c["active"] == 5 * MIN
    clock.advance(5)
    t.checkpoint()
    clock.advance(1)
    s = t.update("k", 1, None)
    assert c["active"] == 11 * MIN == s.active_ms


def test_rules():
    assert is_active(ACTIVE, TrackingRules())
    assert not is_active(AFK_CH, TrackingRules(count_deafened=True))
    assert not is_active(DEAF, TrackingRules())
    assert is_active(DEAF, TrackingRules(count_deafened=True))
    alone = VoiceSnapshot(channel_id=1, humans_in_channel=1)
    assert is_active(alone, TrackingRules())
    assert not is_active(alone, TrackingRules(count_alone=False))
    muted = VoiceSnapshot(channel_id=1, muted=True, humans_in_channel=2)
    assert is_active(muted, TrackingRules())
    assert not is_active(muted, TrackingRules(count_muted=False))


def test_progression_matches_legacy_curve():
    assert progress_for(0).level == 1
    assert progress_for((xp_needed(1) - 1) * MIN).level == 1
    assert progress_for(xp_needed(1) * MIN).level == 2
    # A legacy user file: 8051 min total stored as level 14 / 191 xp by the old code.
    p = progress_for(483087344)
    assert p.level == 14 and abs(p.xp - 191) < 70  # old code dropped partial minutes per call


def test_storage_migrates_legacy_and_roundtrips(tmp_path):
    (tmp_path / "1.json").write_text(json.dumps({
        "id": 1, "username": "old", "progression": {"level": 3, "xp": 5},
        "time": {"seconds": 123456, "current": 1680623805581},
    }))
    (tmp_path / "junk.json").write_text("not json")
    store = UserStore(str(tmp_path))
    rec = store.get(1)
    assert rec.active_ms == 123456 and rec.afk_ms == 0
    rec.afk_ms = 10
    store.save(rec)
    again = UserStore(str(tmp_path)).get(1)
    assert (again.active_ms, again.afk_ms, again.username) == (123456, 10, "old")
    assert json.loads((tmp_path / "1.json").read_text())["version"] == 2


def test_format_and_detectors():
    assert unitils.formatDuration(42_000) == "42s"
    assert unitils.formatDuration(5 * MIN + 3000) == "5m 3s"
    assert unitils.formatDuration(50 * 60 * MIN) == "50h 0m"  # old _old variant wrapped at 24h
    assert unitils.isNettiauto("katso https://www.nettiauto.com/x")
    assert not unitils.isNettiauto("nettiauto ilman linkkiä")
    assert unitils.isCode("```print(1)```")
    assert unitils.isCode("https://stackoverflow.com/q/1")
