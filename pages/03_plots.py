import streamlit as st
import pandas as pd
import utils  # activates the custom Altair theme (see utils.py)

st.title("Data Visualization")

# Load CSV
@st.cache_data # cache the data loading for performance
def load_data():
    df = pd.read_csv("data/open-meteo-subset.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df

df = load_data()

# Selectbox for choosing column to plot
columns = list(df.columns.drop("time"))
option = st.selectbox("Choose a column to plot", ["All"] + columns)

# Slider for selecting month range
months = sorted(df["time"].dt.month.unique())
month_range = st.select_slider(
    "Select months range",
    options=months, 
    value=(months[0], months[0]),  # default is first month
    format_func=lambda x: df[df["time"].dt.month == x]["time"].dt.strftime("%B").iloc[0] # get month name instead of number
)

# Filter data within selected month range 
subset = df[(df["time"].dt.month >= month_range[0]) & (df["time"].dt.month <= month_range[1])]

# Get first and last month names
first_month_name = subset["time"].dt.strftime("%B").iloc[0]
last_month_name = subset["time"].dt.strftime("%B").iloc[-1]

# Create dynamic header text based on selection
if first_month_name == last_month_name:
    header_text = f"{option} for {first_month_name}" if option != "All" else f"All columns for {first_month_name}"
else:
    header_text = f"{option} for {first_month_name} – {last_month_name}" if option != "All" else f"All columns for {first_month_name} – {last_month_name}"

# Display header centered
st.markdown(f"<h2 style='text-align: center;'>{header_text}</h2>", unsafe_allow_html=True)

# Plot the data using a line chart
if option == "All":
    st.line_chart(subset.set_index("time")[columns])
else:
    st.line_chart(subset.set_index("time")[[option]])