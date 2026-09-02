import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_DATA_DIR = Path(os.environ.get("TUTOR_DATA_DIR", Path.cwd() / ".data"))
_DATA_FILE = _DATA_DIR / "progress.json"
_lock = Lock()


def _load() -> dict:
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_attempt(student_id: str, mission_id: str, passed: bool) -> tuple[bool, int]:
    """
    Records an attempt at a mission. `passed` must already be the result of a
    server-side deterministic check (see record_progress tool) - this store
    does not itself validate anything, so callers must never pass
    passed=True on the strength of a model's or a widget's say-so alone.

    Returns (completed, attempts).
    """
    with _lock:
        data = _load()
        records: list[dict] = data.get(student_id, [])
        existing = next((r for r in records if r["missionId"] == mission_id), None)

        if existing:
            existing["attempts"] += 1
            if passed and not existing["completedAt"]:
                existing["completedAt"] = datetime.now(timezone.utc).isoformat()
        else:
            existing = {
                "missionId": mission_id,
                "attempts": 1,
                "completedAt": datetime.now(timezone.utc).isoformat() if passed else "",
            }
            records.append(existing)

        data[student_id] = records
        _save(data)

        return bool(existing["completedAt"]), existing["attempts"]


def get_progress(student_id: str) -> list[dict]:
    return _load().get(student_id, [])
