"""FAOSTAT annual crop area, production and yield for Ghana.

Bulk file "Production_Crops_Livestock_E_Africa.zip":
  https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip
Licence: CC BY 4.0. The zip covers all of Africa (tens of MB) and is kept in
data/raw/faostat/ but listed in .gitignore; the Ghana rows are committed.

Crops kept: cocoa beans, maize, rice, cassava, yams, millet, sorghum.
Elements kept: Area harvested (ha), Production (t), Yield (kg/ha; FAOSTAT
changed the yield unit from hg/ha to kg/ha, and both are converted to kg/ha).
Flags are kept so official, estimated and imputed values can be told apart.

Clean: data/clean/faostat_ghana_crops_annual.csv (long: crop, element, year, value, flag)
"""
import io
import zipfile

import pandas as pd

from common import CLEAN, RAW, check_not_html, fetch

URL = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
CROPS = {"Cocoa beans": "cocoa", "Maize (corn)": "maize", "Rice": "rice", "Cassava, fresh": "cassava",
         "Yams": "yam", "Millet": "millet", "Sorghum": "sorghum"}
ELEMENTS = {"Area harvested": "area_ha", "Production": "production_t", "Yield": "yield_kg_ha"}


def main():
    path = fetch(URL, RAW / "faostat" / "Production_Crops_Livestock_E_Africa.zip",
                 note="FAOSTAT bulk QCL Africa (gitignored)", timeout=900)
    check_not_html(path)
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".csv") and "Flags" not in n
            and "Codes" not in n and "Symboles" not in n][0]
    df = pd.read_csv(z.open(name), encoding="latin-1", low_memory=False)
    df = df[(df.Area == "Ghana") & df.Item.isin(CROPS) & df.Element.isin(ELEMENTS)]
    missing = set(CROPS) - set(df.Item)
    if missing:
        raise KeyError(f"FAOSTAT items not found: {missing}")
    years = [c for c in df.columns if c.startswith("Y") and c[1:].isdigit()]
    rows = []
    for _, r in df.iterrows():
        for y in years:
            v = r[y]
            if pd.isna(v):
                continue
            unit = r.Unit
            if r.Element == "Yield" and unit == "hg/ha":
                v, unit = v / 10, "kg/ha"
            rows.append(dict(crop=CROPS[r.Item], element=ELEMENTS[r.Element], unit=unit,
                             year=int(y[1:]), value=v, flag=r.get(y + "F")))
    out = pd.DataFrame(rows).sort_values(["crop", "element", "year"])
    out.to_csv(CLEAN / "faostat_ghana_crops_annual.csv", index=False)
    print(f"FAOSTAT Ghana: {out.crop.nunique()} crops, {out.year.min()}-{out.year.max()}, {len(out)} values; "
          f"flags: {out.flag.fillna('none').value_counts().to_dict()}")


if __name__ == "__main__":
    main()
