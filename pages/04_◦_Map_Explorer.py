import streamlit as st
import pandas as pd
import json
import folium
from shapely.geometry import Point, shape
from streamlit_folium import st_folium
from branca.colormap import LinearColormap
import numpy as np
import matplotlib.pyplot as plt

from helpers.sidebar import global_sidebar
from helpers.data_loader import load_elhub_data
from helpers.functions import download_era5_data


# -----------------------------------------------------------
# Page setup
# -----------------------------------------------------------
st.set_page_config(page_title="Map Explorer", page_icon="🗺️", layout="wide")


# -----------------------------------------------------------
# Sidebar
# -----------------------------------------------------------
with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one group before continuing.")
    st.stop()

energy_type = st.session_state["energy_type"]
groups = st.session_state["selected_groups"]
chosen_area = st.session_state["price_area"]
df = load_elhub_data()

group_col = "productiongroup" if energy_type == "production" else "consumptiongroup"
title_type = "Production" if energy_type == "production" else "Consumption"


# -----------------------------------------------------------
# Load GeoJSON (cached)
# -----------------------------------------------------------
@st.cache_data
def load_geojson():
    with open("data/file.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

geojson = load_geojson()
FEATURE_KEY = "ElSpotOmr"     # GeoJSON property name containing "NO 1", "NO 2", ...


# -----------------------------------------------------------
# Normalize Elhub area → GeoJSON format ("NO1" → "NO 1")
# -----------------------------------------------------------
def normalize(area: str) -> str:
    return area.replace("NO", "NO ").strip()


# -----------------------------------------------------------
# CACHED: Filter data
# -----------------------------------------------------------
@st.cache_data
def filter_data(df, date_start, date_end, groups, group_col):
    df = load_elhub_data()
    mask = (
        (df["starttime"].dt.date >= date_start) &
        (df["starttime"].dt.date <= date_end) &
        (df[group_col].isin(groups))
    )
    return df[mask]


# -----------------------------------------------------------
# CACHED: Compute mean values per area
# -----------------------------------------------------------
@st.cache_data
def compute_means(df_filtered):
    df_mean = (
        df_filtered.groupby("pricearea", as_index=False)["quantitykwh"]
        .mean()
        .rename(columns={"quantitykwh": "mean_value"})
    )

    # Ensure NO1–NO5 appear
    for area in ["NO1", "NO2", "NO3", "NO4", "NO5"]:
        if area not in df_mean["pricearea"].values:
            df_mean.loc[len(df_mean)] = [area, 0]

    df_mean["geo_key"] = df_mean["pricearea"].apply(lambda x: x.replace("NO", "NO ").strip())
    return df_mean


# -----------------------------------------------------------
# CACHED: Create color scale
# -----------------------------------------------------------
@st.cache_data
def make_colormap(df_mean, title_type):
    custom_colors = [
        "#2A3F57", "#416287", "#5890b7",
        "#9ecaec", "#ffcea8", "#ffb984", "#fd9e53"
    ]

    vmin = float(df_mean["mean_value"].min())
    vmax = float(df_mean["mean_value"].max())

    if vmin == vmax:
        vmax = vmin + 1

    vmin_r = round(vmin, -3)
    vmax_r = round(vmax, -3)

    colormap = LinearColormap(
        colors=custom_colors,
        vmin=vmin_r,
        vmax=vmax_r,
        caption=f"Mean {title_type} (kWh)",
    )

    colormap.tick_labels = [
        vmin_r,
        vmin_r + (vmax_r - vmin_r) * 0.25,
        vmin_r + (vmax_r - vmin_r) * 0.50,
        vmin_r + (vmax_r - vmin_r) * 0.75,
        vmax_r,
    ]

    return colormap


# -----------------------------------------------------------
# CACHED: Value lookup dict
# -----------------------------------------------------------
@st.cache_data
def make_value_lookup(df_mean):
    return df_mean.set_index("geo_key")["mean_value"].to_dict()


# -----------------------------------------------------------
# Select dates
# -----------------------------------------------------------
min_date = df["starttime"].min().date()
max_date = df["starttime"].max().date()

c1, c2 = st.columns(2)
with c1:
    date_start = st.date_input("Start date", min_date)
with c2:
    date_end = st.date_input("End date", max_date)

if date_start > date_end:
    st.error("Start date must be before end date.")
    st.stop()


# -----------------------------------------------------------
# Cached computations
# -----------------------------------------------------------
df_filtered = filter_data(df, date_start, date_end, groups, group_col)
df_mean = compute_means(df_filtered)
colormap = make_colormap(df_mean, title_type)
value_lookup = make_value_lookup(df_mean)


# -----------------------------------------------------------
# Map title
# -----------------------------------------------------------
st.title(f"{title_type} Map Explorer")


# -----------------------------------------------------------
# CREATE FOLIUM MAP
# -----------------------------------------------------------
m = folium.Map(location=[65.0, 13.0], zoom_start=4, tiles="cartodbpositron")

def style_fn(feature):
    geo_key = feature["properties"][FEATURE_KEY]
    val = value_lookup.get(geo_key, 0)
    return {
        "fillColor": colormap(val),
        "color": "black",
        "weight": 0.5,
        "fillOpacity": 0.65,
    }

folium.GeoJson(
    geojson,
    name="choropleth",
    style_function=style_fn,
    highlight_function=lambda _: {"weight": 3, "color": "blue"},
    tooltip=folium.GeoJsonTooltip(
        fields=[FEATURE_KEY],
        aliases=["Price area:"],
    ),
).add_to(m)

colormap.add_to(m)


# -----------------------------------------------------------
# Highlight selected area
# -----------------------------------------------------------
selected_label = normalize(chosen_area)

for feature in geojson["features"]:
    if feature["properties"][FEATURE_KEY] == selected_label:
        folium.GeoJson(
            feature,
            style_function=lambda f: {"fillOpacity": 0, "color": "red", "weight": 4}
        ).add_to(m)


# -----------------------------------------------------------
# Persistent popup marker
# -----------------------------------------------------------
if "active_popup" in st.session_state and st.session_state["active_popup"] is not None:
    lat_p, lon_p = st.session_state["active_popup"]
    folium.Marker(
        [lat_p, lon_p],
        popup=folium.Popup(
            f"<b>Lat:</b> {lat_p:.5f}<br><b>Lon:</b> {lon_p:.5f}",
            max_width=200
        ),
        icon=folium.Icon(color="red")
    ).add_to(m)


# -----------------------------------------------------------
# Render map
# -----------------------------------------------------------
map_data = st_folium(m, height=600, width="100%", key="main_map")


# -----------------------------------------------------------
# Handle clicks (store snapshot values)
# -----------------------------------------------------------
clicked_area = None

if map_data and "last_clicked" in map_data and map_data["last_clicked"]:
    lat = map_data["last_clicked"]["lat"]
    lon = map_data["last_clicked"]["lng"]

    point = Point(lon, lat)
    for feature in geojson["features"]:
        poly = shape(feature["geometry"])
        if poly.contains(point):
            clicked_area = feature["properties"][FEATURE_KEY].replace("NO ", "NO")
            break

    st.session_state["active_popup"] = (lat, lon)

    if clicked_area and clicked_area in df_mean["pricearea"].values:
        mean_at_click = float(
            df_mean.loc[df_mean["pricearea"] == clicked_area, "mean_value"].values[0]
        )
    else:
        mean_at_click = None

    st.session_state.setdefault("click_log", [])
    st.session_state["click_log"].insert(0, {
        "Latitude": round(lat, 5),
        "Longitude": round(lon, 5),
        "Clicked Area": clicked_area or "Outside Norway",
        "Groups": ", ".join(groups),
        "Mean Value": mean_at_click,
        "Start": date_start,
        "End": date_end
    })
    st.session_state["click_log"] = st.session_state["click_log"][:20]

    if clicked_area:
        st.session_state["price_area"] = clicked_area

    st.rerun()


# -----------------------------------------------------------
# Show click log
# -----------------------------------------------------------
st.write("**Clicked Coordinates Log**")

if "click_log" in st.session_state and st.session_state["click_log"]:
    df_log = pd.DataFrame(st.session_state["click_log"])
    max_rows = 4
    row_height = 33

    if len(df_log) <= max_rows:
        st.dataframe(df_log, height=len(df_log) * row_height + 40)
    else:
        st.dataframe(df_log, height=max_rows * row_height + 40)
else:
    st.caption("Click anywhere on the map to record coordinates.")

# -----------------------------------------------------------
# Snow Drift Section
# -----------------------------------------------------------
from helpers.Snow_drift import compute_snow_drift_plotly
from helpers.Snow_drift import compute_monthly_and_yearly_Qt_plotly

st.subheader("Snow Drift Analysis (based on most recent clicked point)")

if "active_popup" in st.session_state and st.session_state["active_popup"] is not None:

    lat_snow, lon_snow = st.session_state["active_popup"]

    year_start, year_end = st.slider(
        "Select year range for snow drift calculation:",
        min_value=2010, max_value=2024, value=(2015, 2020)
    )

    # Download ERA5 data for all years needed to cover July–June seasons
    # For seasons [year_start ... year_end], we need up to June of (year_end + 1)
    MAX_YEAR = pd.Timestamp.today().year
    df_all = []
    for y in range(year_start, min(year_end + 1, MAX_YEAR) + 1):
        df_all.append(download_era5_data(lat_snow, lon_snow, y))

    df_era = pd.concat(df_all, ignore_index=True)

    df_era["time"] = df_era["time"].dt.tz_localize(None)

    fig_Qt, fig_rose, df_yearly = compute_snow_drift_plotly(
        df_era, year_start, year_end
    )

    left, right = st.columns([1.5, 1])
    with left:
        # st.plotly_chart(fig_Qt, use_container_width=True)
        fig_combined, df_yearly, df_monthly = compute_monthly_and_yearly_Qt_plotly(
        df_era, year_start, year_end
    )
        st.plotly_chart(fig_combined, use_container_width=True)
    with right:
        st.plotly_chart(fig_rose, use_container_width=True)

else:
    st.info("Click a location on the map to calculate snow drift.")