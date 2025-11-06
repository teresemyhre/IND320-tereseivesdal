import streamlit as st
import pandas as pd
from helpers.sidebar import global_sidebar
from helpers.functions import (
    download_era5_data,
    temperature_spc_from_satv,
    precipitation_lof_plot,
    cities_df
)

# configure Streamlit layout and page title
st.set_page_config(page_title="Weather Outlier and Anomaly Analysis", page_icon="🌦️", layout="wide")

# synchronize URL query parameters with session state for consistency across pages
qp = st.query_params
if "area" in qp:
    st.session_state["price_area"] = qp["area"]
if "groups" in qp:
    st.session_state["production_group"] = qp["groups"].split(",")

# initialize sidebar controls for price area and production group
with st.sidebar:
    global_sidebar()

# retrieve current selections from session state
area = st.session_state["price_area"]
groups = st.session_state["production_group"]

# title for the page
st.title("Weather Outlier and Anomaly Detection")

# identify the latitude and longitude for the selected price area
row = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = row["latitude"], row["longitude"]

# cache ERA5 data to avoid repeated API calls when switching between pages or reloading
@st.cache_data(show_spinner="Fetching ERA5 weather data…")
def load_weather(lat, lon, year=2021):
    return download_era5_data(lat, lon, year)

df = load_weather(lat, lon)

# cache the SPC and LOF analyses since they can be computationally expensive
@st.cache_data(show_spinner="Computing SPC analysis…")
def cached_spc(df, keep_low_fraction, k, robust, scale_mad):
    """Run and return SPC analysis results for temperature."""
    return temperature_spc_from_satv(
        time=df["time"],
        temperature=df["temperature_2m"],
        keep_low_fraction=keep_low_fraction,
        k=k,
        robust=robust,
        scale_mad=scale_mad
    )

@st.cache_data(show_spinner="Computing LOF analysis…")
def cached_lof(df, contamination, n_neighbors):
    """Run and return LOF anomaly detection results for precipitation."""
    return precipitation_lof_plot(
        time=df["time"],
        precipitation=df["precipitation"],
        contamination=contamination,
        n_neighbors=n_neighbors
    )

# helper function to control when analyses should be recomputed
def run_analysis_if_changed(key, current_params, analysis_func):
    last_params = st.session_state.get(f"last_params_{key}")

    # automatically run analysis on first load
    if last_params is None:
        st.session_state[f"last_params_{key}"] = current_params
        analysis_func()
        return

    # detect parameter changes
    params_changed = current_params != last_params

    # prompt user to rerun only when parameters are modified
    if params_changed:
        st.info("Parameters changed. Click below to rerun the analysis.")
        if st.button(f"Run {key} analysis", key=f"run_{key}"):
            st.session_state[f"last_params_{key}"] = current_params
            analysis_func()
    else:
        analysis_func()

# define two tabs for the two main types of analysis
tab_spc, tab_lof = st.tabs(["SPC / Outlier Analysis", "LOF / Anomaly Detection"])

# SPC analysis tab
with tab_spc:
    st.subheader(f"SPC-based Outlier Detection — {area}")

    # user-adjustable parameters with explanations
    keep_low_fraction = st.slider(
        "Low-frequency fraction",
        0.001, 0.05, 0.01, step=0.001,
        help=(
            "Controls how smooth the DCT-based trend is. "
            "Smaller values give smoother trends, larger values retain faster variations. "
            "Default = 0.01."
        )
    )

    k = st.slider(
        "SPC width (±k)",
        1.0, 5.0, 3.0, step=0.1,
        help=(
            "Specifies the control limit width in standard deviation units. "
            "Wider limits detect fewer outliers. Default = 3.0."
        )
    )

    robust = st.checkbox(
        "Use robust statistics",
        value=True,
        help=(
            "When enabled, uses the median and MAD instead of mean and standard deviation. "
            "This makes the analysis less sensitive to extreme values. Default = True."
        )
    )

    scale_mad = st.checkbox(
        "Scale MAD (SD-equivalent)",
        value=True,
        help=(
            "When enabled, multiplies MAD by 1.4826 so it corresponds to the standard deviation scale. "
            "Default = True."
        )
    )

    if not robust and scale_mad:
        st.info("‘Scale MAD’ has no effect unless robust fitting is enabled.")

    # store SPC parameters to detect changes
    params_spc = dict(
        keep_low_fraction=keep_low_fraction,
        k=k,
        robust=robust,
        scale_mad=scale_mad
    )

    # define what happens when SPC analysis is run
    def do_spc():
        st.markdown("#### Temperature (°C)")
        fig, summary = cached_spc(df, keep_low_fraction, k, robust, scale_mad)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Summary of results:**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total points analyzed", f"{summary['n_total']:,}")
        col2.metric("Outliers detected", f"{summary['n_outliers']:,}")
        col3.metric("Percent outside limits", f"{summary['percent_outliers']} %")

        # Contextual explanation
        st.caption(
            f"{summary['percent_outliers']}% of temperature readings fell outside "
            f"the ±{summary['k']}-sigma control limits.\n\n"
            f"Trend smoothing kept {summary['keep_low_fraction']*100:.1f}% of low-frequency components. "
            f"Robust fitting = {summary['robust']}, Scaled MAD = {summary['scale_mad']}."
        )

    run_analysis_if_changed("SPC", params_spc, do_spc)

# LOF analysis tab
with tab_lof:
    st.subheader(f"LOF-based Anomaly Detection — {area}")

    # user-adjustable parameters with help text
    contamination = st.slider(
        "Expected proportion of anomalies",
        0.001, 0.05, 0.01, step=0.001,
        help=(
            "Fraction of observations expected to be anomalous. "
            "Larger values increase sensitivity but can overflag normal points. "
            "Default = 0.01 (1%)."
        )
    )

    n_neighbors = st.slider(
        "Number of neighbors",
        5, 100, 30, step=1,
        help=(
            "Defines the number of neighbors used to compute local density. "
            "Smaller values detect smaller local structures, larger values yield smoother results. "
            "Default = 30."
        )
    )

    # store LOF parameters for comparison
    params_lof = dict(contamination=contamination, n_neighbors=n_neighbors)

    # define LOF analysis procedure
    def do_lof():
        st.markdown("#### Precipitation (mm)")
        fig, summary = cached_lof(df, contamination, n_neighbors)
        st.plotly_chart(fig, use_container_width=True)
        # Instead of st.json(summary), use this:
        st.markdown("**Summary of results:**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total points analyzed", f"{summary['n_total']:,}")
        col2.metric("Outliers detected", f"{summary['n_outliers']:,}")
        col3.metric("Percent outliers", f"{summary['percent_outliers']} %")

        # Add contextual explanation below
        st.caption(
            f"Detected {summary['n_outliers']} unusual observations "
            f"out of {summary['n_total']} total values "
            f"({summary['percent_outliers']}%). "
            f"Detection sensitivity was set to contamination={summary.get('contamination', 'N/A')} "
            f"and n_neighbors={summary.get('n_neighbors', 'N/A')}."
        )

    run_analysis_if_changed("LOF", params_lof, do_lof)
