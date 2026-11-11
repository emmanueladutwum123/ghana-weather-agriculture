"""Ghana's 16 administrative regions (ADM1) from geoBoundaries (gbOpen, CC BY-SA 2.0).

Output: data/raw/boundaries/geoBoundaries-GHA-ADM1.geojson
"""
import json

from common import RAW, fetch, get

API = "https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM1/"
OUT = RAW / "boundaries" / "geoBoundaries-GHA-ADM1.geojson"
META = RAW / "boundaries" / "geoBoundaries-GHA-ADM1_metadata.json"


def main():
    meta = get(API, timeout=60).json()
    fetch(API, META, note="geoBoundaries API metadata (licence, source)")
    fetch(meta["gjDownloadURL"], OUT, note="geoBoundaries gbOpen GHA ADM1, licence " + meta["boundaryLicense"])
    names = sorted(f["properties"]["shapeName"] for f in json.load(open(OUT))["features"])
    print(f"boundaries: {len(names)} regions: {', '.join(names)}")


if __name__ == "__main__":
    main()
