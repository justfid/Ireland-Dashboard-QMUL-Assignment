import streamlit as st
from streamlit.components.v1 import html
from utils.maps import render_ireland_map
import pandas as pd

#st.set_page_config(page_title="ROI + NI Dashboard", page_icon="🇮🇪", layout="wide", initial_sidebar_state="expanded")
st.set_page_config(page_title="ROI + NI Dashboard", page_icon="🇮🇪", initial_sidebar_state="expanded")

st.title("Republic Of Ireland + Northern Ireland Dashboard:")
st.subheader("One Island, Two Nations")

"This dashboard aims to compare and contrast these 2 nations sharing an island"

st.subheader("Overview:")

intro_text = pd.DataFrame( 
    {
    "Republic of Ireland (ROI)" : [
        "An independent, soverign nation",
        "5,149,139 (April 2022)",
        "$551.604 (€509.952)",
        "26",
        "Euro - EUR(€)",
    ],
    "Northern Ireland (NI)" : [
        "A constituent nation of the United Kingdom (UK)",
        "1,903,175 (March 2021)",
        "$78.701 (£63.265)",
        "6",
        "British Pound - GBP (£)",
    ],
    "All-Island": [
        "A geographical island comprising of ROI and NI",
        "7,052,314",
        "$630.305",
        "32",
        "EUR + GBP",
    ],
    },
    index = ["Overview", "Population (Most Recent Census)", "GDP in Billions (2023)", "Number of Counties", "Currency"]
)

st.table(intro_text)
st.caption("Most recent census used for population for each nation")
st.caption("USD rate based on 2023 average given by The Federal Reserve Bank of St Louis")

usd_rates = pd.DataFrame({
    "Pair": ["USD - GBP", "USD - EUR"],
    "2023 Average Rate": [1.2440, 1.0817],
})
st.dataframe(usd_rates, hide_index=True)


st.subheader("Map")
map = html(render_ireland_map("data/cleaned/geojson/ireland_wgs84.geojson",
    "data/raw/geojson/northern_ireland.geojson"), height=400)

map_key = pd.DataFrame({
    "Nation": ["ROI", "NI"],
    "Colour": ["Green", "Blue"]
})
#Add toggle for counties

st.caption("Key:")
st.dataframe(map_key, hide_index=True)
