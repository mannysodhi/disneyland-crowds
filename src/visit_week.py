# Wait times the week of my visit (Oct 19 - Nov 1, 2026) from the live collector.
# Only 3-5 snapshots a day got saved, so it's a rough comparison.
from pathlib import Path
import glob

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HEADLINERS = ["Space Mountain", "Indiana Jones™ Adventure", "Matterhorn Bobsleds",
              "Haunted Mansion Holiday", "Star Wars: Rise of the Resistance",
              "Big Thunder Mountain Railroad", "Pirates of the Caribbean",
              "Mickey & Minnie's Runaway Railway", "Tiana's Bayou Adventure",
              "Millennium Falcon: Smugglers Run", "Peter Pan's Flight"]
VISIT = pd.Timestamp("2026-10-30").date()

live = pd.concat(pd.read_csv(f) for f in sorted(glob.glob(str(ROOT / "data/live/*.csv"))))
live["local"] = pd.to_datetime(live["snapshot_utc"]).dt.tz_convert("America/Los_Angeles")
live["day"] = live["local"].dt.date
live = live[(live["park"] == "Disneyland") & live["is_open"]
            & live["ride"].isin(HEADLINERS) & live["local"].dt.hour.between(10, 21)]

daily = (live.groupby("day")
             .agg(avg_wait=("wait_time", "mean"), snapshots=("snapshot_utc", "nunique"))
             .round(1).reset_index())
daily["weekday"] = pd.to_datetime(daily["day"]).dt.strftime("%a")
daily.to_csv(ROOT / "data/visit_week_headliners.csv", index=False)
print(daily.to_string(index=False))

fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
colors = ["#ff9500" if d == VISIT else ("#0071e3" if w in ("Fri", "Sat", "Sun") else "#c7c7cc")
          for d, w in zip(daily["day"], daily["weekday"])]
labels = [f"{w}\n{pd.Timestamp(d):%b %-d}" for d, w in zip(daily["day"], daily["weekday"])]
ax.bar(labels, daily["avg_wait"], color=colors, width=0.7)
for i, v in enumerate(daily["avg_wait"]):
    ax.text(i, v + 0.6, f"{v:.0f}", ha="center", fontsize=9)
for sp in ["top", "right", "left"]:
    ax.spines[sp].set_visible(False)
ax.set_yticks([]); ax.tick_params(axis="x", labelsize=8, length=0)
fig.suptitle("My Disneyland day (Fri Oct 30) vs. the rest of Halloween season",
             x=0.02, ha="left", fontsize=14, fontweight="bold")
ax.set_title("Average posted wait (min) at 11 headliner rides, 10 AM–9 PM",
             loc="left", fontsize=10, color="#6e6e73")
fig.text(0.02, 0.01, "Source: Queue-Times.com live API, collected every ~15 min by GitHub Actions "
         "(3–5 snapshots/day) · Orange = my visit · Blue = other Fri–Sun",
         fontsize=7.5, color="#6e6e73")
plt.tight_layout(rect=(0, 0.04, 1, 0.97))
fig.savefig(ROOT / "figures/visit_week.png")
