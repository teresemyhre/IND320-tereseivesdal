import streamlit as st
from helpers.data_loader import load_elhub_data

# ----------------------------------------------
# Categories
# ----------------------------------------------

AREAS = ["NO1", "NO2", "NO3", "NO4", "NO5"]

PROD_GROUPS = ["hydro", "wind", "solar", "thermal", "other"]
CONS_GROUPS = ["cabin", "household", "primary", "secondary", "tertiary"]

ENERGY_TYPES = ["production", "consumption"]


# ----------------------------------------------
# Init globals
# ----------------------------------------------

def _init_globals():
    st.session_state.setdefault("price_area", "NO1")
    st.session_state.setdefault("energy_type", "production")
    st.session_state.setdefault("selected_groups", PROD_GROUPS[:])  # canonical group key
    st.session_state.setdefault("year", 2021)

    # widget mirrors
    st.session_state.setdefault("_price_area_widget", st.session_state["price_area"])
    st.session_state.setdefault("_energy_type_widget", st.session_state["energy_type"])
    st.session_state.setdefault("_groups_widget", st.session_state["selected_groups"])
    st.session_state.setdefault("_year_widget", st.session_state["year"])


# ----------------------------------------------
# Sync callback
# ----------------------------------------------

def _sync_all():
    # Guard against missing widgets on first render
    for k in ["_price_area_widget", "_energy_type_widget", "_groups_widget", "_year_widget"]:
        if k not in st.session_state:
            return

    st.session_state["price_area"] = st.session_state["_price_area_widget"]
    st.session_state["energy_type"] = st.session_state["_energy_type_widget"]
    st.session_state["year"] = st.session_state["_year_widget"]

    # Allowed groups based on energy type
    allowed = PROD_GROUPS if st.session_state["energy_type"] == "production" else CONS_GROUPS

    raw = st.session_state.get("_groups_widget", [])
    if isinstance(raw, str) or raw is None:
        raw = []
    if not isinstance(raw, list):
        raw = []

    cleaned = [g for g in raw if g in allowed]
    if not cleaned:  # fallback to allowed
        cleaned = allowed[:]

    st.session_state["selected_groups"] = cleaned
    st.session_state["_groups_widget"] = cleaned

    # URL sync
    st.query_params.update(
        area=st.session_state["price_area"],
        type=st.session_state["energy_type"],
        year=str(st.session_state["year"]),
        groups=",".join(cleaned),
    )


# ----------------------------------------------
# Global sidebar
# ----------------------------------------------

def global_sidebar():
    st.markdown("### Global Controls")

    # Ensure elhub data loaded
    # st.session_state["elhub_data"] = load_elhub_data()
    load_elhub_data()   # Cached, light, never stored in state

    # Initialize everything
    _init_globals()

    # Mirror canonical => widget
    st.session_state["_price_area_widget"] = st.session_state["price_area"]
    st.session_state["_energy_type_widget"] = st.session_state["energy_type"]
    st.session_state["_year_widget"] = st.session_state["year"]

    allowed = PROD_GROUPS if st.session_state["energy_type"] == "production" else CONS_GROUPS

    cleaned = [g for g in st.session_state["selected_groups"] if g in allowed]
    if not cleaned:
        cleaned = allowed[:]
    st.session_state["_groups_widget"] = cleaned

    # --- WIDGETS ---

    st.radio(
        "Energy type",
        ENERGY_TYPES,
        key="_energy_type_widget",
        horizontal=True,
        on_change=_sync_all
    )

    st.radio(
        "Price area",
        AREAS,
        key="_price_area_widget",
        horizontal=True,
        on_change=_sync_all
    )

    st.number_input(
        "Year",
        min_value=2021, max_value=2024,
        key="_year_widget",
        on_change=_sync_all
    )

    with st.expander("Groups", expanded=True):
        st.pills(
            "Select groups",
            options=allowed,
            selection_mode="multi",
            key="_groups_widget",
            on_change=_sync_all
        )

    # Return validity
    return len(st.session_state["selected_groups"]) > 0