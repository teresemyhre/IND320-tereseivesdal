import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import calendar
import utils  # activates Altair theme + color palette

st.set_page_config(page_title="Production Explorer", page_icon="⚡", layout="wide")

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

# Prepare selection options
price_areas = sorted(df["pricearea"].dropna().unique().tolist())
prod_groups = sorted(df["productiongroup"].dropna().unique().tolist())
months = list(range(1, 13))
month_labels = [calendar.month_name[m] for m in months]

# reuse colors from utils.py
color_map = utils.get_color_map()

st.title("Energy Production Explorer (2021)")

# Columns for layout
left, right = st.columns(2)

# LEFT: pie chart
with left:
    # Total production by group (year)
    st.subheader("Total production by group (year)")
    chosen_area = st.radio("Price area", price_areas, index=0, horizontal=True)

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
    fig_pie.update_layout(title_x=0.15, 
                          width=600, 
                          height=600, 
                          margin=dict(t=60, b=40, l=40, r=40))

    st.plotly_chart(fig_pie, use_container_width=True)

# RIGHT: line plot
with right:
    st.subheader("Hourly production (month)")

    # Streamlit 1.38+ pills, else fallback to multiselect
    if hasattr(st, "pills"):
        selected_groups = st.pills("Production groups", options=prod_groups, selection_mode="multi", default=prod_groups)
    else:
        selected_groups = st.multiselect("Production groups", options=prod_groups, default=prod_groups)

    # Month selection
    month_label = st.selectbox("Month", month_labels, index=0)
    month_num = month_labels.index(month_label) + 1

    # Filter data for line plot
    mask = (
        (df["pricearea"] == chosen_area)
        & (df["starttime"].dt.month == month_num)
        & (df["productiongroup"].isin(selected_groups))
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
    fig_line.update_layout(title_x=0.19, 
                           width=900, 
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
