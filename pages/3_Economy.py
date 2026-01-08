from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.common import ensure_cols, ROI, NI, REGIONS


#page config
st.set_page_config(
    page_title="Economy",
    page_icon="💷",
    layout="wide",
    initial_sidebar_state="expanded",
)

#paths
CLEAN_DIR = Path("data/cleaned/economy")

UNEMP_PATH = CLEAN_DIR / "unemployment_rate.csv"
LABOUR_PATH = CLEAN_DIR / "labour_market_snapshot.csv"
SECTOR_PATH = CLEAN_DIR / "employment_by_sector.csv"
COMMUTE_PATH = CLEAN_DIR / "commute_mode.csv"
GDP_PATH = CLEAN_DIR / "gdp_over_time.csv"


#loaders


@st.cache_data(show_spinner=False)
def load_unemployment(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Sex", "Unemployment rate"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Unemployment rate"] = pd.to_numeric(df["Unemployment rate"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Sex"] = df["Sex"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year", "Sex"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_labour_snapshot(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(
        df,
        [
            "Year",
            "Region",
            "Employed (16+)",
            "Unemployed (16+)",
            "Labour force (16+)",
            "Employment share (%)",
            "Unemployment rate (%)",
        ],
    )

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Region"] = df["Region"].astype(str).str.strip()

    df["Employed (16+)"] = pd.to_numeric(df["Employed (16+)"], errors="coerce").astype(int)
    df["Unemployed (16+)"] = pd.to_numeric(df["Unemployed (16+)"], errors="coerce").astype(int)
    df["Labour force (16+)"] = pd.to_numeric(df["Labour force (16+)"], errors="coerce").astype(int)

    df["Employment share (%)"] = pd.to_numeric(df["Employment share (%)"], errors="coerce")
    df["Unemployment rate (%)"] = pd.to_numeric(df["Unemployment rate (%)"], errors="coerce")

    df = df[df["Region"].isin([ROI, NI])]
    return df.sort_values(["Region", "Year"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_sector_employment(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Sector", "Share", "Persons"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Share"] = pd.to_numeric(df["Share"], errors="coerce")
    df["Persons"] = pd.to_numeric(df["Persons"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Sector"] = df["Sector"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Year", "Region", "Sector"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_commute_modes(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "Mode", "Share", "Persons"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Share"] = pd.to_numeric(df["Share"], errors="coerce")
    df["Persons"] = pd.to_numeric(df["Persons"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Mode"] = df["Mode"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Year", "Region", "Mode"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_gdp(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    ensure_cols(df, ["Year", "Region", "GDP"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["GDP"] = pd.to_numeric(df["GDP"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year"]).reset_index(drop=True)


def _weighted_rate(values: pd.Series, weights: pd.Series) -> float:
    w = pd.to_numeric(weights, errors="coerce")
    v = pd.to_numeric(values, errors="coerce")
    if w.isna().any() or v.isna().any():
        return float("nan")
    total_w = float(w.sum())
    if total_w <= 0:
        return float("nan")
    return float((v * w).sum() / total_w)


#page header
st.title("💷 Economy")
st.write(
    "This section compares labour-market outcomes and economic structure across the Republic of Ireland (ROI), "
    "Northern Ireland (NI), and the All-Island aggregate. Indicators prioritise interpretability and cross-jurisdictional "
    "comparability."
)
st.divider()


#sidebar
with st.sidebar:
    st.header("Filters")

    regions = st.multiselect(
        "Regions",
        REGIONS,
        default=REGIONS,
    )

    st.markdown("---")
    st.subheader("Labour market display")

    labour_display = st.radio(
        "Mode",
        ["Percentages", "Absolute numbers"],
        horizontal=True,
        key="labour_display_mode",
    )

#labour market
st.header("Labour market")

if not UNEMP_PATH.exists():
    st.info("Unemployment data not yet available. Run the CPNI36 cleaning script to generate the cleaned CSV.")
else:
    unemp = load_unemployment(UNEMP_PATH)
    unemp = unemp[unemp["Region"].isin(regions)]

    if unemp.empty:
        st.info("Unemployment data file is present but contains no rows after filtering.")
    else:
        year = int(unemp["Year"].iloc[0])
        sex_order = ["Both sexes", "Male", "Female"]
        unemp = unemp[unemp["Sex"].isin(sex_order)].copy()

        left, right = st.columns([1, 2], gap="large")

        #left column: KPI-style summar
        with left:
            st.subheader("Summary")

            if LABOUR_PATH.exists():
                lm = load_labour_snapshot(LABOUR_PATH)

                if lm.empty:
                    st.info("Labour market snapshot is present but contains no rows after cleaning.")
                else:
                    snap_year = int(lm["Year"].max())
                    lm_y = lm[lm["Year"] == snap_year].copy()

                    roi_row = lm_y[lm_y["Region"] == ROI]
                    ni_row = lm_y[lm_y["Region"] == NI]

                    if roi_row.empty or ni_row.empty:
                        st.info("Labour market snapshot is missing ROI and/or NI rows for the latest year.")
                    else:
                        roi = roi_row.iloc[0]
                        ni = ni_row.iloc[0]

                        c1, c2 = st.columns(2, gap="large")

                        if labour_display == "Absolute numbers":
                            with c1:
                                st.caption(ROI)
                                st.metric("Labour force (16+)", f'{int(roi["Labour force (16+)"]):,}')
                                st.metric("Unemployed (16+)", f'{int(roi["Unemployed (16+)"]):,}')

                            with c2:
                                st.caption(NI)
                                st.metric("Labour force (16+)", f'{int(ni["Labour force (16+)"]):,}')
                                st.metric("Unemployed (16+)", f'{int(ni["Unemployed (16+)"]):,}')

                        else:
                            with c1:
                                st.caption(ROI)
                                st.metric("Employment share (%)", f'{float(roi["Employment share (%)"]):.1f}%')
                                st.metric("Unemployment rate (%)", f'{float(roi["Unemployment rate (%)"]):.1f}%')

                            with c2:
                                st.caption(NI)
                                st.metric("Employment share (%)", f'{float(ni["Employment share (%)"]):.1f}%')
                                st.metric("Unemployment rate (%)", f'{float(ni["Unemployment rate (%)"]):.1f}%')
            else:
                st.info("Labour market snapshot not yet available. Run clean_labour_market_snapshot.py to generate it.")

            st.caption("Note: The data comes from both the 2021 and 2022 census (the most recent census from each nation)")

        #right column
        with right:
            st.subheader(f"ILO unemployment rate — {year}")

            fig_sex = px.bar(
                unemp,
                x="Sex",
                y="Unemployment rate",
                color="Region",
                barmode="group",
                text="Unemployment rate",
                labels={"Unemployment rate": "ILO unemployment rate (%)"},
                category_orders={"Sex": sex_order, "Region": [ROI, NI]},
            )
            fig_sex.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_sex.update_layout(
                height=340,
                yaxis_range=[0, 6],
                margin=dict(l=40, r=20, t=40, b=40),
                legend_title_text="",
            )
            st.plotly_chart(fig_sex, width="stretch", config={"displayModeBar": False})


st.divider()


#employment by sector
st.header("Employment structure")

if SECTOR_PATH.exists():
    sector = load_sector_employment(SECTOR_PATH)
    sector = sector[sector["Region"].isin(regions)]

    sector_y = sector.copy()

    metric_col = "Share" if labour_display == "Percentages" else "Persons"
    value_label = "Share of employment (%)" if labour_display == "Percentages" else "Persons in employment"
    text_tmpl = "%{text:.1f}%" if labour_display == "Percentages" else "%{text:,}"

    sector_y["_nace"] = sector_y["Sector"].str.extract(r"\(([A-Z])\)")
    sector_y = sector_y.sort_values(["_nace", "Sector"])

    fig_sector = px.bar(
        sector_y,
        x=metric_col,
        y="Sector",
        color="Region",
        orientation="h",
        barmode="group",
        text=metric_col,
        labels={metric_col: value_label, "Sector": "Industry"},
        category_orders={"Sector": sector_y["Sector"].unique(), "Region": REGIONS},
        title="Persons in employment by industrial sector",
    )
    fig_sector.update_traces(texttemplate=text_tmpl, textposition="outside")
    fig_sector.update_layout(
        height=620,
        margin=dict(l=20, r=20, t=50, b=40),
        legend_title_text="",
        yaxis_title="Industry",
        xaxis_title=value_label,
    )
    st.plotly_chart(fig_sector, width="stretch", config={"displayModeBar": False})

    st.caption("Industries are ordered by NACE section codes (A–U) shown in brackets, matching the joint publication ordering.")
else:
    st.info("Sectoral employment data not yet integrated.")

st.divider()


#commuting patterns
st.header("Mode of transport to work")

if COMMUTE_PATH.exists():
    commute_all = load_commute_modes(COMMUTE_PATH)
    commute_y = commute_all[commute_all["Region"].isin(regions)].copy()

    metric_col = "Persons"
    value_label = "Persons (16+) at work"
    text_tmpl = "%{text:,.0f}"

    modes = sorted(commute_y["Mode"].unique())
    if "Not stated" in modes:
        modes.remove("Not stated")
        modes.append("Not stated")

    commute_y["Mode"] = pd.Categorical(commute_y["Mode"], categories=modes, ordered=True)
    commute_y = commute_y.sort_values("Mode")

    fig_commute = px.bar(
        commute_y,
        x="Mode",
        y=metric_col,
        color="Region",
        barmode="group",
        text=metric_col,
        labels={metric_col: value_label, "Mode": "Transport mode"},
        category_orders={"Mode": modes, "Region": REGIONS},
        title="Mode of transport to work",
    )
    fig_commute.update_traces(texttemplate=text_tmpl, textposition="outside")
    fig_commute.update_layout(
        height=500,
        margin=dict(l=20, r=20, t=50, b=40),
        legend_title_text="",
        yaxis_title=value_label,
        xaxis_title="",
    )
    fig_commute.update_xaxes(tickangle=-45)
    st.plotly_chart(fig_commute, width="stretch", config={"displayModeBar": False})

    left_pie, right_pie = st.columns(2, gap="large")

    with left_pie:
        roi_data = commute_all[commute_all["Region"] == ROI].copy()
        roi_data = roi_data[(roi_data["Share"].notna()) & (roi_data["Share"] > 0)].copy()
        roi_data = roi_data[~roi_data["Mode"].eq("All means of travel")].copy()

        if not roi_data.empty:
            fig_roi_pie = px.pie(
                roi_data,
                values="Share",
                names="Mode",
                title=f"{ROI} - Transport mode share (%)",
                hole=0.4,
            )
            fig_roi_pie.update_traces(textinfo="percent")
            fig_roi_pie.update_layout(
                height=420,
                margin=dict(l=20, r=20, t=50, b=20),
                legend_title_text="",
            )
            st.plotly_chart(fig_roi_pie, width="stretch", config={"displayModeBar": False})
        else:
            st.info(f"No percentage data available for {ROI}")

    with right_pie:
        ni_data = commute_all[commute_all["Region"] == NI].copy()
        ni_data = ni_data[(ni_data["Share"].notna()) & (ni_data["Share"] > 0)].copy()
        ni_data = ni_data[~ni_data["Mode"].eq("All means of travel")].copy()

        if not ni_data.empty:
            fig_ni_pie = px.pie(
                ni_data,
                values="Share",
                names="Mode",
                title=f"{NI} - Transport mode share (%)",
                hole=0.4,
            )
            fig_ni_pie.update_traces(textinfo="percent")
            fig_ni_pie.update_layout(
                height=420,
                margin=dict(l=20, r=20, t=50, b=20),
                legend_title_text="",
            )
            st.plotly_chart(fig_ni_pie, width="stretch", config={"displayModeBar": False})
        else:
            st.info(f"No percentage data available for {NI}")

else:
    st.info("Commuting mode data not yet integrated.")

#cross-border commuting
st.header("Cross-border commuting")

CROSS_PATH = CLEAN_DIR / "cross_border_commuters.csv"

if CROSS_PATH.exists():
    cross = pd.read_csv(CROSS_PATH)
    ensure_cols(cross, ["Year", "Region", "Age group", "Persons"])

    cross["Year"] = pd.to_numeric(cross["Year"], errors="coerce").astype(int)
    cross["Region"] = cross["Region"].astype(str).str.strip()
    cross["Age group"] = cross["Age group"].astype(str).str.strip()
    cross["Persons"] = pd.to_numeric(cross["Persons"], errors="coerce")

    cross = cross[cross["Region"].isin(regions)].copy()

    if cross.empty:
        st.info("Cross-border commuting file is present but contains no rows after filtering.")
    else:
        cross_year = int(cross["Year"].max())
        cross_y = cross[cross["Year"] == cross_year].copy()

        #sort age groups
        ages = list(cross_y["Age group"].unique())
        all_label = "All ages"
        ages_no_all = [a for a in ages if a != all_label]

        def _age_key(s: str) -> tuple:
            #extract first number from age group string
            s = str(s).strip()
            digits = ""
            for ch in s:
                if ch.isdigit():
                    digits += ch
                elif digits:
                    break
            return (int(digits) if digits else 999, s)

        ages_no_all = sorted(ages_no_all, key=_age_key)
        if all_label in ages:
            ages_order = ages_no_all + [all_label]
        else:
            ages_order = ages_no_all

        cross_y["Age group"] = pd.Categorical(cross_y["Age group"], categories=ages_order, ordered=True)
        cross_y = cross_y.sort_values("Age group")

        fig_cross = px.bar(
            cross_y,
            x="Age group",
            y="Persons",
            color="Region",
            barmode="group",
            text="Persons",
            labels={"Persons": "Cross-border commuters (persons)", "Age group": "Age group"},
            category_orders={"Age group": ages_order, "Region": REGIONS},
            title=f"Cross-border commuters for work — {cross_year}",
        )
        fig_cross.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_cross.update_layout(
            height=520,
            margin=dict(l=20, r=20, t=50, b=120),
            legend_title_text="",
            yaxis_title="Cross-border commuters (persons)",
            xaxis_title="",
        )
        fig_cross.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_cross, width="stretch", config={"displayModeBar": False})

else:
    st.info("Cross-border commuting data not yet integrated. Run the CPNI53 cleaning script to generate the cleaned CSV.")


#GDP

st.header("Economic output (GDP)")

st.markdown(
    """
Gross Domestic Product (GDP) is a widely used indicator of economic scale and was considered for inclusion in the Economy section.

However, GDP data for the Republic of Ireland and Northern Ireland are compiled under different national accounting frameworks and are not directly comparable over time or across jurisdictions.
In addition, GDP figures for the Republic of Ireland are known to be significantly affected by multinational profit-shifting, limiting their usefulness as indicators of underlying domestic economic conditions.

For these reasons, GDP is not used as an analytical variable in the Economy section, which instead focuses on census-based labour market and commuting indicators where population coverage and cross-jurisdictional comparability can be more clearly defined.

A single-year GDP figure is shown in the Overview page to provide high-level contextual information.
"""
)
