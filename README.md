# 🌊 Ocean Health Score Dashboard

**Team ChumBucket** · DataHacks 2026 · Scripps Institution of Oceanography Challenge

**[→ Live App](https://chumbucket.streamlit.app)**

---

## What is this?

The California coast has been monitored by CalCOFI research ships since 1949 — one of the longest-running oceanographic time series in the world. We use 75 years of this data to compute a composite **Ocean Health Score** (0–100) for each sampling station, measuring how today's ocean compares to its own historical baseline.

Stations are visualized on an interactive map of the California coast. Green = healthy. Red = degraded. A time slider lets you watch ocean health change from 1991 to 2021.

---

## Health Score

Each station's score is computed by comparing recent measurements against its own 1949–1990 baseline using z-scores across three variables:

| Variable | Direction |
|---|---|
| Sea surface temperature | Higher than baseline = worse |
| Dissolved oxygen | Lower than baseline = worse |
| Chlorophyll-a (log-scaled) | Higher than baseline = worse |

```
health_score = 100 - clip(10 × (z_temp - z_oxygen + z_chlora), 0, 100)
```

A score of 100 means conditions match the historical baseline. Dips in the time series correspond to known events: the 1997–98 El Niño, the 2005 Pacific warm anomaly, and the 2014–16 "Blob" marine heatwave.

---

## Data

[CalCOFI Bottle Database](https://calcofi.org/data/oceanographic-data/bottle-database) — 895,000 bottle measurements from 1949–2021, filtered to the 0–50m mixed layer. Only stations with 20+ years of baseline data are included (60 stations, 1,568 scored station-year pairs).

Processed data is stored on AWS S3 and loaded at runtime — the app never touches the raw 175 MB CSV.

---

## Run Locally

```bash
git clone https://github.com/eri-gon/Chumbucket_hackathon26
cd Chumbucket_hackathon26
pip install -r requirements.txt
streamlit run app.py
```

To re-run the scoring pipeline from raw data:
```bash
python3 pipeline/score.py
```

---

## Stack

| Layer | Tool |
|---|---|
| Data processing | Python, Pandas, NumPy |
| Cloud storage | AWS S3 |
| Visualization | Plotly |
| App | Streamlit |
| Deployment | Streamlit Community Cloud |
