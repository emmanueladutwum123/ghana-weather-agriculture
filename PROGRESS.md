# Progress log

## 11 November 2026: Phase 1 (data), mostly done

Done. One download and cleaning script per source in `src/`; `make all` reruns everything. Raw files, cleaned series and merged panels are in `data/`, and `data/README.md` documents every series. Draft data request letters to COCOBOD and MoFA SRID are in `letters/` (not sent).

Still running. CHIRPS rainfall: 89 of 549 monthly files downloaded. The CHC server began refusing connections after the script first made parallel requests; the script now downloads one file at a time with back-off. When it finishes, rerun `src/weather_chirps.py` and `src/build_panel.py`, then commit the regional rainfall file and the updated panels.

Decisions made:

1. US Census import data is skipped for now. It needs a free API key, and the EU import series already gives a complete monthly series. Record the missing US data as a limitation.
2. Cleaned Bank of Ghana, GSS and MoFA series are committed. Their raw files are not, because none of the three websites states a reuse licence; the scripts download them.
3. Code licence: MIT.
4. CHIRPS v2.0 is the main rainfall series (the version used in published work so far). v3.0 exists and is wetter.
5. The paper is checked with `tectonic` for now. `pdflatex` is not installed; it has to be installed before Phase 4 is finished.

Open checks before Phase 2:

1. Compare NASA POWER June 2026 rainfall (3 to 10 standard deviations above normal at every site) with CHIRPS for the same month, and decide whether to drop it.
2. Confirm CHIRPS covers all 549 months, or list the missing months.

Waiting on Emmanuel (not urgent):

1. Send the letters in `letters/` after filling in the bracketed items. The COCOBOD address is not yet confirmed.
2. Install `pdflatex` before the paper is final.

## Next: Phase 2 (describe the data)

Summary statistics, coverage tables, plots of each outcome against rainfall and temperature, seasonal patterns, and where sources disagree (2023/24 cocoa: USDA 531,000 t, ICCO 480,000 t; 2024 maize: FAOSTAT up 6 percent, USDA down 36 percent; MoFA revisions across editions). No regressions.

## Later

Phase 3: propose a specification before running anything; justify the lags from the agronomy literature; report every specification run. Phase 4: extend `paper/main.tex` into the full paper with a `.bib` file, and update the news review.
