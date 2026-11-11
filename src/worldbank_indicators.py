"""World Bank World Development Indicators for Ghana, annual, for background.

API: https://api.worldbank.org/v2/country/GHA/indicator/{code}?format=json
Licence: CC BY 4.0.

Raw: data/raw/worldbank/wdi_{code}.json
Clean: data/clean/worldbank_ghana_annual.csv
"""
import json

import pandas as pd

from common import CLEAN, RAW, fetch

WB = {"NV.AGR.TOTL.ZS": "agri_value_added_pct_gdp",
      "NV.AGR.TOTL.KD.ZG": "agri_value_added_growth_pct",
      "SL.AGR.EMPL.ZS": "agri_employment_pct",
      "AG.YLD.CREL.KG": "cereal_yield_kg_ha",
      "FP.CPI.TOTL.ZG": "cpi_inflation_pct"}


def main():
    frames = []
    for code, label in WB.items():
        url = f"https://api.worldbank.org/v2/country/GHA/indicator/{code}?format=json&per_page=200"
        path = fetch(url, RAW / "worldbank" / f"wdi_{code}.json", note=f"World Bank WDI {code}")
        j = json.load(open(path))
        frames.append(pd.DataFrame([dict(year=int(d["date"]), indicator=label, value=d["value"])
                                    for d in j[1]]))
    df = pd.concat(frames).pivot(index="year", columns="indicator", values="value").sort_index()
    df.to_csv(CLEAN / "worldbank_ghana_annual.csv")
    print(f"World Bank WDI: {len(WB)} indicators, {df.index.min()}-{df.index.max()}")


if __name__ == "__main__":
    main()
