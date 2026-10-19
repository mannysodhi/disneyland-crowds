"""
Collect live Disneyland Resort wait times from the official Queue-Times API.

Data: Powered by Queue-Times.com (https://queue-times.com/)

Usage:
  python3 src/collect_live.py --once      # one snapshot (test)
  python3 src/collect_live.py             # every 10 min until you press Ctrl+C

Appends to data/live/YYYY-MM-DD.csv:
  snapshot_utc, park, land, ride, is_open, wait_time, last_updated
"""
import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

PARKS = {16: "Disneyland", 17: "California Adventure"}
API = "https://queue-times.com/parks/{pid}/queue_times.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "live"
INTERVAL_SEC = 600


def snapshot():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for pid, park in PARKS.items():
        r = requests.get(API.format(pid=pid), timeout=30)
        r.raise_for_status()
        data = r.json()
        rides = [(land["name"], ride) for land in data.get("lands", []) for ride in land["rides"]]
        rides += [("", ride) for ride in data.get("rides", [])]
        for land, ride in rides:
            rows.append([now, park, land, ride["name"], ride["is_open"],
                         ride["wait_time"], ride["last_updated"]])
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{datetime.now().date().isoformat()}.csv"
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["snapshot_utc", "park", "land", "ride", "is_open", "wait_time", "last_updated"])
        w.writerows(rows)
    open_rides = [r for r in rows if r[4]]
    avg = sum(r[5] for r in open_rides) / len(open_rides) if open_rides else 0
    print(f"{datetime.now():%H:%M} saved {len(rows)} rides, {len(open_rides)} open, avg wait {avg:.0f} min -> {path.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    while True:
        try:
            snapshot()
        except Exception as e:
            print(f"{datetime.now():%H:%M} error: {e}")
        if a.once:
            break
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
