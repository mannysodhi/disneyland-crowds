# Charts for the Crowd Index post: heatmap, holidays, waits vs searches.
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
BLUE, ORANGE, GRAY, INK, MUTED = "#0072E3", "#FF9500", "#C7C7CC", "#111111", "#6E6E73"
plt.rcParams.update({"font.size": 13, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK, "figure.dpi": 100})

df = pd.read_csv(ROOT / "data" / "crowd_index_daily.csv", parse_dates=["date"])
df = df.dropna(subset=["traffic_cars"])          # days with the core signal only


def titles(fig, title, subtitle, source):
    """Same title / subtitle / source layout as the Part 1 charts."""
    fig.text(0.02, 0.965, title, fontsize=22, weight="bold", color=INK, va="top")
    fig.text(0.02, 0.905, subtitle, fontsize=14, color=MUTED, va="top")
    fig.text(0.02, 0.02, source, fontsize=11, color=MUTED)


# 1. heatmap
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
grid = (df.assign(month=df["date"].dt.month)
          .pivot_table(index="weekday", columns="month", values="crowd_index", aggfunc="mean")
          .reindex(days))

fig, ax = plt.subplots(figsize=(13.5, 7.5))
fig.subplots_adjust(left=0.13, right=0.97, top=0.80, bottom=0.10)
im = ax.imshow(grid.values, cmap="Blues", vmin=25, vmax=75, aspect="auto")
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        v = grid.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=12,
                color="white" if v > 55 else INK)
lo = np.unravel_index(np.nanargmin(grid.values), grid.shape)   # quietest cell
hi = np.unravel_index(np.nanargmax(grid.values), grid.shape)   # busiest cell
for (r, c), col in [(lo, ORANGE), (hi, INK)]:
    ax.add_patch(plt.Rectangle((c - .5, r - .5), 1, 1, fill=False, lw=3, ec=col))
ax.set_xticks(range(12), months); ax.set_yticks(range(7), [d[:3] for d in days])
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
ax.xaxis.tick_top()
full = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May",
        "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October",
        "Nov": "November", "Dec": "December"}
titles(fig, f"The best time to visit Disneyland: a {days[lo[0]]} in {full[months[lo[1]]]}",
       "Average Crowd Index (0 = quietest day of the year, 100 = busiest), 2016–2026",
       f"Crowd Index = freeway traffic + ride waits + Google searches · orange box = quietest "
       f"({days[lo[0]][:3]} in {months[lo[1]]}), black = busiest ({days[hi[0]][:3]} in {months[hi[1]]})")
fig.savefig(FIG / "best_time_heatmap.png", dpi=200); plt.close(fig)

# 2. holidays
hs = pd.read_csv(ROOT / "data" / "tableau" / "holiday_summary.csv")
hs = hs[hs["Signal"] == "crowd_index"].sort_values("Lift Vs Same Weekday Pct")
vals = hs["Lift Vs Same Weekday Pct"].values
colors = [BLUE if v > 0 else GRAY for v in vals]
colors = [ORANGE if h == "Halloween" else c for h, c in zip(hs["Holiday"], colors)]

fig, ax = plt.subplots(figsize=(13.5, 9))
fig.subplots_adjust(left=0.20, right=0.95, top=0.84, bottom=0.08)
ax.barh(hs["Holiday"], vals, color=colors, height=0.65)
ax.axvline(0, color=INK, lw=1)
for y, v in enumerate(vals):
    ax.text(v + (0.8 if v > 0 else -0.8), y, f"{v:+.0f}", va="center",
            ha="left" if v > 0 else "right", fontsize=13)
ax.set_xticks([]); ax.spines["left"].set_visible(False); ax.tick_params(length=0)
ax.set_xlim(vals.min() - 6, vals.max() + 6)
titles(fig, "Memorial Day packs the park. Halloween empties it.",
       "Crowd Index on each holiday minus a normal day on the same weekday (points)",
       "Crowd Index = freeway traffic + ride waits + Google searches, 2016–2026 · COVID closure excluded")
fig.savefig(FIG / "holiday_crowd_index.png", dpi=200); plt.close(fig)

# 3. agreement
w = (df.set_index("date")[["wait_minutes", "search_interest"]]
       .resample("W").mean().loc["2017-06":"2018-12"].dropna())
r = w["wait_minutes"].corr(w["search_interest"])

fig, ax = plt.subplots(figsize=(13.5, 7))
fig.subplots_adjust(left=0.08, right=0.92, top=0.80, bottom=0.12)
ax.plot(w.index, w["wait_minutes"], color=BLUE, lw=2.5)
ax2 = ax.twinx()                                   # second y-axis for search interest
ax2.plot(w.index, w["search_interest"], color=ORANGE, lw=2.5)
ax.set_ylabel("Avg headliner wait (min)", color=BLUE)
ax2.set_ylabel("Google search interest", color=ORANGE)
ax2.spines["right"].set_visible(True)
titles(fig, f"Wait times and Google searches rise and fall together (r = {r:.2f})",
       f"Weekly averages, Disneyland Park, {w.index.min():%b %Y} – {w.index.max():%b %Y}",
       "Waits: Jester565/DisneylandData (30-min ride logs) · Search: Google Trends, \"Disneyland\", California")
fig.savefig(FIG / "signals_agree.png", dpi=200); plt.close(fig)
print("saved 3 charts")
