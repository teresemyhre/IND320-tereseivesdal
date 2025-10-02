import streamlit as st
import pandas as pd

st.title("Data Table – First Month with Line Charts")

# Load CSV
@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

df = load_data()

# Filter first month
first_month = df["time"].dt.month == df["time"].dt.month.min()
df_first_month = df[first_month]

# Transpose so each original column becomes a row
df_transposed = df_first_month.drop(columns=["time"]).T  # drop 'time'
df_transposed.reset_index(inplace=True)
df_transposed.rename(columns={"index": "Variable"}, inplace=True)

# All remaining columns are numeric, create LineChartColumn config
numeric_cols = df_transposed.select_dtypes(include=["float64", "int64"]).columns

column_configs = {}
for col in numeric_cols:
    column_configs[col] = st.column_config.LineChartColumn(
        label=col,
        width=250
    )

# Display the DataFrame with column-level line charts
st.dataframe(df_transposed, column_config=column_configs)