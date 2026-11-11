"""Merge cleaned series into panels in data/panel/.

Main file (the merged monthly panel):
  panel_national_monthly.csv  one row per month, 1981 onward. Outcomes,
      prices, Nino 3.4, and weather averaged over each zone.

Supporting files:
  panel_region_monthly.csv    region x month: CHIRPS rainfall (16 regions),
      NASA POWER point weather (the 9 regions with a site), GSS food CPI.
  panel_market_monthly.csv    WFP market x commodity x price type x month,
      with the CHIRPS rainfall of the region the market lies in (placed by
      its coordinates, because WFP labels markets with the pre-2018 regions).
  panel_national_quarterly.csv GSS agricultural GDP with quarterly weather.
  panel_national_annual.csv   FAOSTAT and MoFA production with annual weather.

Rules:
  * Nothing is filled in. A month with no observation stays empty.
  * Zone weather = unweighted mean over the regions (CHIRPS) or sites (NASA
    POWER) in the zone, computed only when every region or site in the zone
    has a value for that month.
  * The near-real-time NASA POWER precipitation for June 2026 is far outside
    its own history (see data/README.md). It is kept in the clean file and
    left in the panels, with a flag column, so that the decision to drop it
    is made openly in the analysis.
"""
import json

import numpy as np
import pandas as pd

from common import CLEAN, PANEL, RAW, ZONES

ZONE_SITES = {"cocoa": ["SefwiWiawso", "Tarkwa", "Kumasi", "AssinFoso", "Koforidua"],
              "transition": ["Techiman"], "cereal": ["Tamale", "Tumu", "Bolgatanga"]}


def read(name, **kw):
    p = CLEAN / name
    if not p.exists():
        print(f"panel: {name} not found, columns from it are omitted")
        return None
    return pd.read_csv(p, **kw)


def zone_mean(df, key, members, cols):
    """Mean over members of each zone for each month; NaN unless all members present."""
    out = []
    for zone, mem in members.items():
        sub = df[df[key].isin(mem)]
        g = sub.groupby(["year", "month"])
        m = g[cols].mean()
        n = g[cols].count()
        m[n < len(mem)] = np.nan
        m.columns = [f"{zone}_{c}" for c in cols]
        out.append(m)
    return pd.concat(out, axis=1).reset_index()


def market_regions(markets):
    """Assign each WFP market to one of the 16 current regions by point-in-polygon."""
    from shapely.geometry import Point, shape
    feats = json.load(open(RAW / "boundaries" / "geoBoundaries-GHA-ADM1.geojson"))["features"]
    polys = [(f["properties"]["shapeName"].removesuffix(" Region"), shape(f["geometry"])) for f in feats]
    res, how = {}, {}
    for _, r in markets.iterrows():
        pt = Point(r.longitude, r.latitude)
        hit = [n for n, poly in polys if poly.contains(pt)]
        if hit:
            res[r.market], how[r.market] = hit[0], "inside polygon"
            continue
        # Coastal markets can fall just outside the boundary line. Use the nearest
        # region only if it is within 0.15 degrees (about 15 km).
        d, n = min((poly.distance(pt), n) for n, poly in polys)
        res[r.market], how[r.market] = (n, f"nearest region, {d:.3f} deg away") if d < 0.15 else (None, "not placed")
    return res, how


def main():
    months = pd.DataFrame([(y, m) for y in range(1981, 2027) for m in range(1, 13)], columns=["year", "month"])
    nat = months.copy()

    chirps = read("chirps_region_monthly.csv")
    nasa = read("nasa_power_site_monthly.csv")
    if nasa is not None:
        nasa["nasa_rain_flag_2026_06"] = (nasa.year == 2026) & (nasa.month == 6)

    # --- national monthly -------------------------------------------------
    if chirps is not None:
        nat = nat.merge(zone_mean(chirps.rename(columns={"rain_mm": "chirps_rain_mm"}), "region", ZONES,
                                  ["chirps_rain_mm"]), on=["year", "month"], how="left")
    if nasa is not None:
        cols = ["rain_mm", "tmean_c", "tmax_c", "tmin_c", "rh_pct"]
        z = zone_mean(nasa.rename(columns={c: f"nasa_{c}" for c in cols}), "site", ZONE_SITES,
                      [f"nasa_{c}" for c in cols])
        nat = nat.merge(z, on=["year", "month"], how="left")
        nat["nasa_rain_flag"] = (nat.year == 2026) & (nat.month == 6)
    for name, prefix in [("cru_national_monthly.csv", "cru_"), ("nino34_monthly.csv", ""),
                         ("bog_exports_monthly.csv", ""), ("bog_cocoa_prices_monthly.csv", "bog_"),
                         ("eurostat_cocoa_imports_monthly.csv", ""), ("uscensus_cocoa_imports_monthly.csv", ""),
                         ("worldbank_prices_monthly.csv", ""), ("gss_mieg_monthly.csv", "")]:
        d = read(name)
        if d is None:
            continue
        d = d.rename(columns={c: prefix + c for c in d.columns if c not in ("year", "month")})
        nat = nat.merge(d, on=["year", "month"], how="left")
    wfp = read("wfp_prices_monthly_national.csv")
    if wfp is not None:
        for (com, pt), g in wfp.groupby(["commodity", "pricetype"]):
            if com in ("Maize", "Rice (local)", "Yam", "Cassava", "Millet", "Sorghum"):
                col = "wfp_" + com.lower().replace(" (", "_").replace(")", "").replace(" ", "_") + "_" + pt.lower() + "_ghs_kg"
                nat = nat.merge(g[["year", "month", "price_ghs_per_kg_median"]].rename(
                    columns={"price_ghs_per_kg_median": col}), on=["year", "month"], how="left")
    nat.insert(2, "date", pd.to_datetime(dict(year=nat.year, month=nat.month, day=1)).dt.strftime("%Y-%m"))
    data_cols = [c for c in nat.columns if c not in ("year", "month", "date", "nasa_rain_flag")]
    nat = nat[nat[data_cols].notna().any(axis=1)]
    nat.to_csv(PANEL / "panel_national_monthly.csv", index=False, float_format="%.4f")
    print(f"panel_national_monthly: {len(nat)} months x {nat.shape[1]} columns, {nat.date.iloc[0]} to {nat.date.iloc[-1]}")

    # --- region monthly ---------------------------------------------------
    reg = None
    if chirps is not None:
        reg = chirps.rename(columns={"rain_mm": "chirps_rain_mm", "n_cells": "chirps_n_cells"})
    if nasa is not None:
        n = nasa[["region", "site", "year", "month", "rain_mm", "tmean_c", "tmax_c", "tmin_c", "rh_pct",
                  "nasa_rain_flag_2026_06"]]
        n = n.rename(columns={c: f"nasa_{c}" for c in ["site", "rain_mm", "tmean_c", "tmax_c", "tmin_c", "rh_pct"]})
        reg = n if reg is None else reg.merge(n, on=["region", "year", "month"], how="outer")
    cpi = read("gss_cpi_food_region_monthly.csv")
    if cpi is not None and reg is not None:
        reg = reg.merge(cpi[["region", "year", "month", "cpi_food"]].rename(columns={"cpi_food": "gss_cpi_food"}),
                        on=["region", "year", "month"], how="outer")
    if reg is not None:
        reg["zone"] = reg.region.map({r: z for z, rs in ZONES.items() for r in rs})
        reg = reg.sort_values(["region", "year", "month"])
        reg.to_csv(PANEL / "panel_region_monthly.csv", index=False, float_format="%.4f")
        print(f"panel_region_monthly: {len(reg)} rows, {reg.region.nunique()} regions")

    # --- market monthly ---------------------------------------------------
    w = read("wfp_prices_long.csv", low_memory=False)
    if w is not None:
        mk = w.groupby("market")[["latitude", "longitude"]].first().reset_index()
        where, how = market_regions(mk)
        w["region_2018"] = w.market.map(where)
        w["region_2018_method"] = w.market.map(how)
        if chirps is not None:
            w = w.merge(chirps[["region", "year", "month", "rain_mm"]].rename(
                columns={"region": "region_2018", "rain_mm": "chirps_rain_mm"}),
                on=["region_2018", "year", "month"], how="left")
        w.to_csv(PANEL / "panel_market_monthly.csv", index=False, float_format="%.4f")
        odd = {k: v for k, v in how.items() if v != "inside polygon"}
        print(f"panel_market_monthly: {len(w)} rows, {w.market.nunique()} markets; not inside a polygon: {odd}")

    # --- quarterly --------------------------------------------------------
    q = read("gss_qgdp_agric_constant2013.csv")
    if q is not None:
        nm = nat.assign(quarter=(nat.month - 1) // 3 + 1)
        wcols = [c for c in nm.columns if c.endswith("rain_mm")]
        tcols = [c for c in nm.columns if c.endswith(("tmean_c", "tmax_c", "tmin_c"))]
        g = nm.groupby(["year", "quarter"])
        agg = pd.concat([g[wcols].sum(min_count=3), g[tcols].mean()], axis=1)
        cnt = g[wcols + tcols].count()
        agg[cnt < 3] = np.nan  # a quarter needs all three months
        agg = agg.add_suffix("_q").reset_index()
        qq = q.merge(agg, on=["year", "quarter"], how="left")
        qq.to_csv(PANEL / "panel_national_quarterly.csv", index=False, float_format="%.4f")
        print(f"panel_national_quarterly: {len(qq)} quarters")

    # --- annual -----------------------------------------------------------
    fao = read("faostat_ghana_crops_annual.csv")
    if fao is not None:
        a = fao.pivot_table(index="year", columns=["crop", "element"], values="value")
        a.columns = [f"fao_{c}_{e}" for c, e in a.columns]
        mofa = read("mofa_production_area_by_edition.csv")
        if mofa is not None:
            # latest edition that reports each year (later editions carry revisions)
            latest = mofa.sort_values("edition").groupby(["crop", "element", "year"]).last().reset_index()
            m = latest.pivot_table(index="year", columns=["crop", "element"], values="value")
            m.columns = [f"mofa_{c}_{e}" for c, e in m.columns]
            a = a.join(m, how="outer")
        wcols = [c for c in nat.columns if c.endswith("rain_mm")]
        g = nat.groupby("year")
        ann = g[wcols].sum(min_count=12)
        ann[g[wcols].count() < 12] = np.nan
        a = a.join(ann.add_suffix("_annual"), how="left").reset_index()
        a.to_csv(PANEL / "panel_national_annual.csv", index=False, float_format="%.3f")
        print(f"panel_national_annual: {len(a)} years")


if __name__ == "__main__":
    main()
