from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


#page config
st.set_page_config(
    page_title="Living Conditions",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

#paths
CLEAN_DIR = Path("data/cleaned/living_conditions")
TENURE_PATH = CLEAN_DIR / "housing_tenure.csv"
TYPE_PATH = CLEAN_DIR / "housing_type.csv"
OCC_PATH = CLEAN_DIR / "housing_occupancy.csv"

#constants
ROI = "Republic of Ireland"
NI = "Northern Ireland"
REGIONS = [ROI, NI]


#helpers
def _ensure_cols(df: pd.DataFrame, cols: list[str]) -> None:
    if not set(cols).issubset(df.columns):
        raise ValueError(f"Expected columns {cols}, got {list(df.columns)}")


def _simplify_tenure_label(s: str) -> str:
    x = str(s).strip().lower()

    if "not stated" in x or x in {"unknown", "unspecified"}:
        return "Not stated"

    if "owner" in x or "owned" in x:
        return "Home owned"

    return "Home not owned"


#page header
st.title("🏠 Living Conditions")
st.write(
    "This section examines structural and material aspects of how people live, using census-based indicators "
    "where cross-jurisdictional comparability can be clearly defined."
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


#housing
st.header("Housing")
st.subheader("Tenure")

simplify_tenure = st.toggle(
    "Simplify tenure categories",
    value=False,
    help="Collapses tenure into: Home owned, Home not owned, Not stated.",
)

if not TENURE_PATH.exists():
    st.info("Tenure data not yet integrated. Run clean_housing_tenure.py to generate the cleaned CSV.")
else:
    tenure_all = pd.read_csv(TENURE_PATH)
    _ensure_cols(tenure_all, ["Year", "Region", "Nature", "Percentage", "Absolute"])

    tenure_all["Year"] = pd.to_numeric(tenure_all["Year"], errors="coerce").astype(int)
    tenure_all["Region"] = tenure_all["Region"].astype(str).str.strip()
    tenure_all["Nature"] = tenure_all["Nature"].astype(str).str.strip()
    tenure_all["Percentage"] = pd.to_numeric(tenure_all["Percentage"], errors="coerce")
    tenure_all["Absolute"] = pd.to_numeric(tenure_all["Absolute"], errors="coerce")

    tenure_all = tenure_all[tenure_all["Region"].isin(regions)].copy()

    if tenure_all.empty:
        st.info("Tenure file is present but contains no rows after filtering.")
    else:
        year = int(tenure_all["Year"].max())
        tenure_y = tenure_all[tenure_all["Year"] == year].copy()

        if simplify_tenure:
            tenure_y["Nature"] = tenure_y["Nature"].apply(_simplify_tenure_label)

            grouped = tenure_y.groupby(["Year", "Region", "Nature"], as_index=False)["Absolute"].sum()

            totals = grouped.groupby(["Year", "Region"], as_index=False)["Absolute"].sum().rename(
                columns={"Absolute": "_region_total"}
            )

            tenure_y = grouped.merge(totals, on=["Year", "Region"], how="left")
            tenure_y["Percentage"] = (tenure_y["Absolute"] / tenure_y["_region_total"]) * 100
            tenure_y = tenure_y.drop(columns=["_region_total"])

            natures = ["Home owned", "Home not owned", "Not stated"]
        else:
            natures = list(tenure_y["Nature"].dropna().unique())
            if "Not stated" in natures:
                natures = [n for n in natures if n != "Not stated"] + ["Not stated"]

        tenure_y["Nature"] = pd.Categorical(tenure_y["Nature"], categories=natures, ordered=True)
        tenure_y = tenure_y.sort_values("Nature")

        fig_abs = px.bar(
            tenure_y,
            x="Nature",
            y="Absolute",
            color="Region",
            barmode="group",
            text="Absolute",
            labels={"Absolute": "Households", "Nature": "Tenure"},
            category_orders={"Nature": natures, "Region": REGIONS},
            title=f"Housing tenure — {year} (absolute)",
        )
        fig_abs.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_abs.update_layout(
            height=640,
            margin=dict(l=20, r=20, t=70, b=140),
            legend_title_text="",
            yaxis_title="Households",
            xaxis_title="",
        )
        fig_abs.update_xaxes(tickangle=-35)
        st.plotly_chart(fig_abs, use_container_width=True, config={"displayModeBar": False})

        left_pie, right_pie = st.columns(2, gap="large")

        with left_pie:
            roi_data = tenure_y[tenure_y["Region"] == ROI].copy()
            roi_data = roi_data[(roi_data["Percentage"].notna()) & (roi_data["Percentage"] > 0)].copy()

            if roi_data.empty:
                st.info(f"No percentage data available for {ROI}.")
            else:
                fig_roi = px.pie(
                    roi_data,
                    values="Percentage",
                    names="Nature",
                    title=f"{ROI} — tenure share (%)",
                    hole=0.4,
                )
                fig_roi.update_traces(textinfo="percent")
                fig_roi.update_layout(
                    height=420,
                    margin=dict(l=20, r=20, t=60, b=20),
                    legend_title_text="",
                )
                st.plotly_chart(fig_roi, use_container_width=True, config={"displayModeBar": False})

        with right_pie:
            ni_data = tenure_y[tenure_y["Region"] == NI].copy()
            ni_data = ni_data[(ni_data["Percentage"].notna()) & (ni_data["Percentage"] > 0)].copy()

            if ni_data.empty:
                st.info(f"No percentage data available for {NI}.")
            else:
                fig_ni = px.pie(
                    ni_data,
                    values="Percentage",
                    names="Nature",
                    title=f"{NI} — tenure share (%)",
                    hole=0.4,
                )
                fig_ni.update_traces(textinfo="percent")
                fig_ni.update_layout(
                    height=420,
                    margin=dict(l=20, r=20, t=60, b=20),
                    legend_title_text="",
                )
                st.plotly_chart(fig_ni, use_container_width=True, config={"displayModeBar": False})

        st.caption(
            "Simplified tenure mapping (if enabled): "
            "'Home owned' includes all owner-occupied categories. "
            "'Home not owned' includes all non-owner-occupied categories, including rented accommodation and "
            "dwellings occupied free of rent (e.g. living rent-free in a property owned by a relative or employer). "
            "'Not stated' includes cases where tenure was not reported. "
            "This grouping reflects ownership status rather than rental payment."
        )

st.divider()

#housing type & occupancy
st.subheader("Housing type & occupancy")

left_col, right_col = st.columns(2, gap="large")

#left: housing type (percent-only, 100% stacked)
with left_col:
    st.markdown("#### Type")

    if not TYPE_PATH.exists():
        st.info("Housing type data not yet integrated. Run clean_housing_type.py to generate the cleaned CSV.")
    else:
        ht_all = pd.read_csv(TYPE_PATH)
        _ensure_cols(ht_all, ["Year", "Region", "Type", "Percentage"])

        ht_all["Year"] = pd.to_numeric(ht_all["Year"], errors="coerce").astype(int)
        ht_all["Region"] = ht_all["Region"].astype(str).str.strip()
        ht_all["Type"] = ht_all["Type"].astype(str).str.strip()
        ht_all["Percentage"] = pd.to_numeric(ht_all["Percentage"], errors="coerce")

        ht_all = ht_all[ht_all["Region"].isin(regions)].copy()

        if ht_all.empty:
            st.info("Housing type file is present but contains no rows after filtering.")
        else:
            year = int(ht_all["Year"].max())
            ht_y = ht_all[ht_all["Year"] == year].copy()

            types = list(ht_y["Type"].dropna().unique())
            if "Not stated" in types:
                types = [t for t in types if t != "Not stated"] + ["Not stated"]

            ht_y["Type"] = pd.Categorical(ht_y["Type"], categories=types, ordered=True)
            ht_y = ht_y.sort_values("Type")

            check = ht_y.groupby("Region")["Percentage"].sum().round(1)
            if not all(check.between(99.0, 101.0)):
                st.caption(f"Note: percentages do not sum to exactly 100 due to rounding: {check.to_dict()}")

            fig_type = px.bar(
                ht_y,
                x="Region",
                y="Percentage",
                color="Type",
                barmode="stack",
                text="Percentage",
                labels={"Percentage": "Share of households (%)", "Region": "", "Type": "Housing type"},
                title=f"Housing type — {year}",
                category_orders={"Region": REGIONS, "Type": types},
            )
            fig_type.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
            fig_type.update_layout(
                height=520,
                margin=dict(l=20, r=20, t=60, b=40),
                legend_title_text="",
                yaxis_range=[0, 100],
            )
            st.plotly_chart(fig_type, use_container_width=True, config={"displayModeBar": False})

            st.caption("NOTE: Caravan... is not visible on the graph due to it being <0.25% of the housing stock in both regions")


#right: housing occupancy
with right_col:
    st.markdown("#### Occupancy")

    if not OCC_PATH.exists():
        st.info("Housing occupancy data not yet integrated. Run clean_housing_occupancy.py to generate the cleaned CSV.")
    else:
        occ_all = pd.read_csv(OCC_PATH)
        _ensure_cols(occ_all, ["Year", "Region", "Occupancy", "Percentage"])

        occ_all["Year"] = pd.to_numeric(occ_all["Year"], errors="coerce").astype(int)
        occ_all["Region"] = occ_all["Region"].astype(str).str.strip()
        occ_all["Occupancy"] = occ_all["Occupancy"].astype(str).str.strip()
        occ_all["Percentage"] = pd.to_numeric(occ_all["Percentage"], errors="coerce")

        occ_all = occ_all[occ_all["Region"].isin(regions)].copy()

        if occ_all.empty:
            st.info("Housing occupancy file is present but contains no rows after filtering.")
        else:
            year = int(occ_all["Year"].max())
            occ_y = occ_all[occ_all["Year"] == year].copy()

            occ_y = occ_y.groupby(["Region", "Occupancy"], as_index=False)["Percentage"].sum()

            check = occ_y.groupby("Region")["Percentage"].sum().round(1)
            if not all(check.between(99.5, 100.5)):
                raise ValueError(f"Occupancy percentages do not sum to 100 by region: {check.to_dict()}")

            occ_order = [x for x in ["Occupied", "Vacant"] if x in occ_y["Occupancy"].unique()]
            remaining = [x for x in occ_y["Occupancy"].unique() if x not in occ_order]
            occ_order = occ_order + sorted(remaining)

            occ_y["Occupancy"] = pd.Categorical(occ_y["Occupancy"], categories=occ_order, ordered=True)
            occ_y = occ_y.sort_values("Occupancy")

            fig_occ = px.bar(
                occ_y,
                x="Region",
                y="Percentage",
                color="Occupancy",
                barmode="stack",
                text="Percentage",
                labels={"Percentage": "Share of housing stock (%)", "Region": "", "Occupancy": "Status"},
                title=f"Housing occupancy — {year}",
                category_orders={"Region": REGIONS, "Occupancy": occ_order},
            )
            fig_occ.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
            fig_occ.update_layout(
                height=520,
                margin=dict(l=20, r=20, t=60, b=40),
                legend_title_text="",
                yaxis_range=[0, 100],
            )
            st.plotly_chart(fig_occ, use_container_width=True, config={"displayModeBar": False})

st.caption("Shares are within-region percentages of the total housing stock for the census year shown.")
