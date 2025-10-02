import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

df = load_data()

st.title("Data Visualization")

# Column selector
columns = list(df.columns.drop("time"))
option = st.selectbox("Choose a column to plot", ["All"] + columns)

# Month selector
months = sorted(df["time"].dt.month.unique())
month = st.select_slider("Select month", options=months, value=months[0])

subset = df[df["time"].dt.month == month]

if option == "All":
    st.line_chart(subset.set_index("time")[columns])
else:
    st.line_chart(subset.set_index("time")[[option]])