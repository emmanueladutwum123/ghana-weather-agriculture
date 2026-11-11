"""EU monthly imports of cocoa beans (HS 1801) from Ghana: Eurostat Comext.

Dataset DS-045409 "EU trade since 1988 by HS2-4-6 and CN8", via the Comext
dissemination API:
  https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409
Query: freq=M, reporter=EU27_2020 (the EU in its current 27-member
composition, applied to all years), partner=GH, product=1801, flow=1 (imports).
Indicators: VALUE_IN_EUROS and QUANTITY_IN_100KG.
For extra-EU imports the partner is the country of origin.

The United Kingdom is not part of EU27_2020 in any year, so UK imports of
Ghanaian cocoa are not in this series.

Licence: Eurostat data may be reused with acknowledgement (Commission Decision
2011/833/EU). Raw JSON is committed.

Raw: data/raw/eurostat/comext_1801_GH_{year}.json
Clean: data/clean/eurostat_cocoa_imports_monthly.csv
"""
import datetime as dt
import json

import pandas as pd

from common import CLEAN, RAW, fetch

API = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409"
       "?format=JSON&lang=en&freq=M&reporter=EU27_2020&partner=GH&product=1801&flow=1"
       "&indicators=VALUE_IN_EUROS&indicators=QUANTITY_IN_100KG")


def parse(js):
    """Decode a JSON-stat 2.0 response into (time, indicator, value) rows."""
    dims = js["id"]
    sizes = js["size"]
    cats = {d: {v: k for k, v in js["dimension"][d]["category"]["index"].items()} for d in dims}
    rows = []
    for flat, val in js.get("value", {}).items():
        idx, rem = {}, int(flat)
        for d, n in zip(reversed(dims), reversed(sizes)):
            idx[d] = cats[d][rem % n]
            rem //= n
        rows.append(dict(time=idx["time"], indicator=idx["indicators"], value=val))
    return rows


def main():
    rows = []
    this_year = dt.date.today().year
    for y in range(2002, this_year + 1):
        url = API + "".join(f"&time={y}-{m:02d}" for m in range(1, 13))
        path = fetch(url, RAW / "eurostat" / f"comext_1801_GH_{y}.json",
                     note="Eurostat Comext DS-045409, EU27_2020 imports HS1801 from GH",
                     refresh=(y >= this_year - 1))  # recent years are revised; always refresh
        js = json.load(open(path))
        if "error" in js:
            print(f"Eurostat {y}: {js['error']}")
            continue
        rows += parse(js)
    df = pd.DataFrame(rows).pivot_table(index="time", columns="indicator", values="value").reset_index()
    df["year"] = df.time.str[:4].astype(int)
    df["month"] = df.time.str[5:7].astype(int)
    df["eu_imports_tonnes"] = df["QUANTITY_IN_100KG"] / 10
    df["eu_imports_eur_m"] = df["VALUE_IN_EUROS"] / 1e6
    out = df[["year", "month", "eu_imports_tonnes", "eu_imports_eur_m"]].sort_values(["year", "month"])
    out.to_csv(CLEAN / "eurostat_cocoa_imports_monthly.csv", index=False, float_format="%.3f")
    print(f"Eurostat HS1801 from Ghana: {len(out)} months, {out.year.iloc[0]}-{out.month.iloc[0]:02d} "
          f"to {out.year.iloc[-1]}-{out.month.iloc[-1]:02d}")


if __name__ == "__main__":
    main()
