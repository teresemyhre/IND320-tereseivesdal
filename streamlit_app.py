import streamlit as st
import altair as alt

# Defining muted theme palette (5 colors for 5 series)
custom_colors = ["#fd9e53", "#ffcea8", "#6CA0DC", "#9ecaec", "#3b97da"]

@alt.theme.register('custom_theme', enable=True)
def custom_theme():
    return alt.theme.ThemeConfig(
        config={
            "range": {"category": custom_colors}
        }
    )

st.title("IND320 Project – Weather Data")
st.write("Welcome! This app shows data analysis and visualization of the provided CSV file.")
st.write("Use the sidebar to navigate between pages.")
