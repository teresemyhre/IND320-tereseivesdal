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

# Month selector (range)
months = sorted(df["time"].dt.month.unique())
month_range = st.select_slider(
    "Select months range",
    options=months,
    value=(months[0], months[0]),  # default is first month
    format_func=lambda x: df[df["time"].dt.month == x]["time"].dt.strftime("%B").iloc[0]
)

# Filter data within selected month range
subset = df[(df["time"].dt.month >= month_range[0]) & (df["time"].dt.month <= month_range[1])]

# Get the header from first date in the subset
month_names = subset["time"].dt.strftime("%B").unique()
header_text = f"{option} for {' - '.join(month_names)}" if option != "All" else f"All columns for {' - '.join(month_names)}"
st.markdown(f"<h2 style='text-align: center;'>{header_text}</h2>", unsafe_allow_html=True)

# Plot
if option == "All":
    st.line_chart(subset.set_index("time")[columns])
else:
    st.line_chart(subset.set_index("time")[[option]])