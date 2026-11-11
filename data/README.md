# Data

This folder holds every series used in the project. `src/run_all.py` rebuilds all of it.

`raw/` holds files exactly as downloaded. Nothing in `raw/` is edited by hand. `raw/MANIFEST.csv` lists each raw file with its URL, download time (UTC), size and SHA-256 hash. `clean/` holds the series after the cleaning steps described below. `panel/` holds the merged panels.

All downloads in this version were made on 11 November 2026 (UTC). The exact time of each file is in `raw/MANIFEST.csv`.

Some raw files are not in the repository. CHIRPS rasters are too large (about 2.4 GB). Files from the Bank of Ghana, the Ghana Statistical Service and the Ministry of Food and Agriculture are left out because none of the three websites states a reuse licence. The scripts download all of these files again. The cleaned series from these sources are committed. Whether that is acceptable is an open question for the author; see "Open questions" at the end.

No value in any file has been estimated, interpolated or filled in. A missing month stays missing.

---

## Outcome series

### Bank of Ghana: monthly cocoa export value

Source: Bank of Ghana (BoG).
URLs: online table at https://www.bog.gov.gh/economic-data/merchandise-trade-flows/ (read through the site's `admin-ajax.php?action=get_wdtable&table_id=30` endpoint); Monthly Statistical Bulletin, latest edition at https://www.bog.gov.gh/publications/statistical-bulletin/ (this run: `Statistical-Bulletin-Monthly_MAR_2026_APPROVED.xlsx`, Table 16 and Table 18).
Script: `src/outcome_bog.py`.
Coverage: January 2005 to March 2026 for cocoa beans and total merchandise exports, 255 months with no gaps. Cocoa products are reported monthly only from January 2020 (75 months). The bean series excludes products in every year: from 2010 to 2019 the annual sum of monthly bean exports is US$621 million to US$937 million below BoG's annual balance-of-payments figure for beans and products together (online table 17), and in 2020 beans plus products (1,480 + 848) equal that annual figure (2,328).
Unit: US$ million, free on board.
Frequency: monthly.
Clean files: `clean/bog_exports_monthly.csv`, `clean/bog_exports_monthly_long.csv` (with the source of each month), `clean/bog_overlap_check.csv`, `clean/bog_cocoa_prices_monthly.csv`.

Known problems. BoG publishes export value only. Neither BoG source gives monthly export volume, so the brief's request for "export volume and value" from BoG can be met for value only. The online table stops in April 2023, and it shows months it has not filled in as 0.00; those are set to missing, not zero. The bulletin gives the same figure (91.06) for April, May and June 2022, for cocoa beans, cocoa products and total exports alike. Three times that figure equals the sum of the online table's three monthly values to within US$0.01 million, so the bulletin spread a quarterly total evenly over the quarter. For those three months the online table's monthly values are used. The two sources overlap for 121 months (January 2013 to April 2023). They differ by more than US$0.05 million in six months, by up to US$55 million (November 2022 and April 2023). The combined series uses the bulletin, the later release, wherever it has a value. Both values for every overlapping month are in `bog_overlap_check.csv`.

### Eurostat Comext: EU imports of cocoa beans from Ghana

Source: Eurostat, dataset DS-045409 "EU trade since 1988 by HS2-4-6 and CN8".
URL: https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/DS-045409 with `freq=M&reporter=EU27_2020&partner=GH&product=1801&flow=1`.
Script: `src/outcome_eurostat.py`.
Coverage: January 2002 to August 2026, 296 months, no gaps.
Unit: tonnes (from QUANTITY_IN_100KG divided by 10) and euro million.
Frequency: monthly.
Clean file: `clean/eurostat_cocoa_imports_monthly.csv`.
Licence: free reuse with acknowledgement (Commission Decision 2011/833/EU). Raw JSON committed.

Known problems. EU27_2020 means the 27 current member states in every year. The United Kingdom is excluded throughout, so UK imports of Ghanaian beans are missing from this series. These are imports recorded at EU customs, so they lag shipment from Ghana by the sea voyage and do not cover beans sold to other destinations (Asia, North America, Ghana's own grinders). The last one or two years are revised by Eurostat and the script downloads them again on each run.

### US Census Bureau: US imports of cocoa beans from Ghana

Status: NOT DOWNLOADED.
URL: https://api.census.gov/data/timeseries/intltrade/imports/hs (HS 1801, country code 7490).
Script: `src/outcome_uscensus.py` (written, not yet run against live data).
Reason: every request without an API key is redirected to https://api.census.gov/data/missing_key.html. A free key is available at https://api.census.gov/data/key_signup.html. With the key set as the environment variable `CENSUS_API_KEY`, the script will run. Its output has not been checked yet.

### WFP food prices

Source: World Food Programme, through the Humanitarian Data Exchange (HDX).
URL: https://data.humdata.org/dataset/wfp-food-prices-for-ghana
Script: `src/outcome_wfp.py`.
Coverage: January 2006 to July 2023. 44 markets, 26 commodities, 39,038 price observations.
Unit: Ghana cedi per the unit WFP reports (for example 100 kg); `price_ghs_per_kg` converts units given in kilograms.
Frequency: monthly (WFP dates each price on the 15th).
Clean files: `clean/wfp_prices_long.csv`; `clean/wfp_prices_monthly_national.csv` (median across markets, per commodity and price type).
Licence: CC BY-IGO. Raw CSV committed.

Known problems. The HDX dataset ends in July 2023, although HDX shows it as modified on 8 November 2026. There is no WFP price for Ghana after July 2023 in this source. The number of observations per year jumps from about 600 in 2018 to over 3,000 from 2019, because WFP added markets and commodities, so national medians before and after 2019 are built from different market sets. Yam is priced per 100 tubers in some rows; those rows have no per-kg price.

### Ghana Statistical Service: quarterly GDP by agricultural sub-sector

Source: Ghana Statistical Service (GSS), "Rebased GDP quarterly bulletin 2006 to 2026Q2", September 2026 edition, sheet "Constant GDP_Agric".
URL: listing at https://statsghana.gov.gh/api/economic-statistics/national-accounts; file served from https://statsghana.gov.gh/api/minio/file?key=...
Script: `src/outcome_gss.py`.
Coverage: 2006 Q1 to 2026 Q2, 82 quarters.
Unit: GHS million at constant 2013 prices.
Frequency: quarterly.
Clean file: `clean/gss_qgdp_agric_constant2013.csv`. Columns: `crops_cocoa` (crops including cocoa), `cocoa`, `livestock`, `forestry_logging`, `fishing`, `total_value_added`, `ow_informal`, plus `status` (final, revised or provisional, from the file's * and ** marks).

Known problems. GSS revises recent quarters. Quarters from 2024 Q4 are marked revised and 2026 Q2 provisional. Cocoa value added is not a direct measure of tonnes produced; it depends on GSS's method for allocating the cocoa season to quarters.

### Ghana Statistical Service: Monthly Indicator of Economic Growth (MIEG)

Source: GSS, "July 2026 MIEG Bulletin" (.xlsb), sheet "MIEG".
Script: `src/outcome_gss.py`.
Coverage: January 2023 to July 2026, 43 months.
Unit: index, 2023 = 100. Year-on-year growth is a fraction (0.0651 means 6.51 percent).
Clean file: `clean/gss_mieg_monthly.csv`.

Known problems. The series starts in January 2023, so it is short. The agriculture index covers crops, fisheries and forestry, and excludes livestock; it has no separate cocoa index. GSS writes 0 for year-on-year growth in 2023, where there is no earlier year to compare with; these are set to missing. GSS states the index is not seasonally adjusted.

### Ghana Statistical Service: regional food CPI

Source: GSS, "October 2026 CPI COICOP Annexes", sheet "Annex3-CPI by Region".
URL: listing at https://statsghana.gov.gh/api/economic-statistics/price-index.
Script: `src/outcome_gss.py`.
Coverage: September 2022 to October 2026, all 16 regions, 50 months each.
Unit: index, average 2021 = 100 (food and non-alcoholic beverages).
Clean file: `clean/gss_cpi_food_region_monthly.csv`.

Known problems. The current base starts in September 2022 in this file. Earlier editions use other bases; they are not spliced on.

### FAOSTAT: annual crop area, production and yield

Source: FAO, FAOSTAT Crops and Livestock Products, bulk file for Africa.
URL: https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip
Script: `src/outcome_faostat.py`.
Coverage: 1961 to 2024. Cocoa beans, maize, rice, cassava, yams, millet, sorghum.
Unit: hectares, tonnes, kg per hectare.
Frequency: annual.
Clean file: `clean/faostat_ghana_crops_annual.csv` (long form, with FAO flag).
Licence: CC BY 4.0. Raw zip (4.3 MB) committed.

Known problems. FAOSTAT flags each value: A official, E estimated, I imputed, X from an international organisation. Of 1,344 values, 1,063 are A, 211 E, 41 X and 29 I. FAOSTAT and other sources disagree for recent years. FAOSTAT gives 2024 maize as 3.79 million tonnes, up from 3.58 million in 2023, while USDA reported a 36 percent fall (main.tex). FAOSTAT gives 2020 cassava as 24.37 million tonnes; MoFA's 2021 edition gives 22.96 million. For 2024 cocoa, FAOSTAT gives 530,000 tonnes. Phase 2 compares sources in full.

### MoFA SRID: Agriculture in Ghana: Facts and Figures (2018 to 2021 editions)

Source: Ministry of Food and Agriculture (MoFA), Statistics, Research and Information Directorate (SRID).
URL: https://mofa.gov.gh/site/publications/research-reports (PDFs under https://mofa.gov.gh/site/images/pdf/).
Script: `src/outcome_mofa.py`. Tables are extracted from the PDF text with code; the PDFs stay in `raw/mofa/` so each value can be checked against its page.
Coverage: national production and cropped area of 11 crops, 2009 to 2021 (Appendices 15 and 16; each edition covers 5 or 10 years). Annual rainfall for the 10 pre-2018 regions, 2009 to 2021, from the Ghana Meteorological Agency (Table 2.9).
Unit: tonnes, hectares, mm per year.
Frequency: annual.
Clean files: `clean/mofa_production_area_by_edition.csv`, `clean/mofa_regional_rainfall_by_edition.csv`, `clean/mofa_unparsed_rows.csv`.

Known problems. These four editions are the only ones on the MoFA website; nothing after 2021 is posted. The reports do not contain a complete regional or district production panel: district tables list only the ten highest-yielding districts per crop, and regional figures are top-five shares. A full district panel has to be requested (see `letters/`). MoFA revises earlier years between editions; for example, 2019 maize is 2,852,020 t in the 2019 edition and 2,911,884 t in the 2020 and 2021 editions. Every edition's value is kept, tagged by edition. Five table rows could not be read cleanly and are left missing rather than typed in: the 2018 edition's cassava row (wrapped across lines in the PDF), and oil palm rows that have nine numbers for ten years. Table 2.9 in the 2020 and 2021 editions prints Central Region rainfall for 2020 as 30 mm, which cannot be right for an annual total; it is kept as printed and flagged.

### Cocoa and grain prices

World Bank Commodity Price Data (Pink Sheet). URL found each run from https://www.worldbank.org/en/research/commodity-markets (this run: release of 3 November 2026). Script `src/prices_worldbank.py`. Monthly, January 1960 to October 2026. Cocoa in US$ per kg (the World Bank's cocoa price is the ICCO daily price average), maize in US$ per tonne, Thai 5% rice in US$ per tonne. Licence CC BY 4.0; raw file committed. Clean file `clean/worldbank_prices_monthly.csv`. The original `get_data.py` pointed to the January 2025 file; the script now finds the current link.

Bank of Ghana, Statistical Bulletin Table 18: cocoa LIFFE (GBP per tonne, January 2006 to March 2026, 231 months) and CSCE (US$ per tonne, September 2014 to March 2026, 139 months), monthly averages, source given by BoG as Reuters. Clean file `clean/bog_cocoa_prices_monthly.csv`.

ICCO. The ICCO statistics page (https://www.icco.org/statistics/) offers the Quarterly Bulletin of Cocoa Statistics by paid subscription and monthly market reports as PDFs. No ICCO series was downloaded. The Pink Sheet cocoa price is the ICCO price, so a separate ICCO download is not needed for prices. ICCO production estimates by country remain behind the subscription.

### World Bank World Development Indicators

Five annual indicators for Ghana, 1960 to 2025: agriculture value added (percent of GDP and growth), agricultural employment share, cereal yield, CPI inflation. API https://api.worldbank.org/v2/. Script `src/worldbank_indicators.py`. Clean file `clean/worldbank_ghana_annual.csv`. Background only.

---

## Weather series

### CHIRPS v2.0 rainfall, regional averages

Source: Climate Hazards Center, UC Santa Barbara. CHIRPS v2.0, Africa monthly GeoTIFFs, 0.05 degree grid.
URL: https://data.chc.ucsb.edu/products/CHIRPS/v2.0/africa_monthly/tifs/
Script: `src/weather_chirps.py`.
Coverage: January 1981 to September 2026 (549 files listed on 11 November 2026).
Unit: mm per month.
Clean file: `clean/chirps_region_monthly.csv` (16 regions).
Method: for each month, the unweighted mean of the grid cells whose centre lies inside the region boundary (geoBoundaries, below). Cell area differs by under 1.5 percent across Ghana's latitudes and is ignored.

Status and known problems. See the status note at the top of the Phase 1 report: the download was interrupted when the CHC server began refusing connections from this machine (HTTP 429, then timeouts) after the script made parallel requests. The script now downloads one file at a time with back-off. Any month that cannot be downloaded is reported and left missing. CHIRPS v3.0 (released 2025) is also available and is wetter than v2.0 because of a gauge under-catch correction; v2.0 is used because it is the version used in published work so far. CHIRPS is gridded and blends satellite and station data; it is not station data.

### NASA POWER point weather

Source: NASA Langley POWER project, monthly point API, community AG.
URL: https://power.larc.nasa.gov/api/temporal/monthly/point
Script: `src/weather_nasa_power.py`.
Coverage: January 1981 to September 2026, nine sites: Sefwi Wiawso (Western North), Tarkwa (Western), Kumasi (Ashanti), Assin Foso (Central), Koforidua (Eastern), Techiman (Bono East), Tamale (Northern), Tumu (Upper West), Bolgatanga (Upper East).
Unit: rainfall mm per month (the API gives mm per day; multiplied by days in the month), temperature (mean, maximum, minimum) deg C at 2 m, relative humidity percent.
Clean file: `clean/nasa_power_site_monthly.csv`.

Known problems. Each site is the grid cell (about 0.5 by 0.625 degrees) containing the town, not a station and not a regional average. June 2026 rainfall is far outside each site's own history: between 3.0 and 10.3 standard deviations above the 1981 to 2025 June mean (Kumasi 914 mm against a June mean of 235 mm; Techiman 816 mm against 187 mm). Recent POWER precipitation is near-real-time and is replaced later. The value is kept and flagged (`nasa_rain_flag` in the panel). It will be compared with CHIRPS for June 2026 before any decision. The news review records heavy rain in May and June 2026, so some excess is real; the size of the excess is what is doubtful.

### CRU TS 4.09, national average

Source: Climatic Research Unit TS 4.09, through the World Bank Climate Change Knowledge Portal API.
URL: https://cckpapi.worldbank.org/cckp/v1/cru-x0.5_timeseries_{pr,tas,tasmax,tasmin}_timeseries_monthly_1901-2024_mean_historical_cru_ts4.09_mean/GHA
Script: `src/weather_cru_cckp.py`.
Coverage: January 1901 to December 2024, Ghana national average.
Unit: mm per month; deg C.
Clean file: `clean/cru_national_monthly.csv`.
Licence: CC BY 4.0.

Known problems. Only the national average. The API returned empty results for every sub-national code format tried, so regional CRU series were not obtained.

### Nino 3.4 index

Source: NOAA Climate Prediction Center. Public domain.
URLs: https://www.cpc.ncep.noaa.gov/data/indices/ersst5.nino.mth.91-20.ascii (ERSSTv5, January 1950 to June 2026 on the download date) and https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices (OISSTv2, January 1982 to October 2026).
Script: `src/weather_enso.py`.
Unit: deg C, anomaly relative to 1991 to 2020.
Clean file: `clean/nino34_monthly.csv`.

Known problems. The ERSSTv5 file had not been updated past June 2026. The two series are kept as separate columns and are not spliced; their anomalies correlate at 0.988 over the 534 months they share. The panel analysis will use the OISST anomaly because it covers the full sample.

### Region boundaries

Source: geoBoundaries gbOpen, Ghana ADM1 (16 regions), from OpenStreetMap, boundary year 2021.
URL: https://www.geoboundaries.org/api/current/gbOpen/GHA/ADM1/
Licence: CC BY-SA 2.0. Committed.
Script: `src/boundaries.py`.

---

## Panels

`panel/panel_national_monthly.csv` is the merged monthly panel. One row per month from January 1981. Zone weather columns are unweighted means over the regions (CHIRPS: `cocoa_`, `transition_`, `cereal_` prefixes) or sites (NASA POWER) in each zone, computed only when every member has a value. Outcome and price columns are as in the clean files. Empty cells are missing data.

`panel/panel_region_monthly.csv`: region by month. CHIRPS rainfall for all 16 regions, NASA POWER weather for the 9 regions with a site, GSS regional food CPI.

`panel/panel_market_monthly.csv`: WFP prices by market, commodity, price type and month, with each market's current (post-2018) region found from its coordinates and that region's CHIRPS rainfall. Sekondi/Takoradi lies 0.006 degrees outside the coastline polygon and is placed in the nearest region; the method used for each market is recorded.

`panel/panel_national_quarterly.csv`: GSS agricultural GDP with quarterly rainfall totals and mean temperatures.

`panel/panel_national_annual.csv`: FAOSTAT and MoFA (latest edition for each year) production, area and yield with annual rainfall totals.

---

## Sources opened and not downloaded

FAO GIEWS Food Price Monitoring and Analysis tool (https://fpma.fao.org/giews/fpmat4/). It is a JavaScript application; no documented public data API was found. Its Ghana price series overlap the WFP and MoFA prices.

Ghana Meteorological Agency station data. GMet has an online data request form at https://www.meteo.gov.gh/data-request/ with a sector option for academia and research. The page does not state fees. No request has been submitted.

COCOBOD weekly purchases and district production. Not published. A draft request letter is in `letters/`.

MoFA SRID district production. Not published as a complete panel. A draft request letter is in `letters/`.

ICCO Quarterly Bulletin. Paid subscription.

## Open questions for the author

Whether to commit the cleaned BoG, GSS and MoFA series, given that their websites state no reuse licence. They are committed in this version; the raw files are not.
