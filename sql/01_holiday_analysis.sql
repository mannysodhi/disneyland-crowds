-- Disneyland Crowds on Special Days: holiday analysis (PostgreSQL)
-- Data: daily car counts on the two I-5 off-ramps into Disneyland
--       (Caltrans PeMS, cleaned in notebooks/01_explore_pems.ipynb)

-- 0. Tables
-- Daily off-ramp traffic, one row per clean day (both sensors 100% observed)
CREATE TABLE offramp_daily (
    date        DATE PRIMARY KEY,
    total_flow  NUMERIC          -- cars exiting toward Disneyland that day
);

-- Holiday / special-day calendar, 2016-2026 (data/special_days.csv)
CREATE TABLE special_days (
    date      DATE PRIMARY KEY,
    day_name  TEXT
);

-- Load with pgAdmin Import/Export (Header ON) or:
-- \copy offramp_daily FROM 'data/disney_offramp_daily.csv' CSV HEADER
-- \copy special_days  FROM 'data/special_days.csv'         CSV HEADER

-- Sanity check: expect 3243 rows, 2016-01-01 to 2026-09-02
SELECT COUNT(*), MIN(date), MAX(date) FROM offramp_daily;


-- 1. Are special days busier than normal days?
--    LEFT JOIN keeps every traffic day; non-holidays get day_name = NULL.
--    Disneyland was closed 2020-03-14 to 2021-04-29 (COVID), so exclude it.
SELECT
    CASE WHEN s.day_name IS NULL THEN 'Normal day'
         ELSE 'Special day' END       AS day_type,
    COUNT(*)                          AS days,
    ROUND(AVG(o.total_flow))          AS avg_cars
FROM offramp_daily o
LEFT JOIN special_days s ON o.date = s.date
WHERE o.date NOT BETWEEN '2020-03-14' AND '2021-04-29'
GROUP BY day_type;
-- Result: normal 14,079 cars (2,796 days) vs special 12,997 (94 days)


-- 2. Rank each holiday vs the overall normal-day average (14,079)
SELECT
    s.day_name,
    COUNT(*)                                          AS days,
    ROUND(AVG(o.total_flow))                          AS avg_cars,
    ROUND(AVG(o.total_flow) / 14079 * 100 - 100, 1)   AS pct_vs_normal
FROM offramp_daily o
JOIN special_days s ON o.date = s.date            -- inner join = holidays only
WHERE o.date NOT BETWEEN '2020-03-14' AND '2021-04-29'
GROUP BY s.day_name
ORDER BY avg_cars DESC;


-- 3. Fair comparison: each holiday vs a NORMAL day on the same weekday
--    (weekends are naturally busier, so a holiday Monday is compared
--     with an ordinary Monday, not with a Saturday)
WITH clean AS (                                   -- traffic + holiday label + weekday
    SELECT o.date,
           o.total_flow,
           s.day_name,
           EXTRACT(DOW FROM o.date) AS dow         -- 0 = Sunday ... 6 = Saturday
    FROM offramp_daily o
    LEFT JOIN special_days s ON o.date = s.date
    WHERE o.date NOT BETWEEN '2020-03-14' AND '2021-04-29'
),
baseline AS (                                     -- normal-day average per weekday
    SELECT dow, AVG(total_flow) AS normal_avg
    FROM clean
    WHERE day_name IS NULL
    GROUP BY dow
)
SELECT c.day_name,
       COUNT(*)                                               AS days,
       ROUND(AVG(c.total_flow))                               AS avg_cars,
       ROUND(AVG((c.total_flow / b.normal_avg - 1) * 100), 1) AS pct_vs_same_weekday
FROM clean c
JOIN baseline b ON c.dow = b.dow
WHERE c.day_name IS NOT NULL
GROUP BY c.day_name
ORDER BY pct_vs_same_weekday DESC;
-- Result: Monday long weekends +13% to +17% (MLK +16.7%);
--         Halloween -5.3%; Christmas Eve -19.7%
