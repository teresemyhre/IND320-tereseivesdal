import streamlit as st
from helpers.sidebar import global_sidebar
from helpers.functions import stl_decomposition_elhub, plot_spectrogram_elhub

# Cache functions for heavy computations
@st.cache_data(show_spinner="Computing STL decomposition…")
def cached_stl(df, price_area, group, period, seasonal, trend, robust, group_col):
    # Rename group column so STL function can always read "productiongroup"
    # unify naming for analysis
    df2 = df.rename(columns={
        group_col: "group",          # either productiongroup or consumptiongroup → group
        "pricearea": "pricearea"
    })

    df2["pricearea"] = df2["pricearea"].astype(str)
    df2["group"] = df2["group"].astype(str)

    return stl_decomposition_elhub(df2, price_area, group, period, seasonal, trend, robust)

@st.cache_data(show_spinner="Computing Spectrogram…")
def cached_spec(df, price_area, group, window_length, overlap, group_col):
    # unify naming for analysis
    df2 = df.rename(columns={
        group_col: "group",          # either productiongroup or consumptiongroup → group
        "pricearea": "pricearea"
    })

    df2["pricearea"] = df2["pricearea"].astype(str)
    df2["group"] = df2["group"].astype(str)

    return plot_spectrogram_elhub(df2, price_area, group, window_length, overlap)


# Page setup
st.set_page_config(page_title="Signal Analysis", page_icon="📊", layout="wide")

with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one group before continuing.")
    st.stop()

area = st.session_state["price_area"]

energy_type = st.session_state["energy_type"]
groups = st.session_state["selected_groups"]

# normalize for analysis function
if energy_type == "production":
    group_col = "productiongroup"
else:
    group_col = "consumptiongroup"


df = st.session_state["elhub_data"]

# Determine correct column based on energy type
if energy_type == "production":
    group_col = "productiongroup"
    title_type = "Production"
else:
    group_col = "consumptiongroup"
    title_type = "Consumption"

# Safety if consumption data not loaded
if group_col not in df.columns:
    st.error(
        f"⚠️ {title_type} data is not present in MongoDB.\n"
        f"Load consumption data into MongoDB or switch back to Production."
    )
    st.stop()

st.title(f"{title_type} Signal Analysis")


# --- Helper function to control when analysis runs ---
def run_analysis_if_changed(key, current_params, analysis_func, args):
    last_params = st.session_state.get(f"last_params_{key}")

    # First run
    if last_params is None:
        st.session_state[f"last_params_{key}"] = current_params
        for group in groups:
            try:
                fig = analysis_func(*args, group, group_col)   # ← UPDATED
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")
        return

    # Detect parameter change
    params_changed = current_params != last_params
    if params_changed:
        st.info("Parameters changed. Click below to rerun the analysis.")
        if st.button(f"Run {key} analysis", key=f"run_{key}"):
            st.session_state[f"last_params_{key}"] = current_params
            for group in groups:
                try:
                    fig = analysis_func(*args, group, group_col)   # ← UPDATED
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"No data found for {group} in {area}. ({e})")
    else:
        # Reuse cached results
        for group in groups:
            try:
                fig = analysis_func(*args, group, group_col)   # ← UPDATED
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")


# --- Tabs ---
tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

# STL decomposition tab
with tab_stl:
    seasonal = st.slider("Seasonal smoothness", 5, 41, 9, step=2)
    trend = st.slider("Trend smoothness", 101, 501, 241, step=10)
    robust = st.checkbox("Use robust fitting", value=False)

    params_stl = {"seasonal": seasonal, "trend": trend, "robust": robust}

    def stl_func(df, area, group, group_col):
        return cached_stl(df, area, group, 168, seasonal, trend, robust, group_col)

    run_analysis_if_changed("STL", params_stl, stl_func, (df, area))


# Spectrogram tab
with tab_spec:
    window_length = st.slider("Window length (hours)", 24, 24*14, 24*7, step=24)
    overlap = st.slider("Window overlap (hours)", 0, window_length - 1, 24*4, step=12)

    params_spec = {"window_length": window_length, "overlap": overlap}

    def spec_func(df, area, group, group_col):
        return cached_spec(df, area, group, window_length, overlap, group_col)

    run_analysis_if_changed("Spectrogram", params_spec, spec_func, (df, area))