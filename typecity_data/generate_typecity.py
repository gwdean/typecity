"""
TypeCity Data Generator
=======================
Generates all CSV files for the TypeCity analytics project.
Seeded for full reproducibility.

Output files:
  quarters.csv         4 rows
  districts.csv       16 rows
  neighborhoods.csv   64 rows
  cells.csv          256 rows
  subway_lines.csv     2 rows
  subway_stations.csv 18 rows  (Central appears once per line)
  station_lines.csv   18 rows  (junction table)
  ridership.csv    2,856 rows  (17 unique stations × 24h × 7 days)
"""

import pandas as pd
import numpy as np
import os

SEED = 42
rng  = np.random.default_rng(SEED)
OUT  = "typecity_data"
os.makedirs(OUT, exist_ok=True)

POSITIONS = ["A", "B", "C", "D"]

# ──────────────────────────────────────────────
# 1. QUARTERS
# ──────────────────────────────────────────────
quarters_data = [
    ("NW", "Northwest Quarter", "Residential", "high"),
    ("NE", "Northeast Quarter", "Commercial",  "medium"),
    ("SW", "Southwest Quarter", "Industrial",  "low"),
    ("SE", "Southeast Quarter", "Mixed",       "medium"),
]
quarters = pd.DataFrame(quarters_data,
    columns=["quarter_id","name","character","base_pop_density"])


# ──────────────────────────────────────────────
# 2. DISTRICTS  (16 rows — real names)
# ──────────────────────────────────────────────
district_names = {
    "NW": ["Maplewood",   "Riverside",    "Elmhurst",    "Ferndale"],
    "NE": ["Goldgate",    "Iron Row",     "Commerce Row","The Exchange"],
    "SW": ["Millyard",    "Copperton",    "Grayfield",   "Slagtown"],
    "SE": ["Harborview",  "Crossroads",   "Midvale",     "Eastbridge"],
}

districts = pd.DataFrame([
    {"district_id": f"{q}-{p}",
     "quarter_id":  q,
     "position":    p,
     "name":        district_names[q][i]}
    for q, names in district_names.items()
    for i, (p, _) in enumerate(zip(POSITIONS, names))
])


# ──────────────────────────────────────────────
# 3. NEIGHBORHOODS  (64 rows)
# ──────────────────────────────────────────────
neighborhoods = pd.DataFrame([
    {"neighborhood_id": f"{d}-{p}",
     "district_id":     d,
     "quarter_id":      row.quarter_id,
     "position":        p}
    for _, row in districts.iterrows()
    for d, p in [(row.district_id, p) for p in POSITIONS]
])


# ──────────────────────────────────────────────
# 4. CELLS  (256 rows, 16×16 grid)
#
#  Coordinate system (x=0-15 W→E, y=0-15 S→N):
#
#  y=15 ┌──────────┬──────────┐
#       │  NW      │  NE      │
#  y=8  ├──────────┼──────────┤  ← Blue Line
#       │  SW      │  SE      │
#  y=0  └──────────┴──────────┘
#       x=0        x=8       x=15
#                  ↑ Orange Line
# ──────────────────────────────────────────────

density = {
    "NW": dict(pop_mu=4200, pop_sig=800,  inc_mu=72000,  inc_sig=12000),
    "NE": dict(pop_mu=2800, pop_sig=1200, inc_mu=95000,  inc_sig=25000),
    "SW": dict(pop_mu=1400, pop_sig=600,  inc_mu=48000,  inc_sig=8000),
    "SE": dict(pop_mu=3200, pop_sig=900,  inc_mu=61000,  inc_sig=15000),
}

zoning_w = {
    "NW": [0.65, 0.10, 0.05, 0.15, 0.05],
    "NE": [0.15, 0.55, 0.05, 0.20, 0.05],
    "SW": [0.15, 0.10, 0.55, 0.15, 0.05],
    "SE": [0.30, 0.20, 0.10, 0.35, 0.05],
}
ZONES = ["Residential","Commercial","Industrial","Mixed","Park"]

def quarter_of(x, y):
    if x < 8 and y >= 8: return "NW"
    if x >= 8 and y >= 8: return "NE"
    if x < 8 and y <  8: return "SW"
    return "SE"

def district_pos(x, y):
    col = 0 if (x % 8) < 4 else 1
    row = 0 if (y % 8) < 4 else 1
    return POSITIONS[row * 2 + col]

def neighborhood_pos(x, y):
    col = 0 if (x % 4) < 2 else 1
    row = 0 if (y % 4) < 2 else 1
    return POSITIONS[row * 2 + col]

def cell_pos(x, y):
    return POSITIONS[(y % 2) * 2 + (x % 2)]

cells_rows = []
for y in range(16):
    for x in range(16):
        q  = quarter_of(x, y)
        dp = district_pos(x, y)
        np_ = neighborhood_pos(x, y)
        cp = cell_pos(x, y)

        d_id = f"{q}-{dp}"
        n_id = f"{d_id}-{np_}"
        c_id = f"{n_id}-{cp}"

        p   = density[q]
        pop = max(0, int(rng.normal(p["pop_mu"], p["pop_sig"])))
        inc = max(0, int(rng.normal(p["inc_mu"], p["inc_sig"])))
        zone = rng.choice(ZONES, p=zoning_w[q])

        if zone == "Park":
            pop = int(pop * 0.08)

        res  = int(pop / 2.5)  if zone in ("Residential","Mixed") else int(pop / 5)
        comm = int(rng.integers(30, 250)) if zone in ("Commercial","Mixed") else int(rng.integers(0, 40))
        park = float(rng.uniform(0.55, 0.95)) if zone == "Park" else float(rng.uniform(0.0, 0.18))

        cells_rows.append({
            "cell_id":              c_id,
            "neighborhood_id":      n_id,
            "district_id":          d_id,
            "quarter_id":           q,
            "x": x, "y": y,
            "population":           pop,
            "zoning_type":          zone,
            "avg_household_income": inc,
            "residential_units":    res,
            "commercial_units":     comm,
            "park_pct":             round(park, 3),
        })

cells = pd.DataFrame(cells_rows)


# ──────────────────────────────────────────────
# 5. SUBWAY LINES
# ──────────────────────────────────────────────
subway_lines = pd.DataFrame([
    ("Orange","N-S",16,9,"#FF8C00"),
    ("Blue",  "E-W",16,9,"#1E90FF"),
], columns=["line_id","direction","length_miles","num_stops","color_hex"])


# ──────────────────────────────────────────────
# 6. SUBWAY STATIONS  (18 rows — Central once per line)
#    Mile markers 0,2,4,6,8,10,12,14,16
#    Orange: x=8 (city center column), y=mile marker
#    Blue:   y=8 (city center row),    x=mile marker
# ──────────────────────────────────────────────
orange_stations = [
    ("OL-1","South Terminus",         8,  0, False),
    ("OL-2","Southgate",              8,  2, False),
    ("OL-3","South District",         8,  4, False),
    ("OL-4","South Inner",            8,  6, False),
    ("OL-5","Central Station",        8,  8, True ),
    ("OL-6","North Inner",            8, 10, False),
    ("OL-7","North District",         8, 12, False),
    ("OL-8","Northgate",              8, 14, False),
    ("OL-9","North Terminus",         8, 16, False),
]
blue_stations = [
    ("BL-1","West Terminus",          0,  8, False),
    ("BL-2","Westgate",               2,  8, False),
    ("BL-3","West District",          4,  8, False),
    ("BL-4","West Inner",             6,  8, False),
    ("BL-5","Central Station",        8,  8, True ),
    ("BL-6","East Inner",            10,  8, False),
    ("BL-7","East District",         12,  8, False),
    ("BL-8","Eastgate",              14,  8, False),
    ("BL-9","East Terminus",         16,  8, False),
]

stations = pd.DataFrame(
    orange_stations + blue_stations,
    columns=["station_id","name","x","y","is_transfer"]
)


# ──────────────────────────────────────────────
# 7. STATION_LINES  (junction table, 18 rows)
# ──────────────────────────────────────────────
station_lines = pd.DataFrame(
    [{"station_id": s[0], "line_id": "Orange"} for s in orange_stations] +
    [{"station_id": s[0], "line_id": "Blue"}   for s in blue_stations]
)


# ──────────────────────────────────────────────
# 8. RIDERSHIP  (18 stations × 24h × 7 days = 3,024 rows)
#
#  Weekday pattern : bimodal AM (8am) / PM (5:30pm) peaks
#  Weekend pattern : flat midday hump
#  Central Station : ~5× hub multiplier
#  Terminus        : low base
# ──────────────────────────────────────────────
DAYS = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

# Unique-station base daily boardings
base_boardings = {
    "OL-1": 1100, "OL-2": 2200, "OL-3": 3500, "OL-4": 5000,
    "OL-5": 19000,
    "OL-6": 5300, "OL-7": 3700, "OL-8": 2300, "OL-9": 1000,
    "BL-1": 1200, "BL-2": 2400, "BL-3": 3800, "BL-4": 5400,
    "BL-5": 22000,
    "BL-6": 4800, "BL-7": 3400, "BL-8": 2000, "BL-9":  900,
}

def hour_weight(h, weekend):
    if weekend:
        if h < 6 or h > 22:  return 0.015
        if 10 <= h <= 18:    return 0.55 + 0.45 * np.sin((h-10)/8 * np.pi)
        return 0.25
    else:
        am = np.exp(-0.5 * ((h - 8.0) / 1.2) ** 2)
        pm = np.exp(-0.5 * ((h - 17.5)/ 1.5) ** 2)
        return 0.04 + 0.96 * max(am, pm)

ridership_rows = []
for day in DAYS:
    is_wknd = day in ("Saturday","Sunday")
    wknd_f  = 0.62 if is_wknd else 1.0

    raw_weights = np.array([hour_weight(h, is_wknd) for h in range(24)])
    hourly_frac = raw_weights / raw_weights.sum()

    for sid, base in base_boardings.items():
        day_noise   = float(rng.uniform(0.88, 1.12))
        daily_total = base * wknd_f * day_noise

        for h in range(24):
            boardings = int(daily_total * hourly_frac[h])
            # Alightings: mirror with directional skew
            # AM peak → more people arriving (alightings > boardings at destination)
            # PM peak → more people departing  (boardings > alightings at origin)
            if   7 <= h <= 9:  af = float(rng.uniform(1.10, 1.45))
            elif 16 <= h <= 19: af = float(rng.uniform(0.55, 0.90))
            else:               af = float(rng.uniform(0.85, 1.15))

            ridership_rows.append({
                "station_id":  sid,
                "day_of_week": day,
                "hour":        h,
                "boardings":   boardings,
                "alightings":  int(boardings * af),
            })

ridership = pd.DataFrame(ridership_rows)


# ──────────────────────────────────────────────
# SAVE
# ──────────────────────────────────────────────
frames = {
    "quarters.csv":         quarters,
    "districts.csv":        districts,
    "neighborhoods.csv":    neighborhoods,
    "cells.csv":            cells,
    "subway_lines.csv":     subway_lines,
    "subway_stations.csv":  stations,
    "station_lines.csv":    station_lines,
    "ridership.csv":        ridership,
}

print(f"\n{'FILE':<26} {'ROWS':>6}  {'COLS':>4}  COLUMNS")
print("─" * 80)
for fname, df in frames.items():
    df.to_csv(f"{OUT}/{fname}", index=False)
    print(f"{fname:<26} {len(df):>6}  {len(df.columns):>4}  {', '.join(df.columns)}")

# Quick sanity checks
print("\n── Sanity checks ──────────────────────────────────")
print(f"Total city population : {cells['population'].sum():,}")
print(f"Population by quarter :\n{cells.groupby('quarter_id')['population'].sum().to_string()}")
print(f"\nZoning mix (cells)    :\n{cells['zoning_type'].value_counts().to_string()}")
print(f"\nTop 5 ridership stations (weekly boardings):")
weekly = ridership.groupby("station_id")["boardings"].sum().sort_values(ascending=False)
print(weekly.head(5).to_string())
print(f"\nRidership table rows  : {len(ridership):,}")
