from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Society | ROI + NI Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏥 Society")
st.write(
    "This page compares social outcomes across the Republic of Ireland (ROI) and Northern Ireland (NI) "
    "using health, education, and housing indicators."
)
st.caption("All values shown here are **dummy data** for development/testing and will be replaced.")


# Dummy data (replace later)

@st.cache_data(show_spinner=False)
def make_dummy_society_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(123)

    years = list(range(2014, 2025))
    regions = ["Republic of Ireland", "Northern Ireland"]

    # HEALTH 
    le_rows = []
    for r in regions:
        base = 81.3 if r == "Republic of Ireland" else 80.3
        trend = np.linspace(0.0, 0.8 if r == "Republic of Ireland" else 0.6, len(years))
        # dip around 2020–2021 (indices 6 and 7 because 2014..2024 => 2020 index=6)
        covid_dip = np.zeros(len(years), dtype=float)
        if len(years) >= 8:
            covid_dip[6] = -0.5
            covid_dip[7] = -0.2
        noise = rng.normal(0, 0.08, len(years))
        for y, v in zip(years, base + trend + covid_dip + noise):
            le_rows.append((y, r, float(v)))
    life_expectancy = pd.DataFrame(le_rows, columns=["Year", "Region", "Life expectancy (years)"])

    srh_rows = []
    for r in regions:
        base = 83.0 if r == "Republic of Ireland" else 81.0
        trend = np.linspace(0.0, 1.2 if r == "Republic of Ireland" else 0.9, len(years))
        noise = rng.normal(0, 0.4, len(years))
        for y, v in zip(years, base + trend + noise):
            srh_rows.append((y, r, float(np.clip(v, 70, 95))))
    self_reported_health = pd.DataFrame(srh_rows, columns=["Year", "Region", "Good/Very good health (%)"])

    # EDUCATION
    ter_rows = []
    for r in regions:
        base = 42.0 if r == "Republic of Ireland" else 36.0
        trend = np.linspace(0.0, 7.0 if r == "Republic of Ireland" else 5.5, len(years))
        noise = rng.normal(0, 0.6, len(years))
        for y, v in zip(years, base + trend + noise):
            ter_rows.append((y, r, float(np.clip(v, 20, 70))))
    tertiary = pd.DataFrame(ter_rows, columns=["Year", "Region", "Tertiary attainment (%)"])

    esl_rows = []
    for r in regions:
        base = 8.5 if r == "Republic of Ireland" else 9.5
        trend = np.linspace(0.0, -2.5 if r == "Republic of Ireland" else -2.0, len(years))
        noise = rng.normal(0, 0.25, len(years))
        for y, v in zip(years, base + trend + noise):
            esl_rows.append((y, r, float(np.clip(v, 2, 20))))
    early_school_leavers = pd.DataFrame(esl_rows, columns=["Year", "Region", "Early school leavers (%)"])

    # HOUSING
    rent_rows = []
    for r in regions:
        base = 32.0 if r == "Republic of Ireland" else 28.0
        trend = np.linspace(0.0, 6.5 if r == "Republic of Ireland" else 3.5, len(years))
        noise = rng.normal(0, 0.6, len(years))
        for y, v in zip(years, base + trend + noise):
            rent_rows.append((y, r, float(np.clip(v, 10, 60))))
    rent_burden = pd.DataFrame(rent_rows, columns=["Year", "Region", "Rent as % of income"])

    comp_rows = []
    for r in regions:
        base = 18500 if r == "Republic of Ireland" else 7000
        shape = np.array([0, -1200, -800, 200, 1200, 2000, 2800, 1800, 1400, 2200, 2600], dtype=float)
        shape = np.interp(np.linspace(0, len(shape) - 1, len(years)), np.arange(len(shape)), shape)
        noise = rng.normal(0, 550, len(years))
        for y, v in zip(years, base + shape + noise):
            comp_rows.append((y, r, int(max(0, v))))
    completions = pd.DataFrame(comp_rows, columns=["Year", "Region", "Housing completions"])

    # CRIME 
    crime_rows = []
    for r in regions:
        # Recorded crimes per 1,000 population (dummy)
        base = 60 if r == "Republic of Ireland" else 75
        trend = np.linspace(0.0, -8.0 if r == "Republic of Ireland" else -6.0, len(years))
        noise = rng.normal(0, 2.0, len(years))
        for y, v in zip(years, base + trend + noise):
            crime_rows.append((y, r, float(max(10, v))))

    crime_rate = pd.DataFrame(
        crime_rows,
        columns=["Year", "Region", "Recorded crime rate (per 1,000)"],
    )


    tenure = pd.DataFrame({
        "Tenure": ["Owner-occupied", "Private rent", "Social rent", "Other"],
        "Republic of Ireland": [67, 23, 8, 2],
        "Northern Ireland": [66, 16, 16, 2],
    }).melt(id_vars="Tenure", var_name="Region", value_name="Share (%)")

    return {
        "life_expectancy": life_expectancy,
        "self_reported_health": self_reported_health,
        "tertiary": tertiary,
        "early_school_leavers": early_school_leavers,
        "rent_burden": rent_burden,
        "completions": completions,
        "tenure": tenure,
        "crime_rate": crime_rate,
    }


data = make_dummy_society_data()

# Filters
years_all = sorted(data["life_expectancy"]["Year"].unique().tolist())
year_min, year_max = int(min(years_all)), int(max(years_all))

regions_all = sorted(data["life_expectancy"]["Region"].unique().tolist())

with st.sidebar:
    st.header("Filters")
    yr = st.slider("Year range", year_min, year_max, (year_min, year_max), step=1)
    region_sel = st.multiselect("Regions", regions_all, default=regions_all)
    st.markdown("---")
    show_debug = st.checkbox("Show debug tables", value=False)

def f(df: pd.DataFrame) -> pd.DataFrame:
    if "Year" in df.columns and "Region" in df.columns:
        return df[(df["Year"] >= yr[0]) & (df["Year"] <= yr[1]) & (df["Region"].isin(region_sel))].copy()
    return df[df["Region"].isin(region_sel)].copy() if "Region" in df.columns else df.copy()

latest_year = yr[1]

# KPI snapshot row
st.subheader("Snapshot (latest year in range)")

def latest(df: pd.DataFrame, value_col: str, region: str) -> float | None:
    sub = df[(df["Region"] == region) & (df["Year"] == latest_year)]
    if sub.empty:
        return None
    return float(sub[value_col].iloc[0])

r_show = region_sel[:2] if len(region_sel) >= 2 else region_sel

k1, k2, k3, k4 = st.columns(4)

if len(r_show) >= 1:
    rA = r_show[0]
    v = latest(data["life_expectancy"], "Life expectancy (years)", rA)
    k1.metric(f"Life expectancy ({rA})", f"{v:.1f}" if v is not None else "—", f"Year {latest_year}")

if len(r_show) >= 2:
    rB = r_show[1]
    v = latest(data["tertiary"], "Tertiary attainment (%)", rB)
    k2.metric(f"Tertiary attainment ({rB})", f"{v:.1f}%" if v is not None else "—", f"Year {latest_year}")

comp_f = f(data["completions"])
total_comp = int(comp_f[comp_f["Year"] == latest_year]["Housing completions"].sum())
k3.metric("Housing completions (selected)", f"{total_comp:,}", f"Year {latest_year}")

roi_val = latest(data["rent_burden"], "Rent as % of income", "Republic of Ireland") if "Republic of Ireland" in region_sel else None
ni_val = latest(data["rent_burden"], "Rent as % of income", "Northern Ireland") if "Northern Ireland" in region_sel else None
gap = (roi_val - ni_val) if (roi_val is not None and ni_val is not None) else None
k4.metric("Rent burden gap (ROI − NI)", f"{gap:.1f} pp" if gap is not None else "—", f"Year {latest_year}")

st.divider()


# HEALTH

st.header("🏥 Health")

h1, h2 = st.columns(2, gap="large")

with h1:
    le_f = f(data["life_expectancy"])
    fig_le = px.line(
        le_f,
        x="Year",
        y="Life expectancy (years)",
        color="Region",
        markers=True,
        title="Life Expectancy at Birth",
    )
    fig_le.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_le, use_container_width=True)

with h2:
    srh_f = f(data["self_reported_health"])
    snap = srh_f[srh_f["Year"] == latest_year]
    fig_srh = px.bar(
        snap,
        x="Region",
        y="Good/Very good health (%)",
        title=f"Self-reported Good/Very Good Health (%) — {latest_year}",
        text_auto=".1f",
    )
    fig_srh.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_srh, use_container_width=True)

if "Republic of Ireland" in region_sel and "Northern Ireland" in region_sel:
    roi_le = latest(data["life_expectancy"], "Life expectancy (years)", "Republic of Ireland")
    ni_le = latest(data["life_expectancy"], "Life expectancy (years)", "Northern Ireland")
    if roi_le is not None and ni_le is not None:
        diff = roi_le - ni_le
        gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=diff,
            delta={"reference": 0},
            title={"text": "Life expectancy gap (ROI − NI)"},
            gauge={"axis": {"range": [-2, 2]}},
        ))
        gauge.update_layout(height=240, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(gauge, use_container_width=True)

st.divider()


# EDUCATION

st.header("🎓 Education")

e1, e2 = st.columns(2, gap="large")

with e1:
    ter_f = f(data["tertiary"])
    fig_ter = px.area(
        ter_f,
        x="Year",
        y="Tertiary attainment (%)",
        color="Region",
        title="Tertiary Attainment Over Time (%)",
    )
    fig_ter.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_ter, use_container_width=True)

with e2:
    esl_f = f(data["early_school_leavers"])
    fig_esl = px.line(
        esl_f,
        x="Year",
        y="Early school leavers (%)",
        color="Region",
        markers=True,
        title="Early School Leavers Over Time (%)",
    )
    fig_esl.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_esl, use_container_width=True)

st.divider()


# HOUSING
st.header("🏠 Housing")

ho1, ho2 = st.columns(2, gap="large")

with ho1:
    rent_f = f(data["rent_burden"])
    fig_rent = px.line(
        rent_f,
        x="Year",
        y="Rent as % of income",
        color="Region",
        markers=True,
        title="Rent Burden (Rent as % of Income)",
        labels={"Rent as % of income": "Rent as % of income (%)"},
    )
    fig_rent.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_rent, use_container_width=True)

with ho2:
    comp_f = f(data["completions"])
    fig_comp = px.bar(
        comp_f,
        x="Year",
        y="Housing completions",
        color="Region",
        barmode="group",
        title="Housing Completions Over Time (Supply Proxy)",
    )
    fig_comp.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_comp, use_container_width=True)

tenure_df = data["tenure"][data["tenure"]["Region"].isin(region_sel)].copy()
fig_tenure = px.pie(
    tenure_df,
    names="Tenure",
    values="Share (%)",
    hole=0.55,
    title="Housing Tenure Split (Composition Snapshot)",
)
fig_tenure.update_traces(textposition="inside", textinfo="percent+label")
fig_tenure.update_layout(height=420, margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
st.plotly_chart(fig_tenure, use_container_width=True)

st.divider()

st.header("🚔 Crime")

c1, c2 = st.columns(2, gap="large")

with c1:
    crime_f = f(data["crime_rate"])
    fig_crime = px.line(
        crime_f,
        x="Year",
        y="Recorded crime rate (per 1,000)",
        color="Region",
        markers=True,
        title="Recorded Crime Rate per 1,000 Population",
    )
    fig_crime.update_layout(height=360)
    st.plotly_chart(fig_crime, use_container_width=True)

with c2:
    snap = crime_f[crime_f["Year"] == latest_year]
    fig_crime_bar = px.bar(
        snap,
        x="Region",
        y="Recorded crime rate (per 1,000)",
        text_auto=".1f",
        title=f"Recorded Crime Rate — {latest_year}",
    )
    fig_crime_bar.update_layout(height=360)
    st.plotly_chart(fig_crime_bar, use_container_width=True)


st.divider()


with st.expander("Notes & methodology (placeholder)"):
    st.markdown(
        """
- **Dummy data**: all figures on this page are synthetic placeholders.
- **Comparability**: ROI and NI may use different definitions/collection methods. When real data is integrated, document
  definitions and any harmonisation decisions here.
- Planned real sources:
  - Health: official health statistics agencies / ONS / NISRA / CSO
  - Education: attainment and early leaver metrics from CSO / NISRA / DfE NI
  - Housing: rent + income series and completions (CSO completions for ROI + NI equivalent)
"""
    )

if show_debug:
    st.subheader("Debug: filtered data samples")
    st.write("Life expectancy"); st.dataframe(f(data["life_expectancy"]), use_container_width=True, hide_index=True)
    st.write("Self-reported health"); st.dataframe(f(data["self_reported_health"]), use_container_width=True, hide_index=True)
    st.write("Tertiary attainment"); st.dataframe(f(data["tertiary"]), use_container_width=True, hide_index=True)
    st.write("Early school leavers"); st.dataframe(f(data["early_school_leavers"]), use_container_width=True, hide_index=True)
    st.write("Rent burden"); st.dataframe(f(data["rent_burden"]), use_container_width=True, hide_index=True)
    st.write("Completions"); st.dataframe(f(data["completions"]), use_container_width=True, hide_index=True)
    st.write("Tenure"); st.dataframe(data["tenure"], use_container_width=True, hide_index=True)
