import streamlit as st
import pandas as pd

# Load data with caching
@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

df = load_data()

st.title("Data Table – First Month")

# Select first month
first_month = df["time"].dt.month == df["time"].dt.month.min()
df_first_month = df[first_month]

# Build table with one row per column
columns = []
for col in df.columns[1:]:  # skip 'time'
    columns.append(
        st.column_config.LineChartColumn(
            label=col,
            width=250
        )
    )

# Streamlit currently requires using `st.dataframe` or `st.table` with column configs
st.dataframe(df_first_month)