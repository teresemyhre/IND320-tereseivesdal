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

# Transpose so that columns become rows
df_transposed = df_first_month.set_index("time").T
df_transposed.reset_index(inplace=True)
df_transposed.rename(columns={"index": "Variable"}, inplace=True)

# Each numeric column becomes a LineChartColumn
column_configs = {}
for col in df_transposed.columns[1:]:  # skip "Variable" column
    column_configs[col] = st.column_config.LineChartColumn(
        label=col,
        width=250
    )

# Display table with LineChartColumn
st.dataframe(df_transposed, column_config=column_configs)