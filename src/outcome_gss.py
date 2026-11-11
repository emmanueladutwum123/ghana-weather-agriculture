"""Ghana Statistical Service: quarterly GDP by agricultural sub-sector and the
Monthly Indicator of Economic Growth (MIEG).

The GSS site lists files through a JSON API,
  https://statsghana.gov.gh/api/economic-statistics/national-accounts
and serves each file from
  https://statsghana.gov.gh/api/minio/file?key=<downloadKey>
This script reads the listing and downloads the latest edition of:
  1. "Rebased_GDP_quarterly_bulletin_2006_..." (Excel). Sheet "Constant GDP_Agric":
     quarterly value added at constant 2013 prices, GHS million, for
     Crops & Cocoa (which includes cocoa), Cocoa, Livestock, Forestry & Logging,
     Fishing, from 2006 Q1. Revised and provisional quarters are marked
     with * and ** in the file; the flag is kept.
  2. "MIEG Bulletin" (.xlsb). Sheet "MIEG": monthly index (2023 = 100) for the
     whole economy and for agriculture (crops, fisheries, forestry; livestock
     excluded), January 2023 onward. GSS writes 0 for year-on-year growth in
     2023, the base year with no prior year; those 0s are set to missing.
     GSS notes the index is not seasonally adjusted.

No licence statement was found on statsghana.gov.gh, so raw files are not
committed; this script downloads them.

Clean: data/clean/gss_qgdp_agric_constant2013.csv
       data/clean/gss_mieg_monthly.csv
"""
import json
import re
import urllib.parse

import numpy as np
import pandas as pd

from common import CLEAN, RAW, check_not_html, fetch, save, get

LIST = "https://statsghana.gov.gh/api/economic-statistics/national-accounts"
FILE = "https://statsghana.gov.gh/api/minio/file?key="
OUT = RAW / "gss"


def latest(rows, pattern, ext):
    hits = [r for r in rows if re.search(pattern, r.get("downloadKey", ""), re.I)
            and r["downloadKey"].lower().endswith(ext)]
    if not hits:
        raise LookupError(f"GSS: no file matching {pattern}")
    # Edition order: the bulletin name carries the last quarter covered, e.g. 2006_2026Q2.
    def key(r):
        m = re.search(r"(\d{4})Q(\d)", r["downloadKey"])
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        mo = next((i for i, m_ in enumerate(months) if m_ in r["downloadKey"].lower()), 0)
        return (int(m.group(1)), int(m.group(2))) if m else (int(r.get("year") or 0), mo)
    return max(hits, key=key)["downloadKey"]


def download(key):
    url = FILE + urllib.parse.quote(key)
    path = fetch(url, OUT / key.rsplit("/", 1)[1], note="GSS national accounts file")
    check_not_html(path)
    return path


def qgdp(path):
    d = pd.read_excel(path, sheet_name="Constant GDP_Agric", header=None, engine="openpyxl")
    hdr_row = d.index[d.iloc[:, 3].astype(str).str.contains("Crops", na=False)][0]
    names = d.iloc[hdr_row].tolist()
    rows = []
    for r in range(hdr_row + 1, len(d)):
        lab = str(d.iat[r, 1])
        m = re.match(r"\s*(\d{4})_Q(\d)\s*(\**)", lab)
        if not m:
            continue
        rec = dict(year=int(m.group(1)), quarter=int(m.group(2)),
                   status={"": "final", "*": "revised", "**": "provisional"}.get(m.group(3), m.group(3)))
        for c in range(3, d.shape[1]):
            nm = str(names[c]).strip()
            if nm and nm != "nan":
                col = re.sub(r"[^a-z0-9]+", "_", nm.lower()).strip("_")
                rec[col] = pd.to_numeric(d.iat[r, c], errors="coerce")
        rows.append(rec)
    return pd.DataFrame(rows)


def mieg(path):
    m = pd.read_excel(path, sheet_name="MIEG", engine="calamine")
    m = m[pd.to_datetime(m["month"], errors="coerce").notna()].copy()
    t = pd.to_datetime(m["month"])
    m["year"], m["month"] = t.dt.year, t.dt.month
    for c in [c for c in m.columns if c.endswith("_yony")]:
        m.loc[m.year == 2023, c] = np.nan  # base year: GSS writes 0, meaning not available
    keep = ["year", "month", "mieg_index", "mieg_index_agri", "mieg_index_yony", "mieg_index_agri_yony"]
    return m[keep]


def main():
    r = get(LIST, timeout=60)
    save(r.content, OUT / "national_accounts_listing.json", LIST, note="GSS file listing")
    rows = json.loads(r.content)["rows"]
    q = qgdp(download(latest(rows, r"Rebased_GDP_quarterly_bul+etin_2006_\d{4}Q\d", ".xlsx")))
    q.to_csv(CLEAN / "gss_qgdp_agric_constant2013.csv", index=False, float_format="%.3f")
    m = mieg(download(latest([x for x in rows if x.get("category") == "MIEG"], r"MIEG.*Bulletin|Bulletin.*MIEG", ".xlsb")))
    m.to_csv(CLEAN / "gss_mieg_monthly.csv", index=False, float_format="%.4f")
    print(f"GSS quarterly agric GDP: {len(q)} quarters, {q.year.iloc[0]}Q{q.quarter.iloc[0]} to "
          f"{q.year.iloc[-1]}Q{q.quarter.iloc[-1]}; columns {[c for c in q.columns if c not in ('year','quarter','status')]}")
    print(f"GSS MIEG: {len(m)} months, {m.year.iloc[0]}-{m.month.iloc[0]:02d} to {m.year.iloc[-1]}-{m.month.iloc[-1]:02d}")

    c = regional_food_cpi()
    c.to_csv(CLEAN / "gss_cpi_food_region_monthly.csv", index=False, float_format="%.4f")
    print(f"GSS regional food CPI: {c.region.nunique()} regions, {len(c)} rows, "
          f"{c.year.min()}-{c[c.year == c.year.min()].month.min():02d} to "
          f"{c.year.max()}-{c[c.year == c.year.max()].month.max():02d}")


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def regional_food_cpi():
    """GSS CPI COICOP Annexes, Annex 3: monthly CPI by region and COICOP group
    (average 2021 = 100). Only the food and non-alcoholic beverages index is
    kept. The latest edition is used; older editions on earlier bases are not
    spliced on."""
    lst = "https://statsghana.gov.gh/api/economic-statistics/price-index"
    r = get(lst, timeout=60)
    save(r.content, OUT / "price_index_listing.json", lst, note="GSS price index file listing")
    rows = [x for x in json.loads(r.content)["rows"] if x.get("category") == "CPI COICOP Annexes"
            and x.get("downloadKey", "").lower().endswith(".xlsx")]
    full = [m.title() for m in ["January", "February", "March", "April", "May", "June", "July",
                                "August", "September", "October", "November", "December"]]
    key = max(rows, key=lambda x: (int(x["year"]), full.index(x["month"]) if x["month"] in full else -1))["downloadKey"]
    path = download(key)
    d = pd.read_excel(path, sheet_name="Annex3-CPI by Region", header=None, engine="openpyxl")
    food_col = next(c for c in range(d.shape[1]) if str(d.iat[2, c]).startswith("Food"))
    out, region = [], None
    for i in range(3, len(d)):
        lab = str(d.iat[i, 1]).strip()
        m = re.fullmatch(r"([A-Z]{3})_(\d{4})", lab.upper())
        # A region header is a text label with no value beside it (editions write
        # either "WESTERN REGION" or "WESTERN").
        if (not m and lab.upper() not in ("WEIGHT", "NAN", "") and pd.isna(d.iat[i, 2])
                and re.fullmatch(r"[A-Za-z ]+", lab)):
            region = lab.upper().removesuffix(" REGION").title()
            continue
        if region and m and m.group(1) in MONTHS:
            out.append(dict(region=region, year=int(m.group(2)), month=MONTHS.index(m.group(1)) + 1,
                            cpi_food=pd.to_numeric(d.iat[i, food_col], errors="coerce"),
                            source_file=path.name))
    return pd.DataFrame(out)


if __name__ == "__main__":
    main()
