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

# Transpose so columns become rows
df_transposed = df_first_month.set_index("time").T

# Convert column names to strings
df_transposed.columns = df_transposed.columns.astype(str)

# Reset index so row names become a column
df_transposed.reset_index(inplace=True)
df_transposed.rename(columns={"index": "Variable"}, inplace=True)

# Only numeric columns for LineChartColumn
numeric_cols = df_transposed.select_dtypes(include=["float64", "int64"]).columns

# Create column config for line charts
column_configs = {}
for col in numeric_cols:
    column_configs[col] = st.column_config.LineChartColumn(
        label=col,
        width=250
    )

# Display the DataFrame with column-level line charts
st.dataframe(df_transposed, column_config=column_configs)