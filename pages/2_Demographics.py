from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.common import ensure_cols, ALL_REGIONS

pyramid_year = 2022

#page config
st.set_page_config(
    page_title="Demographics",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded",
)

CLEAN_DIR = Path("data/cleaned/demographics")

POP_TIME_PATH = CLEAN_DIR / "population_over_time.csv"
POP_DIST_PATH = CLEAN_DIR / "population_distribution.csv"
MEDIAN_AGE_PATH = CLEAN_DIR / "median_age_over_time.csv"
DEP_RATIO_PATH = CLEAN_DIR / "dependency_ratio_over_time.csv"

REGIONS = ALL_REGIONS


#loaders


@st.cache_data(show_spinner=False)
def load_population_over_time(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Population"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Population"] = pd.to_numeric(df["Population"], errors="coerce").astype(int)
    df["Region"] = df["Region"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_population_distribution(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Sex", "Age band", "Population"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Population"] = pd.to_numeric(df["Population"], errors="coerce").astype(int)
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Sex"] = df["Sex"].astype(str).str.strip()
    df["Age band"] = df["Age band"].astype(str).str.strip()

    df = df[
        (df["Region"].isin(REGIONS))
        & (df["Sex"].isin(["Male", "Female"]))
    ]

    return df.sort_values(["Region", "Year", "Sex", "Age band"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_median_age(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Median age"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Median age"] = pd.to_numeric(df["Median age"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_dependency_ratio(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Dependency ratio"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Dependency ratio"] = pd.to_numeric(df["Dependency ratio"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year"]).reset_index(drop=True)


#helper functions
def filter_years(df: pd.DataFrame, year_range: Tuple[int, int]) -> pd.DataFrame:
    return df[(df["Year"] >= year_range[0]) & (df["Year"] <= year_range[1])]


def make_growth_between_census(pop: pd.DataFrame) -> pd.DataFrame:
    df = pop.sort_values(["Region", "Year"]).copy()
    df["Prev Year"] = df.groupby("Region")["Year"].shift(1)
    df["Prev Pop"] = df.groupby("Region")["Population"].shift(1)

    df = df.dropna()
    df["Interval"] = (
        df["Prev Year"].astype(int).astype(str)
        + "→"
        + df["Year"].astype(int).astype(str)
    )
    df["Change"] = df["Population"] - df["Prev Pop"]
    df["% Change"] = df["Change"] / df["Prev Pop"] * 100
    return df


def make_population_pyramid(
    dist: pd.DataFrame, region: str, year: int, mode: str
) -> go.Figure:
    sub = dist[(dist["Region"] == region) & (dist["Year"] == year)].copy()

    if sub.empty:
        fig = go.Figure()
        fig.update_layout(
            title=f"Population pyramid — {region} ({year})",
            annotations=[dict(text="No data available", x=0.5, y=0.5, showarrow=False)],
        )
        return fig

    if mode == "Combined (both)":
        combined = sub.groupby("Age band", as_index=False)["Population"].sum()
        fig = px.bar(
            combined,
            x="Population",
            y="Age band",
            orientation="h",
            title=f"Population pyramid — {region} ({year}) (combined)",
        )
        fig.update_xaxes(tickformat="~s")
        fig.update_layout(height=520)
        return fig

    sub["Value"] = sub["Population"].astype(float)
    sub.loc[sub["Sex"] == "Male", "Value"] *= -1

    fig = px.bar(
        sub,
        x="Value",
        y="Age band",
        color="Sex",
        orientation="h",
        title=f"Population pyramid — {region} ({year})",
        labels={"Value": "Population (mirrored)", "Age band": "Age band"},
    )
    fig.update_xaxes(tickformat="~s")
    fig.update_layout(height=520)
    return fig


#load data
pop_time = load_population_over_time(POP_TIME_PATH)
pop_dist = load_population_distribution(POP_DIST_PATH)
median_age = load_median_age(MEDIAN_AGE_PATH)
dep_ratio = load_dependency_ratio(DEP_RATIO_PATH)


#sidebar stuff
with st.sidebar:
    st.header("Filters")

    regions_trend = st.multiselect(
        "Regions (trend charts)",
        REGIONS,
        default=REGIONS,
    )

    year_min, year_max = int(pop_time["Year"].min()), int(pop_time["Year"].max())
    year_range: Tuple[int, int] = st.slider(
        "Census year range",
        year_min,
        year_max,
        (year_min, year_max),
    )

    st.markdown("---")
    st.subheader("Population structure")

    pyramid_region = st.radio("Region", REGIONS, horizontal=True)
    pyramid_mode = st.radio(
        "Pyramid display",
        ["Split by sex", "Combined (both)"],
        horizontal=True,
    )

    available_years = sorted(
        pop_dist.loc[pop_dist["Region"] == pyramid_region, "Year"].unique()
    )

#page stuff
st.title("👥 Demographics")
st.write(
    "This section examines population size, structure, and ageing using census data from the Republic of Ireland "
    "and Northern Ireland. All indicators are derived from official census publications and prioritise comparability "
    "across jurisdictions."
)
st.caption(
    "All charts use census observations only. Growth and trends are measured between consecutive censuses."
)
st.divider()


#snapshot
st.header("Population")
latest_year = year_range[1]
snap = filter_years(pop_time, year_range)
snap = snap[(snap["Year"] == latest_year) & (snap["Region"].isin(regions_trend))]

cols = st.columns(3)
for col, region in zip(cols, REGIONS):
    if region in regions_trend:
        v = snap.loc[snap["Region"] == region, "Population"]
        if not v.empty:
            col.metric(f"Population — {region}", f"{int(v.iloc[0]):,}")
            col.caption(f"Census {latest_year}")

st.divider()


#population over time
st.subheader("Population over time (census years)")
pop_f = filter_years(pop_time, year_range)
pop_f = pop_f[pop_f["Region"].isin(regions_trend)]

fig = px.line(
    pop_f,
    x="Year",
    y="Population",
    color="Region",
    markers=True,
    category_orders={"Region": REGIONS},
)
fig.update_yaxes(tickformat="~s")
st.plotly_chart(fig, width="stretch")

growth = make_growth_between_census(pop_f)
metric_mode = st.radio(
    "Growth metric",
    ["% change", "Absolute change"],
    horizontal=True,
)

y_col = "% Change" if metric_mode == "% change" else "Change"
fig_g = px.bar(
    growth,
    x="Interval",
    y=y_col,
    color="Region",
    barmode="group",
    category_orders={"Region": REGIONS},
)
st.plotly_chart(fig_g, width="stretch")

st.caption(
    "Note: growth is measured between consecutive census observations (no annual interpolation)."
)

st.divider()


#population structure
st.header("Population structure (age / sex)")
fig_pyr = make_population_pyramid(
    pop_dist, pyramid_region, pyramid_year, pyramid_mode
)
st.plotly_chart(fig_pyr, width="stretch")

st.caption(
    "Sex-specific population structure is shown via the pyramid only to avoid overloading summary trend charts."
)

st.divider()


#median age & dependency ratio
st.header("Population ageing indicators")

col_left, col_right = st.columns(2)

#median age
with col_left:
    st.subheader("Median age over time")

    ma = filter_years(median_age, year_range)
    ma = ma[ma["Region"].isin(regions_trend)]

    fig_ma = px.line(
        ma,
        x="Year",
        y="Median age",
        color="Region",
        markers=True,
        category_orders={"Region": REGIONS},
    )
    st.plotly_chart(fig_ma, width="stretch")

    st.caption(
        "All-Island median age values are population-weighted estimates derived from ROI and NI "
        "(not exact pooled medians)."
    )

#dependency ratio
with col_right:
    st.subheader("Dependency ratio over time")

    dr = filter_years(dep_ratio, year_range)
    dr = dr[dr["Region"].isin(regions_trend)]

    fig_dr = px.line(
        dr,
        x="Year",
        y="Dependency ratio",
        color="Region",
        markers=True,
        category_orders={"Region": REGIONS},
    )
    st.plotly_chart(fig_dr, width="stretch")

    st.caption(
        "All-Island dependency ratio values are population-weighted estimates derived from ROI and NI "
        "(not exact pooled ratios). "
        "The dataset includes an early observation labelled '1936/1937', recorded here as 1936 for consistency."
    )
