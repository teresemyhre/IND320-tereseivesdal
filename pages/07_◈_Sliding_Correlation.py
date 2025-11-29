import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Your helpers
from helpers.sidebar import global_sidebar
from helpers.functions import download_era5_data, cities_df
from helpers.utils import custom_colors


# -----------------------------------------------------------
# Page config
# -----------------------------------------------------------
st.set_page_config(page_title="Sliding Window Correlation", page_icon="📈", layout="wide")

with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one group before continuing.")
    st.stop()

st.title("Sliding-Window Correlation: Meteorology ↔ Energy")


# -----------------------------------------------------------
# Read global state from sidebar
# -----------------------------------------------------------
area = st.session_state["price_area"]
groups_sidebar = st.session_state["selected_groups"]
year = st.session_state["year"]
energy_type = st.session_state["energy_type"]

group_col = "productiongroup" if energy_type == "production" else "consumptiongroup"


# -----------------------------------------------------------
# UI: Local SWC controls
# -----------------------------------------------------------
st.subheader("Sliding Window Settings")

# --- Row 1: Weather + Energy group (horizontal) ---
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    met_var = st.selectbox(
        "Meteorological variable",
        ["temperature_2m", "precipitation", "wind_speed_10m",
         "wind_gusts_10m", "wind_direction_10m"]
    )

with row1_col2:
    if len(groups_sidebar) == 0:
        st.error("No production/consumption groups selected in sidebar.")
        st.stop()

    selected_group = st.selectbox(
        "Energy group (from sidebar selection)",
        groups_sidebar
    )
    page_groups = [selected_group]

# --- Row 2: Month selection ---
month_names = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}
selected_month = st.selectbox(
    "Select month",
    list(month_names.keys()),
    format_func=lambda x: month_names[x]
)

# --- Row 3: Window + Lag sliders (horizontal) ---
row3_col1, row3_col2 = st.columns(2)

with row3_col1:
    window = st.slider("Window length (hours)", 24, 500, 168)

with row3_col2:
    lag = st.slider("Lag (hours)", -168, +168, 0)


# -----------------------------------------------------------
# Load ERA5 weather for area/year
# -----------------------------------------------------------
row = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = row["latitude"], row["longitude"]

@st.cache_data
def load_weather(lat, lon, year):
    return download_era5_data(lat, lon, year)

df_weather = load_weather(lat, lon, year)
df_weather["time"] = (
    pd.to_datetime(df_weather["time"], utc=True)
    .dt.tz_localize(None)
)
df_weather = df_weather.set_index("time")


# -----------------------------------------------------------
# Load Elhub energy data
# -----------------------------------------------------------
df_energy = st.session_state["elhub_data"]

df_energy = df_energy[
    (df_energy["pricearea"] == area) &
    (df_energy["starttime"].dt.year == year) &
    (df_energy[group_col].isin(page_groups))
]

df_energy = df_energy.groupby("starttime")["quantitykwh"].sum()
df_energy = df_energy.resample("1H").mean().interpolate()


# -----------------------------------------------------------
# Merge weather + energy
# -----------------------------------------------------------
df = pd.DataFrame({
    "meteo": df_weather[met_var],
    "energy": df_energy
}).dropna()

# Filter month
df = df[df.index.month == selected_month].sort_index()

if df.empty:
    st.warning("No data available for selected month / settings.")
    st.stop()

# Apply lag
df["meteo_lagged"] = df["meteo"].shift(lag)


# -----------------------------------------------------------
# Sliding-window correlation (centered)
# -----------------------------------------------------------
def sliding_corr_centered(series_x, series_y, W):
    half = W // 2
    out = []

    for i in range(len(series_x)):
        start = max(0, i - half)
        end = min(len(series_x), i + half)

        if end - start < 5:
            out.append(np.nan)
            continue

        r = np.corrcoef(series_x.iloc[start:end], series_y.iloc[start:end])[0, 1]
        out.append(r)

    return pd.Series(out, index=series_x.index)


corr = sliding_corr_centered(df["meteo_lagged"], df["energy"], window)


# -----------------------------------------------------------
# Window highlight selector
# -----------------------------------------------------------
max_idx = len(df) - 1
center = st.slider(
    "Highlight position in the selected month",
    0, max_idx, max_idx // 2
)

w_start = max(0, center - window // 2)
w_end = min(len(df), center + window // 2)


# -----------------------------------------------------------
# Build 3-panel plot
# -----------------------------------------------------------
fig = make_subplots(
    rows=3, cols=1,
    vertical_spacing=0.08,
    shared_xaxes=False,
    subplot_titles=(
        f"{met_var} (lagged {lag}h)",
        f"Energy (kWh) – {selected_group}",
        "Sliding-Window Correlation"
    )
)

# --- 1. Meteorology ---
fig.add_trace(
    go.Scatter(
        x=df.index, y=df["meteo_lagged"],
        line=dict(color=custom_colors[2], width=2)
    ),
    row=1, col=1
)

fig.add_trace(
    go.Scatter(
        x=df.index[w_start:w_end],
        y=df["meteo_lagged"].iloc[w_start:w_end],
        line=dict(color="red", width=3)
    ),
    row=1, col=1
)

# --- 2. Energy ---
fig.add_trace(
    go.Scatter(
        x=df.index, y=df["energy"],
        line=dict(color=custom_colors[3], width=2)
    ),
    row=2, col=1
)

fig.add_trace(
    go.Scatter(
        x=df.index[w_start:w_end],
        y=df["energy"].iloc[w_start:w_end],
        line=dict(color="red", width=3)
    ),
    row=2, col=1
)

# --- 3. SWC ---
fig.add_trace(
    go.Scatter(
        x=corr.index, y=corr,
        line=dict(color=custom_colors[1], width=2)
    ),
    row=3, col=1
)

# Marker at selected point
fig.add_trace(
    go.Scatter(
        x=[corr.index[center]],
        y=[corr.iloc[center]],
        mode="markers",
        marker=dict(color="red", size=12)
    ),
    row=3, col=1
)

# Zero line
fig.add_hline(y=0, line_dash="dot", line_color="gray", row=3, col=1)

fig.update_layout(
    height=1000,
    template="plotly_white",
    showlegend=False,
    margin=dict(l=40, r=30, t=60, b=40)
)

st.plotly_chart(fig, use_container_width=True)


# -----------------------------------------------------------
# Show correlation value
# -----------------------------------------------------------
corr_val = corr.iloc[center]
if pd.isna(corr_val):
    st.info("Correlation undefined for this window.")
else:
    st.success(
        f"**Sliding-window correlation for "
        f"{month_names[selected_month]} / {selected_group} "
        f"at selected position: {corr_val:.3f}**"
    )