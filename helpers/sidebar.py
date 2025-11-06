import streamlit as st

AREAS  = ["NO1", "NO2", "NO3", "NO4", "NO5"]
GROUPS = ["hydro", "wind", "solar", "thermal", "other"]

def _init_globals():
    st.session_state.setdefault("price_area", "NO1")
    st.session_state.setdefault("production_group", GROUPS[:])

def _sync_all():
    st.session_state["price_area"] = st.session_state["_price_area_widget"]
    st.session_state["production_group"] = st.session_state["_production_group_widget"]
    st.query_params.update(
        area=st.session_state["price_area"],
        groups=",".join(st.session_state["production_group"])
    )

def global_sidebar():
    st.markdown("### Global Controls")
    _init_globals()

    # Mirror canonical values into widget keys on every render
    st.session_state["_price_area_widget"] = st.session_state["price_area"]
    st.session_state["_production_group_widget"] = st.session_state["production_group"]

    # Both widgets share the same on_change callback
    st.radio(
        "Price area", AREAS,
        key="_price_area_widget",
        on_change=_sync_all
    )

    # Ensure widget state is valid before rendering the pills 
    sel = st.session_state.get("_production_group_widget", None)

    # Normalize: must be a non-empty list of valid options
    if isinstance(sel, str):                      # sometimes becomes '' (string)
        sel = []                                  # normalize to empty list
    if not sel or any(v not in GROUPS for v in sel):
        sel = GROUPS[:]                           # fallback to all

    st.session_state["_production_group_widget"] = sel
    st.session_state["production_group"] = sel    # keep canonical in sync
    
    # Create the pills widget
    st.pills(
        "Production groups",
        options=GROUPS,
        selection_mode="multi",
        key="_production_group_widget",
        on_change=_sync_all
    )

    # Prevent empty selection (fallback to all)
    if not st.session_state["production_group"]:
        st.session_state["production_group"] = GROUPS[:]