# Disneyland crowds

I went to Disneyland over Halloween and it got me wondering how busy the park really is on holidays. Disney doesn't publish daily attendance, so I tried to estimate it from public data.

Dashboard: [Tableau Public](https://public.tableau.com/views/disneyland_crowd_index/DisneylandCrowdIndex)

## Data

- **Freeway traffic**: Caltrans PeMS, the two sensors on the I-5 Disneyland off-ramps, 2016–2026
- **Wait times**: the [Jester565/DisneylandData](https://github.com/Jester565/DisneylandData) ride logs (2017–2018), plus a small GitHub Action that saves live waits from [Queue-Times](https://queue-times.com/) every 15 min
- **Google Trends**: "Disneyland", California

## What I found

- 3-day weekends are the busy days. Monday holidays get 13–17% more cars than a normal Monday.
- Big family holidays are quiet: Christmas Eve −20%, Thanksgiving −18%, Election Day −16%, Halloween −5%.
- When I combined all three sources into a 0–100 crowd score, the quietest time was a Tuesday in October (29) and the busiest was a Saturday in January (69).

![Holiday traffic vs a normal day](figures/holiday_vs_weekday.png)

![Best time to visit](figures/best_time_heatmap.png)

## Things that went wrong

- My first traffic numbers showed a 93% drop in July 2024. It turned out to be a broken sensor, not an empty park. I ended up keeping only days where both sensors reported the full day (3,243 days).
- I first tried scraping 10 years of wait times from Queue-Times (`src/scrape_queue_times.py`), but I didn't get usable history out of it. I switched to the 2017–2018 dataset instead.
- The first version of the crowd score said 2020 was the busiest year ever. Google searches for Disneyland have been dropping since 2016, so ranking all years together was unfair. Ranking each day within its own year fixed it.
- Traffic isn't attendance, since hotel guests and cast members use the same exits. Wait times only cover 2017–2018, so most days have just 2 of the 3 sources.

## Files

- `notebooks/01_explore_pems.ipynb`: traffic cleaning
- `sql/01_holiday_analysis.sql`: holidays vs the same weekday (Postgres)
- `src/build_crowd_index.py`: combines the three sources into the crowd score
- `src/`: wait-time cleanup, live collector, charts

## Next

- Universal Studios Hollywood, to compare
- More live wait-time data as the collector keeps running

Manny Sodhi
