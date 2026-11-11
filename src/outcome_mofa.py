"""MoFA SRID "Agriculture in Ghana: Facts and Figures" (editions 2018-2021): tables
extracted from the PDFs with code.

Source pages:
  https://mofa.gov.gh/site/publications/research-reports
These four editions were the only ones posted on 11 Nov 2026.

What the reports contain, and what they do not:
  * Appendix 15 / 16: national annual production ('000 t or t) and cropped
    area ('000 ha or ha) of major crops, ten years per edition.
  * Table 2.9: annual rainfall by (old, 10-region) region, from the Ghana
    Meteorological Agency (station data, mm).
  * District tables (4.7-4.17) list only the ten best-yielding districts per
    crop, and regional figures are top-five shares. Neither is a complete
    regional or district panel, so they are NOT extracted. A full district
    panel has to be requested from SRID (see letters/).

Parsing rule: a table row is kept only if it yields exactly one number per
year column. Rows that do not (for example, a row the PDF wraps across lines)
are written to data/clean/mofa_unparsed_rows.csv and left missing. No value
is typed in by hand. Values are kept as printed, including obvious errors
(the 2020 edition prints 30 mm for Central Region rainfall in 2020); such
rows are flagged, not corrected.

The PDFs are kept in data/raw/mofa/ so the extraction can be checked. No
licence statement was found on mofa.gov.gh, so the PDFs are not committed.

Clean: data/clean/mofa_production_area_by_edition.csv
       data/clean/mofa_regional_rainfall_by_edition.csv
       data/clean/mofa_unparsed_rows.csv
"""
import re

import pandas as pd
import pdfplumber

from common import CLEAN, RAW, check_not_html, fetch

BASE = "https://mofa.gov.gh/site/images/pdf/"
EDITIONS = {
    2018: "AGRIC%20IN%20GHANA%20F&F_2018.pdf",
    2019: "2019%20AGRICULTURE%20FACT%20AND%20FIGURES.pdf",
    2020: "2020%20Agriculture%20In%20Ghana%20Facts%20&%20Figures_%20MASTER.pdf",
    2021: "AGRICULTURE%20IN%20GHANA%20(Facts%20&%20Figures)%202021.pdf",
}
NUM = r"-?\d[\d,]*\.?\d*"
CROP_NAMES = {"MAIZE": "maize", "RICE (PADDY)": "rice_paddy", "MILLET": "millet", "SORGHUM": "sorghum",
              "CASSAVA": "cassava", "COCOYAM": "cocoyam", "YAM": "yam", "PLANTAIN": "plantain",
              "GROUNDNUT": "groundnut", "GROUNDNUTS": "groundnut", "OIL PALM": "oil_palm",
              "COWPEA": "cowpea", "SOYBEAN": "soybean", "SOYABEAN": "soybean",
              "G’NUTS": "groundnut", "G'NUTS": "groundnut"}
REGIONS = ["WESTERN", "CENTRAL", "GREATER ACCRA", "VOLTA", "EASTERN", "ASHANTI", "BRONG AHAFO",
           "NORTHERN", "UPPER EAST", "UPPER WEST"]


def to_float(s):
    return float(s.replace(",", ""))


def page_texts(path):
    with pdfplumber.open(path) as pdf:
        return [(i + 1, pg.extract_text() or "") for i, pg in enumerate(pdf.pages)]


def parse_crop_table(text, edition, page, element, unparsed):
    """Parse an Appendix 15/16 block that starts at its title and ends at 'SOURCE'."""
    head = re.search(r"CROP\s+((?:\d{4}\s+)+\d{4})", text, re.I)
    if not head:
        return []
    years = [int(y) for y in head.group(1).split()]
    title = text[:head.start()].upper()
    scale = 1000.0 if "'000" in title.replace("‘", "'").replace("’", "'") else 1.0
    rows = []
    for line in text[head.end():].splitlines():
        if line.strip().upper().startswith("SOURCE"):
            break
        if re.fullmatch(r"\s*(\d+\s*\|\s*P\s*a\s*g\s*e|CROP(\s+\d{4})+|TOTAL.*|<<PAGE \d+>>)\s*", line, re.I):
            continue  # page footer, repeated header after a page break, or the total row
        m = re.match(r"\s*([A-Za-z][A-Za-z ()’']*?)\s+(" + NUM + r"(?:\s+" + NUM + r")*)\s*$", line)
        if not m:
            if line.strip():
                unparsed.append(dict(edition=edition, page=page, table=element, line=line.strip()))
            continue
        name = m.group(1).strip().upper()
        vals = re.findall(NUM, m.group(2))
        crop = CROP_NAMES.get(name)
        if crop is None or len(vals) != len(years):
            unparsed.append(dict(edition=edition, page=page, table=element, line=line.strip()))
            continue
        for y, v in zip(years, vals):
            rows.append(dict(edition=edition, page=page, element=element, crop=crop, year=y,
                             value=to_float(v) * scale, unit="t" if element == "production" else "ha"))
    return rows


def parse_rainfall(text, edition, page, unparsed):
    """Table 2.9. Two layouts: regions as rows (2018, 2019 editions) or years as rows (2020, 2021)."""
    rows = []
    head = re.search(r"REGION\s+((?:\d{4}\s+)+\d{4})", text)
    if head:  # regions are rows
        years = [int(y) for y in head.group(1).split()]
        for line in text[head.end():].splitlines():
            for reg in REGIONS:
                m = re.match(rf"\s*{reg}\s+((?:{NUM}\s+)*{NUM})\s*$", line.upper())
                if m:
                    vals = re.findall(NUM, m.group(1))
                    if len(vals) < len(years):
                        unparsed.append(dict(edition=edition, page=page, table="rainfall", line=line.strip()))
                        break
                    for y, v in zip(years, vals[:len(years)]):
                        rows.append(dict(edition=edition, page=page, region=reg.title(), year=y, rain_mm=to_float(v)))
                    break
        # A region name split across two lines ("GREATER" / "ACCRA 805 ...") is handled here.
        m = re.search(rf"GREATER\s*\n\s*ACCRA\s+((?:{NUM}\s+)*{NUM})\s*\n", text.upper())
        if m and not any(r["region"] == "Greater Accra" for r in rows):
            vals = re.findall(NUM, m.group(1))
            if len(vals) >= len(years):
                for y, v in zip(years, vals[:len(years)]):
                    rows.append(dict(edition=edition, page=page, region="Greater Accra", year=y, rain_mm=to_float(v)))
        return rows
    # years are rows; column order taken from the 2020 edition header
    order = ["Western", "Central", "Greater Accra", "Volta", "Eastern", "Ashanti", "Brong Ahafo",
             "Northern", "Upper East", "Upper West"]
    for line in text.splitlines():
        m = re.match(rf"\s*(\d{{4}})\s+((?:{NUM}\s+)+{NUM})\s*$", line)
        if not m:
            continue
        vals = re.findall(NUM, m.group(2))
        if len(vals) != 12:  # 10 regions + total + average
            unparsed.append(dict(edition=edition, page=page, table="rainfall", line=line.strip()))
            continue
        for reg, v in zip(order, vals[:10]):
            rows.append(dict(edition=edition, page=page, region=reg, year=int(m.group(1)), rain_mm=to_float(v)))
    return rows


def main():
    prod, rain, unparsed = [], [], []
    for ed, fname in EDITIONS.items():
        path = fetch(BASE + fname, RAW / "mofa" / f"facts_and_figures_{ed}.pdf",
                     note=f"MoFA SRID Agriculture in Ghana: Facts and Figures {ed}", timeout=600)
        check_not_html(path)
        pages = page_texts(path)
        for k, (page, text) in enumerate(pages):
            up = text.upper()
            # Tables can run onto the next page, so parse from the title through the following page.
            text2 = text + "\n<<PAGE %d>>\n" % (page + 1) + (pages[k + 1][1] if k + 1 < len(pages) else "")
            for element, pat in [("production", r"APPENDIX 15\s*:\s*ANNUAL PRODUCTION"),
                                 ("area", r"APPENDIX 16\s*:\s*ANNUAL (?:CROPPED|CULTIVATED) AREA")]:
                m = re.search(pat, up)
                if m and page > 30:
                    prod += parse_crop_table(text2[m.start():], ed, page, element, unparsed)
            m = re.search(r"TABLE 2\.\s?9\s*:?\s*ANNUAL REGIONAL RAINFALL", up)
            if m and page < 40:
                rain += parse_rainfall(text[m.start():], ed, page, unparsed)

    p = pd.DataFrame(prod).drop_duplicates(["edition", "element", "crop", "year"])
    p.to_csv(CLEAN / "mofa_production_area_by_edition.csv", index=False)
    r = pd.DataFrame(rain).drop_duplicates(["edition", "region", "year"])
    # Flag values that are implausible for annual regional rainfall rather than editing them.
    r["flag"] = ""
    r.loc[r.rain_mm < 200, "flag"] = "implausible as printed (below 200 mm/yr); not corrected"
    r.to_csv(CLEAN / "mofa_regional_rainfall_by_edition.csv", index=False)
    pd.DataFrame(unparsed).to_csv(CLEAN / "mofa_unparsed_rows.csv", index=False)

    print(f"MoFA production/area: {len(p)} values; editions {sorted(p.edition.unique())}; "
          f"years {p.year.min()}-{p.year.max()}")
    print(f"MoFA regional rainfall: {len(r)} values; {int((r.flag != '').sum())} flagged")
    print(f"MoFA rows not parsed (left missing, listed in mofa_unparsed_rows.csv): {len(unparsed)}")


if __name__ == "__main__":
    main()
