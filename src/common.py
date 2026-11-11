"""Shared paths, HTTP session and download log for every source script.

Every file written to data/raw/ is recorded in data/raw/MANIFEST.csv with its
URL, download time (UTC), size and SHA-256, so the README can cite the exact
download date and anyone can check that a raw file has not been edited.
"""
import csv
import datetime as dt
import hashlib
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
PANEL = ROOT / "data" / "panel"
MANIFEST = RAW / "MANIFEST.csv"

for p in (RAW, CLEAN, PANEL):
    p.mkdir(parents=True, exist_ok=True)

# Some government sites refuse requests without a browser-like User-Agent.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = UA


def get(url, retries=3, timeout=180, **kw):
    """GET with retries. Raises on HTTP errors."""
    last = None
    for i in range(retries):
        try:
            r = SESSION.get(url, timeout=timeout, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_download(path, url, note=""):
    """Append one row to data/raw/MANIFEST.csv (replacing any older row for the same path)."""
    path = Path(path)
    rel = str(path.relative_to(ROOT))
    row = dict(path=rel, url=url,
               downloaded_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               bytes=path.stat().st_size, sha256=sha256(path), note=note)
    rows = []
    if MANIFEST.exists():
        with open(MANIFEST, newline="") as f:
            rows = [r for r in csv.DictReader(f) if r["path"] != rel]
    rows.append(row)
    rows.sort(key=lambda r: r["path"])
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        w.writeheader()
        w.writerows(rows)


def save(content, path, url, note=""):
    """Write bytes to data/raw and log them."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)
    log_download(path, url, note)
    return path


def fetch(url, path, note="", refresh=False, **kw):
    """Download url to path unless it already exists (use refresh=True to force)."""
    path = Path(path)
    if path.exists() and not refresh and os.environ.get("REFRESH") != "1":
        return path
    r = get(url, **kw)
    return save(r.content, path, url, note)


def check_not_html(path):
    """Raise if a supposed data file is actually an HTML error page."""
    with open(path, "rb") as f:
        head = f.read(512).lower()
    if b"<html" in head or b"<!doctype html" in head:
        raise ValueError(f"{path} is an HTML page, not data")


# Locations used for point weather (NASA POWER). One town per region in the
# three zones named in the brief. These are points, not regional averages.
SITES = {
    "SefwiWiawso": dict(region="Western North", zone="cocoa", lat=6.21, lon=-2.49),
    "Tarkwa": dict(region="Western", zone="cocoa", lat=5.30, lon=-1.99),
    "Kumasi": dict(region="Ashanti", zone="cocoa", lat=6.69, lon=-1.62),
    "AssinFoso": dict(region="Central", zone="cocoa", lat=5.70, lon=-1.28),
    "Koforidua": dict(region="Eastern", zone="cocoa", lat=6.09, lon=-0.26),
    "Techiman": dict(region="Bono East", zone="transition", lat=7.59, lon=-1.94),
    "Tamale": dict(region="Northern", zone="cereal", lat=9.40, lon=-0.84),
    "Tumu": dict(region="Upper West", zone="cereal", lat=10.88, lon=-1.98),
    "Bolgatanga": dict(region="Upper East", zone="cereal", lat=10.79, lon=-0.85),
}

ZONES = {
    "cocoa": ["Western North", "Western", "Ashanti", "Central", "Eastern"],
    "transition": ["Bono East"],
    "cereal": ["Northern", "Upper West", "Upper East"],
}
