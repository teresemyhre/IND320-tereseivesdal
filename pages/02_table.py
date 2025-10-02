import streamlit as st
import pandas as pd

st.title("Data Table – First Month")
st.write("Each row shows a column of the dataset with a mini line chart for the first month.")

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

# Display table with line charts
for idx, row in df_transposed.iterrows():
    st.write(f"**{idx}**")  # Column name
    st.line_chart(row)       # Mini line chart for that column