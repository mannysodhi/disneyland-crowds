"""
Scrape daily Disneyland Resort crowd + wait-time pages from Queue-Times.com.

Data: Powered by Queue-Times.com (https://queue-times.com/)

Usage:
  python3 src/scrape_queue_times.py --test                 # 10 sample days
  python3 src/scrape_queue_times.py --start 2016-01-01 --end 2025-12-31

Saves raw HTML to data/raw/ (so re-runs skip pages already downloaded)
and tidy CSVs to data/:
  queue_times_daily.csv   date, park, crowd_level_pct
  queue_times_tables.csv  date, park, table, row_label, column, value
"""
import argparse
import csv
import re
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

PARKS = {16: "Disneyland", 17: "California Adventure"}
BASE = "https://queue-times.com/parks/{pid}/calendar/{y}/{m:02d}/{d:02d}"
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
DELAY_SEC = 2.0
HEADERS = {"User-Agent": "disneyland-crowds portfolio project (github.com/mannysodhi/disneyland-crowds)"}

TEST_DATES = ["2019-07-04", "2023-07-04", "2024-07-03", "2024-07-04", "2024-07-05",
              "2024-10-31", "2024-11-05", "2024-11-12", "2024-12-25", "2025-05-06"]

# Disneyland closed for COVID
CLOSED = (date(2020, 3, 14), date(2021, 4, 29))


def daterange(start, end):
    d = start
    while d <= end:
        if not (CLOSED[0] <= d <= CLOSED[1]):
            yield d
        d += timedelta(days=1)


def fetch(pid, d, session):
    path = RAW / f"{pid}_{d.isoformat()}.html"
    if path.exists():
        return path.read_text(encoding="utf-8")
    url = BASE.format(pid=pid, y=d.year, m=d.month, d=d.day)
    r = session.get(url, headers=HEADERS, timeout=30)
    time.sleep(DELAY_SEC)
    if r.status_code != 200:
        print(f"  ! {url} -> HTTP {r.status_code}")
        return None
    path.write_text(r.text, encoding="utf-8")
    return r.text


def table_title(tbl):
    cap = tbl.find("caption")
    if cap:
        return cap.get_text(" ", strip=True)
    prev = tbl.find_previous(["h1", "h2", "h3", "h4", "h5", "th"])
    return prev.get_text(" ", strip=True) if prev else "untitled"


def parse(html, d, park):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"Crowd level\s*(\d+)\s*%", text, re.I)
    crowd = int(m.group(1)) if m else None

    rows = []
    for tbl in soup.find_all("table"):
        title = table_title(tbl)
        trs = tbl.find_all("tr")
        if not trs:
            continue
        header = [c.get_text(" ", strip=True) for c in trs[0].find_all(["th", "td"])]
        for tr in trs[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) < 2:
                continue
            for i, val in enumerate(cells[1:], start=1):
                col = header[i] if i < len(header) else f"col{i}"
                rows.append([d.isoformat(), park, title, cells[0], col, val])
    return crowd, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--start")
    ap.add_argument("--end")
    a = ap.parse_args()

    if a.test:
        dates = [date.fromisoformat(s) for s in TEST_DATES]
    elif a.start and a.end:
        dates = list(daterange(date.fromisoformat(a.start), date.fromisoformat(a.end)))
    else:
        ap.error("use --test or --start/--end")

    RAW.mkdir(parents=True, exist_ok=True)
    daily, tables = [], []
    s = requests.Session()
    total = len(dates) * len(PARKS)
    n = 0
    for d in dates:
        for pid, park in PARKS.items():
            n += 1
            print(f"[{n}/{total}] {park} {d}")
            html = fetch(pid, d, s)
            if not html:
                continue
            crowd, rows = parse(html, d, park)
            daily.append([d.isoformat(), park, crowd])
            tables.extend(rows)

    with open(OUT / "queue_times_daily.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "park", "crowd_level_pct"])
        w.writerows(daily)
    with open(OUT / "queue_times_tables.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "park", "table", "row_label", "column", "value"])
        w.writerows(tables)

    found = sum(1 for r in daily if r[2] is not None)
    print(f"\nDone. {len(daily)} pages, crowd level found on {found}, {len(tables)} table cells.")
    print("Saved data/queue_times_daily.csv and data/queue_times_tables.csv")


if __name__ == "__main__":
    main()
