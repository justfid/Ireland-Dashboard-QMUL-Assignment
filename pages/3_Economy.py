import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(
    page_title="Economy | ROI + NI Dashboard",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💷 Economy")
st.write(
    "This section compares economic performance between the Republic of Ireland (ROI) "
    "and Northern Ireland (NI) using headline indicators such as GDP, labour market outcomes, "
    "and sectoral composition."
)

st.caption("All values shown are **dummy data** for development purposes and will be replaced.")


# Dummy data

years = list(range(2015, 2024))
regions = ["Republic of Ireland", "Northern Ireland"]

# GDP per capita (USD)
gdp_pc = pd.DataFrame({
    "Year": years * 2,
    "Region": ["Republic of Ireland"] * len(years) + ["Northern Ireland"] * len(years),
    "GDP per capita (USD)": (
        np.linspace(55_000, 85_000, len(years)).tolist()
        + np.linspace(35_000, 45_000, len(years)).tolist()
    ),
})

# Employment / unemployment rate
labour = pd.DataFrame({
    "Year": years * 2,
    "Region": ["Republic of Ireland"] * len(years) + ["Northern Ireland"] * len(years),
    "Unemployment rate (%)": (
        np.linspace(10, 4, len(years)).tolist()
        + np.linspace(8, 5, len(years)).tolist()
    ),
})

# GDP per worker (USD)
productivity = pd.DataFrame({
    "Region": regions,
    "GDP per worker (USD)": [120_000, 85_000],
})

# Sectoral breakdown (% of employment)
sectors = pd.DataFrame({
    "Sector": ["Agriculture", "Industry", "Construction", "Services"],
    "Republic of Ireland": [5, 25, 7, 63],
    "Northern Ireland": [4, 20, 8, 68],
}).melt(id_vars="Sector", var_name="Region", value_name="Share (%)")

# Row 1 — GDP

c1, c2 = st.columns(2)

with c1:
    fig_gdp = px.line(
        gdp_pc,
        x="Year",
        y="GDP per capita (USD)",
        color="Region",
        title="GDP per Capita (USD)",
        markers=True,
    )
    fig_gdp.update_layout(height=350)
    st.plotly_chart(fig_gdp, use_container_width=True)

with c2:
    fig_prod = px.bar(
        productivity,
        x="Region",
        y="GDP per worker (USD)",
        title="GDP per Worker (Productivity Proxy)",
        text_auto=".2s",
    )
    fig_prod.update_layout(height=350)
    st.plotly_chart(fig_prod, use_container_width=True)


# Row 2 — Labour market

fig_labour = px.line(
    labour,
    x="Year",
    y="Unemployment rate (%)",
    color="Region",
    title="Unemployment Rate Over Time",
    markers=True,
)
fig_labour.update_layout(height=350)
st.plotly_chart(fig_labour, use_container_width=True)


# Row 3 — Sectoral breakdown

fig_sector = px.bar(
    sectors,
    x="Region",
    y="Share (%)",
    color="Sector",
    title="Employment by Sector",
)
fig_sector.update_layout(
    barmode="stack",
    height=400,
)
st.plotly_chart(fig_sector, use_container_width=True)


# Notes / assumptions

with st.expander("Notes & assumptions"):
    st.markdown(
        """
- GDP values are expressed in USD for cross-region comparability.
- GDP per worker is used as a proxy for labour productivity.
- Sectoral shares represent proportions of total employment.
- All figures are placeholder values for development and visual testing.
"""
    )
