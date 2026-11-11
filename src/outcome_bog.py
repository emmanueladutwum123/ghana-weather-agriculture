"""Bank of Ghana: monthly cocoa export values and international cocoa prices.

Two BoG sources, both value only. BoG does not publish monthly cocoa export
VOLUME in either place.

1. Online "Merchandise Trade Flows" table (wpDataTables id 30) on
   https://www.bog.gov.gh/economic-data/merchandise-trade-flows/
   Monthly, January 2005 to April 2023, US$ million, cocoa beans and cocoa
   products separately. Months not yet filled are shown as 0.00; these are
   set to missing, not zero.
2. Monthly Statistical Bulletin (Excel), latest edition listed on
   https://www.bog.gov.gh/publications/statistical-bulletin/
   Table 16: merchandise trade flows, US$ million, January 2013 onward.
   Table 18: commodity prices, cocoa LIFFE (GBP/t) and CSCE (US$/t), 2006 onward.

Combined series: the bulletin where it has data (it is the later release and
carries revisions), the online table before January 2013. Every month records
which source it came from, and data/clean/bog_overlap_check.csv lists both
values for the overlapping months so the revisions can be seen.

No licence statement was found on bog.gov.gh, so the raw files are not
committed (see .gitignore); this script downloads them.
"""
import json
import re

import numpy as np
import pandas as pd

from common import CLEAN, RAW, SESSION, check_not_html, fetch, get, save

PAGE = "https://www.bog.gov.gh/economic-data/merchandise-trade-flows/"
AJAX = "https://www.bog.gov.gh/wp-admin/admin-ajax.php?action=get_wdtable&table_id={}"
BULLETINS = "https://www.bog.gov.gh/publications/statistical-bulletin/"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
OUT = RAW / "bog"


def num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def online_table():
    html = get(PAGE, timeout=60).text
    nonce = re.search(r'wdtNonceFrontendServerSide_30" value="([a-z0-9]+)', html).group(1)
    r = SESSION.post(AJAX.format(30), timeout=120,
                     data={"draw": 1, "start": 0, "length": 20000, "wdtNonce": nonce})
    r.raise_for_status()
    path = save(r.content, OUT / "bog_wdtable30_merchandise_trade.json", AJAX.format(30),
                note="BoG online merchandise trade table, wpDataTables 30")
    rows = []
    for rec in json.load(open(path))["data"]:
        year, var = int(rec[0]), rec[1]
        if "Cocoa Beans" in var:
            item = "cocoa_beans"
        elif "Cocoa Products" in var:
            item = "cocoa_products"
        elif var.startswith("Merchandise Exports (f.o.b)"):
            item = "total_exports"
        else:
            continue
        for m, v in enumerate(rec[2:14], start=1):
            v = num(v)
            rows.append(dict(year=year, month=m, item=item,
                             value_usd_m=np.nan if v == 0 else v))  # 0.00 = not yet filled
    return pd.DataFrame(rows)


def latest_bulletin():
    html = get(BULLETINS, timeout=60).text
    links = sorted(set(re.findall(r'href="([^"]*Statistical-Bulletin-Monthly_[^"]*\.xlsx)"', html)))
    # File names look like ...Monthly_MAR_2026_APPROVED.xlsx; pick the latest month.
    def key(u):
        m = re.search(r"Monthly_([A-Z]{3})_(\d{4})", u)
        return (int(m.group(2)), [x.upper() for x in MONTHS].index(m.group(1))) if m else (0, 0)
    url = max(links, key=key)
    path = fetch(url, OUT / url.rsplit("/", 1)[1], note="BoG monthly statistical bulletin")
    check_not_html(path)
    return path, url


def bulletin_table16(path):
    d = pd.read_excel(path, sheet_name="16", header=None, engine="openpyxl")
    years = d.iloc[1].ffill()
    months = d.iloc[2]
    rows = []
    for r in range(3, len(d)):
        label = str(d.iat[r, 0]).strip()
        item = {"Cocoa Beans": "cocoa_beans", "Cocoa Products": "cocoa_products",
                "Merchandise Exports (f.o.b)": "total_exports"}.get(label)
        if not item:
            continue
        for c in range(1, d.shape[1]):
            mo = str(months.iat[c]).strip()[:3].title()
            if mo not in MONTHS or pd.isna(years.iat[c]):
                continue
            y = int(re.sub(r"\D", "", str(years.iat[c]))[:4])
            v = num(d.iat[r, c])
            rows.append(dict(year=y, month=MONTHS.index(mo) + 1, item=item, value_usd_m=v))
    return pd.DataFrame(rows)


def bulletin_table18(path):
    d = pd.read_excel(path, sheet_name="18", header=None, engine="openpyxl")
    hdr = d.iloc[1].astype(str)
    c_date = hdr[hdr.str.contains("Month")].index[0]
    c_liffe = hdr[hdr.str.contains("LIFFE")].index[0]
    c_csce = hdr[hdr.str.contains("CSCE")].index[0]
    rows = []
    for r in range(2, len(d)):
        t = pd.to_datetime(d.iat[r, c_date], errors="coerce")
        if pd.isna(t):
            continue
        rows.append(dict(year=t.year, month=t.month,
                         cocoa_liffe_gbp_t=num(d.iat[r, c_liffe]), cocoa_csce_usd_t=num(d.iat[r, c_csce])))
    return pd.DataFrame(rows)


def main():
    a = online_table().assign(source="BoG online table 30")
    path, url = latest_bulletin()
    b = bulletin_table16(path).assign(source=f"BoG Statistical Bulletin {path.name}")

    wide = lambda df: df.pivot_table(index=["year", "month"], columns="item", values="value_usd_m")
    ov = wide(a).merge(wide(b), left_index=True, right_index=True, suffixes=("_online", "_bulletin"), how="inner").reset_index()
    ov.to_csv(CLEAN / "bog_overlap_check.csv", index=False)

    # In some quarters the bulletin repeats one value for all three months: a
    # quarterly total divided by three, not monthly data (found for 2022 Q2,
    # where 3 x 91.06 equals the sum of the online table's three monthly
    # values). Drop those bulletin rows so the online monthly values are used.
    b = b.sort_values(["item", "year", "month"])
    v = b.value_usd_m.round(4)
    run = ((v != v.groupby(b.item).shift()) | (b.item != b.item.shift())).cumsum()
    flat = v.groupby(run).transform("size") >= 3
    b.loc[flat, "value_usd_m"] = np.nan
    if flat.any():
        f = b[flat]
        print("BoG bulletin: flat quarterly spreads set aside:",
              sorted(set(zip(f.year, f.month))))
    b_ok = b.dropna(subset=["value_usd_m"])
    keys = set(zip(b_ok.year, b_ok.month, b_ok.item))
    a_use = a[[k not in keys for k in zip(a.year, a.month, a.item)]].dropna(subset=["value_usd_m"])
    comb = pd.concat([a_use, b_ok]).sort_values(["item", "year", "month"])
    comb.to_csv(CLEAN / "bog_exports_monthly_long.csv", index=False)

    w = comb.pivot_table(index=["year", "month"], columns="item", values="value_usd_m").reset_index()
    w.columns.name = None
    w = w.rename(columns={c: f"bog_{c}_usd_m" for c in ["cocoa_beans", "cocoa_products", "total_exports"]})
    w.to_csv(CLEAN / "bog_exports_monthly.csv", index=False)

    p = bulletin_table18(path)
    p.to_csv(CLEAN / "bog_cocoa_prices_monthly.csv", index=False)

    s = w.dropna(subset=["bog_cocoa_beans_usd_m"])
    beans = ov.dropna(subset=["cocoa_beans_online", "cocoa_beans_bulletin"])
    diff = (beans.cocoa_beans_bulletin - beans.cocoa_beans_online).abs()
    print(f"BoG cocoa bean exports: {len(s)} months, {s.year.iloc[0]}-{s.month.iloc[0]:02d} to "
          f"{s.year.iloc[-1]}-{s.month.iloc[-1]:02d}; overlap {len(beans)} months, "
          f"{(diff > 0.05).sum()} differ by more than US$0.05m (max {diff.max():.2f})")
    print(f"BoG cocoa prices: {len(p)} months to {p.year.iloc[-1]}-{p.month.iloc[-1]:02d}")


if __name__ == "__main__":
    main()
