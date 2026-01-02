import streamlit as st
from streamlit.components.v1 import html
import pandas as pd
from utils.generate_maps import render_ireland_map

# Constants / data
USD_RATES_2023 = {
    "GBPUSD": 1.2440,
    "EURUSD": 1.0817,
}

NATIONS = {
    "ROI": {
        "name": "Republic of Ireland (ROI)",
        "overview": "An independent, sovereign nation",
        "population": ("5,149,139", "April 2022"),
        "gdp_usd_b": 551.604,
        "gdp_native_b": 509.952,
        "native_currency": "EUR (€)",
        "counties": 26,
        "map_colour": "Green",
    },
    "NI": {
        "name": "Northern Ireland (NI)",
        "overview": "A constituent nation of the United Kingdom (UK)",
        "population": ("1,903,175", "March 2021"),
        "gdp_usd_b": 78.701,
        "gdp_native_b": 63.265,
        "native_currency": "GBP (£)",
        "counties": 6,
        "map_colour": "Blue",
    },
    "ALL": {
        "name": "All-Island",
        "overview": "A geographical island comprising ROI and NI",
        "population": ("7,052,314", "Combined latest censuses"),
        "gdp_usd_b": 630.305,
        "gdp_native_b": None,  #mixed currencies
        "native_currency": "EUR + GBP (€ + £)",
        "counties": 32,
        "map_colour": "Green + Blue",
    },
}

# State

def _toggle_view() -> None:
    st.session_state.view = "county" if st.session_state.view == "nation" else "nation"


@st.cache_data(show_spinner=False)
def build_intro_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Republic of Ireland (ROI)": [
                NATIONS["ROI"]["overview"],
                NATIONS["ROI"]["population"][0],
                f'{NATIONS["ROI"]["gdp_usd_b"]:.3f} (USD) / {NATIONS["ROI"]["gdp_native_b"]:.3f} (EUR)',
                str(NATIONS["ROI"]["counties"]),
                NATIONS["ROI"]["native_currency"],
            ],
            "Northern Ireland (NI)": [
                NATIONS["NI"]["overview"],
                NATIONS["NI"]["population"][0],
                f'{NATIONS["NI"]["gdp_usd_b"]:.3f} (USD) / {NATIONS["NI"]["gdp_native_b"]:.3f} (GBP)',
                str(NATIONS["NI"]["counties"]),
                NATIONS["NI"]["native_currency"],
            ],
            "All-Island": [
                NATIONS["ALL"]["overview"],
                NATIONS["ALL"]["population"][0],
                f'{NATIONS["ALL"]["gdp_usd_b"]:.3f} (USD)',
                str(NATIONS["ALL"]["counties"]),
                NATIONS["ALL"]["native_currency"],
            ],
        },
        index=[
            "Overview",
            "Population (Most Recent Census)",
            "GDP in Billions (2023)",
            "Number of Counties",
            "Currency",
        ],
    )


@st.cache_data(show_spinner=False)
def render_map_html(view: str) -> str:
    if view == "county":
        ireland_path = "data/raw/geojson/ie_county.json"
        ni_path = "data/raw/geojson/ni_county.geojson"
        county_view = True
    else:
        ireland_path = "data/raw/geojson/ie.json"
        ni_path = "data/raw/geojson/northern_ireland.geojson"
        county_view = False

    return render_ireland_map(ireland_path, ni_path, county_view)


def render_header():
    st.title("🇮🇪 Republic of Ireland + Northern Ireland Dashboard")
    st.subheader("One island, two nations")
    st.write(
        "This dashboard compares ROI and NI across key themes (demographics, economy, health, and identity) "
        "to highlight similarities, differences, and trends over time."
    )
    st.markdown(
        """
**Planned sections**
- Overview & geography (this page)
- Demographics (population pyramids, age dependency, change over time, religion & NI identity split)
- Economy (GDP, wages, cost-of-living indicators)
- Society (health, education, housing indicators)
"""
    )


def render_overview_controls():
    c1, c2 = st.columns([1, 1])
    with c1:
        focus = st.selectbox("Focus", ["All-Island", "Republic of Ireland (ROI)", "Northern Ireland (NI)"])
    with c2:
        gdp_mode = st.radio("GDP display", ["USD (comparable)", "Native currency"], horizontal=True)
    return focus, gdp_mode


def render_kpis(focus: str, gdp_mode: str):
    key = "ALL" if "All-Island" in focus else ("ROI" if "ROI" in focus else "NI")
    data = NATIONS[key]

    pop_value, pop_date = data["population"]

    if gdp_mode == "Native currency" and data["gdp_native_b"] is not None:
        gdp_value = f'{data["gdp_native_b"]:.3f}B'
        gdp_delta = data["native_currency"]
    else:
        gdp_value = f'{data["gdp_usd_b"]:.3f}B'
        gdp_delta = "USD (2023)"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population", pop_value, pop_date)
    k2.metric("GDP", gdp_value, gdp_delta)
    k3.metric("Counties", str(data["counties"]))
    k4.metric("Currency", data["native_currency"])


def render_map_panel():
    #persistent view
    if "view" not in st.session_state:
        st.session_state.view = "nation"

    left, right = st.columns([3, 1], gap="large")

    with left:
        st.subheader("Map")
        map_html = render_map_html(st.session_state.view)
        html(map_html, height=420)

    with right:
        st.write(f"**Current view:** {st.session_state.view.title()}")
        st.button(
            "Switch to nation view" if st.session_state.view == "county" else "Switch to county view",
            key="toggle_view",
            on_click=_toggle_view,
            use_container_width=True,
        )

        st.markdown("**Key**")
        map_key = pd.DataFrame(
            {"Nation": ["ROI", "NI"], "Colour": ["Green", "Blue"]}
        )
        st.dataframe(map_key, hide_index=True, use_container_width=True)


def render_sources_and_notes():
    with st.expander("Data sources, provenance & assumptions (for marking)"):
        st.markdown(
            f"""
- **Population:** using the most recent censuses shown on the overview table.
- **GDP:** 2023 values. USD conversions use 2023 average exchange rates:
  - GBP→USD: {USD_RATES_2023["GBPUSD"]}
  - EUR→USD: {USD_RATES_2023["EURUSD"]}
- **Map boundaries:** GeoJSON files stored locally in `data/raw/geojson/`.
- **Cleaning (applies across dashboard):** place names normalised to consistent casing and naming conventions
  (e.g. `Derry/Londonderry` in NI pages).
"""
        )
    st.caption(
        "A dashboard implies interactivity and ideally up-to-date data; this project focuses on interactive exploration "
        "and reproducible methods."  #aligns with brief language
    )


def main() -> None:
    st.set_page_config(
        page_title="ROI + NI Dashboard",
        page_icon="🇮🇪",
        layout="wide",  #better responsiveness for maps/columns
        initial_sidebar_state="expanded",
    )

    render_header()

    st.subheader("Overview")
    focus, gdp_mode = render_overview_controls()
    render_kpis(focus, gdp_mode)

    st.markdown("---")
    st.subheader("Quick comparison table")
    st.table(build_intro_table())
    st.caption("Most recent census used for each nation’s population figure (see expander for assumptions).")

    st.markdown("---")
    render_map_panel()

    st.markdown("---")
    render_sources_and_notes()


main()
