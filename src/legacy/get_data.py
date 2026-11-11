"""
Ghana agriculture + weather: monthly data downloader.
Run locally:  pip install requests pandas openpyxl ; python get_data.py
Each source is independent; a failure prints a message and the rest continue.
Output goes to ./ghana_data/
"""
import io, os, zipfile
import requests, pandas as pd

OUT = "ghana_data"; os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers["User-Agent"] = "capstone-research"

def step(name, fn):
    try:
        fn(); print(f"[ok]   {name}")
    except Exception as e:
        print(f"[FAIL] {name}: {e}")

# 1. NASA POWER: monthly rainfall, temperature, humidity, 1990-2025, by location
SITES = {  # name: (lat, lon, zone)
    "SefwiWiawso_WesternNorth": (6.21, -2.49, "cocoa"),
    "Tarkwa_Western":           (5.30, -1.99, "cocoa"),
    "Kumasi_Ashanti":           (6.69, -1.62, "cocoa"),
    "AssinFoso_Central":        (5.70, -1.28, "cocoa"),
    "Koforidua_Eastern":        (6.09, -0.26, "cocoa"),
    "Techiman_BonoEast":        (7.59, -1.94, "transition"),
    "Tamale_Northern":          (9.40, -0.84, "cereal"),
    "Tumu_UpperWest":           (10.88, -1.98, "cereal"),
    "Bolgatanga_UpperEast":     (10.79, -0.85, "cereal"),
}
PARAMS = "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M"

def nasa_power():
    rows = []
    for site, (lat, lon, zone) in SITES.items():
        r = S.get("https://power.larc.nasa.gov/api/temporal/monthly/point",
                  params=dict(parameters=PARAMS, community="AG", latitude=lat,
                              longitude=lon, start=1990, end=2025, format="JSON"),
                  timeout=120)
        r.raise_for_status()
        par = r.json()["properties"]["parameter"]
        for ym in par["PRECTOTCORR"]:
            if ym.endswith("13"):      # month 13 = annual value
                continue
            row = dict(site=site, zone=zone, lat=lat, lon=lon,
                       year=int(ym[:4]), month=int(ym[4:]))
            for p in par:
                v = par[p][ym]
                row[p] = None if v == -999 else v
            rows.append(row)
    df = pd.DataFrame(rows)
    days = pd.to_datetime(dict(year=df.year, month=df.month, day=1)).dt.days_in_month
    df["rain_mm_month"] = df["PRECTOTCORR"] * days   # API gives mm/day
    df.to_csv(f"{OUT}/weather_monthly_nasa_power.csv", index=False)

# 2. WFP food prices for Ghana (monthly, by market and commodity) via HDX
def wfp_prices():
    meta = S.get("https://data.humdata.org/api/3/action/package_show",
                 params={"id": "wfp-food-prices-for-ghana"}, timeout=60).json()
    for res in meta["result"]["resources"]:
        url = res["url"]
        if url.lower().endswith(".csv"):
            name = os.path.basename(url.split("?")[0])
            open(f"{OUT}/{name}", "wb").write(S.get(url, timeout=180).content)

# 3. World Bank "Pink Sheet": monthly world cocoa (and maize, rice) prices since 1960
#    If this link 404s, get the current one from worldbank.org/commodities
def pink_sheet():
    url = ("https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-"
           "0050012025/related/CMO-Historical-Data-Monthly.xlsx")
    r = S.get(url, timeout=180); r.raise_for_status()
    open(f"{OUT}/worldbank_pinksheet_monthly.xlsx", "wb").write(r.content)

# 4. FAOSTAT: annual production, area, yield by crop (filter to Ghana)
def faostat():
    url = "https://bulks-faostat.fao.org/production/Production_Crops_Livestock_E_Africa.zip"
    z = zipfile.ZipFile(io.BytesIO(S.get(url, timeout=600).content))
    name = [n for n in z.namelist() if n.endswith(".csv") and "Flags" not in n
            and "Codes" not in n][0]
    df = pd.read_csv(z.open(name), encoding="latin-1")
    df[df["Area"] == "Ghana"].to_csv(f"{OUT}/faostat_ghana_production.csv", index=False)

# 5. World Bank annual indicators for context
WB = {"NV.AGR.TOTL.ZS": "agri_value_added_pct_gdp",
      "NV.AGR.TOTL.KD.ZG": "agri_value_added_growth",
      "SL.AGR.EMPL.ZS": "agri_employment_pct",
      "AG.YLD.CREL.KG": "cereal_yield_kg_ha",
      "FP.CPI.TOTL.ZG": "cpi_inflation"}

def worldbank():
    frames = []
    for code, label in WB.items():
        j = S.get(f"https://api.worldbank.org/v2/country/GHA/indicator/{code}",
                  params={"format": "json", "per_page": 200}, timeout=60).json()
        frames.append(pd.DataFrame([dict(year=int(d["date"]), indicator=label,
                                         value=d["value"]) for d in j[1]]))
    (pd.concat(frames).pivot(index="year", columns="indicator", values="value")
       .sort_index().to_csv(f"{OUT}/worldbank_ghana_annual.csv"))

for name, fn in [("NASA POWER monthly weather", nasa_power),
                 ("WFP food prices (HDX)", wfp_prices),
                 ("World Bank Pink Sheet", pink_sheet),
                 ("FAOSTAT production", faostat),
                 ("World Bank indicators", worldbank)]:
    step(name, fn)
print(f"\nFiles written to ./{OUT}/")
