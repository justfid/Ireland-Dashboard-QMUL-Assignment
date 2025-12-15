import streamlit as st
from streamlit.components.v1 import html
from utils.generate_maps import render_ireland_map
import pandas as pd

def _toggle_view() -> None:
    st.session_state.view = "county" if st.session_state.view == "nation" else "nation"

def main() -> None:
    st.set_page_config(page_title="ROI + NI Dashboard", page_icon="🇮🇪", layout = "centered", initial_sidebar_state="expanded")

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
            "EUR + GBP (€+£)",
        ],
        },
        index = ["Overview", "Population (Most Recent Census)", "GDP in Billions (2023)", "Number of Counties", "Currency"]
    )

    st.table(intro_text)
    st.caption("Most recent census used for population for each nation")
    st.caption("""USD rate based on 2023 average from The Federal Reserve Bank of St Louis:  
        GBP-USD: 1.2440  
        EUR-USD: 1.0817""")

    # ensure a persistent view state
    if "view" not in st.session_state:
        st.session_state.view = "nation"  # default view

    left, middle, right = st.columns(3)
    left.subheader("Map")

    with right:
        right.write(f"**Current view:** {st.session_state.view.title()}")
        if st.session_state.view == "county":
            right.button("Switch to nation view", key="toggle_view", on_click=_toggle_view)
        else:
            right.button("Switch to county view", key="toggle_view", on_click=_toggle_view)

    # pick paths based on state
    if st.session_state.view == "county":
        ireland_path = "data/raw/geojson/ie_county.json"
        ni_path = "data/raw/geojson/ni_county.geojson"
        county_view = True
    else:
        ireland_path = "data/raw/geojson/ie.json"
        ni_path = "data/raw/geojson/northern_ireland.geojson"
        county_view = False

    OSM_map = html(render_ireland_map(ireland_path, ni_path, county_view), height=400)

    left, middle, right = st.columns(3)

    left.caption("**Key:**")

    map_key = pd.DataFrame({
        "Nation": ["ROI", "NI"],
        "Colour": ["Green", "Blue"]
    })

    left.dataframe(map_key, hide_index=True)

main()