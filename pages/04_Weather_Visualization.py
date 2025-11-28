import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from helpers.utils import custom_colors

from helpers.functions import download_era5_data, cities_df

# Sidebar with global controls
from helpers.sidebar import global_sidebar

qp = st.query_params
if "area" in qp:
    st.session_state["price_area"] = qp["area"]
if "groups" in qp:
    st.session_state["production_group"] = qp["groups"].split(",")

with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one production group before continuing.")
    st.stop()

# read current state anywhere
area = st.session_state["price_area"]
groups = st.session_state.get("selected_groups", [])

st.title("Data Visualization")

# Get coordinates for selected price area
row = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = row["latitude"], row["longitude"]

# Download ERA5 data for the selected area (if not already cached)
@st.cache_data(show_spinner="Fetching ERA5 weather data…")
def load_weather(lat, lon, year=2021):
    return download_era5_data(lat, lon, year)

df = load_weather(lat, lon)

# Selectbox for choosing column to plot
columns = list(df.columns.drop("time"))
option = st.selectbox("Choose a column to plot", ["All"] + columns)

# Slider for selecting month range
months = sorted(df["time"].dt.month.unique())
month_range = st.select_slider(
    "Select months range",
    options=months, 
    value=(months[0], months[0]),  # default is first month
    format_func=lambda x: df[df["time"].dt.month == x]["time"].dt.strftime("%B").iloc[0] # get month name instead of number
)

# Filter data within selected month range 
subset = df[(df["time"].dt.month >= month_range[0]) & (df["time"].dt.month <= month_range[1])]

# Get first and last month names
first_month_name = subset["time"].dt.strftime("%B").iloc[0]
last_month_name = subset["time"].dt.strftime("%B").iloc[-1]

fig = go.Figure()

# Plot logic mirrors st.line_chart above
if option == "All":
    # Plot all relevant numeric columns except wind direction
    plot_cols = [c for c in subset.columns if c not in ["time", "wind_direction_10m"]]
    for i, col in enumerate(plot_cols):
        fig.add_trace(go.Scatter(
            x=subset["time"],
            y=subset[col],
            mode="lines",
            line=dict(color=custom_colors[i+1 % len(custom_colors)], width=2),
            name=col
        ))
else:
    # Plot only the selected variable
    fig.add_trace(go.Scatter(
        x=subset["time"],
        y=subset[option],
        mode="lines",
        line=dict(color=custom_colors[0], width=2),
        name=option
    ))


# Arrow parameters
arrow_every = max(1, len(subset) // 90)

# Determine data y-range dynamically for displayed data
if option == "All":
    # Use the full numeric data range (excluding wind direction)
    numeric_cols = subset.select_dtypes(include=[np.number]).columns.drop("wind_direction_10m", errors="ignore")
    y_min = subset[numeric_cols].min().min()
    y_max = subset[numeric_cols].max().max()
else:
    # Use the displayed column only
    y_min = subset[option].min()
    y_max = subset[option].max()

# Compute arrow baseline and size as if using the 'All' mode
# (global logic to make arrows visually consistent)
numeric_cols_global = subset.select_dtypes(include=[np.number]).columns.drop("wind_direction_10m", errors="ignore")
global_y_min = subset[numeric_cols_global].min().min()
global_y_max = subset[numeric_cols_global].max().max()

arrow_y = global_y_min - (global_y_max - global_y_min) * 0.1
arrow_len = (global_y_max - global_y_min) * 0.1
dx_time = pd.Timedelta(hours=1)

# Add arrows showing wind direction
if option == "All" or option == "wind_direction_10m":
    for i in range(0, len(subset), arrow_every):
        t = subset["time"].iloc[i]
        wind_dir = subset["wind_direction_10m"].iloc[i]

        # Convert from direction → to direction (wind blows toward)
        theta = np.deg2rad(wind_dir + 180)

        # Compute vector (wind blows toward this direction)
        dx = np.cos(theta) * arrow_len
        dy = np.sin(theta) * arrow_len

        # Convert horizontal offset from data to time delta
        arrow_dx = pd.Timedelta(hours=dy * 1)
        arrow_y2 = arrow_y + dx * 0.8

        fig.add_annotation(
            x=t, y=arrow_y,
            ax=t + arrow_dx, ay=arrow_y2,
            xref="x", yref="y", axref="x", ayref="y",
            text="",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.3,
            arrowwidth=1.4,
            arrowcolor=custom_colors[0],
        )

    # Legend entry for wind direction
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="lines+markers",
        line=dict(color=custom_colors[0], width=2),
        marker=dict(symbol="triangle-right", color=custom_colors[0], size=10),
        name="Wind Direction",
        showlegend=True
    ))

# change header name 
names = {
    "temperature_2m": "Temperature (°C)",
    "precipitation": "Precipitation (mm)",
    "wind_speed_10m": "Wind Speed (m/s)",
    "wind_direction_10m": "Wind Direction (°)",
    "wind_gusts_10m": "Wind Gusts (m/s)",
}

# Update legend names
for trace in fig.data:
    if trace.name in names:
        trace.name = names[trace.name]

# Create dynamic header text based on selection
if first_month_name == last_month_name:
    header_text = f"{names.get(option, option)} for {first_month_name}" if option != "All" else f"All columns for {first_month_name}"
else:
    header_text = f"{names.get(option, option)} for {first_month_name} – {last_month_name}" if option != "All" else f"All columns for {first_month_name} – {last_month_name}"


# Layout
fig.update_layout(
    title=dict(
        text=header_text,
        x=0.5,                 # center it
        xanchor="center",
        font=dict(size=30)     # increase title font size
    ),
    xaxis_title="Time",
    # yaxis_title=f"{option if option != 'All' else ""}",
    template="plotly_white",
    width=950,
    height=520,
    # margin=dict(t=60, b=90),
    legend=dict(orientation="h", y=-0.2),
)

# Determine data y-range dynamically for displayed data
if option == "All":
    # Use the full numeric data range (excluding wind direction)
    numeric_cols = subset.select_dtypes(include=[np.number]).columns.drop("wind_direction_10m", errors="ignore")
    y_min = subset[numeric_cols].min().min()
    y_max = subset[numeric_cols].max().max()
    # Extend y-axis to make space for arrows
    fig.update_yaxes(range=[arrow_y - (y_max - y_min) * 0.08, y_max], nticks=11)
elif option == "wind_direction_10m":
    # Use the displayed column only
    y_min = subset[option].min()
    y_max = subset[option].max()
    # Extend y-axis to make space for arrows
    fig.update_yaxes(range=[arrow_y - (y_max - y_min) * 0.08, y_max], nticks=11)
else:
    # Use the displayed column only
    y_min = subset[option].min()
    y_max = subset[option].max()
    fig.update_yaxes(range=[y_min, y_max], nticks=11)


st.plotly_chart(fig, use_container_width=True)
