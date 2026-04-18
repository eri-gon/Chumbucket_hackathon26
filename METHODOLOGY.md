# Methodology

## Data Sources

Two CSVs from the [CalCOFI Bottle Database](https://calcofi.org/data/oceanographic-data/bottle-database), joined on `Cst_Cnt`:

| File | Rows | Description |
|---|---|---|
| `Cast.csv` | 35,644 | Cruise metadata: station ID, lat/lon, date/year |
| `Bottle.csv` | 895,371 | Chemical measurements at depth, 62 columns |

---

## Exploration Findings

### pH is unusable
`pH1` had only 84 non-null values across 895K rows, exclusively from 2014–2015. Dropped entirely.

### Variable coverage splits by era
Temperature and oxygen were measured consistently since 1949. Nutrients and chlorophyll weren't collected systematically until the 1990s — sparse in the baseline, dense in the scoring period.

| Variable | Baseline (1949–1990) | Scoring (1991–2021) |
|---|---|---|
| T_degC | 96% | 100% |
| O2ml_L | 71% | 95% |
| ChlorA | 20% | 95% |
| NO3uM | 21% | 94% |
| PO4uM | 33% | 94% |
| pH1 | ~0% | ~0% |

### Station sparsity
Of 2,600+ unique stations, only **106** had data spanning 20+ distinct years within the 1949–1990 baseline (eligibility threshold). Of those, **60** also had post-1990 data to score against.

### Depth filter: 0–50m
The dataset spans 0–5,351m depth. We restrict to the **mixed layer (0–50m)**:
- Captures surface-driven processes: warming, oxygen depletion, phytoplankton blooms
- Consistent across casts (not all casts go deep)
- Multiple bottle samples per cast are averaged to a single annual mean per station

### ChlorA is log-normally distributed
Raw ChlorA z-scores reached 13–24× during algal bloom years, collapsing health scores to 0. Log-transforming before z-scoring is standard oceanographic practice and stabilized the metric.

---

## Variable Selection

**Final variables: `T_degC`, `O2ml_L`, `log(ChlorA)`**

| Variable | Direction | Rationale |
|---|---|---|
| T_degC | Higher = worse | Ocean warming is a primary stress indicator |
| O2ml_L | Lower = worse | Hypoxia directly threatens marine life |
| log(ChlorA) | Higher = worse | Elevated chlorophyll signals algal blooms / eutrophication |

NO3 and PO4 were excluded — only 21–33% baseline coverage made per-station baselines unreliable.

---

## Quality Filtering

Rows where a quality-code column equals `8` (suspect) or `9` (missing) have the corresponding measurement set to `NaN` before any aggregation:

| Measurement | Quality column |
|---|---|
| T_degC | T_qual |
| O2ml_L | O_qual |
| NO3uM | NO3q |
| PO4uM | PO4q |

ChlorA and SiO3 have no quality columns — NaN values are treated as missing naturally.

---

## Health Score Formula

```python
# ChlorA must be log-transformed before z-scoring
log_ChlorA = log(ChlorA.clip(lower=1e-4))

# Per-station z-scores relative to 1949–1990 baseline
z_temp   = (T_degC     - baseline_mean_T)      / baseline_std_T
z_oxygen = (O2ml_L     - baseline_mean_O2)     / baseline_std_O2
z_chlora = (log_ChlorA - baseline_mean_logChl) / baseline_std_logChl

# Missing z-scores → 0 (neutral, no penalty)
health_score = 100 - clip(10 * (z_temp - z_oxygen + z_chlora), 0, 100)
```

The `10×` multiplier means a 1 standard deviation combined anomaly = 10-point score drop. Scores are bounded to [0, 100].

---

## Pipeline

| Step | Output |
|---|---|
| Load Cast + Bottle, join on `Cst_Cnt` | merged DataFrame |
| Apply quality filters (drop qual 8/9) | cleaned DataFrame |
| Filter to 0–50m depth | 265,268 rows |
| Keep stations with 20+ baseline years | 106 stations |
| Aggregate to annual means per station | 4,327 (station, year) rows |
| Compute baseline stats (mean/std, 1949–1990) | `baseline_stats.parquet` |
| Compute z-scores + health scores (1991–2021) | `scores.parquet` |
| Preserve full time series for drill-down | `annual_means.parquet` |

---

## Results

- **60 stations** scored (subset of 106 eligible that also have post-1990 data)
- **1,568** (station, year) pairs, 1991–2021
- Score range: **16.9 – 100**
- Mean score: **85.3** (stations are generally near-baseline, with periodic stress events)

### Validation
Mean score dips align with known oceanographic events:

| Year(s) | Event | Mean Score |
|---|---|---|
| 1997–98 | El Niño | ~82 |
| 2005 | Pacific warm anomaly | ~81 |
| 2014–16 | "The Blob" marine heatwave + El Niño | ~78–76 |
| 2020 | Warming anomaly | ~74 (lowest) |

---

## Column Reference

Source: [CalCOFI Bottle Database](https://calcofi.org/data/oceanographic-data/bottle-database/)

### Cast Table (cruise metadata)

| Column | Units | Description |
|---|---|---|
| Cst_Cnt | — | Sequential cast number — **join key** with Bottle |
| Sta_ID | — | Line and station designation |
| Year | — | Calendar year |
| Month | — | Calendar month |
| Date | — | Month, day, year |
| Lat_Dec | decimal degrees | Latitude |
| Lon_Dec | decimal degrees | Longitude |
| Bottom_D | meters | Seafloor depth |
| Data_Type | — | Measurement type (PR, HY, 10, CT, MX) |
| Ship_Name | — | Vessel name |
| Wind_Spd | knots | Wind speed |
| Wave_Ht | feet | Wave height |
| Secchi | meters | Water clarity depth |

### Bottle Table (measurements)

| Column | Units | Description |
|---|---|---|
| Cst_Cnt | — | Cast number — **join key** with Cast |
| Depthm | meters | Sample collection depth |
| T_degC | °C | Water temperature |
| T_qual | — | Temperature quality flag (8=suspect, 9=missing) |
| Salnty | PSS-1978 | Salinity |
| S_qual | — | Salinity quality flag |
| O2ml_L | ml/L | Dissolved oxygen concentration |
| O_qual | — | Oxygen quality flag (8=suspect, 9=missing) |
| O2Sat | % | Oxygen saturation |
| ChlorA | µg/L | Chlorophyll-a — photosynthetic pigment concentration |
| Chlqua | — | Chlorophyll quality flag |
| Phaeop | µg/L | Phaeopigment (degraded chlorophyll) |
| NO3uM | µmol/L | Nitrate concentration |
| NO3q | — | Nitrate quality flag |
| NO2uM | µmol/L | Nitrite concentration |
| PO4uM | µmol/L | Phosphate concentration |
| PO4q | — | Phosphate quality flag |
| SiO3uM | µmol/L | Silicate concentration |
| NH3uM | µmol/L | Ammonia concentration |
| pH1 | pH | Seawater acidity (sparse — only 84 non-null rows, 2014–2015 only) |
| pH2 | pH | pH replicate |
| DIC1 | µmol/kg | Dissolved inorganic carbon |
| TA1 | µmol/kg | Total alkalinity |
| STheta | kg/m³ | Potential density anomaly |
