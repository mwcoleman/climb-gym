"""Pull recent climbing + strength sessions from Garmin into DATA_DIR/garmin.json.

Only adds activities it hasn't seen, and never touches openGym's own state files.

    python sync.py                 # last DAYS_BACK days (default 28)
    DAYS_BACK=365 python sync.py   # backfill a year
"""
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path

from garmin_login import ROOT, get_client

# Garmin typeKeys to keep. Override with GARMIN_TYPES=a,b,c in .env.
WANTED = set(
    filter(None, os.environ.get(
        "GARMIN_TYPES", "strength_training,bouldering,indoor_climbing,rock_climbing"
    ).split(","))
)
DAYS_BACK = int(os.environ.get("DAYS_BACK", 28))
PAUSE_SEC = float(os.environ.get("PAUSE_SEC", 1))
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
OUT_FILE = DATA_DIR / "garmin.json"


def load_existing():
    if OUT_FILE.exists():
        return json.loads(OUT_FILE.read_text())
    return {"activities": {}}


def save(store):
    # Write-then-rename, so the API never reads half a file mid-sync.
    tmp = OUT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(store, indent=2))
    os.replace(tmp, OUT_FILE)


def grade_label(value):
    """Garmin's {"valueKey": "_6B_PLUS", "scale": "FONT"} -> "6B+"."""
    key = (value or {}).get("valueKey") or ""
    return key.lstrip("_").replace("_PLUS", "+").replace("_MINUS", "-").replace("_", "") or None


def compact_climbs(typed_splits):
    """One row per climb: grade, sent or not, seconds on the wall."""
    return [
        {
            "grade": grade_label(s.get("gradeValue")),
            "sent": s.get("status") == "CLIMB_COMPLETED",
            "sec": round(s.get("duration") or 0),
            "rank": (s.get("gradeValue") or {}).get("sortOrder"),
        }
        for s in (typed_splits or {}).get("splits") or []
        if s.get("type") == "CLIMB_ACTIVE"
    ]


def compact_sets(exercise_sets):
    """One row per working set: exercise, reps, kg (Garmin sends grams), seconds."""
    rows = []
    for s in (exercise_sets or {}).get("exerciseSets") or []:
        if s.get("setType") != "ACTIVE":
            continue
        ex = (s.get("exercises") or [{}])[0]
        rows.append({
            "exercise": ex.get("name"),
            "category": ex.get("category"),
            "reps": s.get("repetitionCount") or 0,
            "kg": round((s.get("weight") or 0) / 1000, 1),
            "sec": round(s.get("duration") or 0, 1),
        })
    return rows


def fetch_details(g, activity_id, type_key):
    time.sleep(PAUSE_SEC)   # be gentle: Garmin rate-limits hard
    if type_key == "strength_training":
        return {"sets": compact_sets(g.get_activity_exercise_sets(activity_id))}
    climbs = compact_climbs(g.get_activity_typed_splits(activity_id))
    sent = [c for c in climbs if c["sent"]]
    return {
        "climbs": climbs,
        "attempted": len(climbs),
        "sent": len(sent),
        "max_sent": max(sent, key=lambda c: c["rank"] or -1, default={}).get("grade"),
    }


def sync():
    g = get_client()
    store = load_existing()
    start = (date.today() - timedelta(days=DAYS_BACK)).isoformat()
    new_count = 0

    for a in g.get_activities_by_date(start, date.today().isoformat()):
        type_key = a["activityType"]["typeKey"]
        activity_id = str(a["activityId"])
        if type_key not in WANTED or activity_id in store["activities"]:
            continue
        store["activities"][activity_id] = {
            "date": a["startTimeLocal"][:10],
            "start": a["startTimeLocal"],
            "type": type_key,
            "name": a.get("activityName"),
            "duration_min": round((a.get("duration") or 0) / 60),
            "details": fetch_details(g, activity_id, type_key),
        }
        new_count += 1

    store["last_sync"] = date.today().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save(store)
    print(f"Synced: {new_count} new, {len(store['activities'])} total", flush=True)


if __name__ == "__main__":
    sync()
