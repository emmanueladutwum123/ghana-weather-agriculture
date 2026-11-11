"""CRU TS 4.09 monthly climate for Ghana (national average), via the World Bank
Climate Change Knowledge Portal (CCKP) API. Licence: CC BY 4.0.

  https://cckpapi.worldbank.org/cckp/v1/cru-x0.5_timeseries_{var}_timeseries_monthly_1901-2024_mean_historical_cru_ts4.09_mean/GHA?_format=json

Variables: pr (precipitation, mm/month), tas, tasmax, tasmin (deg C).
Coverage: January 1901 to December 2024.
The API returned empty results for every sub-national code format tried
(GHA.1, GHA.1_1, GHA.2_1 and others), so only the national series is used.

Raw: data/raw/cru_cckp/{var}.json
Clean: data/clean/cru_national_monthly.csv
"""
import json

import pandas as pd

from common import CLEAN, RAW, fetch

URL = ("https://cckpapi.worldbank.org/cckp/v1/cru-x0.5_timeseries_{v}_timeseries_monthly_"
       "1901-2024_mean_historical_cru_ts4.09_mean/GHA?_format=json")
VARS = {"pr": "rain_mm", "tas": "tmean_c", "tasmax": "tmax_c", "tasmin": "tmin_c"}


def main():
    frames = []
    for v, name in VARS.items():
        path = fetch(URL.format(v=v), RAW / "cru_cckp" / f"{v}.json", note=f"CRU TS4.09 via CCKP, {v}, Ghana")
        d = json.load(open(path))["data"]["GHA"]
        s = pd.Series(d, name=name)
        s.index = pd.MultiIndex.from_tuples([(int(k[:4]), int(k[5:7])) for k in s.index],
                                            names=["year", "month"])
        frames.append(s)
    df = pd.concat(frames, axis=1).reset_index()
    df.to_csv(CLEAN / "cru_national_monthly.csv", index=False)
    print(f"CRU (CCKP): {len(df)} months, {df.year.min()}-{df.year.max()}, "
          f"missing values: {int(df[list(VARS.values())].isna().sum().sum())}")


if __name__ == "__main__":
    main()
