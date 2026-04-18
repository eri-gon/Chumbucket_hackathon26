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

DATA_PATH = "data/processed/"

@st.cache_data
def load_data():
    scores = pd.read_parquet(DATA_PATH + "scores.parquet")
    annual = pd.read_parquet(DATA_PATH + "annual_means.parquet")
    return scores, annual

scores_df, annual_df = load_data()

# --- Sidebar ---
st.sidebar.title("🌊 Ocean Health Dashboard")
st.sidebar.markdown("CalCOFI data · California Coast · 1991–2021")

year = st.sidebar.slider(
    "Year",
    int(scores_df["Year"].min()),
    int(scores_df["Year"].max()),
    2010,
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Health Score** compares each station's temperature, dissolved oxygen, "
    "and chlorophyll-a against its own 1949–1990 baseline using z-scores. "
    "100 = pristine baseline conditions."
)

# --- Filter to selected year ---
year_df = scores_df[scores_df["Year"] == year].copy()

# --- Header ---
st.title("Ocean Health Score Dashboard")
st.markdown(f"Showing **{len(year_df)}** CalCOFI stations · Year **{year}**")

# --- Top metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Stations", len(year_df))
m2.metric("Avg Health Score", f"{year_df['health_score'].mean():.1f}")
m3.metric("Worst Station", f"{year_df['health_score'].min():.1f}")
m4.metric("Best Station", f"{year_df['health_score'].max():.1f}")

st.markdown("---")

# --- Map + time series layout ---
col_map, col_ts = st.columns([6, 4])

with col_map:
    st.subheader(f"Station Health Scores — {year}")

    fig_map = px.scatter_mapbox(
        year_df,
        lat="Lat_Dec",
        lon="Lon_Dec",
        color="health_score",
        hover_name="Sta_ID",
        hover_data={
            "health_score": ":.1f",
            "T_degC": ":.2f",
            "O2ml_L": ":.2f",
            "ChlorA": ":.3f",
            "Lat_Dec": False,
            "Lon_Dec": False,
        },
        color_continuous_scale=[
            [0.0, "#d73027"],
            [0.4, "#fc8d59"],
            [0.6, "#fee08b"],
            [0.8, "#91cf60"],
            [1.0, "#1a9850"],
        ],
        range_color=[0, 100],
        zoom=5,
        center={"lat": 33.5, "lon": -120.5},
        height=550,
        mapbox_style="carto-darkmatter",
        size_max=14,
    )
    fig_map.update_traces(marker=dict(size=12, opacity=0.85))
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        coloraxis_colorbar=dict(title="Health Score"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col_ts:
    st.subheader("Mean Health Score Over Time")

    yearly_mean = (
        scores_df.groupby("Year")["health_score"]
        .mean()
        .reset_index()
        .rename(columns={"health_score": "Mean Health Score"})
    )

    fig_ts = go.Figure()
    fig_ts.add_trace(go.Scatter(
        x=yearly_mean["Year"],
        y=yearly_mean["Mean Health Score"],
        mode="lines+markers",
        line=dict(color="#58a6ff", width=2),
        marker=dict(size=5),
        name="Mean Score",
    ))
    fig_ts.add_vline(x=year, line_dash="dash", line_color="#ff6b6b", line_width=1.5)

    # Annotate known events
    events = {1998: "El Niño", 2005: "Warm Anomaly", 2015: "The Blob"}
    for yr, label in events.items():
        if yr in yearly_mean["Year"].values:
            fig_ts.add_annotation(
                x=yr,
                y=yearly_mean.loc[yearly_mean["Year"] == yr, "Mean Health Score"].values[0],
                text=label, showarrow=True, arrowhead=2,
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

    # --- Station drill-down ---
    st.subheader("Station Time Series")
    station_ids = sorted(scores_df["Sta_ID"].unique())
    selected_station = st.selectbox("Select a station", station_ids)

    sta_data = annual_df[annual_df["Sta_ID"] == selected_station].sort_values("Year")

    for var, label, color in [
        ("T_degC",  "Temperature (°C)",       "#ff6b6b"),
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
            title=dict(text=label, font=dict(size=12)),
            xaxis_title=None, yaxis_title=None,
            margin=dict(l=10, r=10, t=30, b=10),
            height=160,
        )
        st.plotly_chart(fig_v, use_container_width=True)

# --- Bottom table ---
with st.expander("View station data for selected year"):
    st.dataframe(
        year_df[["Sta_ID", "Lat_Dec", "Lon_Dec", "T_degC", "O2ml_L", "ChlorA", "health_score"]]
        .sort_values("health_score")
        .reset_index(drop=True),
        use_container_width=True,
    )
