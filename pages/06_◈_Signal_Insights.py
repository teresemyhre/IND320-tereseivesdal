import streamlit as st
import pandas as pd
from helpers.sidebar import global_sidebar
from helpers.functions import stl_decomposition_elhub, plot_spectrogram_elhub
from helpers.data_loader import load_elhub_data

# -----------------------------------------------------------
# Cached STL + Spectrogram (no df passed)
# -----------------------------------------------------------
@st.cache_data(show_spinner="Computing STL decomposition…")
def cached_stl(price_area, group, period, seasonal, trend, robust, group_col):
    df = load_elhub_data()   # cached inside
    df2 = df.rename(columns={group_col: "group"})
    df2["pricearea"] = df2["pricearea"].astype(str)
    df2["group"] = df2["group"].astype(str)

    return stl_decomposition_elhub(
        df2, price_area, group, period, seasonal, trend, robust
    )


@st.cache_data(show_spinner="Computing Spectrogram…")
def cached_spec(price_area, group, window_length, overlap, group_col):
    df = load_elhub_data()   # cached inside
    df2 = df.rename(columns={group_col: "group"})
    df2["pricearea"] = df2["pricearea"].astype(str)
    df2["group"] = df2["group"].astype(str)

    return plot_spectrogram_elhub(
        df2, price_area, group, window_length, overlap
    )


# -----------------------------------------------------------
# Page setup
# -----------------------------------------------------------
st.set_page_config(page_title="Signal Analysis", page_icon="📊", layout="wide")

with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one group before continuing.")
    st.stop()

area = st.session_state["price_area"]
energy_type = st.session_state["energy_type"]
groups = st.session_state["selected_groups"]

# Determine group column
group_col = "productiongroup" if energy_type == "production" else "consumptiongroup"
title_type = "Production" if energy_type == "production" else "Consumption"

df = load_elhub_data()

if group_col not in df.columns:
    st.error(
        f"⚠️ {title_type} data is not present in MongoDB.\n"
        f"Load consumption data into MongoDB or switch back to Production."
    )
    st.stop()

st.title(f"{title_type} Signal Analysis")


# -----------------------------------------------------------
# Helper: run only when sliders change
# -----------------------------------------------------------
def run_analysis_if_changed(key, current_params, analysis_func):
    last_params = st.session_state.get(f"last_params_{key}")

    if last_params is None:
        st.session_state[f"last_params_{key}"] = current_params
        analysis_func()
        return

    if current_params != last_params:
        st.info("Parameters changed. Click below to rerun the analysis.")
        if st.button(f"Run {key} analysis"):
            st.session_state[f"last_params_{key}"] = current_params
            analysis_func()
    else:
        analysis_func()


# -----------------------------------------------------------
# Tabs
# -----------------------------------------------------------
tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])


# -----------------------------------------------------------
# STL tab
# -----------------------------------------------------------
with tab_stl:
    seasonal = st.slider("Seasonal smoothness", 5, 41, 9, step=2)
    trend = st.slider("Trend smoothness", 101, 501, 241, step=10)
    robust = st.checkbox("Use robust fitting", value=False)

    params_stl = {"seasonal": seasonal, "trend": trend, "robust": robust}

    def run_stl():
        for group in groups:
            try:
                fig = cached_stl(area, group, 168, seasonal, trend, robust, group_col)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")

    run_analysis_if_changed("STL", params_stl, run_stl)


# -----------------------------------------------------------
# Spectrogram tab
# -----------------------------------------------------------
with tab_spec:
    window_length = st.slider("Window length (hours)", 24, 24*14, 24*7, step=24)
    overlap = st.slider("Window overlap (hours)", 0, window_length - 1, 24*4, step=12)

    params_spec = {"window_length": window_length, "overlap": overlap}

    def run_spec():
        for group in groups:
            try:
                fig = cached_spec(area, group, window_length, overlap, group_col)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")

    run_analysis_if_changed("Spectrogram", params_spec, run_spec)