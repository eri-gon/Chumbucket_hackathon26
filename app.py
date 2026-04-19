import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Ocean Health Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #0e1117 0%, #161b22 100%); }
    h1, h2, h3 { color: #58a6ff !important; font-family: 'Inter', sans-serif; }
    </style>
""", unsafe_allow_html=True)

S3_BASE = "https://datahacks26-ocean-health.s3.us-west-2.amazonaws.com/processed"
LOCAL_BASE = "data/processed"
SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]
HEALTH_COLORSCALE = [
    [0.0, "#d73027"], [0.4, "#fc8d59"], [0.6, "#fee08b"],
    [0.8, "#91cf60"], [1.0, "#1a9850"],
]

@st.cache_data
def load_data():
    try:
        scores   = pd.read_parquet(f"{S3_BASE}/scores.parquet")
        annual   = pd.read_parquet(f"{S3_BASE}/annual_means.parquet")
        seasonal = pd.read_parquet(f"{S3_BASE}/seasonal_scores.parquet")
    except Exception:
        scores   = pd.read_parquet(f"{LOCAL_BASE}/scores.parquet")
        annual   = pd.read_parquet(f"{LOCAL_BASE}/annual_means.parquet")
        seasonal = pd.read_parquet(f"{LOCAL_BASE}/seasonal_scores.parquet")
    return scores, annual, seasonal

scores_df, annual_df, seasonal_df = load_data()
all_years = sorted(scores_df["Year"].unique().tolist())

# --- Sidebar ---
st.sidebar.title("🌊 Ocean Health Dashboard")
st.sidebar.markdown("CalCOFI data · California Coast · 1991–2021")

view_mode = st.sidebar.radio("View by", ["Annual", "Seasonal"])

start_year, end_year = st.sidebar.select_slider(
    "Year range",
    options=all_years,
    value=(all_years[0], all_years[-1]),
)

if view_mode == "Seasonal":
    season = st.sidebar.selectbox("Season", SEASON_ORDER)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Health Score** compares each station's temperature, dissolved oxygen, "
    "and chlorophyll-a against its own 1949–1990 baseline using z-scores. "
    "100 = pristine baseline conditions."
)

# --- Filter data to year range ---
if view_mode == "Annual":
    base_df = scores_df
    source_label = "Annual"
else:
    base_df = seasonal_df[seasonal_df["Season"] == season]
    source_label = season

range_df = base_df[
    (base_df["Year"] >= start_year) & (base_df["Year"] <= end_year)
].sort_values("Year")

yearly_mean = (
    range_df.groupby("Year")["health_score"]
    .mean()
    .reset_index()
    .rename(columns={"health_score": "Mean Health Score"})
)

# --- Header ---
st.title("Ocean Health Score Dashboard")
st.markdown("""
The California Cooperative Oceanic Fisheries Investigations (CalCOFI) dataset provides decades of oceanographic measurements from the California coast. This app lets you explore temperature, salinity, and spatial trends across time—revealing how marine environments change and evolve.
""")
label = f"{source_label} · {start_year}–{end_year}"
st.markdown(f"**{label}** · {range_df['Sta_ID'].nunique()} stations · {len(range_df):,} observations")

# --- Top metrics (across selected range) ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Stations", range_df["Sta_ID"].nunique())
m2.metric("Avg Health Score", f"{range_df['health_score'].mean():.1f}" if len(range_df) else "—")
m3.metric("Worst Score", f"{range_df['health_score'].min():.1f}" if len(range_df) else "—")
m4.metric("Best Score", f"{range_df['health_score'].max():.1f}" if len(range_df) else "—")

st.markdown("---")

col_map, col_ts = st.columns([6, 4])

# --- Animated map ---
with col_map:
    st.subheader(f"Station Health Scores — {source_label} (press ▶ to animate)")

    if len(range_df):
        fig_map = px.scatter_mapbox(
            range_df,
            lat="Lat_Dec",
            lon="Lon_Dec",
            color="health_score",
            animation_frame="Year",
            hover_name="Sta_ID",
            hover_data={
                "health_score": ":.1f",
                "T_degC": ":.2f",
                "O2ml_L": ":.2f",
                "ChlorA": ":.3f",
                "Lat_Dec": False,
                "Lon_Dec": False,
                "Year": False,
            },
            color_continuous_scale=HEALTH_COLORSCALE,
            range_color=[0, 100],
            zoom=5,
            center={"lat": 33.5, "lon": -120.5},
            height=560,
            mapbox_style="carto-darkmatter",
        )
        fig_map.update_traces(marker=dict(size=12, opacity=0.85))
        fig_map.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            coloraxis_colorbar=dict(title="Health Score"),
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("No data for this selection.")

# --- Animated time series + station drill-down ---
with col_ts:
    st.subheader("Mean Health Score Over Time")

    events = {1998: "El Niño", 2005: "Warm Anomaly", 2015: "The Blob"}

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=yearly_mean["Year"],
        y=yearly_mean["Mean Health Score"],
        mode="lines+markers",
        line=dict(color="#58a6ff", width=2),
        marker=dict(size=5),
    ))
    for yr, label_text in events.items():
        if yr in yearly_mean["Year"].values:
            fig_ts.add_annotation(
                x=yr,
                y=yearly_mean.loc[yearly_mean["Year"] == yr, "Mean Health Score"].values[0],
                text=label_text, showarrow=True, arrowhead=2,
                font=dict(size=9, color="#aaa"), arrowcolor="#aaa",
                ax=30, ay=-30,
            )
    fig_ts.update_layout(
        template="plotly_dark",
        xaxis_title="Year",
        yaxis_title="Mean Health Score",
        yaxis_range=[0, 105],
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
        showlegend=False,
    )
    st.plotly_chart(fig_ts, use_container_width=True)

    # --- Station drill-down (filtered to year range) ---
    st.subheader("Station Time Series")
    station_ids = sorted(scores_df["Sta_ID"].unique())
    selected_station = st.selectbox("Select a station", station_ids)

    sta_data = (annual_df[
        (annual_df["Sta_ID"] == selected_station) &
        (annual_df["Year"] >= start_year) &
        (annual_df["Year"] <= end_year)
    ].sort_values("Year"))

    for var, var_label, color in [
        ("T_degC",  "Temperature (°C)",        "#ff6b6b"),
        ("O2ml_L",  "Dissolved Oxygen (ml/L)", "#58a6ff"),
        ("ChlorA",  "Chlorophyll-a (µg/L)",    "#2ecc71"),
    ]:
        if sta_data[var].notna().sum() < 2:
            continue
        fig_v = go.Figure()
        fig_v.add_trace(go.Scatter(
            x=sta_data["Year"], y=sta_data[var],
            mode="lines+markers",
            line=dict(color=color, width=1.5),
            marker=dict(size=4),
        ))
        fig_v.add_vline(x=1990, line_dash="dot", line_color="#888", line_width=1)
        fig_v.update_layout(
            template="plotly_dark",
            title=dict(text=var_label, font=dict(size=12)),
            xaxis_title=None, yaxis_title=None,
            margin=dict(l=10, r=10, t=30, b=10),
            height=160,
        )
        st.plotly_chart(fig_v, use_container_width=True)

# --- Bottom table ---
with st.expander("View station data for selected year range"):
    st.markdown("""
| Column | Units | Description |
|---|---|---|
| Sta_ID | — | CalCOFI line and station ID |
| Lat_Dec | decimal degrees | Station latitude |
| Lon_Dec | decimal degrees | Station longitude |
| T_degC | °C | Mean sea surface temperature (0–50m) |
| O2ml_L | ml/L | Mean dissolved oxygen concentration (0–50m) |
| ChlorA | µg/L | Mean chlorophyll-a concentration (0–50m) |
| health_score | 0–100 | Ocean Health Score vs 1949–1990 baseline |
""")
    st.dataframe(
        range_df[["Sta_ID", "Year", "Lat_Dec", "Lon_Dec", "T_degC", "O2ml_L", "ChlorA", "health_score"]]
        .sort_values(["health_score", "Year"])
        .reset_index(drop=True),
        use_container_width=True,
    )
