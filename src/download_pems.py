"""
Download Caltrans PeMS "Station Day" files for District 12 (Orange County).

PeMS asks batch tools to fetch files one at a time -- this script does that,
with a pause between files, and skips files already downloaded.

Usage:
  python3 src/download_pems.py --test      # list 2024 files, download July 2024 only
  python3 src/download_pems.py             # all months 2016-2026

Your PeMS email/password are typed in Terminal (hidden) and never saved.
Files go to data/pems/raw/
"""
import argparse
import getpass
import json
import re
import time
from pathlib import Path

import requests

BASE = "https://pems.dot.ca.gov/"
DISTRICT = 12
YEARS = range(2016, 2027)
OUT = Path(__file__).resolve().parent.parent / "data" / "pems" / "raw"
PAUSE_SEC = 3
UA = {"User-Agent": "disneyland-crowds portfolio project (github.com/mannysodhi/disneyland-crowds)"}


def login(s):
    user = input("PeMS email: ").strip()
    pw = getpass.getpass("PeMS password (hidden): ")
    print("Logging in to PeMS... (up to 30 sec)", flush=True)
    s.post(BASE, data={"redirect": "", "username": user, "password": pw, "login": "Login"},
           headers=UA, timeout=120)
    print("Checking login...", flush=True)
    check = s.get(BASE, params={"dnode": "Clearinghouse"}, headers=UA, timeout=120)
    if "Logout" not in check.text:
        raise SystemExit("Login failed - check email/password and try again.")
    print("Logged in.")


def list_files(s, year, ftype):
    """Return [(file_name, download_id)] for one year."""
    print(f"Asking PeMS for the {year} file list...", flush=True)
    r = s.get(BASE, headers=UA, timeout=120, params={
        "srq": "clearinghouse", "district_id": DISTRICT, "geotag": "null",
        "yy": year, "type": ftype, "returnformat": "text"})
    files = []
    try:
        data = json.loads(r.text)
        for month_files in (data.get("data") or {}).values():
            for f in month_files:
                m = re.search(r"download=(\d+)", f.get("url", ""))
                if m:
                    files.append((f["file_name"], m.group(1)))
    except ValueError:
        # fallback: pull links straight out of the page
        for fid, name in re.findall(r"download=(\d+)[^>]*>\s*([\w.]+\.gz)", r.text):
            files.append((name, fid))
    return sorted(set(files))


def download(s, name, fid):
    path = OUT / name
    if path.exists() and path.stat().st_size > 0:
        print(f"  skip {name} (already have it)")
        return
    print(f"  downloading {name}...", flush=True)
    r = s.get(BASE, params={"download": fid, "dnode": "Clearinghouse"}, headers=UA, timeout=300)
    is_gz = r.content[:2] == b"\x1f\x8b"
    looks_html = r.content[:200].lstrip().lower().startswith((b"<!doctype", b"<html"))
    if r.status_code != 200 or (name.endswith(".gz") and not is_gz) or looks_html:
        print(f"  ! {name}: unexpected response (HTTP {r.status_code}) - skipped")
        return
    path.write_bytes(r.content)
    print(f"  saved {name} ({len(r.content)/1e6:.1f} MB)")
    time.sleep(PAUSE_SEC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    login(s)

    years = [2024] if a.test else YEARS
    for y in years:
        files = list_files(s, y, "station_day")
        print(f"{y}: {len(files)} monthly files found")
        if a.test:
            files = [f for f in files if f[0].endswith("2024_07.txt.gz")]
        for name, fid in files:
            download(s, name, fid)

    # station metadata (where each sensor is) - newest file of the latest year
    for y in [2026, 2025]:
        meta = list_files(s, y, "meta")
        if meta:
            download(s, *meta[-1])
            break
    print("Done. Files are in data/pems/raw/")


if __name__ == "__main__":
    main()
