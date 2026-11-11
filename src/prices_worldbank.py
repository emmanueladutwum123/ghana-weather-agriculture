"""World Bank Commodity Price Data ("Pink Sheet"), monthly, nominal US$.

The current file link is read from https://www.worldbank.org/en/research/commodity-markets
each run, because the URL changes with each release. The link in the original
get_data.py pointed to the January 2025 file.

Series used: Cocoa (US$/kg; the World Bank's source for cocoa is the ICCO
daily price average), Maize (US$/mt), Rice Thai 5% (US$/mt).
Licence: CC BY 4.0. Raw Excel is committed.

Raw: data/raw/worldbank/CMO-Historical-Data-Monthly.xlsx
Clean: data/clean/worldbank_prices_monthly.csv
"""
import re

import pandas as pd

from common import CLEAN, RAW, check_not_html, fetch, get

PAGE = "https://www.worldbank.org/en/research/commodity-markets"
WANT = {"Cocoa": "wb_cocoa_usd_kg", "Maize": "wb_maize_usd_t", "Rice, Thai 5% ": "wb_rice_thai5_usd_t"}


def main():
    html = get(PAGE, timeout=60).text
    url = re.search(r"https://thedocs\.worldbank\.org/[^\"']*CMO-Historical-Data-Monthly\.xlsx", html).group(0)
    path = fetch(url, RAW / "worldbank" / "CMO-Historical-Data-Monthly.xlsx",
                 note="World Bank Pink Sheet monthly", refresh=True)
    check_not_html(path)
    d = pd.read_excel(path, sheet_name="Monthly Prices", header=None, engine="openpyxl")
    updated = str(d.iat[3, 0])
    hdr = d.iloc[4].fillna("").astype(str)
    cols = {}
    for name, out in WANT.items():
        hit = [i for i, h in enumerate(hdr) if h.strip() == name.strip()]
        if not hit:
            raise KeyError(f"Pink Sheet column {name!r} not found")
        cols[hit[0]] = out
    body = d.iloc[6:, [0] + list(cols)].copy()
    body.columns = ["period"] + list(cols.values())
    body = body[body.period.astype(str).str.match(r"\d{4}M\d{2}")]
    body["year"] = body.period.str[:4].astype(int)
    body["month"] = body.period.str[5:7].astype(int)
    for c in cols.values():
        body[c] = pd.to_numeric(body[c], errors="coerce")  # ".." and "…" mean not available
    body = body.drop(columns="period").dropna(subset=list(cols.values()), how="all")
    body[["year", "month"] + list(cols.values())].to_csv(CLEAN / "worldbank_prices_monthly.csv", index=False)
    print(f"Pink Sheet ({updated}): {len(body)} months to {body.year.iloc[-1]}-{body.month.iloc[-1]:02d}; "
          f"file {url.rsplit('/', 3)[1][:12]}...")


if __name__ == "__main__":
    main()
