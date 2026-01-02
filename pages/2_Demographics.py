from __future__ import annotations
import streamlit as st
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Demographics", page_icon="👥", layout="wide")


#cleaning utilities TODO move to own file (NI specific)

TITLE_EXCEPTIONS = {"and", "or", "the", "of", "in", "on", "at", "to", "for", "a", "an"}

def title_case_place(name: str) -> str:
    """
    Title-case place names but keep small words lowercase (unless first word).
    Also normalises whitespace.
    """
    if not isinstance(name, str) or not name.strip():
        return name
    name = re.sub(r"\s+", " ", name.strip().lower())
    parts = name.split(" ")
    out = []
    for i, w in enumerate(parts):
        if i > 0 and w in TITLE_EXCEPTIONS:
            out.append(w)
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)

def normalise_ni_places(name: str) -> str:
    """
    NI naming requirements:
    - Clean to Title Case
    - Change to 'Derry/Londonderry' (covers common variants)
    """
    if not isinstance(name, str):
        return name

    raw = name.strip().lower()
    #common variants -> required combined label
    if raw in {"derry", "londonderry", "derry/londonderry", "london-derry"}:
        return "Derry/Londonderry"

    return title_case_place(name)

def apply_place_cleaning(df: pd.DataFrame, col: str = "area") -> pd.DataFrame:
    df = df.copy()
    if col in df.columns:
        df[col] = df[col].astype(str).map(normalise_ni_places)
    return df

#Dummy data for now

@dataclass
class SyntheticConfig:
    years: List[int] = None
    areas: List[str] = None

def make_synthetic_data(cfg: Optional[SyntheticConfig] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      pop_pyramid_df: area, year, age_band, sex, population
      pop_time_df: area, year, population_total
      religion_df: area, year, religion, share (0-1)
      identity_df: area, year, identity, share (0-1)  # republican/nationalist vs unionist vs other
    """
    if cfg is None:
        cfg = SyntheticConfig(
            years=list(range(2011, 2025)),
            areas=[
                "Belfast",
                "Derry",                 # will be cleaned to Derry/Londonderry
                "Newry and Mourne",
                "Lisburn",
                "Antrim and Newtownabbey",
            ],
        )

    rng = np.random.default_rng(42)

    years = cfg.years
    areas = cfg.areas

    #population totals over time 
    base = {
        "Belfast": 340_000,
        "Derry": 110_000,
        "Newry and Mourne": 180_000,
        "Lisburn": 150_000,
        "Antrim and Newtownabbey": 150_000,
    }
    pop_time_rows = []
    for a in areas:
        b = base.get(a, 120_000)
        growth = rng.normal(loc=0.004, scale=0.003, size=len(years))  # ~0.4% avg
        pop = b
        for y, g in zip(years, growth):
            pop = max(50_000, int(pop * (1 + g)))
            pop_time_rows.append((a, y, pop))
    pop_time_df = pd.DataFrame(pop_time_rows, columns=["area", "year", "population_total"])

    #Population pyramid (sex split + age bands)
    age_bands = ["0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39",
                 "40-44","45-49","50-54","55-59","60-64","65-69","70-74","75-79","80+"]

    pyramid_rows = []
    for a in areas:
        for y in years:
            total = int(pop_time_df.loc[(pop_time_df.area == a) & (pop_time_df.year == y), "population_total"].iloc[0])
            #age distribution: a gently peaky working-age shape
            weights = np.array([0.055,0.055,0.055,0.058,0.070,0.075,0.072,0.067,
                                0.062,0.060,0.058,0.055,0.048,0.040,0.030,0.020,0.020], dtype=float)
            weights = weights / weights.sum()
            age_counts = rng.multinomial(total, weights)

            #sex split varies slightly by age band (older -> more female)
            for band, count in zip(age_bands, age_counts):
                female_share = 0.49 + (0.06 if band in {"70-74","75-79","80+"} else 0.0) + rng.normal(0, 0.005)
                female_share = float(np.clip(female_share, 0.45, 0.60))
                f = int(round(count * female_share))
                m = int(count - f)
                pyramid_rows += [
                    (a, y, band, "Male", m),
                    (a, y, band, "Female", f),
                ]

    pop_pyramid_df = pd.DataFrame(pyramid_rows, columns=["area", "year", "age_band", "sex", "population"])

    #Religion split
    religions = ["Catholic", "Protestant & Other Christian", "Other Religion", "No Religion", "Not Stated"]
    religion_rows = []
    for a in areas:
        for y in years:
            #drift slowly over time to look realistic
            t = (y - years[0]) / max(1, (years[-1] - years[0]))
            catholic = 0.42 + 0.05 * t + rng.normal(0, 0.01)
            protestant = 0.38 - 0.06 * t + rng.normal(0, 0.01)
            other_rel = 0.03 + 0.02 * t + rng.normal(0, 0.003)
            none = 0.12 + 0.03 * t + rng.normal(0, 0.008)
            not_stated = 1.0 - (catholic + protestant + other_rel + none)
            vec = np.array([catholic, protestant, other_rel, none, not_stated], dtype=float)
            vec = np.clip(vec, 0.01, None)
            vec = vec / vec.sum()
            for r, s in zip(religions, vec):
                religion_rows.append((a, y, r, float(s)))
    religion_df = pd.DataFrame(religion_rows, columns=["area", "year", "religion", "share"])

    #NI republican vs unionist split (stacked bar later)
    identities = ["Nationalist/Republican", "Unionist/Loyalist", "Neither/Other"]
    identity_rows = []
    for a in areas:
        for y in years:
            t = (y - years[0]) / max(1, (years[-1] - years[0]))
            nat = 0.40 + 0.03 * t + rng.normal(0, 0.01)
            uni = 0.42 - 0.04 * t + rng.normal(0, 0.01)
            neither = 1.0 - (nat + uni)
            vec = np.array([nat, uni, neither], dtype=float)
            vec = np.clip(vec, 0.02, None)
            vec = vec / vec.sum()
            for i, s in zip(identities, vec):
                identity_rows.append((a, y, i, float(s)))
    identity_df = pd.DataFrame(identity_rows, columns=["area", "year", "identity", "share"])

    #Apply NI place cleaning requirements
    pop_time_df = apply_place_cleaning(pop_time_df, "area")
    pop_pyramid_df = apply_place_cleaning(pop_pyramid_df, "area")
    religion_df = apply_place_cleaning(religion_df, "area")
    identity_df = apply_place_cleaning(identity_df, "area")

    return pop_pyramid_df, pop_time_df, religion_df, identity_df


@st.cache_data(show_spinner=False)
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Replace this with real dataset loaders later (CSV/API/DB).
    Keep schema the same to avoid rewriting charts.
    """
    return make_synthetic_data()


# Metrics & calculations
def dependency_ratio(pyramid: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Age dependency ratio:
      - Youth dependency = (0-14) / (15-64) * 100
      - Old-age dependency = (65+) / (15-64) * 100
      - Total dependency = (0-14 + 65+) / (15-64) * 100
    """
    #Map age band to approximate group
    youth = {"0-4","5-9","10-14"}
    working = {"15-19","20-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64"}
    old = {"65-69","70-74","75-79","80+"}

    grouped = pyramid.groupby("age_band", as_index=False)["population"].sum()
    y = grouped.loc[grouped.age_band.isin(youth), "population"].sum()
    w = grouped.loc[grouped.age_band.isin(working), "population"].sum()
    o = grouped.loc[grouped.age_band.isin(old), "population"].sum()

    if w == 0:
        return 0.0, 0.0, 0.0

    youth_ratio = (y / w) * 100
    old_ratio = (o / w) * 100
    total_ratio = ((y + o) / w) * 100
    return float(youth_ratio), float(old_ratio), float(total_ratio)


def make_population_pyramid(pyr: pd.DataFrame, area: str, year: int) -> go.Figure:
    df = pyr[(pyr["area"] == area) & (pyr["year"] == year)].copy()
    order = ["0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39",
             "40-44","45-49","50-54","55-59","60-64","65-69","70-74","75-79","80+"]

    #Males to negative for left side
    df["value"] = df["population"].astype(int)
    df.loc[df["sex"] == "Male", "value"] *= -1
    df["age_band"] = pd.Categorical(df["age_band"], categories=order, ordered=True)
    df = df.sort_values("age_band")

    fig = px.bar(
        df,
        x="value",
        y="age_band",
        color="sex",
        orientation="h",
        title=f"Population Pyramid — {area} ({year})",
        labels={"value": "Population", "age_band": "Age band"},
    )
    fig.update_layout(
        barmode="relative",
        xaxis=dict(tickformat="~s"),
        yaxis=dict(title=""),
        legend_title_text="",
        height=520,
        margin=dict(l=10, r=10, t=55, b=10),
    )
    #Make axis symmetric and show absolute tick labels via custom ticktext
    max_abs = int(df["value"].abs().max())
    fig.update_xaxes(range=[-max_abs, max_abs])
    return fig


def make_population_change(pop_time: pd.DataFrame, area: str) -> go.Figure:
    df = pop_time[pop_time["area"] == area].sort_values("year").copy()

    fig = px.area(
        df,
        x="year",
        y="population_total",
        title=f"Population Change Over Time — {area}",
        labels={"population_total": "Population"},
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10))
    fig.update_yaxes(tickformat="~s")
    return fig


def make_split_donut(df: pd.DataFrame, area: str, year: int, category_col: str, title: str) -> go.Figure:
    sub = df[(df["area"] == area) & (df["year"] == year)].copy()
    sub["pct"] = sub["share"] * 100

    fig = px.pie(
        sub,
        names=category_col,
        values="pct",
        hole=0.55,
        title=title,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=55, b=10), showlegend=False)
    return fig


def make_identity_stacked(identity: pd.DataFrame, area: str) -> go.Figure:
    """
    Different chart type to avoid 'everything is a pie':
    100% stacked bar by year for Republican vs Unionist vs Other.
    """
    df = identity[identity["area"] == area].copy()
    df["pct"] = df["share"] * 100

    fig = px.bar(
        df,
        x="year",
        y="pct",
        color="identity",
        title=f"NI Constitutional Identity Over Time — {area}",
        labels={"pct": "Share (%)", "year": "Year"},
    )
    fig.update_layout(barmode="stack", height=360, margin=dict(l=10, r=10, t=55, b=10))
    fig.update_yaxes(range=[0, 100])
    return fig


# UI

st.title("👥 Demographics")
st.caption("Temporary values are used for now. When you plug in real NI datasets, keep the same column names/schemas.")

pop_pyr, pop_time, religion, identity = load_data()

#sidebar filters
with st.sidebar:
    st.header("Filters")
    all_areas = sorted(pop_time["area"].unique().tolist())
    area = st.selectbox("Area", all_areas, index=0)

    years = sorted(pop_time["year"].unique().tolist())
    year = st.slider("Year", min_value=min(years), max_value=max(years), value=max(years), step=1)

    st.markdown("---")
    st.write("**Data cleaning applied:** Title Case + `Derry/Londonderry` normalisation.")


# Layout: top row (pyramid + dependency metrics)
left, right = st.columns([1.4, 1.0], gap="large")

with left:
    fig_pyr = make_population_pyramid(pop_pyr, area, year)
    st.plotly_chart(fig_pyr, use_container_width=True)

with right:
    st.subheader("Age Dependency Ratio")
    sub_pyr = pop_pyr[(pop_pyr["area"] == area) & (pop_pyr["year"] == year)].copy()
    youth_r, old_r, total_r = dependency_ratio(sub_pyr)

    m1, m2, m3 = st.columns(3)
    m1.metric("Youth (0–14) / Working", f"{youth_r:.1f}%")
    m2.metric("Old-age (65+) / Working", f"{old_r:.1f}%")
    m3.metric("Total dependency", f"{total_r:.1f}%")

    st.markdown("")

    #simple gauge-style indicator
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=total_r,
        title={"text": "Total dependency (per 100 working-age)"},
        gauge={"axis": {"range": [0, 100]}},
    ))
    gauge.update_layout(height=260, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(gauge, use_container_width=True)


# Middle row: population change + identity over time
c1, c2 = st.columns(2, gap="large")

with c1:
    st.plotly_chart(make_population_change(pop_time, area), use_container_width=True)

with c2:
    st.plotly_chart(make_identity_stacked(identity, area), use_container_width=True)


# Bottom row: religious split (donut) + current-year identity split (donut)
b1, b2 = st.columns(2, gap="large")

with b1:
    st.plotly_chart(
        make_split_donut(
            religion, area, year,
            category_col="religion",
            title=f"Religious Split — {area} ({year})"
        ),
        use_container_width=True
    )

with b2:
    st.plotly_chart(
        make_split_donut(
            identity, area, year,
            category_col="identity",
            title=f"NI Republican vs Unionist vs Other — {area} ({year})"
        ),
        use_container_width=True
    )



# Debug / schema preview (helpful while integrating real datasets)
with st.expander("Show expected schemas (for plugging in real datasets)"):
    st.write("**Population pyramid schema:** area, year, age_band, sex, population")
    st.dataframe(pop_pyr.head(10), use_container_width=True)

    st.write("**Population time series schema:** area, year, population_total")
    st.dataframe(pop_time.head(10), use_container_width=True)

    st.write("**Religion schema:** area, year, religion, share (0–1)")
    st.dataframe(religion.head(10), use_container_width=True)

    st.write("**Identity schema:** area, year, identity, share (0–1)")
    st.dataframe(identity.head(10), use_container_width=True)
