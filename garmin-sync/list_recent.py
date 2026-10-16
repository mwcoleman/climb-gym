"""Print your recent Garmin activities: id, start time, typeKey, name.

    python list_recent.py        # last 30
    python list_recent.py 200    # last 200
"""
import sys
from collections import Counter

from garmin_login import get_client

count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
g = get_client()
activities = g.get_activities(0, count)
for a in activities:
    print(a["activityId"], a["startTimeLocal"], a["activityType"]["typeKey"], a.get("activityName"))

print("\nTypes:", dict(Counter(a["activityType"]["typeKey"] for a in activities)))
