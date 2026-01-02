from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Capital Cities | ROI + NI Dashboard",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📍 Capital Cities")
st.write(
    "This page compares the capital cities of the Republic of Ireland and Northern Ireland — "
    "**Dublin** and **Belfast** — across demographic, economic, social, and environmental indicators."
)
st.caption("All values shown here are **dummy data** for development/testing and will be replaced.")


# Dummy data

@st.cache_data(show_spinner=False)
def make_dummy_capital_data():
    years = list(range(2015, 2025))
    cities = ["Dublin", "Belfast"]
    rng = np.random.default_rng(77)

    #population (city proper / metro proxy)
    pop = pd.DataFrame({
        "Year": years * 2,
        "City": ["Dublin"] * len(years) + ["Belfast"] * len(years),
        "Population": (
            np.linspace(1.35e6, 1.55e6, len(years)).astype(int).tolist()
            + np.linspace(0.60e6, 0.67e6, len(years)).astype(int).tolist()
        ),
    })

    #median disposable income (USD, dummy)
    income = pd.DataFrame({
        "City": cities,
        "Median income (USD)": [42000, 34000],
    })

    #unemployment rate (%)
    unemp = pd.DataFrame({
        "Year": years * 2,
        "City": ["Dublin"] * len(years) + ["Belfast"] * len(years),
        "Unemployment rate (%)": (
            np.linspace(9.5, 4.0, len(years)).tolist()
            + np.linspace(8.5, 5.2, len(years)).tolist()
        ),
    })

    #rent burden (% of income)
    rent = pd.DataFrame({
        "Year": years * 2,
        "City": ["Dublin"] * len(years) + ["Belfast"] * len(years),
        "Rent as % of income": (
            np.linspace(35, 45, len(years)).tolist()
            + np.linspace(28, 33, len(years)).tolist()
        ),
    })

    #average annual PM2.5 (µg/m³)
    air = pd.DataFrame({
        "Year": years * 2,
        "City": ["Dublin"] * len(years) + ["Belfast"] * len(years),
        "PM2.5 (µg/m³)": (
            np.linspace(10.5, 8.5, len(years)).tolist()
            + np.linspace(12.0, 9.5, len(years)).tolist()
        ),
    })

    #weather snapshot (annual averages)
    weather = pd.DataFrame({
        "City": cities,
        "Avg temp (°C)": [10.1, 9.3],
        "Annual rainfall (mm)": [760, 910],
    })

    return pop, income, unemp, rent, air, weather


pop, income, unemp, rent, air, weather = make_dummy_capital_data()


# Controls

with st.sidebar:
    st.header("Filters")
    year_min, year_max = int(pop["Year"].min()), int(pop["Year"].max())
    year_range = st.slider("Year range", year_min, year_max, (year_min, year_max))
    city_sel = st.multiselect(
        "Cities",
        options=sorted(pop["City"].unique()),
        default=sorted(pop["City"].unique()),
    )
    show_debug = st.checkbox("Show debug tables", value=False)


def f(df: pd.DataFrame, city_col: str = "City") -> pd.DataFrame:
    if "Year" in df.columns:
        return df[
            (df["Year"] >= year_range[0]) &
            (df["Year"] <= year_range[1]) &
            (df[city_col].isin(city_sel))
        ].copy()
    return df[df[city_col].isin(city_sel)].copy()


latest_year = year_range[1]

# Snapshot KPIs

st.subheader("Snapshot (latest year in range)")

k1, k2, k3, k4 = st.columns(4)

def latest(df, col, city):
    sub = df[(df["City"] == city) & (df["Year"] == latest_year)]
    return float(sub[col].iloc[0]) if not sub.empty else None

if "Dublin" in city_sel:
    k1.metric(
        "Population (Dublin)",
        f"{latest(pop, 'Population', 'Dublin')/1e6:.2f}M",
        f"Year {latest_year}",
    )

if "Belfast" in city_sel:
    k2.metric(
        "Population (Belfast)",
        f"{latest(pop, 'Population', 'Belfast')/1e6:.2f}M",
        f"Year {latest_year}",
    )

k3.metric(
    "Median income (Dublin)",
    f"${income.loc[income['City']=='Dublin','Median income (USD)'].iloc[0]:,.0f}"
)

k4.metric(
    "Median income (Belfast)",
    f"${income.loc[income['City']=='Belfast','Median income (USD)'].iloc[0]:,.0f}"
)

st.divider()

# Population & labour

c1, c2 = st.columns(2, gap="large")

with c1:
    fig_pop = px.line(
        f(pop),
        x="Year",
        y="Population",
        color="City",
        markers=True,
        title="Population growth",
    )
    fig_pop.update_layout(height=360)
    st.plotly_chart(fig_pop, use_container_width=True)

with c2:
    fig_unemp = px.line(
        f(unemp),
        x="Year",
        y="Unemployment rate (%)",
        color="City",
        markers=True,
        title="Unemployment rate",
    )
    fig_unemp.update_layout(height=360)
    st.plotly_chart(fig_unemp, use_container_width=True)

st.divider()

# Housing & cost of living

c3, c4 = st.columns(2, gap="large")

with c3:
    fig_rent = px.line(
        f(rent),
        x="Year",
        y="Rent as % of income",
        color="City",
        markers=True,
        title="Rent burden (rent as % of income)",
    )
    fig_rent.update_layout(height=360)
    st.plotly_chart(fig_rent, use_container_width=True)

with c4:
    fig_income = px.bar(
        income[income["City"].isin(city_sel)],
        x="City",
        y="Median income (USD)",
        text_auto=",.0f",
        title="Median disposable income",
    )
    fig_income.update_layout(height=360)
    st.plotly_chart(fig_income, use_container_width=True)

st.divider()

# Environment (city-level)
c5, c6 = st.columns(2, gap="large")

with c5:
    fig_air = px.line(
        f(air),
        x="Year",
        y="PM2.5 (µg/m³)",
        color="City",
        markers=True,
        title="Air quality (PM2.5)",
    )
    fig_air.update_layout(height=360)
    st.plotly_chart(fig_air, use_container_width=True)

with c6:
    fig_weather = px.bar(
        weather[weather["City"].isin(city_sel)],
        x="City",
        y=["Avg temp (°C)", "Annual rainfall (mm)"],
        barmode="group",
        title="Average weather conditions",
    )
    fig_weather.update_layout(height=360)
    st.plotly_chart(fig_weather, use_container_width=True)

st.divider()


# Notes
with st.expander("Notes & methodology (placeholder)"):
    st.markdown(
        """
- **Dummy data**: all figures are synthetic placeholders.
- **City definitions**: values represent a city/metro proxy rather than administrative boundaries.
- **Planned data sources**:
  - Population & labour: CSO (Dublin), NISRA / ONS (Belfast)
  - Housing: rental statistics and income surveys
  - Environment: Open-Meteo (weather), OpenAQ (air quality)
- **Comparability**: capital cities differ structurally; results should be interpreted comparatively, not causally.
"""
    )

if show_debug:
    st.subheader("Debug tables")
    st.dataframe(f(pop), use_container_width=True, hide_index=True)
    st.dataframe(f(unemp), use_container_width=True, hide_index=True)
    st.dataframe(f(rent), use_container_width=True, hide_index=True)
    st.dataframe(f(air), use_container_width=True, hide_index=True)
