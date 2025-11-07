import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import calendar
import helpers.utils as utils  # activates Altair theme + color palette
import numpy as np
from helpers.sidebar import AREAS, GROUPS, _init_globals, _sync_all

st.set_page_config(page_title="Production Explorer", page_icon="⚡", layout="wide")

qp = st.query_params
if "area" in qp:
    st.session_state["price_area"] = qp["area"]
if "groups" in qp:
    st.session_state["production_group"] = qp["groups"].split(",")

# MongoDB connection
@st.cache_resource
def get_mongo_collection():
    uri = st.secrets["MONGO"]["uri"]
    client = MongoClient(uri, server_api=ServerApi("1"))
    db = client[st.secrets["MONGO"]["database"]]
    return db[st.secrets["MONGO"]["collection"]]

@st.cache_data(show_spinner=False)
def load_df():
    col = get_mongo_collection()
    cursor = col.find({}, {"_id": 0, "pricearea": 1, "productiongroup": 1, "starttime": 1, "quantitykwh": 1})
    df = pd.DataFrame(list(cursor))
    df["starttime"] = pd.to_datetime(df["starttime"])
    df.columns = [c.lower() for c in df.columns]
    return df

# Load data
df = load_df()

# Store globally so all pages can access
st.session_state["elhub_data"] = df

# Prepare selection options
price_areas = sorted(df["pricearea"].dropna().unique().tolist())
prod_groups = sorted(df["productiongroup"].dropna().unique().tolist())
months = list(range(1, 13))
month_labels = [calendar.month_name[m] for m in months]

# reuse colors from utils.py
color_map = utils.get_color_map()

st.title("Energy Production Explorer (2021)")


_init_globals()

# --- Mirror canonical session state into widgets before rendering ---
st.session_state["_price_area_widget"] = st.session_state["price_area"]
st.session_state["_production_group_widget"] = st.session_state["production_group"]

# Columns for layout
left, right = st.columns(2)

# LEFT: pie chart
with left:
    # Total production by group (year)
    st.subheader("Total production by group (year)")
    st.radio(
        "Price area", AREAS,
        horizontal=True,
        key="_price_area_widget",
        on_change=_sync_all
    )
    chosen_area = st.session_state["price_area"] 

    # Aggregate data for pie chart
    df_area_year = (
        df[df["pricearea"] == chosen_area]
        .groupby("productiongroup", as_index=False)["quantitykwh"]
        .sum()
        .sort_values("quantitykwh", ascending=False)
    )

    # Pie chart
    fig_pie = px.pie(
        df_area_year,
        values="quantitykwh",
        names="productiongroup",
        color="productiongroup",
        color_discrete_map=color_map,
        title=f"Total Production by Group — {chosen_area} (2021)",
        template="plotly_white",
    )
    # Customize layout
    fig_pie.update_layout(width=600, 
                          height=600, 
                          margin=dict(t=60, b=40, l=40, r=40))

    st.plotly_chart(fig_pie, use_container_width=True)

# RIGHT: line plot
with right:
    st.subheader("Hourly production (month)")

    # Ensure valid selection before rendering pills
    sel = st.session_state.get("_production_group_widget", None)

    if isinstance(sel, str):  # sometimes becomes '' as a string
        sel = []
    if not sel or any(v not in GROUPS for v in sel):
        sel = GROUPS[:]  # fallback to all valid groups

    st.session_state["_production_group_widget"] = sel
    st.session_state["production_group"] = sel  # keep canonical in sync
    
    # Create the pills widget
    st.pills(
        "Production groups", options=GROUPS,
        selection_mode="multi",
        key="_production_group_widget",
        on_change=_sync_all
    )

    # Prevent empty selection (fallback to all)
    if not st.session_state["_production_group_widget"]:
        st.session_state["_production_group_widget"] = GROUPS[:]
        st.session_state["production_group"] = GROUPS[:]






    selected_groups = st.session_state["production_group"]  # canonical

    # Month selection
    month_label = st.selectbox("Month", month_labels)
    month_num = month_labels.index(month_label) + 1

    # Filter data for line plot
    mask = (
        (df["pricearea"].str.upper() == st.session_state["price_area"].upper())
        & (df["starttime"].dt.month == month_num)
        & (df["productiongroup"].str.lower().isin([g.lower() for g in st.session_state["production_group"]]))
    )
    df_month = df[mask].copy().sort_values("starttime")

    # Line plot
    fig_line = px.line(
        df_month,
        x="starttime",
        y="quantitykwh",
        color="productiongroup",
        color_discrete_map=color_map,
        title=f"Hourly Production — {chosen_area}, {month_label} 2021",
        template="plotly_white",

    )
    # Customize layout
    fig_line.update_layout(width=900, 
                           height=450, 
                           margin=dict(t=60, b=40, l=40, r=40), 
                           xaxis_title="Time",
                           yaxis_title="Production (kWh)")
    st.plotly_chart(fig_line, use_container_width=True)

# Expander for data source info
with st.expander("Data source"):
    # Get the MongoDB collection from the cached function
    collection = get_mongo_collection()
    record_count = collection.count_documents({})

    st.markdown(f"""
**Source:** [Elhub API](https://api.elhub.no) — `PRODUCTION_PER_GROUP_MBA_HOUR`.  
            The dataset contains hourly electricity production for Norway’s five price areas (NO1–NO5) in 2021.
                
**Processing:**
The data were retrieved from the API, processed in Jupyter using Apache Spark for filtering and formatting, and stored in Cassandra for structured access.
Finally, the curated dataset was moved to MongoDB for visualization in this app.
                
**Total Records in Database:** {record_count:,}
    """)
