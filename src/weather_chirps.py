"""CHIRPS v2.0 monthly rainfall, averaged over each of Ghana's 16 regions.

Source: Climate Hazards Center, UC Santa Barbara.
  https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/
One gzipped GeoTIFF per month (0.05 degree grid, mm per month), 1981 onward.

The Africa-wide files total about 2.4 GB, so they are cached in
data/raw/chirps_v2/ and listed in .gitignore. The script downloads any month
that is missing. The committed output is the regional average in
data/clean/chirps_region_monthly.csv.

Regional average = unweighted mean of the grid cells whose centre lies inside
the region polygon (geoBoundaries ADM1). Ghana spans 4.5N to 11.2N, so the
difference in cell area across the country is under 1.5% and is ignored.
"""
import gzip
import io
import json
import re
import time

import requests

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

from common import CLEAN, RAW, SESSION, get, log_download

BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/"
CACHE = RAW / "chirps_v2"
BOUNDS = RAW / "boundaries" / "geoBoundaries-GHA-ADM1.geojson"
BBOX = (-3.4, 4.6, 1.3, 11.3)  # lon_min, lat_min, lon_max, lat_max around Ghana


def list_months():
    html = get(BASE, timeout=60).text
    return sorted(set(re.findall(r"chirps-v2\.0\.(\d{4})\.(\d{2})\.tif\.gz", html)))


def download(ym, tries=6):
    """Download one month. The CHC server answers HTTP 429 when requests come
    too fast, so go one file at a time, pause between files, and back off."""
    y, m = ym
    name = f"chirps-v2.0.{y}.{m}.tif.gz"
    path = CACHE / name
    if path.exists() and path.stat().st_size > 1_000_000:
        return path
    wait = 30
    for _ in range(tries):
        try:
            r = SESSION.get(BASE + name, timeout=300)
            if r.status_code == 200 and len(r.content) > 1_000_000:
                path.write_bytes(r.content)
                log_download(path, BASE + name, note="CHIRPS v2.0 Africa monthly, gitignored cache")
                time.sleep(2)
                return path
            wait = int(r.headers.get("Retry-After", wait))
        except requests.RequestException:
            pass
        time.sleep(wait)
        wait = min(wait * 2, 600)
    print(f"CHIRPS: could not download {name}; month left missing")
    return None


def region_masks(transform, shape):
    feats = json.load(open(BOUNDS))["features"]
    masks = {}
    for f in feats:
        inside = ~geometry_mask([f["geometry"]], out_shape=shape, transform=transform,
                                all_touched=False)
        masks[f["properties"]["shapeName"].removesuffix(" Region")] = inside
    return masks


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    months = list_months()
    print(f"CHIRPS: {len(months)} months listed, {months[0]} to {months[-1]}")
    paths = [download(ym) for ym in months]

    rows, masks = [], None
    for (y, m), path in zip(months, paths):
        if path is None:
            continue
        with gzip.open(path) as gz:
            data = gz.read()
        with rasterio.MemoryFile(io.BytesIO(data)) as mf, mf.open() as r:
            win = from_bounds(*BBOX, r.transform).round_offsets().round_lengths()
            a = r.read(1, window=win).astype("float64")
            nodata = r.nodata
            if masks is None:
                masks = region_masks(r.window_transform(win), a.shape)
        a[(a < 0) | (a == nodata)] = np.nan  # CHIRPS uses -9999 for ocean / no data
        for region, mk in masks.items():
            vals = a[mk]
            rows.append(dict(region=region, year=int(y), month=int(m),
                             rain_mm=np.nanmean(vals) if np.isfinite(vals).any() else np.nan,
                             n_cells=int(np.isfinite(vals).sum())))
    df = pd.DataFrame(rows).sort_values(["region", "year", "month"])
    out = CLEAN / "chirps_region_monthly.csv"
    df.to_csv(out, index=False, float_format="%.3f")
    print(f"CHIRPS: wrote {out.name}, {len(df)} rows, {df.region.nunique()} regions, "
          f"{df.year.min()}-{df.year.max()}, missing {df.rain_mm.isna().sum()}")


if __name__ == "__main__":
    main()
