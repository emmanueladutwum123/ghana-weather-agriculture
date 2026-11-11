"""US monthly imports of cocoa beans (HS 1801) from Ghana: US Census Bureau.

International Trade API, imports by HS code:
  https://api.census.gov/data/timeseries/intltrade/imports/hs
Ghana's Census country code is 7490. GEN_VAL_MO is general imports value
(US$), GEN_QY1_MO the first quantity (kg for HS 1801).

STATUS (11 Nov 2026): the API now redirects every request without a key to
https://api.census.gov/data/missing_key.html, so this series has NOT been
downloaded. A free key is available at
https://api.census.gov/data/key_signup.html. Put it in the environment as
CENSUS_API_KEY and rerun. This script has not yet been run against live data
with a key, so check its output the first time.

Raw: data/raw/uscensus/imports_hs1801_ghana.json
Clean: data/clean/uscensus_cocoa_imports_monthly.csv
"""
import json
import os
import sys

import pandas as pd

from common import CLEAN, RAW, get, save

API = ("https://api.census.gov/data/timeseries/intltrade/imports/hs"
       "?get=CTY_NAME,GEN_VAL_MO,GEN_QY1_MO,UNIT_QY1&CTY_CODE=7490&I_COMMODITY=1801"
       "&time=from+2002-01&key={key}")


def main():
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        print("US Census: SKIPPED. No CENSUS_API_KEY set; the API refuses requests without a key.")
        return
    r = get(API.format(key=key), timeout=120)
    # Log the URL without the key so the key never lands in the repository.
    path = save(r.content, RAW / "uscensus" / "imports_hs1801_ghana.json", API.format(key="REDACTED"),
                note="US Census intltrade imports HS1801 CTY 7490")
    rows = json.load(open(path))
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["year"] = df.time.str[:4].astype(int)
    df["month"] = df.time.str[5:7].astype(int)
    df["us_imports_usd_m"] = pd.to_numeric(df.GEN_VAL_MO) / 1e6
    units = set(df.UNIT_QY1)
    if units != {"KG"}:
        print(f"US Census: unexpected quantity units {units}; check before using tonnes", file=sys.stderr)
    df["us_imports_tonnes"] = pd.to_numeric(df.GEN_QY1_MO) / 1000
    out = df[["year", "month", "us_imports_tonnes", "us_imports_usd_m"]].sort_values(["year", "month"])
    out.to_csv(CLEAN / "uscensus_cocoa_imports_monthly.csv", index=False)
    print(f"US Census HS1801 from Ghana: {len(out)} months")


if __name__ == "__main__":
    main()
