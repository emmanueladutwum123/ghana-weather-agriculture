"""NASA POWER monthly point weather for nine towns (one per region in the three zones).

Source: NASA Langley POWER project, monthly point API, community=AG.
  https://power.larc.nasa.gov/api/temporal/monthly/point
Variables:
  PRECTOTCORR  bias-corrected precipitation, mm/day (monthly mean of daily values)
  T2M, T2M_MAX, T2M_MIN  air temperature at 2 m, deg C (monthly mean, max, min)
  RH2M         relative humidity at 2 m, percent
The grid is about 0.5 x 0.625 degrees (roughly 55 x 70 km), so each "site" is
the grid cell containing the town, not a station.

Raw: one JSON file per site in data/raw/nasa_power/.
Clean: data/clean/nasa_power_site_monthly.csv
"""
import datetime as dt
import json

import pandas as pd

from common import CLEAN, RAW, SITES, fetch

API = "https://power.larc.nasa.gov/api/temporal/monthly/point"
PARAMS = "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M"
START = 1981
END = dt.date.today().year


def main():
    rows = []
    for site, s in SITES.items():
        url = (f"{API}?parameters={PARAMS}&community=AG&latitude={s['lat']}"
               f"&longitude={s['lon']}&start={START}&end={END}&format=JSON")
        path = fetch(url, RAW / "nasa_power" / f"{site}.json", note=f"NASA POWER monthly point {site}")
        par = json.load(open(path))["properties"]["parameter"]
        for ym in par["PRECTOTCORR"]:
            if ym.endswith("13"):  # month 13 is the annual value
                continue
            row = dict(site=site, region=s["region"], zone=s["zone"], lat=s["lat"], lon=s["lon"],
                       year=int(ym[:4]), month=int(ym[4:]))
            for p in par:
                v = par[p][ym]
                row[p] = None if v in (-999, -999.0) else v  # -999 = not yet available
            rows.append(row)
    df = pd.DataFrame(rows)
    days = pd.to_datetime(dict(year=df.year, month=df.month, day=1)).dt.days_in_month
    df["rain_mm"] = df["PRECTOTCORR"] * days  # mm/day times days in month
    df = df.rename(columns={"T2M": "tmean_c", "T2M_MAX": "tmax_c", "T2M_MIN": "tmin_c",
                            "RH2M": "rh_pct", "PRECTOTCORR": "rain_mm_per_day"})
    df = df.dropna(subset=["rain_mm_per_day", "tmean_c"], how="all")
    out = CLEAN / "nasa_power_site_monthly.csv"
    df.to_csv(out, index=False, float_format="%.3f")
    ym = (df.dropna(subset=["rain_mm"]).assign(ym=lambda d: d.year * 100 + d.month).groupby("site").ym.max().min())
    print(f"NASA POWER: {len(df)} rows, {df.site.nunique()} sites, from {df.year.min()}, "
          f"complete for all sites to {ym // 100}-{ym % 100:02d}")


if __name__ == "__main__":
    main()
