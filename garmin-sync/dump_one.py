"""Dump everything Garmin will give us about one activity to scratch/dumps/<id>.json.

    python dump_one.py 1234567890
"""
import json
import sys

from garmin_login import ROOT, get_client

activity_id = sys.argv[1]
g = get_client()

out = {"summary": g.get_activity(activity_id)}
for name, fn in [
    ("splits", g.get_activity_splits),
    ("split_summaries", g.get_activity_split_summaries),
    ("exercise_sets", g.get_activity_exercise_sets),
]:
    try:
        out[name] = fn(activity_id)
    except Exception as e:
        out[name] = f"ERROR: {e}"

folder = ROOT / "scratch" / "dumps"
folder.mkdir(parents=True, exist_ok=True)
(folder / f"{activity_id}.json").write_text(json.dumps(out, indent=2))
print("Saved", folder / f"{activity_id}.json")
