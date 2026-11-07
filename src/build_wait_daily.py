# Daily average wait times from the Jester565/DisneylandData ride log (2017-2018).
# Only Disneyland Park, 10am-9pm, days with at least 15 rides reporting.
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "external"
DISNEYLAND_PARK = 330339
HEADLINERS = ["Space Mountain", "Indiana Jones", "Matterhorn", "Haunted Mansion",
              "Big Thunder", "Pirates of the Caribbean", "Peter Pan", "Splash Mountain",
              "Star Tours", "Finding Nemo"]

rides = pd.read_csv(next(EXT.glob("DisneylandData-*/rides.csv")))
park_rides = rides[rides["parkID"] == DISNEYLAND_PARK]
headliner_ids = park_rides[park_rides["name"].str.contains("|".join(HEADLINERS), case=False)]["id"]

waits = pd.read_csv(EXT / "disneyRideTimes.csv", na_values="NULL",
                    usecols=["rideID", "dateTime", "waitMins", "status"])
waits = waits[waits["rideID"].isin(park_rides["id"])
              & (waits["status"] == "Operating")].dropna(subset=["waitMins"])
waits["dateTime"] = pd.to_datetime(waits["dateTime"])
waits = waits[waits["dateTime"].dt.hour.between(10, 20)]       # 10 AM - 9 PM, park daytime
waits["date"] = waits["dateTime"].dt.normalize()

daily = waits.groupby("date").agg(avg_wait_all=("waitMins", "mean"),
                                  rides_reporting=("rideID", "nunique"))
daily["avg_wait_headliners"] = (waits[waits["rideID"].isin(headliner_ids)]
                                .groupby("date")["waitMins"].mean())
daily = daily[daily["rides_reporting"] >= 15].round(1).reset_index()   # drop thin days
daily.to_csv(ROOT / "data" / "wait_daily.csv", index=False)
print(f"{len(daily)} days, {daily['date'].min():%Y-%m-%d} to {daily['date'].max():%Y-%m-%d}")
print("headliners matched:", sorted(park_rides[park_rides['id'].isin(headliner_ids)]['name']))
