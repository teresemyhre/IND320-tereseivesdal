import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


# --------------------------------------------------
# Get MongoDB client
# --------------------------------------------------
@st.cache_resource
def _get_mongo_client():
    uri = st.secrets["MONGO"]["uri"]
    return MongoClient(uri, server_api=ServerApi("1"))


# --------------------------------------------------
# Helper: load a *single* collection by name
# --------------------------------------------------
def _load_collection(client, collection_name):
    db = client[st.secrets["MONGO"]["database"]]
    col = db[collection_name]
    cursor = col.find({}, {"_id": 0})
    rows = list(cursor)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.columns = [c.lower() for c in df.columns]

    if "starttime" in df.columns:
        df["starttime"] = pd.to_datetime(df["starttime"])

    return df


# --------------------------------------------------
# Universal loader for production + consumption
# --------------------------------------------------
@st.cache_data(show_spinner=False)
def load_elhub_data():
    """
    Loads production AND consumption collections (if present),
    merges them into one unified DataFrame, and lowercases all columns.
    """

    client = _get_mongo_client()

    prod_name = st.secrets["MONGO"]["production_collection"]
    cons_name = st.secrets["MONGO"]["consumption_collection"]

    df_prod = _load_collection(client, prod_name)
    df_cons = _load_collection(client, cons_name)

    # Tag the energy type for clarity
    if not df_prod.empty:
        df_prod["energy_type"] = "production"
    if not df_cons.empty:
        df_cons["energy_type"] = "consumption"

    # Combine (handles missing collections gracefully)
    df = pd.concat([df_prod, df_cons], ignore_index=True)

    return df