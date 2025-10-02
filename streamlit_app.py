import streamlit as st
import altair as alt

# Define your muted theme palette (exactly 5 colors for your 5 series)
custom_colors = [
    "#1f77b4",  # muted blue
    "#ff7f0e",  # soft orange
    "#2ca02c",  # muted green
    "#d62728",  # muted red
    "#9467bd"   # soft purple
]
alt.themes.register('custom_theme', lambda: {
    "config": {
        "range": {
            "category": custom_colors
        }
    }
})
alt.themes.enable('custom_theme')

st.title("IND320 Project – Weather Data")
st.write("Welcome! This app shows data analysis and visualization of the provided CSV file.")
st.write("Use the sidebar to navigate between pages.")
