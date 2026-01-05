from __future__ import annotations
from pathlib import Path
from typing import List
import pandas as pd
import plotly.express as px
import streamlit as st


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

ROI = "Republic of Ireland"
NI = "Northern Ireland"
REGIONS: List[str] = [ROI, NI]


#loaders
def _ensure_cols(df: pd.DataFrame, cols: List[str]) -> None:
    if not set(cols).issubset(df.columns):
        raise ValueError(f"Expected columns {cols}, got {list(df.columns)}")


@st.cache_data(show_spinner=False)
def load_unemployment(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    _ensure_cols(df, ["Year", "Region", "Sex", "Unemployment rate"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Unemployment rate"] = pd.to_numeric(df["Unemployment rate"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Sex"] = df["Sex"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Region", "Year", "Sex"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_labour_snapshot(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    _ensure_cols(
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
    _ensure_cols(df, ["Year", "Region", "Sector", "Share", "Persons"])

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
    _ensure_cols(df, ["Year", "Region", "Mode", "Share"])

    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype(int)
    df["Share"] = pd.to_numeric(df["Share"], errors="coerce")
    df["Region"] = df["Region"].astype(str).str.strip()
    df["Mode"] = df["Mode"].astype(str).str.strip()

    df = df[df["Region"].isin(REGIONS)]
    return df.sort_values(["Year", "Region", "Mode"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_gdp(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    _ensure_cols(df, ["Year", "Region", "GDP"])

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
    "This section compares labour-market outcomes and economic structure across the Republic of Ireland (ROI) and Northern Ireland (NI). "
    "Indicators prioritise interpretability and cross-jurisdictional comparability."
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

        #left column: KPI-style summary (no chart)
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

        #right column: CPNI36 chart
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
            st.plotly_chart(fig_sex, use_container_width=True, config={"displayModeBar": False})


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

    #nace section letter ordering (a-u)
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
    st.plotly_chart(fig_sector, use_container_width=True, config={"displayModeBar": False})

    st.caption("Industries are ordered by NACE section codes (A-U) shown in brackets, matching the joint publication ordering.")
else:
    st.info("Sectoral employment data not yet integrated.")

st.divider()

#commuting patterns
st.header("Mode of transport to work")

if COMMUTE_PATH.exists():
    commute = load_commute_modes(COMMUTE_PATH)
    commute = commute[commute["Region"].isin(regions)]

    years = sorted(commute["Year"].unique())
    year_c = st.selectbox("Year (commuting)", years, index=len(years) - 1, key="commute_year")

    commute_y = commute[commute["Year"] == year_c]

    fig_commute = px.bar(
        commute_y,
        x="Region",
        y="Share",
        color="Mode",
        barmode="stack",
        labels={"Share": "Share of workers (%)"},
        category_orders={"Region": REGIONS},
        title="Mode of transport to work",
    )
    st.plotly_chart(fig_commute, use_container_width=True)
else:
    st.info("Commuting mode data not yet integrated.")

st.divider()


#economic output (contextual)
st.header("Economic output (contextual)")

if GDP_PATH.exists():
    gdp = load_gdp(GDP_PATH)
    gdp = gdp[gdp["Region"].isin(regions)]

    fig_gdp = px.line(
        gdp,
        x="Year",
        y="GDP",
        color="Region",
        markers=True,
        category_orders={"Region": REGIONS},
        title="GDP over time",
    )
    st.plotly_chart(fig_gdp, use_container_width=True)

    st.caption("GDP is sourced from national accounts and is presented separately from census-derived indicators.")
else:
    st.info("GDP data not yet integrated.")


with st.expander("Methods & comparability notes"):
    st.markdown(
        """
- The dashboard reads only from `data/cleaned/`.
- CPNI36 is used for ILO unemployment rates by sex (persons aged 16+).
- CPNI35 is used for labour force and unemployed counts and within-labour-force shares (persons aged 16+).
- CPNI38 is used for sectoral composition of employment (persons aged 16+).
- The joint label '2021/2022' is aligned to 2022 for consistent ordering and filtering.
"""
    )
