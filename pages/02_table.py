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

# Prepare a table: one row per column
table_data = []
for col in df_first_month.columns:
    if col == "time":
        continue  # skip time column
    row = {
        "Variable": col,
        "First Month": df_first_month[col].tolist()  # list of values for LineChartColumn
    }
    table_data.append(row)

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