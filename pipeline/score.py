import pandas as pd
import numpy as np
import os

RAW_DIR = "data/raw"
OUT_DIR = "data/processed"
CAST_FILE = os.path.join(RAW_DIR, "Cast.csv")
BOTTLE_FILE = os.path.join(RAW_DIR, "Bottle.csv")

BASELINE_END = 1990
SCORING_START = 1991
DEPTH_MAX = 50
MIN_BASELINE_YEARS = 20
VARS = ["T_degC", "O2ml_L", "ChlorA"]
QUAL_MAP = {"T_degC": "T_qual", "O2ml_L": "O_qual"}

SEASON_MAP = {12: "Winter", 1: "Winter", 2: "Winter",
              3: "Spring", 4: "Spring", 5: "Spring",
              6: "Summer", 7: "Summer", 8: "Summer",
              9: "Fall",   10: "Fall",  11: "Fall"}


def load_and_join():
    print("Loading Cast...")
    cast = pd.read_csv(
        CAST_FILE,
        usecols=["Cst_Cnt", "Sta_ID", "Year", "Month", "Lat_Dec", "Lon_Dec"],
        low_memory=False,
    )

    print("Loading Bottle (~175MB)...")
    bottle = pd.read_csv(
        BOTTLE_FILE,
        usecols=["Cst_Cnt", "Depthm", "T_degC", "O2ml_L", "ChlorA", "T_qual", "O_qual"],
        low_memory=False,
        encoding="latin-1",
    )

    print("Joining on Cst_Cnt...")
    df = bottle.merge(cast, on="Cst_Cnt", how="inner")
    df["Season"] = df["Month"].map(SEASON_MAP)
    print(f"  Merged: {len(df):,} rows")
    return df


def apply_quality_filter(df):
    for var, qcol in QUAL_MAP.items():
        bad = df[qcol].isin([8.0, 9.0])
        df.loc[bad, var] = np.nan
    return df


def filter_depth(df):
    return df[df["Depthm"] <= DEPTH_MAX].copy()


def get_eligible_stations(df):
    baseline = df[df["Year"] <= BASELINE_END]
    years_per_station = baseline.groupby("Sta_ID")["Year"].nunique()
    return set(years_per_station[years_per_station >= MIN_BASELINE_YEARS].index)


def get_station_coords(df, eligible):
    return (df[df["Sta_ID"].isin(eligible)]
            .groupby("Sta_ID")[["Lat_Dec", "Lon_Dec"]]
            .median()
            .reset_index())


def add_log_chlora(df):
    df = df.copy()
    df["log_ChlorA"] = np.log(df["ChlorA"].clip(lower=1e-4))
    return df


# --- Annual pipeline ---

def aggregate_annual(df, eligible, coords):
    annual = (df[df["Sta_ID"].isin(eligible)]
              .groupby(["Sta_ID", "Year"])[VARS]
              .mean()
              .reset_index()
              .merge(coords, on="Sta_ID"))
    return add_log_chlora(annual)


def compute_baseline_stats(annual):
    baseline = annual[annual["Year"] <= BASELINE_END]
    stats = (baseline.groupby("Sta_ID")[["T_degC", "O2ml_L", "log_ChlorA"]]
             .agg(["mean", "std"])
             .reset_index())
    stats.columns = ["Sta_ID"] + [
        f"{v}_{s}" for v in ["T_degC", "O2ml_L", "log_ChlorA"] for s in ["mean", "std"]
    ]
    return stats


def compute_scores(annual, baseline_stats):
    scoring = annual[annual["Year"] >= SCORING_START].merge(baseline_stats, on="Sta_ID")
    scoring["z_temp"]   = (scoring["T_degC"]    - scoring["T_degC_mean"])     / scoring["T_degC_std"]
    scoring["z_oxygen"] = (scoring["O2ml_L"]    - scoring["O2ml_L_mean"])     / scoring["O2ml_L_std"]
    scoring["z_chlora"] = (scoring["log_ChlorA"] - scoring["log_ChlorA_mean"]) / scoring["log_ChlorA_std"]
    for col in ["z_temp", "z_oxygen", "z_chlora"]:
        scoring[col] = scoring[col].fillna(0)
    raw = 10 * (scoring["z_temp"] - scoring["z_oxygen"] + scoring["z_chlora"])
    scoring["health_score"] = (100 - np.clip(raw, 0, 100)).round(1)
    return scoring


# --- Seasonal pipeline ---

def aggregate_seasonal(df, eligible, coords):
    seasonal = (df[df["Sta_ID"].isin(eligible)]
                .groupby(["Sta_ID", "Year", "Season"])[VARS]
                .mean()
                .reset_index()
                .merge(coords, on="Sta_ID"))
    return add_log_chlora(seasonal)


def compute_seasonal_baseline_stats(seasonal):
    baseline = seasonal[seasonal["Year"] <= BASELINE_END]
    stats = (baseline.groupby(["Sta_ID", "Season"])[["T_degC", "O2ml_L", "log_ChlorA"]]
             .agg(["mean", "std"])
             .reset_index())
    stats.columns = ["Sta_ID", "Season"] + [
        f"{v}_{s}" for v in ["T_degC", "O2ml_L", "log_ChlorA"] for s in ["mean", "std"]
    ]
    return stats


def compute_seasonal_scores(seasonal, seasonal_baseline_stats):
    scoring = (seasonal[seasonal["Year"] >= SCORING_START]
               .merge(seasonal_baseline_stats, on=["Sta_ID", "Season"]))
    scoring["z_temp"]   = (scoring["T_degC"]     - scoring["T_degC_mean"])     / scoring["T_degC_std"]
    scoring["z_oxygen"] = (scoring["O2ml_L"]     - scoring["O2ml_L_mean"])     / scoring["O2ml_L_std"]
    scoring["z_chlora"] = (scoring["log_ChlorA"] - scoring["log_ChlorA_mean"]) / scoring["log_ChlorA_std"]
    for col in ["z_temp", "z_oxygen", "z_chlora"]:
        scoring[col] = scoring[col].fillna(0)
    raw = 10 * (scoring["z_temp"] - scoring["z_oxygen"] + scoring["z_chlora"])
    scoring["health_score"] = (100 - np.clip(raw, 0, 100)).round(1)
    return scoring


# --- Save ---

def save_outputs(scores, annual, baseline_stats, seasonal_scores):
    os.makedirs(OUT_DIR, exist_ok=True)

    score_cols = ["Sta_ID", "Year", "Lat_Dec", "Lon_Dec", "T_degC", "O2ml_L", "ChlorA",
                  "z_temp", "z_oxygen", "z_chlora", "health_score"]
    scores[score_cols].to_parquet(os.path.join(OUT_DIR, "scores.parquet"), index=False)
    print(f"  scores.parquet: {len(scores):,} rows")

    annual.to_parquet(os.path.join(OUT_DIR, "annual_means.parquet"), index=False)
    print(f"  annual_means.parquet: {len(annual):,} rows")

    baseline_stats.to_parquet(os.path.join(OUT_DIR, "baseline_stats.parquet"), index=False)
    print(f"  baseline_stats.parquet: {len(baseline_stats):,} rows")

    seasonal_cols = ["Sta_ID", "Year", "Season", "Lat_Dec", "Lon_Dec",
                     "T_degC", "O2ml_L", "ChlorA", "z_temp", "z_oxygen", "z_chlora", "health_score"]
    seasonal_scores[seasonal_cols].to_parquet(
        os.path.join(OUT_DIR, "seasonal_scores.parquet"), index=False)
    print(f"  seasonal_scores.parquet: {len(seasonal_scores):,} rows")


if __name__ == "__main__":
    df = load_and_join()

    print("Applying quality filters...")
    df = apply_quality_filter(df)

    print(f"Filtering to 0–{DEPTH_MAX}m depth...")
    df = filter_depth(df)

    print(f"Finding stations with {MIN_BASELINE_YEARS}+ baseline years...")
    eligible = get_eligible_stations(df)
    print(f"  Eligible stations: {len(eligible)}")

    coords = get_station_coords(df, eligible)

    print("Aggregating to annual means...")
    annual = aggregate_annual(df, eligible, coords)

    print("Computing annual baseline stats (1949–1990)...")
    baseline_stats = compute_baseline_stats(annual)

    print(f"Scoring annual (1991–present)...")
    scores = compute_scores(annual, baseline_stats)
    print(f"  Scored pairs: {len(scores):,}  |  Stations: {scores['Sta_ID'].nunique()}")

    print("Aggregating to seasonal means...")
    seasonal = aggregate_seasonal(df, eligible, coords)

    print("Computing seasonal baseline stats (1949–1990)...")
    seasonal_baseline = compute_seasonal_baseline_stats(seasonal)

    print("Scoring seasonal (1991–present)...")
    seasonal_scores = compute_seasonal_scores(seasonal, seasonal_baseline)
    print(f"  Seasonal scored pairs: {len(seasonal_scores):,}")

    print("Saving parquets...")
    save_outputs(scores, annual, baseline_stats, seasonal_scores)

    print("\nDone. Run pipeline/upload.py to push to S3.")
