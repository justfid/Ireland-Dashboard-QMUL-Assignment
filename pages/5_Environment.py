from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Environment | ROI + NI Dashboard",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌿 Environment")
st.write(
    "This page compares environmental indicators for the Republic of Ireland (ROI) and Northern Ireland (NI), "
    "including **CO₂ emissions**, **weather patterns** (planned: Open-Meteo), and **air quality** (planned: OpenAQ)."
)
st.caption("All values shown here are **dummy data** for development/testing and will be replaced with live API data.")

# Dummy data generation (replace with APIs later)

@st.cache_data(show_spinner=False)
def make_dummy_environment_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(2025)

    regions = ["Republic of Ireland", "Northern Ireland"]
    years = list(range(2005, 2025))

    # CO2 emissions (MtCO2e) and per-capita (tCO2e)
    co2_rows = []
    for r in regions:
        # ROI bigger absolute emissions; NI smaller.
        base_mt = 46.0 if r == "Republic of Ireland" else 18.0
        # gentle decline with some noise (policy + tech improvements)
        trend = np.linspace(0, -8.0 if r == "Republic of Ireland" else -4.5, len(years))
        noise = rng.normal(0, 0.7 if r == "Republic of Ireland" else 0.5, len(years))
        for y, mt in zip(years, base_mt + trend + noise):
            mt = float(max(0, mt))
            # per-capita proxy (ROI slightly higher in dummy)
            pc_base = 10.5 if r == "Republic of Ireland" else 8.2
            pc_trend = np.interp(y, [years[0], years[-1]], [0.0, -1.7 if r == "Republic of Ireland" else -1.2])
            pc_noise = float(rng.normal(0, 0.18))
            tpc = float(max(0, pc_base + pc_trend + pc_noise))
            co2_rows.append((y, r, mt, tpc))
    co2 = pd.DataFrame(co2_rows, columns=["Year", "Region", "CO₂ emissions (MtCO₂e)", "CO₂ per capita (tCO₂e)"])

    # Weather patterns: monthly temps & rainfall (dummy; planned Open-Meteo)
    months = pd.date_range("2024-01-01", "2024-12-01", freq="MS")
    weather_rows = []
    for r in regions:
        # NI slightly cooler, slightly wetter on average
        temp_offset = 0.0 if r == "Republic of Ireland" else -0.7
        rain_offset = 0.0 if r == "Republic of Ireland" else 8.0

        for dt in months:
            m = dt.month
            # seasonal sine wave for temperature
            temp = 9.5 + 6.5 * np.sin((m - 3) * (2 * np.pi / 12)) + temp_offset + rng.normal(0, 0.6)
            # rainfall: higher in winter months, lower in summer (roughly)
            rain = 75 + 25 * np.cos((m - 1) * (2 * np.pi / 12)) + rain_offset + rng.normal(0, 6.0)
            weather_rows.append((dt, r, float(temp), float(max(0, rain))))
    weather = pd.DataFrame(weather_rows, columns=["Month", "Region", "Avg temp (°C)", "Rainfall (mm)"])

    # Air quality: daily PM2.5 + NO2 (dummy; planned OpenAQ)
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="D")
    aq_rows = []
    for r in regions:
        # NI a touch higher in dummy
        pm_base = 9.5 if r == "Republic of Ireland" else 11.0
        no2_base = 18.0 if r == "Republic of Ireland" else 20.5

        for dt in dates:
            # weekday effect + noise
            weekday = dt.weekday()
            weekday_bump = 1.2 if weekday < 5 else -0.6

            pm25 = pm_base + weekday_bump + rng.normal(0, 2.0)
            no2 = no2_base + 1.6 * weekday_bump + rng.normal(0, 4.0)

            # occasional pollution spikes
            if rng.random() < 0.02:
                pm25 += rng.uniform(8, 18)
                no2 += rng.uniform(15, 35)

            aq_rows.append((dt, r, float(max(0, pm25)), float(max(0, no2))))
    air_quality = pd.DataFrame(aq_rows, columns=["Date", "Region", "PM2.5 (µg/m³)", "NO₂ (µg/m³)"])

    # Air quality categories snapshot for a composition chart
    # (good / moderate / poor) based on dummy PM2.5 thresholds
    def pm_band(v: float) -> str:
        if v < 10:
            return "Good"
        if v < 20:
            return "Moderate"
        return "Poor"

    band_df = air_quality.copy()
    band_df["PM2.5 band"] = band_df["PM2.5 (µg/m³)"].map(pm_band)
    aq_band = (
        band_df.groupby(["Region", "PM2.5 band"], as_index=False)
        .size()
        .rename(columns={"size": "Days"})
    )
    aq_band["Share (%)"] = aq_band.groupby("Region")["Days"].transform(lambda s: 100 * s / s.sum())

    return {
        "co2": co2,
        "weather": weather,
        "air_quality": air_quality,
        "aq_band": aq_band,
    }


data = make_dummy_environment_data()


# Controls

with st.sidebar:
    st.header("Filters")

    region_all = sorted(data["co2"]["Region"].unique().tolist())
    region_sel = st.multiselect("Regions", region_all, default=region_all)

    st.markdown("---")
    st.subheader("CO₂")
    co2_metric = st.radio(
        "Metric",
        ["CO₂ emissions (MtCO₂e)", "CO₂ per capita (tCO₂e)"],
        horizontal=False,
    )

    st.markdown("---")
    st.subheader("Weather (dummy — planned Open-Meteo)")
    weather_metric = st.radio("Weather metric", ["Avg temp (°C)", "Rainfall (mm)"], horizontal=False)

    st.markdown("---")
    st.subheader("Air quality (dummy — planned OpenAQ)")
    aq_metric = st.radio("Air quality metric", ["PM2.5 (µg/m³)", "NO₂ (µg/m³)"], horizontal=False)

    show_debug = st.checkbox("Show debug tables", value=False)


def only_regions(df: pd.DataFrame) -> pd.DataFrame:
    if "Region" in df.columns:
        return df[df["Region"].isin(region_sel)].copy()
    return df.copy()


# KPI snapshot row (latest year + latest day)
st.subheader("Snapshot")

co2_df = only_regions(data["co2"])
latest_year = int(co2_df["Year"].max())
latest_day = only_regions(data["air_quality"])["Date"].max()

k1, k2, k3 = st.columns(3)

#CO2 latest year average across selected regions
latest_co2 = co2_df[co2_df["Year"] == latest_year]
if not latest_co2.empty:
    #show ROI vs NI if both selected; otherwise show selected mean
    if len(region_sel) == 2:
        roi_val = float(latest_co2.loc[latest_co2["Region"] == "Republic of Ireland", co2_metric].iloc[0])
        ni_val = float(latest_co2.loc[latest_co2["Region"] == "Northern Ireland", co2_metric].iloc[0])
        k1.metric(f"{co2_metric} (ROI)", f"{roi_val:.2f}", f"Year {latest_year}")
        k2.metric(f"{co2_metric} (NI)", f"{ni_val:.2f}", f"Year {latest_year}")
        gap = roi_val - ni_val
        k3.metric("Gap (ROI − NI)", f"{gap:.2f}", f"Year {latest_year}")
    else:
        mean_val = float(latest_co2[co2_metric].mean())
        k1.metric(f"{co2_metric} (avg selected)", f"{mean_val:.2f}", f"Year {latest_year}")
        aq_latest = only_regions(data["air_quality"])
        if latest_day is not None and not aq_latest.empty:
            day_vals = aq_latest[aq_latest["Date"] == latest_day][aq_metric]
            k2.metric(f"{aq_metric} (avg selected)", f"{float(day_vals.mean()):.1f}", f"{latest_day.date()}")
        k3.metric("Selected regions", str(len(region_sel)))

st.divider()


# CO2 SECTION
st.header("🌍 CO₂ emissions")

c1, c2 = st.columns(2, gap="large")

with c1:
    fig_co2 = px.line(
        only_regions(data["co2"]),
        x="Year",
        y=co2_metric,
        color="Region",
        markers=True,
        title=f"{co2_metric} over time",
    )
    fig_co2.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_co2, use_container_width=True)

with c2:
    #Different chart type: bar snapshot for latest year
    snap = only_regions(data["co2"])
    snap = snap[snap["Year"] == latest_year]
    fig_co2_bar = px.bar(
        snap,
        x="Region",
        y=co2_metric,
        title=f"{co2_metric} — {latest_year} snapshot",
        text_auto=".2f",
    )
    fig_co2_bar.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_co2_bar, use_container_width=True)

st.divider()


# WEATHER SECTION (Open-Meteo later)

st.header("🌦️ Weather patterns (planned: Open-Meteo)")

w1, w2 = st.columns(2, gap="large")

with w1:
    weather_df = only_regions(data["weather"])
    fig_weather = px.line(
        weather_df,
        x="Month",
        y=weather_metric,
        color="Region",
        markers=True,
        title=f"{weather_metric} by month (2024)",
    )
    fig_weather.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_weather, use_container_width=True)

with w2:
    #Different chart type: heatmap of month vs region for temperatures/rainfall
    heat = weather_df.pivot_table(index="Region", columns="Month", values=weather_metric, aggfunc="mean")
    heat = heat.sort_index()
    fig_heat = px.imshow(
        heat,
        aspect="auto",
        title=f"Seasonality heatmap — {weather_metric} (2024)",
        labels=dict(x="Month", y="Region", color=weather_metric),
    )
    fig_heat.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_heat, use_container_width=True)

st.divider()


# AIR QUALITY SECTION (OpenAQ later)

st.header("🫁 Air quality (planned: OpenAQ)")

a1, a2 = st.columns(2, gap="large")

with a1:
    aq_df = only_regions(data["air_quality"])
    fig_aq = px.line(
        aq_df,
        x="Date",
        y=aq_metric,
        color="Region",
        title=f"{aq_metric} over time (daily)",
    )
    fig_aq.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_aq, use_container_width=True)

with a2:
    #composition chart: PM2.5 quality band shares
    band = only_regions(data["aq_band"])
    #if user filters to only NO2 metric we still show PM2.5 band composition (it’s clearly labelled)
    fig_band = px.pie(
        band,
        names="PM2.5 band",
        values="Share (%)",
        color="PM2.5 band",
        hole=0.55,
        title="PM2.5 air quality bands (share of days, dummy)",
    )
    fig_band.update_traces(textposition="inside", textinfo="percent+label")
    fig_band.update_layout(height=360, margin=dict(l=10, r=10, t=60, b=10), showlegend=False)
    st.plotly_chart(fig_band, use_container_width=True)

#optional: a simple “latest day” gauge for PM2.5 (variety)
if "PM2.5 (µg/m³)" in data["air_quality"].columns:
    aq_latest = only_regions(data["air_quality"])
    if not aq_latest.empty:
        d = aq_latest[aq_latest["Date"] == latest_day]
        if not d.empty:
            val = float(d["PM2.5 (µg/m³)"].mean())
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=val,
                title={"text": f"Avg PM2.5 (selected) — {latest_day.date()}"},
                gauge={"axis": {"range": [0, 50]}},
            ))
            gauge.update_layout(height=240, margin=dict(l=10, r=10, t=60, b=10))
            st.plotly_chart(gauge, use_container_width=True)

st.divider()

with st.expander("Notes & methodology (placeholder)"):
    st.markdown(
        """
- **Dummy data**: all figures are synthetic placeholders for layout/visual testing.
- **Planned APIs**:
  - **Open-Meteo** for weather (temperature, rainfall, wind, etc.).
  - **OpenAQ** for air quality (PM2.5, NO₂, etc.).
- **Comparability**:
  - Ensure API queries use consistent locations (e.g., capital city coordinates or population-weighted points).
  - Consider using multi-year averages for climate patterns and daily/weekly smoothing for air quality.
- **CO₂**:
  - When replacing, specify whether emissions are territorial vs consumption-based and keep that consistent for ROI vs NI.
"""
    )

if show_debug:
    st.subheader("Debug: underlying dummy data")
    st.write("CO₂"); st.dataframe(only_regions(data["co2"]), use_container_width=True, hide_index=True)
    st.write("Weather"); st.dataframe(only_regions(data["weather"]), use_container_width=True, hide_index=True)
    st.write("Air quality"); st.dataframe(only_regions(data["air_quality"]), use_container_width=True, hide_index=True)
    st.write("PM2.5 bands"); st.dataframe(only_regions(data["aq_band"]), use_container_width=True, hide_index=True)
