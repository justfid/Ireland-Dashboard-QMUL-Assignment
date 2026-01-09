import streamlit as st
from streamlit.components.v1 import html
import pandas as pd
from utils.generate_maps import render_ireland_map
from utils.common import ROI, NI
from typing import Tuple

#constants / data
USD_RATES_2023 = {
    "GBPUSD": 1.2440,
    "EURUSD": 1.0817,
}

NATIONS = {
    "ROI": {
        "name": "Republic of Ireland (ROI)",
        "overview": "An independent, sovereign nation",
        "capital": "Dublin",
        "gdp_usd_b": 551.604,
        "gdp_native_b": 509.952,
        "native_currency": "EUR (€)",
        "counties": 26,
        "map_colour": "Green",
    },
    "NI": {
        "name": "Northern Ireland (NI)",
        "overview": "A constituent nation of the United Kingdom (UK)",
        "capital": "Belfast",
        "gdp_usd_b": 78.701,
        "gdp_native_b": 63.265,
        "native_currency": "GBP (£)",
        "counties": 6,
        "map_colour": "Blue",
    },
    "ALL": {
        "name": "All-Island",
        "overview": "A geographical island comprising ROI and NI",
        "capital": "Dublin / Belfast",
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
def _load_latest_census_populations() -> dict:
    #uses the cleaned demographics file
    path = "data/cleaned/demographics/population_over_time.csv"
    df = pd.read_csv(path)

    required = {"Year", "Region", "Population"}
    if not required.issubset(df.columns):
        raise ValueError(f"Expected columns {sorted(required)}, got {list(df.columns)}")

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Population"] = pd.to_numeric(df["Population"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df = df.dropna(subset=["Year", "Population"])

    region_map = {
        ROI: "ROI",
        NI: "NI",
    }

    out: dict = {}
    for region_name, key in region_map.items():
        sub = df[df["Region"] == region_name].sort_values("Year")
        if sub.empty:
            continue
        latest = sub.iloc[-1]
        year = int(latest["Year"])
        pop = int(latest["Population"])
        out[key] = (f"{pop:,}", f"Census {year}")

    # Calculate All-Island total if both ROI and NI exist
    if "ROI" in out and "NI" in out:
        roi_pop = int(out["ROI"][0].replace(",", ""))
        ni_pop = int(out["NI"][0].replace(",", ""))
        all_pop = roi_pop + ni_pop
        # Use the most recent year from either region
        roi_df = df[df["Region"] == ROI].sort_values("Year")
        ni_df = df[df["Region"] == NI].sort_values("Year")
        latest_year = max(int(roi_df.iloc[-1]["Year"]), int(ni_df.iloc[-1]["Year"]))
        out["ALL"] = (f"{all_pop:,}", f"Census {latest_year}")

    return out


@st.cache_data(show_spinner=False)
def build_intro_table() -> pd.DataFrame:
    pop_map = _load_latest_census_populations()
    return pd.DataFrame(
        {
            "Republic of Ireland (ROI)": [
                NATIONS["ROI"]["overview"],
                NATIONS["ROI"]["capital"],
                pop_map["ROI"][0],
                f'{NATIONS["ROI"]["gdp_usd_b"]:.3f} (USD) / {NATIONS["ROI"]["gdp_native_b"]:.3f} (EUR)',
                str(NATIONS["ROI"]["counties"]),
                NATIONS["ROI"]["native_currency"],
            ],
            "Northern Ireland (NI)": [
                NATIONS["NI"]["overview"],
                NATIONS["NI"]["capital"],
                pop_map["NI"][0],
                f'{NATIONS["NI"]["gdp_usd_b"]:.3f} (USD) / {NATIONS["NI"]["gdp_native_b"]:.3f} (GBP)',
                str(NATIONS["NI"]["counties"]),
                NATIONS["NI"]["native_currency"],
            ],
            "All-Island": [
                NATIONS["ALL"]["overview"],
                NATIONS["ALL"]["capital"],
                pop_map["ALL"][0],
                f'{NATIONS["ALL"]["gdp_usd_b"]:.3f} (USD)',
                str(NATIONS["ALL"]["counties"]),
                NATIONS["ALL"]["native_currency"],
            ],
        },
        index=[
            "Overview",
            "Capital",
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


def render_header() -> None:
    st.title("🇮🇪 Republic of Ireland + Northern Ireland Dashboard")
    st.subheader("One island, two jurisdictions")

    st.write(
        "This dashboard provides a comparative analysis of the island of Ireland using official census statistics "
        "to examine demographics, economic indicators, social conditions, and cultural identity. "
        "It is designed to support exploration of differences, similarities, and trends across jurisdictions."
    )

    st.caption(
        "Use the sidebar to navigate themes. Where definitions differ between ROI and NI, charts include notes on comparability."
    )


def render_overview_controls() -> Tuple[str, str]:
    c1, c2 = st.columns([1, 1])

    with c1:
        focus: str = st.selectbox(
            "Focus",
            ["All-Island", "Republic of Ireland (ROI)", "Northern Ireland (NI)"],
            key="focus_select",
        )

    disable_native: bool = (focus == "All-Island")

    #set/repair session state BEFORE creating the radio widget
    if "gdp_mode_radio" not in st.session_state:
        st.session_state["gdp_mode_radio"] = "USD (comparable)"

    if disable_native and st.session_state["gdp_mode_radio"] == "Native currency":
        st.session_state["gdp_mode_radio"] = "USD (comparable)"

    with c2:
        gdp_mode: str = st.radio(
            "GDP display",
            ["USD (comparable)", "Native currency"],
            horizontal=True,
            key="gdp_mode_radio",
            disabled=disable_native,
        )

        if disable_native:
            st.caption("Native currency is disabled for All-Island because it combines EUR and GBP.")

    return focus, gdp_mode


def render_kpis(focus: str, gdp_mode: str) -> None:
    key: str = (
        "ALL" if focus == "All-Island"
        else "ROI" if "ROI" in focus
        else "NI"
    )
    data: dict = NATIONS[key]

    pop_map = _load_latest_census_populations()
    pop_value, pop_date = pop_map[key]

    #GDP display logic
    if gdp_mode == "Native currency" and data["gdp_native_b"] is not None:
        gdp_value: str = f'{data["gdp_native_b"]:.3f}B'
        gdp_context: str = data["native_currency"]
    else:
        gdp_value = f'{data["gdp_usd_b"]:.3f}B'
        gdp_context = "USD (2023)"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population", pop_value)
    k1.caption(pop_date)

    k2.metric("GDP", gdp_value)
    k2.caption(gdp_context)

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
            width='stretch',
        )

        st.markdown("**Key**")
        map_key = pd.DataFrame(
            {"Nation": ["ROI", "NI"], "Colour": ["Green", "Blue"]}
        )
        st.dataframe(map_key, hide_index=True, width='stretch')

        st.caption("Markers indicate capital cities")



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
    st.caption("Most recent census used for each nation's population figure (see expander for assumptions).")

    st.markdown("---")
    render_map_panel()

    st.markdown("---")
    
    st.subheader("Notes")

    st.markdown(
        """
    - Where joint census tables report different census years (e.g. 2021 for the Republic of Ireland and 2022 for Northern Ireland), 
    the combined label **'2021/2022'** is recorded as **2022** throughout the dashboard. This is done solely for consistent ordering, 
    filtering, and presentation, and does not imply a harmonised census year.

    - GDP values shown in the Overview refer to **2023 only** and are converted to USD using average 2023 exchange rates 
    (GBP→USD: **1.244**; EUR→USD: **1.0817**) for presentation consistency.
    """
    )



main()
