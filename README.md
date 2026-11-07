# How Crowded Is Disneyland, Really?

I went to Disneyland this Halloween and wanted to know when the park is actually packed. Disney doesn't publish daily attendance, so I pieced it together from three public sources:

| Source | What it tells you |
|---|---|
| Freeway traffic (Caltrans PeMS sensors on the I-5 Disneyland off-ramps) | When people drive in |
| Ride wait times (2017–2018 ride logs + my own live snapshots from Queue-Times) | How packed it is inside |
| Google Trends, "Disneyland", California | When people plan a trip |

I combined them into a daily Crowd Index from 0 to 100.

📊 [Interactive dashboard on Tableau Public](https://public.tableau.com/views/disneyland_crowd_index/DisneylandCrowdIndex)

## What I found

![Holiday traffic vs a normal day](figures/holiday_vs_weekday.png)

- Long weekends fill the park, not holidays. Monday holidays bring 13–17% more cars than a normal Monday.
- Family holidays are quiet: Christmas Eve −20%, Thanksgiving −18%, Election Day −16%, Halloween −5%.
- The week I went, headliner waits on Friday Oct 30 averaged 31 minutes vs 40 the Friday before.

![Halloween week](figures/visit_week.png)

### The best time to go

![Best time to visit](figures/best_time_heatmap.png)

- Quietest: a Tuesday in October (Crowd Index 29). Busiest: a Saturday in January (69).
- Busiest holiday: Memorial Day (+26 points vs a normal Monday). Quietest: Halloween (−25) and Election Day (−23).

![Holidays ranked](figures/holiday_crowd_index.png)

### Do the three sources agree?

Mostly. Wait times and Google searches move together week to week (r = 0.69). Traffic lines up with wait times month to month (r = 0.62) but is noisy week to week, since hotel guests and staff use the same exits.

![Wait times vs searches](figures/signals_agree.png)

![10 years of traffic](figures/traffic_trend.png)

## How I built it

1. Traffic cleaning (`notebooks/01_explore_pems.ipynb`): 129 monthly PeMS files from 2016–2026, narrowed to the two Disneyland off-ramp sensors. I kept only the 3,243 days where both sensors reported all day. In July 2024 a sensor outage made traffic look like it dropped 93%, which is how I learned that missing data isn't zero.
2. Holiday analysis in PostgreSQL (`sql/01_holiday_analysis.sql`): each holiday is compared to a normal day on the same weekday, because weekends are always busier.
3. Wait times (`src/build_wait_daily.py`): daily averages from a public 2017–2018 ride-time log. A GitHub Action (`src/collect_live.py`) also saves live waits every 15 minutes.
4. Crowd Index (`src/build_crowd_index.py`): each source becomes a 0–100 percentile within its own year, then I average them. My first version ranked across all 10 years and made 2020 look like the busiest year ever, because Google searches have slowly declined since 2016. Ranking within each year fixed it.
5. Charts (`src/part2_charts.py`) and the Tableau workbook (`src/make_tableau.py`).

Limits: off-ramp traffic is a proxy, not a turnstile count. The park was closed from March 2020 to April 2021, so those dates are excluded. Historical wait times only cover 2017–2018, so most days use two of the three sources.

## Run it yourself

```bash
pip install -r requirements.txt
python3 src/build_wait_daily.py
python3 src/build_crowd_index.py
python3 src/part2_charts.py
python3 src/make_tableau.py
```

```
data/        cleaned datasets (raw PeMS files are not in the repo)
notebooks/   traffic cleaning
sql/         PostgreSQL holiday analysis
src/         data collection, Crowd Index, charts, Tableau export
figures/     charts
tableau/     Tableau workbook
```

Data: [Caltrans PeMS](https://pems.dot.ca.gov/) · [Queue-Times.com](https://queue-times.com/) · [Jester565/DisneylandData](https://github.com/Jester565/DisneylandData) · Google Trends

Manny Sodhi · Python, PostgreSQL, Tableau
