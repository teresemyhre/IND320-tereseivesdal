import streamlit as st
from helpers.sidebar import global_sidebar
from helpers.functions import stl_decomposition_elhub, plot_spectrogram_elhub

# Cache functions for heavy computations
@st.cache_data(show_spinner="Computing STL decomposition…")
def cached_stl(df, price_area, production_group, period, seasonal, trend, robust):
    return stl_decomposition_elhub(df, price_area, production_group, period, seasonal, trend, robust)

@st.cache_data(show_spinner="Computing Spectrogram…")
def cached_spec(df, price_area, production_group, window_length, overlap):
    return plot_spectrogram_elhub(df, price_area, production_group, window_length, overlap)


# Page setup
st.set_page_config(page_title="Signal Analysis", page_icon="📊", layout="wide")

with st.sidebar:
    global_sidebar()

area = st.session_state["price_area"]
groups = st.session_state["production_group"]

st.title("Production Signal Analysis")

# Check for dataset
if "elhub_data" not in st.session_state:
    st.error("No data available yet. Please load it first on the 'Production Explorer' page.")
    if st.button("➡️ Go to Production Explorer to load data"):
        st.switch_page("pages/02_Database_Insights.py")
    st.stop()

df = st.session_state["elhub_data"]


# --- Helper function to control when analysis runs ---
def run_analysis_if_changed(key, current_params, analysis_func, args):
    last_params = st.session_state.get(f"last_params_{key}")

    # If this is the first run, initialize with current defaults and show results immediately
    if last_params is None:
        st.session_state[f"last_params_{key}"] = current_params
        for group in groups:
            try:
                fig = analysis_func(*args, group)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")
        return

    # If parameters changed after initial run, show rerun prompt
    params_changed = current_params != last_params
    if params_changed:
        st.info("Parameters changed. Click below to rerun the analysis.")
        if st.button(f"Run {key} analysis", key=f"run_{key}"):
            st.session_state[f"last_params_{key}"] = current_params
            for group in groups:
                try:
                    fig = analysis_func(*args, group)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"No data found for {group} in {area}. ({e})")
    else:
        # Parameters unchanged → reuse last cached results
        for group in groups:
            try:
                fig = analysis_func(*args, group)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No data found for {group} in {area}. ({e})")


# --- Tabs ---
tab_stl, tab_spec = st.tabs(["STL decomposition", "Spectrogram"])

# STL decomposition tab
with tab_stl:
    seasonal = st.slider(
        "Seasonal smoothness", 5, 41, 9, step=2,
        help=(
            "Controls how smooth the seasonal component is. "
            "Lower values make the seasonal pattern smoother; higher values capture more detail. "
            "Default = 9."
        )
    )

    trend = st.slider(
        "Trend smoothness", 101, 501, 241, step=10,
        help=(
            "Determines how much the long-term trend is smoothed. "
            "Larger values produce slower, smoother trends. "
            "Default = 241."
        )
    )

    robust = st.checkbox(
        "Use robust fitting", value=False,
        help=(
            "If enabled, reduces the influence of outliers on the fit. "
            "Use for noisy data. Default = False."
        )
    )

    params_stl = {"seasonal": seasonal, "trend": trend, "robust": robust}

    def stl_func(df, area, group):
        return cached_stl(df, area, group, 168, seasonal, trend, robust)

    run_analysis_if_changed("STL", params_stl, stl_func, (df, area))


# Spectrogram tab
with tab_spec:
    window_length = st.slider(
        "Window length (hours)", 24, 24 * 14, 24 * 7, step=24,
        help=(
            "Defines the duration of each analysis window in the STFT. "
            "Shorter windows capture faster changes; longer ones show smoother frequency patterns. "
            "Default = 168 hours (1 week)."
        )
    )

    overlap = st.slider(
        "Window overlap (hours)", 0, window_length - 1, 24 * 4, step=12,
        help=(
            "Determines how much consecutive windows overlap. "
            "Higher overlap gives smoother transitions but increases runtime. "
            "Default = 96 hours (4 days)."
        )
    )

    params_spec = {"window_length": window_length, "overlap": overlap}

    def spec_func(df, area, group):
        return cached_spec(df, area, group, window_length, overlap)

    run_analysis_if_changed("Spectrogram", params_spec, spec_func, (df, area))

