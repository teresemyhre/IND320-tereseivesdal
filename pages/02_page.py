import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

df = load_data()

st.title("Data Table")
st.write("Here’s a preview of the dataset:")
st.dataframe(df.head())

st.write("Row-wise chart preview (first month):")
first_month = df[df["time"].dt.month == df["time"].dt.month.min()]
st.dataframe(first_month.set_index("time"))