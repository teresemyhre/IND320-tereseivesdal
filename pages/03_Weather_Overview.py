import streamlit as st
import pandas as pd
import helpers.utils as utils  # activates the custom Altair theme (see utils.py)
from helpers.sidebar import global_sidebar
from helpers.functions import download_era5_data, cities_df

# Sync URL params
qp = st.query_params
if "area" in qp:
    st.session_state["price_area"] = qp["area"]
if "groups" in qp:
    st.session_state["production_group"] = qp["groups"].split(",")

# Sidebar with global controls
with st.sidebar:
    valid = global_sidebar()

if not valid:
    st.error("Please select at least one production group before continuing.")
    st.stop()

# read current session state
area = st.session_state["price_area"]
groups = st.session_state.get("selected_groups", [])
 
st.title("Data Table – First Month with Line Charts")

# Get coordinates for selected price area
row = cities_df[cities_df["price_area"] == area].iloc[0]
lat, lon = row["latitude"], row["longitude"]

# Download ERA5 data for the selected area (if not already cached)
@st.cache_data(show_spinner="Fetching ERA5 weather data…")
def load_weather(lat, lon, year=2021):
    return download_era5_data(lat, lon, year)

df = load_weather(lat, lon)

# Filter first month
first_month = df["time"].dt.month == df["time"].dt.month.min()
df_first_month = df[first_month]

# Prepare a table: one row per column to use LineChartColumn
table_data = []
for col in df_first_month.columns:
    if col == "time":
        continue  # skip time column because it doesn't make sense to plot it as a line chart
    row = {
        "Variable": col,
        "First Month": df_first_month[col].tolist()  # list of values for LineChartColumn
    }
    table_data.append(row)

# Create DataFrame of the table data
df_table = pd.DataFrame(table_data) 

# Configure the LineChartColumn
column_configs = {
    "First Month": st.column_config.LineChartColumn(
        label="First Month Values",
        width=400
    )
}

# Display the table
st.dataframe(df_table, column_config=column_configs)

