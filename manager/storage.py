"""Per-user JSON storage.

File format (v2):
    {"version": 2, "id": 123, "username": "name",
     "time": {"active_ms": 0, "afk_ms": 0}}

Legacy (v1) files stored the total under time.seconds (which was actually milliseconds,
and included AFK time) plus a `current` start timestamp. They are migrated on load.
"""
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

SCHEMA_VERSION = 2


@dataclass
class UserRecord:
    id: int
    username: str = ""
    active_ms: int = 0
    afk_ms: int = 0

    def to_json(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "id": self.id,
            "username": self.username,
            "time": {"active_ms": self.active_ms, "afk_ms": self.afk_ms},
        }

    @classmethod
    def from_json(cls, data: dict) -> "UserRecord":
        t = data.get("time", {})
        if data.get("version", 1) < 2:
            # v1: "seconds" was really milliseconds; "current" was an unreliable start stamp
            # (often stale after a restart) and is intentionally dropped.
            active = int(t.get("seconds", 0))
            afk = 0
        else:
            active = int(t.get("active_ms", 0))
            afk = int(t.get("afk_ms", 0))
        username = data.get("username", "")
        return cls(id=int(data["id"]), username=username, active_ms=active, afk_ms=afk)


class UserStore:
    def __init__(self, directory: str):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._cache: Dict[int, UserRecord] = {}
        self._load_all()

    def _path(self, user_id: int) -> str:
        return os.path.join(self.directory, f"{user_id}.json")

    def _load_all(self) -> None:
        for name in os.listdir(self.directory):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self.directory, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    rec = UserRecord.from_json(json.load(f))
            except (ValueError, KeyError, TypeError) as e:
                log.warning("Skipping unreadable user file %s: %s", path, e)
                continue
            self._cache[rec.id] = rec

    def get(self, user_id: int, username: Optional[str] = None) -> UserRecord:
        rec = self._cache.get(user_id)
        if rec is None:
            rec = UserRecord(id=user_id, username=username or "")
            self._cache[user_id] = rec
        elif username:
            rec.username = username
        return rec

    def find(self, user_id: int) -> Optional[UserRecord]:
        return self._cache.get(user_id)

    def save(self, rec: UserRecord) -> None:
        """Atomic write: a crash mid-write can't leave a half-written (corrupt) file."""
        self._cache[rec.id] = rec
        fd, tmp = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(rec.to_json(), f, ensure_ascii=False)
            os.replace(tmp, self._path(rec.id))
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def all(self) -> List[UserRecord]:
        return list(self._cache.values())

    def top(self, n: int = 10) -> List[UserRecord]:
        return sorted(self._cache.values(), key=lambda r: r.active_ms, reverse=True)[:n]

    def rank_of(self, user_id: int) -> Optional[int]:
        ordered = sorted(self._cache.values(), key=lambda r: r.active_ms, reverse=True)
        for i, rec in enumerate(ordered, start=1):
            if rec.id == user_id:
                return i
        return None
