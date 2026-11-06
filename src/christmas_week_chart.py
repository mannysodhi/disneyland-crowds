"""
Signals disagree: Christmas week 2017, freeway traffic vs. ride waits.
Usage: python3 src/christmas_week_chart.py -> figures/christmas_week_2017.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
d = pd.read_csv(ROOT / "data/crowd_index_daily.csv", parse_dates=["date"])
w = d[d["date"].between("2017-12-04", "2017-12-31")].dropna(subset=["traffic_cars", "wait_minutes"])
base = d[d["date"].between("2017-12-04", "2017-12-15")]
t0, w0 = base["traffic_cars"].mean(), base["wait_minutes"].mean()   # early-December baseline

fig, ax = plt.subplots(figsize=(9, 4.8), dpi=150)
ax.plot(w["date"], (w["traffic_cars"] / t0 - 1) * 100, color="#8e8e93", lw=2.5, marker="o", ms=4,
        label="Cars exiting I-5 at Disneyland")
ax.plot(w["date"], (w["wait_minutes"] / w0 - 1) * 100, color="#0071e3", lw=2.5, marker="o", ms=4,
        label="Avg wait at headliner rides")
ax.axhline(0, color="#1d1d1f", lw=0.8)
ax.axvspan(pd.Timestamp("2017-12-23"), pd.Timestamp("2017-12-31"), color="#ff9500", alpha=0.08)
ax.text(pd.Timestamp("2017-12-27"), 120, "Christmas week", ha="center", color="#ff9500", fontsize=10)
for sp in ["top", "right"]:
    ax.spines[sp].set_visible(False)
ax.set_ylabel("% vs. early December")
ax.legend(frameon=False, loc="upper left", fontsize=9)
fig.suptitle("The freeway said Christmas week was quiet. The rides disagreed.",
             x=0.02, ha="left", fontsize=14, fontweight="bold")
fig.text(0.02, 0.01, "Sources: Caltrans PeMS (Disney Dr. off-ramps) · Jester565/DisneylandData ride waits · "
         "baseline = Dec 4–15, 2017", fontsize=7.5, color="#6e6e73")
plt.tight_layout(rect=(0, 0.04, 1, 0.95))
fig.savefig(ROOT / "figures/christmas_week_2017.png")
print("ok")
