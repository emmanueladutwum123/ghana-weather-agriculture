"""WFP food prices for Ghana, by market and commodity, via HDX.

  https://data.humdata.org/dataset/wfp-food-prices-for-ghana
Licence: CC BY-IGO. Raw CSVs are committed.

On 11 Nov 2026 the HDX dataset ran from January 2006 to July 2023 only (HDX
"dataset_date" [2006-01-15 TO 2023-07-15]), although the dataset page was
modified on 8 Nov 2026. There is no WFP price after July 2023 in this source.
WFP dates each monthly price on the 15th.

Raw: data/raw/wfp/wfp_food_prices_gha.csv, wfp_markets_gha.csv, hdx_metadata.json
Clean: data/clean/wfp_prices_long.csv (one row per market, commodity, unit,
       price type, month), and data/clean/wfp_prices_monthly_national.csv
       (median across markets of selected staples, GHS per kg).
"""
import json
import re

import pandas as pd

from common import CLEAN, RAW, check_not_html, fetch, get, save

META = "https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-ghana"
STAPLES = ["Maize", "Maize (yellow)", "Rice (local)", "Rice (imported)", "Yam", "Cassava",
           "Millet", "Sorghum", "Gari", "Cowpeas", "Plantains"]


def unit_kg(unit):
    """Convert WFP unit strings such as '100 KG', 'KG', '91 KG' to kilograms. Others -> None."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)?\s*KG\s*", str(unit).upper())
    if not m:
        return None
    return float(m.group(1)) if m.group(1) else 1.0


def main():
    r = get(META, timeout=60)
    save(r.content, RAW / "wfp" / "hdx_metadata.json", META, note="HDX package metadata")
    meta = r.json()["result"]
    for res in meta["resources"]:
        url = res["url"]
        if url.lower().endswith(".csv"):
            p = fetch(url, RAW / "wfp" / url.rsplit("/", 1)[1].split("?")[0],
                      note=f"WFP via HDX, {res['name']}", refresh=True)
            check_not_html(p)

    df = pd.read_csv(RAW / "wfp" / "wfp_food_prices_gha.csv", low_memory=False)
    df = df[df.date.astype(str).str.match(r"\d{4}-\d{2}-\d{2}")]  # drop HXL tag row if present
    df["date"] = pd.to_datetime(df.date)
    df["year"], df["month"] = df.date.dt.year, df.date.dt.month
    df["price"] = pd.to_numeric(df.price, errors="coerce")
    df["kg"] = df.unit.map(unit_kg)
    df["price_ghs_per_kg"] = df.price / df.kg
    keep = ["year", "month", "admin1", "admin2", "market", "latitude", "longitude", "category",
            "commodity", "unit", "pricetype", "priceflag", "currency", "price", "price_ghs_per_kg", "usdprice"]
    df[keep].sort_values(["commodity", "market", "year", "month"]).to_csv(
        CLEAN / "wfp_prices_long.csv", index=False)

    st = df[df.commodity.isin(STAPLES) & df.kg.notna() & (df.currency == "GHS")]
    nat = (st.groupby(["year", "month", "commodity", "pricetype"])
             .agg(price_ghs_per_kg_median=("price_ghs_per_kg", "median"), n_markets=("market", "nunique"))
             .reset_index())
    nat.to_csv(CLEAN / "wfp_prices_monthly_national.csv", index=False, float_format="%.4f")
    print(f"WFP: {len(df)} price rows, {df.market.nunique()} markets, {df.commodity.nunique()} commodities, "
          f"{df.date.min():%Y-%m} to {df.date.max():%Y-%m}; units not in kg dropped from national file: "
          f"{sorted(set(df[df.commodity.isin(STAPLES) & df.kg.isna()].unit))}")


if __name__ == "__main__":
    main()
