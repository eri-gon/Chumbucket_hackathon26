import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pyathena import connect
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Ocean Health Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS for Premium Look ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background: linear-gradient(180deg, #0e1117 0%, #161b22 100%);
    }
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Data Loading Logic ---
@st.cache_data
def load_data(source="local"):
    if source == "local":
        if os.path.exists('processed_ocean_data.csv'):
            return pd.read_csv('processed_ocean_data.csv')
        else:
            st.error("Processed data not found. Please run process_data.py first.")
            return pd.DataFrame()
    else:
        # Placeholder for Athena connection
        # conn = connect(s3_staging_dir='s3://your-athena-results-bucket/',
        #               region_name='us-west-2')
        # return pd.read_sql("SELECT * FROM ocean_health_observations", conn)
        return pd.read_csv('processed_ocean_data.csv') # Fallback

# --- Sidebar Controls ---
st.sidebar.title("🌊 Query Controls")
st.sidebar.markdown("Filter oceanographic observations by time and region.")

data_source = st.sidebar.selectbox("Data Source", ["Local CSV (Mock)", "AWS Athena"])
df = load_data(source="local" if data_source == "Local CSV (Mock)" else "athena")

if not df.empty:
    year_range = st.sidebar.slider(
        "Year Range",
        int(df['year'].min()),
        int(df['year'].max()),
        (1990, 2021)
    )

    variable = st.sidebar.selectbox(
        "Primary Variable",
        ["temperature", "oxygen", "ph", "salinity", "health_score"]
    )

    # --- Header ---
    st.title("Ocean Health Query & Visualization")
    st.markdown("Exploring CalCOFI environmental trends for sustainable oceans.")

    # --- Filtering ---
    filtered_df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]

    # --- Top Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Observations", len(filtered_df))
    with m2:
        st.metric(f"Avg {variable.capitalize()}", round(filtered_df[variable].mean(), 2))
    with m3:
        st.metric("Avg Health Score", f"{round(filtered_df['health_score'].mean(), 1)}%")
    with m4:
        st.metric("Year Range", f"{year_range[0]} - {year_range[1]}")

    st.markdown("---")

    # --- Main Visualization Layout ---
    c1, c2 = st.columns([6, 4])

    with c1:
        st.subheader("Geospatial Distribution")
        # Use Plotly for a better map
        fig_map = px.scatter_mapbox(
            filtered_df,
            lat="lat",
            lon="lon",
            color=variable,
            size=variable if variable != "ph" else None,
            color_continuous_scale=px.colors.sequential.Plasma,
            zoom=4,
            height=600,
            mapbox_style="carto-darkmatter"
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

    with c2:
        st.subheader("Temporal Trends")
        # Aggregate by year for the chart
        yearly_trends = filtered_df.groupby('year')[variable].mean().reset_index()
        fig_chart = px.line(
            yearly_trends,
            x='year',
            y=variable,
            template="plotly_dark",
            color_discrete_sequence=['#58a6ff']
        )
        fig_chart.update_traces(line_width=3, mode='lines+markers')
        st.plotly_chart(fig_chart, use_container_width=True)

    # --- Bottom Data Table ---
    with st.expander("🔍 View Raw Observations"):
        st.dataframe(filtered_df.sort_values('year', ascending=False), use_container_width=True)

else:
    st.info("No data loaded. Check your configuration.")
