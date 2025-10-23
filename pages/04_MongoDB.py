import streamlit as st
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import pandas as pd

# Connect using Streamlit secrets
uri = st.secrets["MONGO"]["uri"]
client = MongoClient(uri, server_api=ServerApi('1'))
db = client[st.secrets["MONGO"]["database"]]
collection = db[st.secrets["MONGO"]["collection"]]

st.success("✅ Connected to MongoDB!")

# Example: fetch and display a few records
data = list(collection.find().limit(5))
df = pd.DataFrame(data)
st.dataframe(df)