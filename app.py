import streamlit as st
from streamlit.components.v1 import html
from utils.map import render_ireland_map 

st.title("Ireland + Northern Ireland Dashboard")


"Map:"
map = html(render_ireland_map("data/geojson/ireland_wgs84.geojson",
    "data/geojson/northern_ireland.geojson"), height=400)

st.markdown("""**Key:** \n
    Republic of Ireland: Green \n
    Northern Ireland: Blue
"""
)

