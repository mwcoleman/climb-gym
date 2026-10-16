"""Container entrypoint: sync now, then every SYNC_MINUTES (default 30)."""
import os
import time
import traceback

from sync import sync

MINUTES = int(os.environ.get("SYNC_MINUTES", 30))

while True:
    try:
        sync()
    except Exception:
        traceback.print_exc()
    time.sleep(MINUTES * 60)
