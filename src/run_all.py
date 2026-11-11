"""Run the whole data pipeline: download, clean, build panels.

    python src/run_all.py            # use cached raw files where present
    REFRESH=1 python src/run_all.py  # download everything again

Each step runs on its own. A failure is reported and the remaining steps
continue, and the run ends with a list of what failed, so a broken website
cannot silently drop a series.
"""
import importlib
import sys
import time
import traceback

STEPS = [
    "boundaries",
    "weather_nasa_power",
    "weather_chirps",
    "weather_cru_cckp",
    "weather_enso",
    "outcome_bog",
    "outcome_eurostat",
    "outcome_uscensus",
    "outcome_wfp",
    "outcome_gss",
    "outcome_faostat",
    "outcome_mofa",
    "prices_worldbank",
    "worldbank_indicators",
    "build_panel",
]


def main():
    failed = []
    for name in STEPS:
        t = time.time()
        print(f"\n=== {name}")
        try:
            importlib.import_module(name).main()
            print(f"--- ok ({time.time() - t:.0f}s)")
        except Exception as e:  # report and keep going
            traceback.print_exc()
            failed.append((name, repr(e)[:200]))
    print("\n=== summary")
    if failed:
        for n, e in failed:
            print(f"FAILED {n}: {e}")
        sys.exit(1)
    print("all steps ran")


if __name__ == "__main__":
    main()
