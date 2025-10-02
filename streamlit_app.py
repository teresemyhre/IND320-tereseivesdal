import streamlit as st
import altair as alt

# Define your muted theme palette (exactly 5 colors for your 5 series)
custom_colors = [
    "#1f77b4",  # blue
    "#ffb97e",  # light orange
    "#1f77b4",  # repeat or add muted variants
    "#ffb97e",
    "#1f77b4"
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
