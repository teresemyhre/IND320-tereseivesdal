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

# Inject CSS and mirrored layout for duck and speech bubble
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

    .speech-bubble {{
        position: relative;
        top: -110px; /* Adjust this number for height */
        background: #f9f9f9;
        border-radius: 20px;
        padding: 25px 30px;
        max-width: 550px;
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
        right: -18px;  /* Tail moved to the right side */
        top: 40px;
        width: 0;
        height: 0;
        border: 12px solid transparent;
        border-left-color: #f9f9f9;
    }}
    </style>

    <div class="duck-container">
        <img src="data:image/png;base64,{duck_base64}" width="300">  <!-- Bigger duck -->
        <div class="speech-bubble">
            <strong>Hey! I’m the Data Duck 🦆</strong><br>
            I love long walks on the grid and the occasional breeze of fresh data. <br><br>
            Use the sidebar and start quacking around!
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
