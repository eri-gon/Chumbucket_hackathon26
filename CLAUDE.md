# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**Ocean Health Score Dashboard** — DataHacks 2026 (April 18–19, 2026), Scripps Institution of Oceanography Challenge.

Computes a composite Ocean Health Score (0–100) per CalCOFI sampling station by comparing recent measurements against a 1949–1990 baseline. Visualized on an interactive California coast map with a time slider.

**Tracks:** Cloud Development + Data Analytics
**Deployment target:** Streamlit Community Cloud
**AWS:** S3 for data storage

## Project Structure

```
app.py                              # Streamlit entrypoint
METHODOLOGY.md                      # Data exploration findings and formula rationale
datahacks-2026_accessKeys.csv       # AWS credentials (never commit)
data/
  raw/                              # Cast.csv (~13MB), Bottle.csv (~175MB)
  processed/                        # scores.parquet, annual_means.parquet, baseline_stats.parquet
notebooks/
  exploration.ipynb                 # our EDA and pipeline prototyping
  exploration_teammate.ipynb        # teammate's EDA
  charts/                           # saved figures
pipeline/
  score.py                          # (to build) standalone pipeline: load → filter → score → save
  upload.py                         # (to build) push parquets to S3
  athena_setup.sql                  # Athena table DDL (optional path)
```

## Running the App

```bash
pip install streamlit plotly pandas numpy boto3 pyarrow
streamlit run app.py
```

AWS credentials are in `datahacks-2026_accessKeys.csv` — load into `~/.aws/credentials` before running S3 code.

## Data

Raw CSVs in `data/raw/`. Join `Cast.csv` + `Bottle.csv` on `Cst_Cnt`.

**Quality filtering:** set measurement to NaN where quality column is `8.0` (suspect) or `9.0` (missing).
Quality column map: `T_degC→T_qual`, `O2ml_L→O_qual`, `NO3uM→NO3q`, `PO4uM→PO4q`.

**Station eligibility:** 20+ distinct years of data within 1949–1990 baseline. Depth filter: 0–50m.

**pH is unusable** — only 84 non-null rows across 895K, only 2014–2015.

## Health Score Formula (finalized)

Variables: `T_degC`, `O2ml_L`, `log(ChlorA)`. Result: 60 stations, 1,568 scored (station, year) pairs, 1991–2021.

```python
# ChlorA is log-normally distributed — must log-transform before z-scoring
log_ChlorA = np.log(ChlorA.clip(lower=1e-4))

# Per-station z-scores vs 1949–1990 baseline
z_temp   = (T_degC     - baseline_mean_T)      / baseline_std_T
z_oxygen = (O2ml_L     - baseline_mean_O2)     / baseline_std_O2
z_chlora = (log_ChlorA - baseline_mean_logChl) / baseline_std_logChl

# Missing z-scores → 0 (neutral). Higher temp/chlora = worse; higher O2 = better.
health_score = 100 - np.clip(10 * (z_temp - z_oxygen + z_chlora), 0, 100)
```

## Tech Stack

| Layer | Library |
|---|---|
| Data processing | Pandas, NumPy |
| Visualization | Plotly (map + charts) |
| App framework | Streamlit |
| Cloud storage | AWS S3 (`boto3`) |

## Processed Data Schema

`data/processed/scores.parquet` — one row per (station, year), 1991–2021:
`Sta_ID, Year, Lat_Dec, Lon_Dec, T_degC, O2ml_L, ChlorA, z_temp, z_oxygen, z_chlora, health_score`

`data/processed/annual_means.parquet` — full time series 1949–2021 for drill-down charts:
`Sta_ID, Year, T_degC, O2ml_L, ChlorA, log_ChlorA, Lat_Dec, Lon_Dec`

`data/processed/baseline_stats.parquet` — per-station baseline stats:
`Sta_ID, T_degC_mean, T_degC_std, O2ml_L_mean, O2ml_L_std, log_ChlorA_mean, log_ChlorA_std`
