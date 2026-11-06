"""
Build the Disneyland Crowd Index: one daily 0-100 score from 3 public signals.

Signals (each converted to a 0-100 percentile within its calendar year):
  1. traffic  - cars exiting I-5 at the Disneyland off-ramps (Caltrans PeMS)
                data/disney_offramp_daily.csv            (notebooks/01_explore_pems.ipynb)
  2. waits    - avg posted wait at headliner rides, 2017-2018
                data/wait_daily.csv  (src/build_wait_daily.py, Jester565/DisneylandData)
  3. search   - weekly Google Trends interest, "Disneyland", California
                data/trends/*.csv  (3 overlapping downloads, stitched below)

Crowd Index = equal-weight average of the signals available that day.
Days in the COVID closure (2020-03-14 to 2021-04-29) are excluded.

Outputs:
  data/crowd_index_daily.csv           one row per day, every signal + index
  data/tableau/crowd_index_daily.csv   same, Tableau-friendly column names
  data/tableau/holiday_summary.csv     holiday vs same-weekday lift per signal

Usage:  python3 src/build_crowd_index.py
"""
from pathlib import Path
import io

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CLOSED = ("2020-03-14", "2021-04-29")


# ---------------------------------------------------------------- loaders
def load_traffic():
    df = pd.read_csv(DATA / "disney_offramp_daily.csv", parse_dates=["date"])
    return df.rename(columns={"total_flow": "traffic_cars"})


def load_waits():
    """Daily headliner wait (min), 2017-2018, from src/build_wait_daily.py."""
    path = DATA / "wait_daily.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    return df[["date", "avg_wait_headliners"]].rename(
        columns={"avg_wait_headliners": "wait_minutes"})


def read_trends_file(path):
    """Google Trends CSVs start with a few metadata lines; find the real header."""
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.split(",")[0].strip().strip('"').lower() in ("week", "time", "date", "day", "month"))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])))
    df.columns = ["week", "interest"]
    df["week"] = pd.to_datetime(df["week"])
    df["interest"] = pd.to_numeric(df["interest"].astype(str).str.replace("<1", "0"), errors="coerce")
    return df.dropna()


def load_search():
    files = sorted((DATA / "trends").glob("*.csv"))
    if not files:
        return None
    parts = sorted((read_trends_file(f) for f in files), key=lambda d: d["week"].min())
    # Stitch: each Trends download is scaled 0-100 on its own, so rescale every
    # later file to match the previous one on the weeks they share.
    out = parts[0]
    for nxt in parts[1:]:
        overlap = out.merge(nxt, on="week", suffixes=("_a", "_b"))
        if len(overlap) and overlap["interest_b"].mean() > 0:
            nxt = nxt.assign(interest=nxt["interest"] * overlap["interest_a"].mean()
                             / overlap["interest_b"].mean())
        out = pd.concat([out, nxt[nxt["week"] > out["week"].max()]])
    # Spread each week's value onto its 7 days
    days = out.set_index("week")["interest"].resample("D").ffill().reset_index()
    return days.rename(columns={"week": "date", "interest": "search_interest"})


# ---------------------------------------------------------------- build
def pct_rank(s, year):
    """0-100 percentile of each day *within its own calendar year*.
    Ranking inside each year removes long-term drift (e.g. Google search
    interest slowly falling, the 2021 reopening ramp), so the score answers
    "how busy was this day compared with the rest of its year?"."""
    return (s.groupby(year).rank(pct=True) * 100).round(1)


def main():
    df = load_traffic()
    for name, loader in [("waits", load_waits), ("search", load_search)]:
        extra = loader()
        if extra is None:
            print(f"- {name}: no data yet, skipped")
            continue
        df = df.merge(extra, on="date", how="outer")
        print(f"- {name}: {len(extra):,} days loaded")

    df = df[~df["date"].between(*CLOSED)].sort_values("date").reset_index(drop=True)

    signal_cols = {"traffic_cars": "traffic_score",
                   "wait_minutes": "waits_score",
                   "search_interest": "search_score"}
    scores = []
    for raw, score in signal_cols.items():
        if raw in df:
            df[score] = pct_rank(df[raw], df["date"].dt.year)
            scores.append(score)

    df["signals_used"] = df[scores].notna().sum(axis=1)
    df["crowd_index"] = df[scores].mean(axis=1).round(1)        # equal weights

    special = pd.read_csv(DATA / "special_days.csv", parse_dates=["date"])
    df = df.merge(special, on="date", how="left")
    df["weekday"] = df["date"].dt.day_name()
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.strftime("%b")      # Jan, Feb... (for Tableau)
    df["month_num"] = df["date"].dt.month           # sort order for the month axis
    df["weekday_num"] = df["date"].dt.dayofweek     # 0 = Monday, sort order for weekdays

    df.to_csv(DATA / "crowd_index_daily.csv", index=False)

    # Tableau exports
    tab = DATA / "tableau"
    tab.mkdir(exist_ok=True)
    df.rename(columns=lambda c: c.replace("_", " ").title()).to_csv(
        tab / "crowd_index_daily.csv", index=False)

    rows = []
    normal = df[df["day_name"].isna()]
    for col in ["traffic_cars", "wait_minutes", "search_interest", "crowd_index"]:
        if col not in df:
            continue
        base = normal.groupby("weekday")[col].mean()
        h = df[df["day_name"].notna()].dropna(subset=[col]).copy()
        if col == "crowd_index":
            # the index is already a 0-100 score, so report the gap in points
            h["lift_pct"] = h[col] - h["weekday"].map(base)
        else:
            h["lift_pct"] = (h[col] / h["weekday"].map(base) - 1) * 100
        g = h.groupby("day_name")["lift_pct"].agg(["count", "mean"]).reset_index()
        g["signal"] = col
        rows.append(g)
    pd.concat(rows).rename(columns={"day_name": "Holiday", "count": "Days",
                                    "mean": "Lift Vs Same Weekday Pct",
                                    "signal": "Signal"}).round(1).to_csv(
        tab / "holiday_summary.csv", index=False)

    print(f"\nSaved {len(df):,} days. Signals: {', '.join(scores)}")
    print(df.groupby("signals_used").size().rename("days").to_string())


if __name__ == "__main__":
    main()
