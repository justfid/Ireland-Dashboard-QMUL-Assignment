import streamlit as st
from streamlit.components.v1 import html
from utils.map import render_ireland_map 


st.set_page_config(page_title="Ireland Dashboard", page_icon="🇮🇪")

st.title("Ireland + Northern Ireland Dashboard")

"This dashboard aims to show the differing systems of 2 nations sharing an island"
"""Some context \n
The Republic of Ireland is a sovereign state whereas Northern Ireland is a constituent nation of the UK"""

"Map:"
map = html(render_ireland_map("data/geojson/ireland_wgs84.geojson",
    "data/geojson/northern_ireland.geojson"), height=400)

st.markdown("""**Key:** \n
    Republic of Ireland: Green \n
    Northern Ireland: Blue
"""
)

