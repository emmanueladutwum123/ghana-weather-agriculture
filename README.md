# Weather and agricultural output in Ghana

Economics capstone, Soka University of America. Author: Emmanuel Adutwum. Advisor: Prof. Diya Mazumder.

## Question

What is the impact of weather on Ghana's agricultural sector, measured through farmers' output of cocoa and other crops?

## Data

No public source reports crop production in Ghana monthly. Production is published once a year or once a season. This project therefore uses monthly series that move with output: Bank of Ghana cocoa export values, EU imports of cocoa beans from Ghana, WFP market prices for staple foods, and the Ghana Statistical Service's quarterly agricultural GDP and monthly growth indicator. Annual production comes from FAOSTAT and from the Ministry of Food and Agriculture. Weather comes from CHIRPS (rainfall by region), NASA POWER (rainfall, temperature and humidity at nine towns), CRU (national, from 1901) and NOAA's Nino 3.4 index.

`data/README.md` describes every series: source, URL, download date, coverage, unit and known problems. It also lists the sources that were opened but could not be downloaded, and why.

## How to rerun

You need Python 3.11 or later and an internet connection.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
make all                # same as: .venv/bin/python src/run_all.py
```

The first run downloads about 2.5 GB, most of it CHIRPS rainfall rasters, which are not stored in the repository. Files already downloaded are reused. To download everything again, run `REFRESH=1 make all`. The US import series needs a free Census API key in the environment variable `CENSUS_API_KEY`; without it that step is skipped and the run says so.

## Layout

```
src/            one script per source, plus build_panel.py and run_all.py
src/legacy/     the first download script, kept for reference
data/raw/       files as downloaded, with MANIFEST.csv (URL, time, SHA-256)
data/clean/     cleaned series
data/panel/     merged panels (national monthly is the main one)
letters/        draft data requests to COCOBOD and MoFA SRID (not sent)
paper/          the LaTeX paper
```

## Status

Phase 1 (data) is mostly done; see `PROGRESS.md` for what remains and the decisions made so far. Phase 2 (description), Phase 3 (analysis) and Phase 4 (the paper) have not started. The paper in `paper/main.tex` is still the November 2026 data inventory and news review.

Main gaps at this stage: no public source gives monthly cocoa export volume from Ghana, only value; WFP prices end in July 2023; the US import series needs an API key; COCOBOD purchases and MoFA district production must be requested.

## Licences

Code: MIT. Data keep their own licences, listed in `data/README.md`. Raw files from sources with no stated reuse licence (Bank of Ghana, Ghana Statistical Service, Ministry of Food and Agriculture) are not committed; the scripts download them.
