"""Package the merged panels as one dataset for readers who do not run the code.

Writes to dataset/:
  ghana_weather_agriculture_dataset.xlsx  README, Sources, Codebook, then one
      sheet per panel (values exactly as in data/panel/*.csv).
  codebook.csv                            one row per panel column.
  ghana_weather_agriculture_dataset.zip   the panel CSVs, codebook.csv and
      data/README.md, for use in Stata, R or Python.

Every column of every panel must have a codebook entry; the script stops
with an error if one does not, so no column ships undocumented.
"""
import datetime as dt
import re
import zipfile

import pandas as pd
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from common import PANEL, ROOT, ZONES

OUT = ROOT / "dataset"
STEM = "ghana_weather_agriculture_dataset"

ZONE_TEXT = {
    "cocoa": "cocoa zone (" + ", ".join(ZONES["cocoa"]) + ")",
    "transition": "transition zone (" + ", ".join(ZONES["transition"]) + ")",
    "cereal": "cereal zone (" + ", ".join(ZONES["cereal"]) + ")",
}
NASA_ZONE_TEXT = {
    "cocoa": "cocoa zone (Sefwi Wiawso, Tarkwa, Kumasi, Assin Foso, Koforidua)",
    "transition": "transition zone (Techiman)",
    "cereal": "cereal zone (Tamale, Tumu, Bolgatanga)",
}
VAR = {"rain_mm": ("rainfall", "mm"), "tmean_c": ("mean air temperature at 2 m", "deg C"),
       "tmax_c": ("maximum air temperature at 2 m", "deg C"), "tmin_c": ("minimum air temperature at 2 m", "deg C"),
       "rh_pct": ("relative humidity at 2 m", "percent")}

PANELS = [
    ("national_monthly", "panel_national_monthly.csv",
     "One row per month from January 1981. Zone weather, national weather, Nino 3.4, cocoa exports and "
     "prices, EU cocoa imports, GSS monthly growth index and WFP national median food prices."),
    ("national_quarterly", "panel_national_quarterly.csv",
     "One row per quarter, 2006 Q1 to 2026 Q2. GSS agricultural GDP (constant 2013 prices) with quarterly weather."),
    ("national_annual", "panel_national_annual.csv",
     "One row per year from 1961. FAOSTAT and MoFA crop area and production with annual rainfall."),
    ("region_monthly", "panel_region_monthly.csv",
     "One row per region and month. CHIRPS rainfall (16 regions), NASA POWER point weather "
     "(9 regions with a site) and GSS regional food CPI."),
    ("market_monthly", "panel_market_monthly.csv",
     "One row per WFP market, commodity, price type and month, 2006 to July 2023, with the CHIRPS "
     "rainfall of the region the market lies in."),
]

SRC = {
    "chirps": "CHIRPS v2.0, Climate Hazards Center, UC Santa Barbara",
    "nasa": "NASA POWER monthly point API",
    "cru": "CRU TS 4.09 via World Bank Climate Change Knowledge Portal",
    "nino": "NOAA Climate Prediction Center",
    "bog": "Bank of Ghana (online trade table and Monthly Statistical Bulletin)",
    "eu": "Eurostat Comext DS-045409",
    "wb": "World Bank Commodity Price Data (Pink Sheet)",
    "mieg": "Ghana Statistical Service, Monthly Indicator of Economic Growth",
    "wfp": "World Food Programme via HDX",
    "gss_q": "Ghana Statistical Service, Rebased quarterly GDP, Sept 2026 edition",
    "fao": "FAOSTAT Crops and Livestock Products",
    "mofa": "MoFA SRID, Agriculture in Ghana: Facts and Figures (latest edition reporting the year)",
    "cpi": "Ghana Statistical Service, CPI COICOP Annexes, Oct 2026",
    "geo": "geoBoundaries gbOpen GHA ADM1",
}

FIXED = {
    "year": ("Calendar year", "", ""),
    "month": ("Calendar month (1 to 12)", "", ""),
    "quarter": ("Calendar quarter (1 to 4)", "", ""),
    "date": ("Month as YYYY-MM", "", ""),
    "region": ("Region (16 regions in force since 2018)", "", SRC["geo"]),
    "zone": ("Agro-ecological zone used in this project (cocoa, transition, cereal); empty for other regions", "", ""),
    "nasa_site": ("Town whose NASA POWER grid cell represents the region", "", SRC["nasa"]),
    "nasa_rain_flag": ("True for June 2026, when NASA POWER rainfall is 3 to 10 SD above each site's June mean; "
                       "kept, not dropped (see data/README.md)", "True/False", SRC["nasa"]),
    "nasa_rain_flag_2026_06": ("True for June 2026 (NASA POWER rainfall outlier, see data/README.md)", "True/False", SRC["nasa"]),
    "chirps_n_cells": ("Number of CHIRPS 0.05 degree grid cells averaged for the region", "count", SRC["chirps"]),
    "gss_cpi_food": ("Food and non-alcoholic beverages CPI for the region", "index, 2021 = 100", SRC["cpi"]),
    "nino34_ersst_sst_c": ("Nino 3.4 sea surface temperature, ERSSTv5", "deg C", SRC["nino"]),
    "nino34_ersst_anom_c": ("Nino 3.4 anomaly vs 1991 to 2020, ERSSTv5", "deg C", SRC["nino"]),
    "nino34_oisst_sst_c": ("Nino 3.4 sea surface temperature, OISSTv2", "deg C", SRC["nino"]),
    "nino34_oisst_anom_c": ("Nino 3.4 anomaly vs 1991 to 2020, OISSTv2", "deg C", SRC["nino"]),
    "bog_cocoa_beans_usd_m": ("Value of cocoa bean exports, fob", "US$ million", SRC["bog"]),
    "bog_cocoa_products_usd_m": ("Value of cocoa product exports, fob (monthly from Jan 2020 only)", "US$ million", SRC["bog"]),
    "bog_total_exports_usd_m": ("Value of total merchandise exports, fob", "US$ million", SRC["bog"]),
    "bog_cocoa_liffe_gbp_t": ("Cocoa price, LIFFE, monthly average", "GBP per tonne", SRC["bog"] + " Table 18 (Reuters)"),
    "bog_cocoa_csce_usd_t": ("Cocoa price, CSCE, monthly average", "US$ per tonne", SRC["bog"] + " Table 18 (Reuters)"),
    "eu_imports_tonnes": ("EU27 (2020 membership) imports of cocoa beans (HS 1801) from Ghana, quantity", "tonnes", SRC["eu"]),
    "eu_imports_eur_m": ("EU27 (2020 membership) imports of cocoa beans (HS 1801) from Ghana, value", "EUR million", SRC["eu"]),
    "wb_cocoa_usd_kg": ("Cocoa price (ICCO daily average)", "US$ per kg", SRC["wb"]),
    "wb_maize_usd_t": ("Maize price", "US$ per tonne", SRC["wb"]),
    "wb_rice_thai5_usd_t": ("Rice price, Thai 5% broken", "US$ per tonne", SRC["wb"]),
    "mieg_index": ("Monthly Indicator of Economic Growth, whole economy (not seasonally adjusted)", "index, 2023 = 100", SRC["mieg"]),
    "mieg_index_agri": ("MIEG agriculture index (crops, fisheries, forestry; excludes livestock)", "index, 2023 = 100", SRC["mieg"]),
    "mieg_index_yony": ("MIEG year-on-year growth, whole economy", "fraction (0.05 = 5 percent)", SRC["mieg"]),
    "mieg_index_agri_yony": ("MIEG year-on-year growth, agriculture", "fraction (0.05 = 5 percent)", SRC["mieg"]),
    "status": ("GSS status of the quarter: final, revised or provisional", "", SRC["gss_q"]),
    "crops_cocoa": ("Value added, crops including cocoa", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "cocoa": ("Value added, cocoa", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "livestock": ("Value added, livestock", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "forestry_logging": ("Value added, forestry and logging", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "fishing": ("Value added, fishing", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "total_value_added": ("Agriculture total value added", "GHS million, constant 2013 prices", SRC["gss_q"]),
    "ow_informal": ("Of which informal (as labelled by GSS)", "GHS million, constant 2013 prices", SRC["gss_q"]),
    # market panel (WFP long file)
    "admin1": ("Region as labelled by WFP (pre-2018 regions)", "", SRC["wfp"]),
    "admin2": ("District as labelled by WFP", "", SRC["wfp"]),
    "market": ("Market name", "", SRC["wfp"]),
    "latitude": ("Market latitude", "degrees", SRC["wfp"]),
    "longitude": ("Market longitude", "degrees", SRC["wfp"]),
    "category": ("WFP commodity category", "", SRC["wfp"]),
    "commodity": ("Commodity", "", SRC["wfp"]),
    "unit": ("Unit the price refers to (for example 100 KG)", "", SRC["wfp"]),
    "pricetype": ("Retail or Wholesale", "", SRC["wfp"]),
    "priceflag": ("WFP price flag (actual, aggregate, ...)", "", SRC["wfp"]),
    "currency": ("Currency of price", "", SRC["wfp"]),
    "price": ("Price per the stated unit", "currency per unit", SRC["wfp"]),
    "price_ghs_per_kg": ("Price converted to per kg where the unit is in kilograms; empty otherwise", "GHS per kg", SRC["wfp"]),
    "usdprice": ("Price in US dollars as reported by WFP", "US$ per unit", SRC["wfp"]),
    "region_2018": ("Current region the market lies in, from its coordinates", "", SRC["geo"]),
    "region_2018_method": ("How region_2018 was assigned (inside polygon, or nearest region within 0.15 deg)", "", ""),
}


def describe(col):
    if col in FIXED:
        return FIXED[col]
    m = re.fullmatch(r"(cocoa|transition|cereal)_(chirps|nasa)_(rain_mm|tmean_c|tmax_c|tmin_c|rh_pct)(_q|_annual)?", col)
    if m:
        zone, src, var, agg = m.groups()
        what, unit = VAR[var]
        where = ZONE_TEXT[zone] if src == "chirps" else NASA_ZONE_TEXT[zone]
        how = "unweighted mean over regions" if src == "chirps" else "unweighted mean over sites"
        return (_agg_text(what, agg) + f", {how} in the {where}; missing unless every member has a value",
                _agg_unit(unit, var, agg), SRC[src])
    m = re.fullmatch(r"cru_(rain_mm|tmean_c|tmax_c|tmin_c)(_q|_annual)?", col)
    if m:
        var, agg = m.groups()
        what, unit = VAR[var]
        return (_agg_text(what, agg) + ", Ghana national average", _agg_unit(unit, var, agg), SRC["cru"])
    m = re.fullmatch(r"(chirps|nasa)_(rain_mm|tmean_c|tmax_c|tmin_c|rh_pct)", col)
    if m:
        src, var = m.groups()
        what, unit = VAR[var]
        where = "mean over grid cells in the region" if src == "chirps" else "grid cell containing nasa_site"
        return (f"Monthly {what}, {where}", unit + (" per month" if var == "rain_mm" else ""), SRC[src])
    m = re.fullmatch(r"wfp_(\w+?)_(retail|wholesale)_ghs_kg", col)
    if m:
        com, pt = m.groups()
        return (f"{com.replace('_', ' ').capitalize()} {pt} price, median across WFP markets reporting that month",
                "GHS per kg", SRC["wfp"])
    m = re.fullmatch(r"fao_(\w+)_(area_ha|production_t|yield_kg_ha)", col)
    if m:
        crop, el = m.groups()
        what, unit = {"area_ha": ("area harvested", "hectares"), "production_t": ("production", "tonnes"),
                      "yield_kg_ha": ("yield", "kg per hectare")}[el]
        return (f"{crop.replace('_', ' ').capitalize()} {what} (FAO flag in data/clean/faostat_ghana_crops_annual.csv)",
                unit, SRC["fao"])
    m = re.fullmatch(r"mofa_(\w+)_(area|production)", col)
    if m:
        crop, el = m.groups()
        what, unit = {"area": ("cropped area", "hectares"), "production": ("production", "tonnes")}[el]
        return (f"{crop.replace('_', ' ').capitalize()} {what}", unit, SRC["mofa"])
    if col == "chirps_rain_mm":
        return ("Monthly rainfall of region_2018, mean over grid cells", "mm per month", SRC["chirps"])
    raise KeyError(f"no codebook entry for column {col!r}")


def _agg_text(what, agg):
    if agg == "_q":
        return ("Quarterly total " if what == "rainfall" else "Quarterly mean of monthly ") + what
    if agg == "_annual":
        return "Annual total " + what
    return "Monthly " + what


def _agg_unit(unit, var, agg):
    if var != "rain_mm":
        return unit
    return unit + {"_q": " per quarter", "_annual": " per year"}.get(agg, " per month")


def coverage(s, df):
    """Earliest and latest period with a value, and the number of non-missing cells."""
    s = s.dropna()
    if s.empty:
        return "", "", 0
    idx = df.loc[s.index]
    if "month" in df:
        key = idx.year * 100 + idx.month
        fmt = lambda k: f"{k // 100}-{k % 100:02d}"
    elif "quarter" in df:
        key = idx.year * 10 + idx.quarter
        fmt = lambda k: f"{k // 10} Q{k % 10}"
    else:
        key = idx.year
        fmt = str
    return fmt(int(key.min())), fmt(int(key.max())), len(s)


def main():
    OUT.mkdir(exist_ok=True)
    frames, rows = {}, []
    for sheet, fname, _ in PANELS:
        df = pd.read_csv(PANEL / fname, low_memory=False)
        sort = [c for c in ("region", "market", "commodity", "pricetype", "year", "quarter", "month") if c in df]
        df = df.sort_values(sort, kind="stable").reset_index(drop=True)
        frames[sheet] = df
        for col in df.columns:
            desc, unit, src = describe(col)
            first, last, n = coverage(df[col], df) if col not in ("year", "month", "quarter", "date") else ("", "", df[col].notna().sum())
            rows.append(dict(sheet=sheet, file=fname, column=col, description=desc, unit=unit, source=src,
                             first_obs=first, last_obs=last, n_nonmissing=n, n_rows=len(df)))
    cb = pd.DataFrame(rows)
    cb.to_csv(OUT / "codebook.csv", index=False)

    built = dt.date.today().isoformat()
    readme = [
        ["Weather and agriculture in Ghana: dataset"],
        [f"Author: Emmanuel Adutwum. Built {built} from data/panel/ by src/export_dataset.py."],
        [""],
        ["Rules applied throughout"],
        ["No value has been estimated, interpolated or filled in. An empty cell is missing data."],
        ["Zone weather is the unweighted mean over the member regions or sites, and is missing unless every member has a value."],
        ["Quarterly and annual weather need all 3 or all 12 months; otherwise missing."],
        ["NASA POWER rainfall for June 2026 is an outlier (3 to 10 SD above normal; CHIRPS shows 0.5 SD below to 1.3 SD above). It is flagged, not dropped. CHIRPS is the main rainfall measure."],
        ["Full source documentation, download dates and known problems: data/README.md (included in the zip)."],
        ["Raw files with URL, download time and SHA-256: data/raw/MANIFEST.csv in the repository."],
        [""],
        ["Sheets"],
        ["Codebook: one row per column of every panel, with unit, source and coverage."],
        ["Sources: each source, its coverage and licence."],
    ] + [[f"{s}: {d}"] for s, _, d in PANELS]

    sources = pd.DataFrame([
        ("Bank of Ghana", "Cocoa bean, product and total export value; LIFFE and CSCE cocoa prices", "Monthly", "2005-01 to 2026-03", "No licence stated"),
        ("Eurostat Comext", "EU27 imports of cocoa beans from Ghana, tonnes and EUR", "Monthly", "2002-01 to 2026-08", "Reuse with acknowledgement"),
        ("World Food Programme (HDX)", "Market food prices, 44 markets, 26 commodities", "Monthly", "2006-01 to 2023-07", "CC BY-IGO"),
        ("Ghana Statistical Service", "Agricultural GDP by sub-sector, constant 2013 prices", "Quarterly", "2006 Q1 to 2026 Q2", "No licence stated"),
        ("Ghana Statistical Service", "Monthly Indicator of Economic Growth", "Monthly", "2023-01 to 2026-07", "No licence stated"),
        ("Ghana Statistical Service", "Regional food CPI, 16 regions", "Monthly", "2022-09 to 2026-10", "No licence stated"),
        ("FAOSTAT", "Area, production, yield: cocoa, maize, rice, cassava, yams, millet, sorghum", "Annual", "1961 to 2024", "CC BY 4.0"),
        ("MoFA SRID", "Production and cropped area of 11 crops", "Annual", "2009 to 2021", "No licence stated"),
        ("World Bank Pink Sheet", "Cocoa, maize, rice prices", "Monthly", "1960-01 to 2026-10", "CC BY 4.0"),
        ("CHIRPS v2.0", "Rainfall, 0.05 deg grid averaged to 16 regions", "Monthly", "1981-01 onward (see Codebook)", "Public domain"),
        ("NASA POWER", "Rainfall, temperature, humidity at 9 sites", "Monthly", "1981-01 to 2026-09", "Public, NASA"),
        ("CRU TS 4.09 (World Bank CCKP)", "National rainfall and temperature", "Monthly", "1901-01 to 2024-12", "CC BY 4.0"),
        ("NOAA CPC", "Nino 3.4 index (ERSSTv5, OISSTv2)", "Monthly", "1950-01 / 1982-01 to 2026", "Public domain"),
        ("geoBoundaries", "Region boundaries (ADM1, 16 regions)", "", "2021 boundaries", "CC BY-SA 2.0"),
    ], columns=["source", "series", "frequency", "coverage", "licence"])

    xlsx = OUT / f"{STEM}.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
        pd.DataFrame(readme).to_excel(xw, sheet_name="README", index=False, header=False)
        sources.to_excel(xw, sheet_name="Sources", index=False)
        cb.to_excel(xw, sheet_name="Codebook", index=False)
        for sheet, df in frames.items():
            df.to_excel(xw, sheet_name=sheet, index=False)
        wb = xw.book
        wb["README"]["A1"].font = Font(bold=True, size=14)
        for r in (4, 12):
            wb["README"].cell(r, 1).font = Font(bold=True)
        for ws in wb.worksheets[1:]:
            ws.freeze_panes = "A2" if ws.title in ("Sources", "Codebook") else "C2"
            for c in ws[1]:
                c.font = Font(bold=True)
            for i, col in enumerate(ws.iter_cols(min_row=1, max_row=min(ws.max_row, 200)), 1):
                w = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[get_column_letter(i)].width = min(max(w + 2, 8), 70)
        for c in wb["Codebook"]["D"][1:]:
            c.alignment = Alignment(wrap_text=True, vertical="top")

    with zipfile.ZipFile(OUT / f"{STEM}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for _, fname, _ in PANELS:
            z.write(PANEL / fname, f"{STEM}/{fname}")
        z.write(OUT / "codebook.csv", f"{STEM}/codebook.csv")
        z.write(ROOT / "data" / "README.md", f"{STEM}/README.md")
    print(f"export: {xlsx.name}, {len(cb)} codebook rows, sheets {list(frames)}")


if __name__ == "__main__":
    main()
