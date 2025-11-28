import streamlit as st
import pandas as pd
import plotly.express as px
import calendar
import helpers.utils as utils
import numpy as np

from helpers.sidebar import (
    AREAS,
    PROD_GROUPS,
    CONS_GROUPS,
    _init_globals,
    _sync_all
)
from helpers.data_loader import load_elhub_data


# --------------------------------------------------------
# Page setup
# --------------------------------------------------------
st.set_page_config(page_title="Energy Explorer", page_icon="⚡", layout="wide")

# Sync URL params for area/type/groups
qp = st.query_params
if "area" in qp:
    st.session_state["price_area"] = qp["area"]
if "type" in qp:
    st.session_state["energy_type"] = qp["type"]
if "groups" in qp:
    st.session_state["selected_groups"] = qp["groups"].split(",")

# --------------------------------------------------------
# Ensure data is loaded (no global_sidebar on this page)
# --------------------------------------------------------
if "elhub_data" not in st.session_state:
    st.session_state["elhub_data"] = load_elhub_data()

df = st.session_state["elhub_data"]

# Initialize sidebar globals for safety
_init_globals()

# --------------------------------------------------------
# Determine analysis mode (production / consumption)
# --------------------------------------------------------
energy_type = st.session_state.get("energy_type", "production")

if energy_type == "production":
    group_col = "productiongroup"
    allowed_groups = PROD_GROUPS
    value_label = "Production (kWh)"
    title_type = "Production"
else:
    group_col = "consumptiongroup"
    allowed_groups = CONS_GROUPS
    value_label = "Consumption (kWh)"
    title_type = "Consumption"

# ---- Safety: prevent errors when consumption not yet in Mongo ----
if energy_type == "consumption" and group_col not in df.columns:
    st.error(
        "⚠️ Consumption data is not present in MongoDB.\n\n"
        "Please load CONSUMPTION_PER_GROUP_MBA_HOUR into Mongo, "
        "or switch back to **Production**."
    )
    st.stop()

# --------------------------------------------------------
# Prepare UI helpers
# --------------------------------------------------------
color_map = utils.get_color_map()
months = list(range(1, 12 + 1))
month_labels = [calendar.month_name[m] for m in months]

# Determine available years
years = sorted(df["starttime"].dt.year.unique())

# --------------------------------------------------------
# TITLE
# --------------------------------------------------------
st.title(f"Energy {title_type} Explorer")

# --------------------------------------------------------
# Prepare widget state for this page (mirroring canonical)
# --------------------------------------------------------
st.session_state.setdefault("_price_area_widget", st.session_state["price_area"])
st.session_state.setdefault("_energy_type_widget", energy_type)
st.session_state.setdefault("_groups_widget", st.session_state.get("selected_groups", allowed_groups[:]))


# Energy type selector (production / consumption)
st.radio(
    "Energy type",
    ["production", "consumption"],
    key="_energy_type_widget",
    horizontal=True,
    on_change=_sync_all
)

energy_type = st.session_state["energy_type"]

# Switch logic based on selected energy type
if energy_type == "production":
    group_col = "productiongroup"
    allowed_groups = PROD_GROUPS
    value_label = "Production (kWh)"
    title_type = "Production"
else:
    group_col = "consumptiongroup"
    allowed_groups = CONS_GROUPS
    value_label = "Consumption (kWh)"
    title_type = "Consumption"


# --------------------------------------------------------
# Layout: two columns
# --------------------------------------------------------
left1, right1 = st.columns(2)
left2, right2 = st.columns(2)


# ========================================================
# LEFT SIDE — PIE CHART
# ========================================================
with left1:
    st.subheader(f"Total {title_type.lower()} by group (year)")

    # Price area selector
    st.radio(
        "Price area",
        AREAS,
        key="_price_area_widget",
        horizontal=True,
        on_change=_sync_all
    )

    chosen_area = st.session_state["price_area"]

with left2:
    # Year selector
    year = st.selectbox("Year", years)

    # Aggregate yearly values
    df_year = df[
        (df["pricearea"] == chosen_area)
        & (df["starttime"].dt.year == year)
    ]

    df_area_year = (
        df_year.groupby(group_col, as_index=False)["quantitykwh"]
        .sum()
        .sort_values("quantitykwh", ascending=False)
    )

    # Pie chart
    fig_pie = px.pie(
        df_area_year,
        values="quantitykwh",
        names=group_col,
        color=group_col,
        color_discrete_map=color_map,
        title=f"{title_type} by Group — {chosen_area} ({year})",
        template="plotly_white",
    )

    fig_pie.update_layout(
        width=600,
        height=500,
        # margin=dict(t=60, b=40, l=40, r=40), 
    )

    st.plotly_chart(fig_pie, use_container_width=True)


# ========================================================
# RIGHT SIDE — LINE PLOT
# ========================================================
with right1:
    st.subheader(f"Hourly {title_type.lower()} (month)")

    # Normalize widget state for group pills
    raw = st.session_state.get("_groups_widget", [])
    if isinstance(raw, str) or raw is None or not isinstance(raw, list):
        raw = []

    valid_groups = [g for g in raw if g in allowed_groups]
    if not valid_groups:
        valid_groups = allowed_groups[:]

    st.session_state["_groups_widget"] = valid_groups
    st.session_state["selected_groups"] = valid_groups

    # Pills widget (group selection)
    st.pills(
        "Groups",
        options=allowed_groups,
        selection_mode="multi",
        key="_groups_widget",
        on_change=_sync_all
    )

    groups = st.session_state["selected_groups"]

    if not groups:
        st.warning(f"Please select at least one {title_type.lower()} group.")
        st.stop()

with right2:
    # This pushes the month box down to align with the year box on the left
    month_label = st.selectbox("Month", month_labels)
    month_num = month_labels.index(month_label) + 1



    # Filter data for line plot
    mask = (
        (df["pricearea"].str.upper() == chosen_area.upper()) &
        (df["starttime"].dt.year == year) &
        (df["starttime"].dt.month == month_num) &
        (df[group_col].isin(groups))
    )

    df_month = df[mask].copy().sort_values("starttime")

    fig_line = px.line(
        df_month,
        x="starttime",
        y="quantitykwh",
        color=group_col,
        color_discrete_map=color_map,
        title=f"Hourly {title_type} — {chosen_area}, {month_label} {year}",
        template="plotly_white",
    )

    fig_line.update_layout(
        width=600,
        height=450,
        # margin=dict(t=60, b=40, l=40, r=40),
        xaxis_title="Time",
        yaxis_title=value_label, 
    )

    st.plotly_chart(fig_line, use_container_width=True)


# ========================================================
# DATA SOURCE INFO
# ========================================================
with st.expander("Data source"):
    record_count = len(df)
    st.markdown(f"""
**Source:**  
Elhub API — `PRODUCTION_PER_GROUP_MBA_HOUR` & `CONSUMPTION_PER_GROUP_MBA_HOUR`  
(2021–2024)

**Processing:**  
Retrieved via API → processed in Jupyter with Spark → saved to Cassandra →  
exported to MongoDB → loaded dynamically in this app.

**Total Records Loaded:** {record_count:,}
    """)