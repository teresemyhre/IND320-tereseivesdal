import os
import base64
import streamlit as st

st.set_page_config(page_title="IND320 Project", page_icon="🦆", layout="wide")
 

# --- Initialize global state once ---
if "price_area" not in st.session_state:
    st.session_state["price_area"] = "NO1"

if "production_group" not in st.session_state:
    st.session_state["production_group"] = ["hydro", "wind", "solar", "thermal", "other"]


# Load and encode the duck image 
base_dir = os.path.dirname(__file__)

duck_path = os.path.join(base_dir, "data", "images", "duck.png")
with open(duck_path, "rb") as f:
    duck_base64 = base64.b64encode(f.read()).decode("utf-8")
left, right = st.columns([1.5, 1])

with left:
    # Inject CSS and mirrored layout for duck and speech bubble
    st.markdown(
        f"""
        <style>
        .speech-bubble {{
            position: relative;
            top: 70px; /* Adjust this number for height */
            background: #f9f9f9;
            border-radius: 20px;
            padding: 25px 30px;
            max-width: 8000px;
            font-size: 18px;          /* Larger text */
            line-height: 1.6;         /* More spacing between lines */
            font-weight: 500;         /* Slightly bolder text */
            box-shadow: 2px 2px 12px rgba(0,0,0,0.15);
            text-align: left;
        }}

        .speech-bubble strong {{
            font-size: 18px;          /* Larger title line */
            font-weight: 700;         /* Bold greeting */
        }}

        .speech-bubble:after {{
            content: "";
            position: absolute;
            right: -20px;  /* Tail moved to the right side */
            top: 120px;
            width: 0;
            height: 0;
            border: 12px solid transparent;
            border-left-color: #f9f9f9;
        }}
        </style>
        <div class="speech-bubble">
            <strong>Hey! I’m the Data Duck 🦆</strong><br>
            I love long walks on the grid and the occasional breeze of fresh data. <br><br>
            Use the sidebar and start quacking around!
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write(" ")
    st.write(" ")
    st.write(" ")
    st.write(" ")
    st.write(" ")
    st.write(" ")
    st.write(" ")
    st.write(" ")




    st.markdown("""
            
    ### 🔍 How to Navigate the Dashboard

    This dashboard is organized into three groups. The symbols you see in the sidebar help you understand what type of analysis each page belongs to.

    ##### ◦ Explorative
    Pages marked with **◦** focus on exploring the raw data. Here you can browse and visualize weather and energy information through tables, maps, and interactive plots.

    ##### ◈ Patterns & Anomalies
    Pages marked with **◈** contain analytical tools. These include signal decomposition, spectrograms, sliding-window correlations, and detection of unusual values using SPC and LOF.
    
    ##### ➤ Predictive
    Pages marked with **➤** produce forecasts. This section includes predictive modelling and visualization of expected future values.

    """)

with right:
    st.markdown(
        f"""
        <style>
        .duck-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: row-reverse;  /* Duck on the right side */
            gap: 30px;
            margin-top: 50px;
        }}

        </style>
        <div class="duck-container">
            <img src="data:image/png;base64,{duck_base64}" width="330">  <!-- Bigger duck -->
        </div>
        """,
        unsafe_allow_html=True
    )