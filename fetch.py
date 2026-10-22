"""
fetch.py — download CAISO day-ahead and real-time prices and solar output,
reshape to 24 rows per day, and save as CSV.

Output columns: date, hour, p_d, p_r, solar
  p_d   day-ahead hourly price ($/MWh)
  p_r   real-time price, 15-minute intervals averaged to hourly ($/MWh)
  solar CAISO system solar output, averaged to hourly (MW); build.py rescales it to one plant
"""

import time

import pandas as pd
import gridstatus
from gridstatus import Markets

LOCATION = "TH_SP15_GEN-APND"   # southern California trading hub
START = "2025-06-01"
END = "2025-06-07"              # inclusive
OUT = "caiso_sp15.csv"


def to_hourly(df, value_col, location=None):
    """Turn a raw table into one hourly-averaged column. Handles column names across gridstatus versions."""
    if location is not None and "Location" in df.columns:
        df = df[df["Location"] == location]
    time_col = "Interval Start" if "Interval Start" in df.columns else "Time"
    s = df.set_index(time_col)[value_col].astype(float)
    return s.resample("h").mean().rename_axis("start")


def fetch_day(caiso, day):
    da = caiso.get_lmp(date=day, market=Markets.DAY_AHEAD_HOURLY, locations=[LOCATION])
    rt = caiso.get_lmp(date=day, market=Markets.REAL_TIME_15_MIN, locations=[LOCATION])
    mix = caiso.get_fuel_mix(day)

    out = pd.concat(
        {
            "p_d": to_hourly(da, "LMP", LOCATION),
            "p_r": to_hourly(rt, "LMP", LOCATION),
            "solar": to_hourly(mix, "Solar"),
        },
        axis=1,
    ).dropna()

    # daylight-saving changeover days have 23 or 25 hours; skip them for now
    if len(out) != 24:
        raise ValueError(f"got {len(out)} hours instead of 24")

    out = out.reset_index()
    out.insert(0, "hour", out["start"].dt.hour)
    out.insert(0, "date", day)
    return out.drop(columns="start")


def main():
    caiso = gridstatus.CAISO()
    days = []
    for d in pd.date_range(START, END, freq="D"):
        day = d.strftime("%Y-%m-%d")
        try:
            days.append(fetch_day(caiso, day))
            print(f"{day}: ok")
        except Exception as e:
            print(f"{day}: skipped ({e})")
        time.sleep(1)   # do not request too fast

    if days:
        pd.concat(days, ignore_index=True).to_csv(OUT, index=False)
        print(f"saved {len(days)} days to {OUT}")


if __name__ == "__main__":
    main()
