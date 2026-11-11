"""Monthly Nino 3.4 index from NOAA Climate Prediction Center (public domain).

Two CPC files, kept as separate columns and never spliced:
  ERSSTv5, 1950 onward, anomaly vs 1991-2020:
    https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii
    (on 11 Nov 2026 this file ended in June 2026)
  OISSTv2, 1982 onward, anomaly vs 1991-2020:
    https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices
    (on 11 Nov 2026 this file ran to October 2026)
The panel uses the OISST anomaly because it covers the whole sample period.

Raw: data/raw/enso/
Clean: data/clean/nino34_monthly.csv
"""
import pandas as pd

from common import CLEAN, RAW, fetch

ERSST = "https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii"
OISST = "https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices"


def read(path, prefix):
    df = pd.read_csv(path, sep=r"\s+")
    i = list(df.columns).index("NINO3.4")  # next column is its anomaly
    return pd.DataFrame({"year": df.iloc[:, 0], "month": df.iloc[:, 1],
                         f"nino34_{prefix}_sst_c": df.iloc[:, i],
                         f"nino34_{prefix}_anom_c": df.iloc[:, i + 1]})


def main():
    e = read(fetch(ERSST, RAW / "enso" / "ersst5.nino.mth.91-20.ascii", note="NOAA CPC Nino, ERSSTv5"), "ersst")
    o = read(fetch(OISST, RAW / "enso" / "sstoi.indices", note="NOAA CPC Nino, OISSTv2"), "oisst")
    df = e.merge(o, on=["year", "month"], how="outer").sort_values(["year", "month"])
    df.to_csv(CLEAN / "nino34_monthly.csv", index=False)
    for c in ["nino34_ersst_anom_c", "nino34_oisst_anom_c"]:
        s = df.dropna(subset=[c])
        print(f"Nino 3.4 {c}: {s.year.iloc[0]}-{s.month.iloc[0]:02d} to {s.year.iloc[-1]}-{s.month.iloc[-1]:02d}")
    both = df.dropna()
    print(f"  ERSST vs OISST anomaly correlation over {len(both)} common months: "
          f"{both.nino34_ersst_anom_c.corr(both.nino34_oisst_anom_c):.3f}")


if __name__ == "__main__":
    main()
