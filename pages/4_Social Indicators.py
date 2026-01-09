from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.common import ensure_cols, ROI, NI, REGIONS


#page config
st.set_page_config(
    page_title="Social Indicators",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

#paths
CLEAN_DIR = Path("data/cleaned/social_indicators")
TENURE_PATH = CLEAN_DIR / "housing_tenure.csv"
TYPE_PATH = CLEAN_DIR / "housing_type.csv"
OCC_PATH = CLEAN_DIR / "housing_occupancy.csv"
HH_SIZE_PATH = CLEAN_DIR / "household_size.csv"
HH_COMP_PATH = CLEAN_DIR / "household_composition.csv"
EDU_QUAL_PATH = CLEAN_DIR / "education_qualifications.csv"
HEALTH_PATH = CLEAN_DIR / "general_health.csv"
HEALTH_AGE_PATH = CLEAN_DIR / "general_health_by_age.csv"


#helpers


def _simplify_tenure_label(s: str) -> str:
    x = str(s).strip().lower()

    if "not stated" in x or x in {"unknown", "unspecified"}:
        return "Not stated"

    if "owner" in x or "owned" in x:
        return "Home owned"

    return "Home not owned"


#page header
st.title("📊 Social Indicators")
st.write(
    "This section examines key social metrics including housing, education, and health using census-based measures that are comparable across jurisdictions."
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
    st.subheader("Display")

    display_mode = st.radio(
        "Mode",
        ["Percentages", "Absolute numbers"],
        horizontal=True,
        key="housing_display_mode",
        help="Controls display format for composition charts (housing type/occupancy, household composition, education, general health). Tenure and general health by age sections always show their default formats.",
    )
    st.caption("Note: Tenure and general health by age are not affected by the display mode toggle.")


st.header("Housing")

#tenure (unaffected by sidebar display_mode)
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
    ensure_cols(tenure_all, ["Year", "Region", "Nature", "Percentage", "Absolute"])

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
        st.plotly_chart(fig_abs, width="stretch", config={"displayModeBar": False})

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
                st.plotly_chart(fig_roi, width="stretch", config={"displayModeBar": False})

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
                st.plotly_chart(fig_ni, width="stretch", config={"displayModeBar": False})

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

#type
with left_col:
    st.markdown("#### Type")

    if not TYPE_PATH.exists():
        st.info("Housing type data not yet integrated. Run clean_housing_type.py to generate the cleaned CSV.")
    else:
        ht_all = pd.read_csv(TYPE_PATH)
        ensure_cols(ht_all, ["Year", "Region", "Type", "Percentage", "Absolute"])

        ht_all["Year"] = pd.to_numeric(ht_all["Year"], errors="coerce").astype(int)
        ht_all["Region"] = ht_all["Region"].astype(str).str.strip()
        ht_all["Type"] = ht_all["Type"].astype(str).str.strip()
        ht_all["Percentage"] = pd.to_numeric(ht_all["Percentage"], errors="coerce")
        ht_all["Absolute"] = pd.to_numeric(ht_all["Absolute"], errors="coerce")

        ht_all = ht_all[ht_all["Region"].isin(regions)].copy()

        if ht_all.empty:
            st.info("Housing type file is present but contains no rows after filtering.")
        else:
            year = int(ht_all["Year"].max())
            ht_y = ht_all[ht_all["Year"] == year].copy()

            # collapse duplicates (safe after category merges)
            ht_y = ht_y.groupby(["Region", "Type"], as_index=False)[["Percentage", "Absolute"]].sum()

            types = list(ht_y["Type"].dropna().unique())
            if "Not stated" in types:
                types = [t for t in types if t != "Not stated"] + ["Not stated"]

            ht_y["Type"] = pd.Categorical(ht_y["Type"], categories=types, ordered=True)
            ht_y = ht_y.sort_values("Type")

            if display_mode == "Absolute numbers":
                metric_col = "Absolute"
                value_label = "Households (count)"
                text_tmpl = "%{text:,.0f}"
                title_suffix = "absolute"
            else:
                metric_col = "Percentage"
                value_label = "Share of households (%)"
                text_tmpl = "%{text:.1f}%"
                title_suffix = "percent"

                check = ht_y.groupby("Region")["Percentage"].sum().round(1)
                if not all(check.between(99.0, 101.0)):
                    st.caption(f"Note: percentages do not sum to exactly 100 due to rounding: {check.to_dict()}")

            fig_type = px.bar(
                ht_y,
                x="Region",
                y=metric_col,
                color="Type",
                barmode="stack",
                text=metric_col,
                labels={metric_col: value_label, "Region": "", "Type": "Housing type"},
                title=f"Housing type — {year} ({title_suffix})",
                category_orders={"Region": REGIONS, "Type": types},
            )
            fig_type.update_traces(texttemplate=text_tmpl, textposition="inside")
            fig_type.update_layout(
                height=520,
                margin=dict(l=20, r=20, t=60, b=40),
                legend_title_text="",
            )
            if metric_col == "Percentage":
                fig_type.update_yaxes(range=[0, 100])

            st.plotly_chart(fig_type, width="stretch", config={"displayModeBar": False})

            st.caption("NOTE: Caravan... is not visible on the graph due to it being <0.25% of the housing stock in both regions")

#occupancy: toggle if Absolute exists, else percent-only
with right_col:
    st.markdown("#### Occupancy")

    if not OCC_PATH.exists():
        st.info("Housing occupancy data not yet integrated. Run clean_housing_occupancy.py to generate the cleaned CSV.")
    else:
        occ_all = pd.read_csv(OCC_PATH)

        if "Absolute" in occ_all.columns:
            ensure_cols(occ_all, ["Year", "Region", "Occupancy", "Percentage", "Absolute"])
        else:
            ensure_cols(occ_all, ["Year", "Region", "Occupancy", "Percentage"])

        occ_all["Year"] = pd.to_numeric(occ_all["Year"], errors="coerce").astype(int)
        occ_all["Region"] = occ_all["Region"].astype(str).str.strip()
        occ_all["Occupancy"] = occ_all["Occupancy"].astype(str).str.strip()
        occ_all["Percentage"] = pd.to_numeric(occ_all["Percentage"], errors="coerce")

        if "Absolute" in occ_all.columns:
            occ_all["Absolute"] = pd.to_numeric(occ_all["Absolute"], errors="coerce")

        occ_all = occ_all[occ_all["Region"].isin(regions)].copy()

        if occ_all.empty:
            st.info("Housing occupancy file is present but contains no rows after filtering.")
        else:
            year = int(occ_all["Year"].max())
            occ_y = occ_all[occ_all["Year"] == year].copy()

            agg_cols = ["Percentage"] + (["Absolute"] if "Absolute" in occ_y.columns else [])
            occ_y = occ_y.groupby(["Region", "Occupancy"], as_index=False)[agg_cols].sum()

            occ_order = [x for x in ["Occupied", "Vacant"] if x in occ_y["Occupancy"].unique()]
            remaining = [x for x in occ_y["Occupancy"].unique() if x not in occ_order]
            occ_order = occ_order + sorted(remaining)

            occ_y["Occupancy"] = pd.Categorical(occ_y["Occupancy"], categories=occ_order, ordered=True)
            occ_y = occ_y.sort_values("Occupancy")

            if display_mode == "Absolute numbers" and "Absolute" in occ_y.columns:
                metric_col = "Absolute"
                value_label = "Dwellings (count)"
                text_tmpl = "%{text:,.0f}"
                title_suffix = "absolute"
            else:
                metric_col = "Percentage"
                value_label = "Share of housing stock (%)"
                text_tmpl = "%{text:.1f}%"
                title_suffix = "percent"

                check = occ_y.groupby("Region")["Percentage"].sum().round(1)
                if not all(check.between(99.5, 100.5)):
                    raise ValueError(f"Occupancy percentages do not sum to 100 by region: {check.to_dict()}")

            fig_occ = px.bar(
                occ_y,
                x="Region",
                y=metric_col,
                color="Occupancy",
                barmode="stack",
                text=metric_col,
                labels={metric_col: value_label, "Region": "", "Occupancy": "Status"},
                title=f"Housing occupancy — {year} ({title_suffix})",
                category_orders={"Region": REGIONS, "Occupancy": occ_order},
            )
            fig_occ.update_traces(texttemplate=text_tmpl, textposition="inside")
            fig_occ.update_layout(
                height=520,
                margin=dict(l=20, r=20, t=60, b=40),
                legend_title_text="",
            )
            if metric_col == "Percentage":
                fig_occ.update_yaxes(range=[0, 100])

            st.plotly_chart(fig_occ, width="stretch", config={"displayModeBar": False})

st.divider()

#household composition
st.subheader("Household composition")

if not HH_COMP_PATH.exists():
    st.info("Household composition data not yet integrated. Run clean_household_composition.py to generate the cleaned CSV.")
else:
    comp_all = pd.read_csv(HH_COMP_PATH)
    ensure_cols(comp_all, ["Year", "Region", "Composition", "Percentage", "Absolute"])

    comp_all["Year"] = pd.to_numeric(comp_all["Year"], errors="coerce").astype(int)
    comp_all["Region"] = comp_all["Region"].astype(str).str.strip()
    comp_all["Composition"] = comp_all["Composition"].astype(str).str.strip()
    comp_all["Percentage"] = pd.to_numeric(comp_all["Percentage"], errors="coerce")
    comp_all["Absolute"] = pd.to_numeric(comp_all["Absolute"], errors="coerce")

    comp_all = comp_all[comp_all["Region"].isin(regions)].copy()

    if comp_all.empty:
        st.info("Household composition file is present but contains no rows after filtering.")
    else:
        year = int(comp_all["Year"].max())
        comp_y = comp_all[comp_all["Year"] == year].copy()

        comp_order = sorted(comp_y["Composition"].unique())

        comp_y["Composition"] = pd.Categorical(comp_y["Composition"], categories=comp_order, ordered=True)
        comp_y = comp_y.sort_values(["Region", "Composition"])

        if display_mode == "Absolute numbers":
            metric_col = "Absolute"
            value_label = "Households (count)"
            text_tmpl = "%{text:,.0f}"
            title_suffix = "absolute"
        else:
            metric_col = "Percentage"
            value_label = "Share of households (%)"
            text_tmpl = "%{text:.1f}%"
            title_suffix = "percent"

        fig_comp = px.bar(
            comp_y,
            y="Composition",
            x=metric_col,
            color="Region",
            barmode="group",
            text=metric_col,
            orientation="h",
            labels={metric_col: value_label, "Composition": ""},
            title=f"Household composition — {year} ({title_suffix})",
            category_orders={"Region": REGIONS, "Composition": comp_order},
        )
        fig_comp.update_traces(texttemplate=text_tmpl, textposition="outside")
        fig_comp.update_layout(
            height=480,
            margin=dict(l=20, r=20, t=60, b=40),
            legend_title_text="",
        )
        st.plotly_chart(fig_comp, width="stretch", config={"displayModeBar": False})

st.divider()

#education
st.header("Education")

st.subheader("Qualification classification comparison")
st.write(
    "The education systems in the Republic of Ireland and Northern Ireland operate under different frameworks and qualification structures. "
    "This table maps comparable education levels across both jurisdictions to enable cross-border comparison."
)

classification_data = {
    "Level": [
        "Basic",
        "Intermediate",
        "Advanced",
        "Higher/Professional",
    ],
    "Republic of Ireland": [
        "Primary, Junior Cert (NFQ 1-3)",
        "Leaving Cert, Vocational (NFQ 4-5)",
        "Higher Cert, Apprenticeship (NFQ 6)",
        "Bachelor to Doctorate (NFQ 7-10)",
    ],
    "Northern Ireland": [
        "1-4 GCSEs, O levels, 1 AS, NVQ 1",
        "5+ GCSEs (A*-C), 1-3 AS, NVQ 2, BTEC",
        "2+ A Levels, 4+ AS, NVQ 3, OND/ONC",
        "Degree, Foundation degree, NVQ 4+, HND/HNC",
    ],
}

classification_df = pd.DataFrame(classification_data)

st.dataframe(
    classification_df,
    hide_index=True,
    use_container_width=True,
)

st.caption("NFQ = National Framework of Qualifications (ROI) | NVQ = National Vocational Qualification (NI)")

st.divider()

st.subheader("Educational attainment")

if not EDU_QUAL_PATH.exists():
    st.info("Education qualifications data not yet integrated. Run clean_education_qualifications.py to generate the cleaned CSV.")
else:
    edu_all = pd.read_csv(EDU_QUAL_PATH)
    ensure_cols(edu_all, ["Year", "Region", "Sex", "Qualification", "Percentage", "Absolute"])

    edu_all["Year"] = pd.to_numeric(edu_all["Year"], errors="coerce").astype(int)
    edu_all["Region"] = edu_all["Region"].astype(str).str.strip()
    edu_all["Sex"] = edu_all["Sex"].astype(str).str.strip()
    edu_all["Qualification"] = edu_all["Qualification"].astype(str).str.strip()
    edu_all["Percentage"] = pd.to_numeric(edu_all["Percentage"], errors="coerce")
    edu_all["Absolute"] = pd.to_numeric(edu_all["Absolute"], errors="coerce")

    edu_all = edu_all[edu_all["Region"].isin(regions)].copy()

    if edu_all.empty:
        st.info("Education qualifications file is present but contains no rows after filtering.")
    else:
        sex_filter = st.radio(
            "Sex",
            ["Both sexes", "Male", "Female"],
            horizontal=True,
            key="edu_sex_filter",
        )

        year = int(edu_all["Year"].max())
        edu_y = edu_all[edu_all["Year"] == year].copy()
        edu_y = edu_y[edu_y["Sex"] == sex_filter].copy()

        if edu_y.empty:
            st.info(f"No data available for {sex_filter}.")
        else:
            qual_order = [
                "Basic qualification",
                "Intermediate and advanced qualification",
                "Higher and professional qualification",
                "Other qualification",
                "Qualification not stated",
            ]
            existing_quals = [q for q in qual_order if q in edu_y["Qualification"].unique()]
            remaining_quals = [q for q in edu_y["Qualification"].unique() if q not in qual_order]
            qual_order = existing_quals + sorted(remaining_quals)

            edu_y["Qualification"] = pd.Categorical(edu_y["Qualification"], categories=qual_order, ordered=True)
            edu_y = edu_y.sort_values(["Region", "Qualification"])

            if display_mode == "Absolute numbers":
                metric_col = "Absolute"
                value_label = "Population (count)"
                text_tmpl = "%{text:,.0f}"
                title_suffix = "absolute"
            else:
                metric_col = "Percentage"
                value_label = "Share of population (%)"
                text_tmpl = "%{text:.1f}%"
                title_suffix = "percent"

            fig_edu = px.bar(
                edu_y,
                x="Qualification",
                y=metric_col,
                color="Region",
                barmode="group",
                text=metric_col,
                labels={metric_col: value_label, "Qualification": ""},
                title=f"Educational attainment — {sex_filter} ({year}, {title_suffix})",
                category_orders={"Region": REGIONS, "Qualification": qual_order},
            )
            fig_edu.update_traces(texttemplate=text_tmpl, textposition="outside")
            fig_edu.update_layout(
                height=600,
                margin=dict(l=20, r=20, t=60, b=100),
                legend_title_text="",
            )
            fig_edu.update_xaxes(tickangle=-35)
            st.plotly_chart(fig_edu, width="stretch", config={"displayModeBar": False})

st.divider()

#health
st.header("Health")

if not HEALTH_PATH.exists():
    st.info("Health indicators data will be integrated here.")
else:
    health_all = pd.read_csv(HEALTH_PATH)
    ensure_cols(health_all, ["Year", "Region", "Rating", "Percentage", "Absolute"])

    health_all["Year"] = pd.to_numeric(health_all["Year"], errors="coerce").astype(int)
    health_all["Region"] = health_all["Region"].astype(str).str.strip()
    health_all["Rating"] = health_all["Rating"].astype(str).str.strip()
    health_all["Percentage"] = pd.to_numeric(health_all["Percentage"], errors="coerce")
    health_all["Absolute"] = pd.to_numeric(health_all["Absolute"], errors="coerce")

    health_all = health_all[health_all["Region"].isin(regions)].copy()

    if health_all.empty:
        st.info("General health file is present but contains no rows after filtering.")
    else:
        year = int(health_all["Year"].max())
        health_y = health_all[health_all["Year"] == year].copy()

        rating_order = ["Very good", "Good", "Fair", "Bad", "Very Bad", "Not stated"]
        existing_ratings = [r for r in rating_order if r in health_y["Rating"].unique()]

        health_y["Rating"] = pd.Categorical(health_y["Rating"], categories=existing_ratings, ordered=True)
        health_y = health_y.sort_values(["Region", "Rating"])

        if display_mode == "Absolute numbers":
            metric_col = "Absolute"
            value_label = "Population (count)"
            text_tmpl = "%{text:,.0f}"
            title_suffix = "absolute"
        else:
            metric_col = "Percentage"
            value_label = "Share of population (%)"
            text_tmpl = "%{text:.1f}%"
            title_suffix = "percent"

        fig_health = px.bar(
            health_y,
            x="Rating",
            y=metric_col,
            color="Region",
            barmode="group",
            text=metric_col,
            labels={metric_col: value_label, "Rating": ""},
            title=f"General health — {year} ({title_suffix})",
            category_orders={"Region": REGIONS, "Rating": existing_ratings},
        )
        fig_health.update_traces(texttemplate=text_tmpl, textposition="outside")
        fig_health.update_layout(
            height=520,
            margin=dict(l=20, r=20, t=60, b=100),
            legend_title_text="",
        )
        fig_health.update_xaxes(tickangle=-35)
        st.plotly_chart(fig_health, width="stretch", config={"displayModeBar": False})
        
        st.caption("Note: General health ratings are self-reported by census respondents.")

st.divider()

st.subheader("General health by age")

if not HEALTH_AGE_PATH.exists():
    st.info("Health by age data not yet integrated. Run clean_general_health_by_age.py to generate the cleaned CSV.")
else:
    health_age_all = pd.read_csv(HEALTH_AGE_PATH)
    ensure_cols(health_age_all, ["Year", "Region", "Rating", "Age_Bracket", "Percentage"])

    health_age_all["Year"] = health_age_all["Year"].astype(str).str.strip()
    health_age_all["Region"] = health_age_all["Region"].astype(str).str.strip()
    health_age_all["Rating"] = health_age_all["Rating"].astype(str).str.strip()
    health_age_all["Age_Bracket"] = health_age_all["Age_Bracket"].astype(str).str.strip()
    health_age_all["Percentage"] = pd.to_numeric(health_age_all["Percentage"], errors="coerce")

    health_age_all = health_age_all[health_age_all["Region"].isin(regions)].copy()

    if health_age_all.empty:
        st.info("Health by age file is present but contains no rows after filtering.")
    else:
        rating_order = ["Very good", "Good", "Fair", "Bad", "Very Bad", "Not stated"]
        available_ratings = [r for r in rating_order if r in health_age_all["Rating"].unique()]

        selected_rating = st.selectbox(
            "Select health rating",
            available_ratings,
            index=1 if "Good" in available_ratings else 0,
            key="health_age_rating_selector",
        )

        year = health_age_all["Year"].iloc[0]
        health_age_filtered = health_age_all[health_age_all["Rating"] == selected_rating].copy()

        if health_age_filtered.empty:
            st.info(f"No data available for rating: {selected_rating}")
        else:
            age_order = [
                "0 - 4 years", "5 - 9 years", "10 - 14 years", "15 - 19 years",
                "20 - 24 years", "25 - 29 years", "30 - 34 years", "35 - 39 years",
                "40 - 44 years", "45 - 49 years", "50 - 54 years", "55 - 59 years",
                "60 - 64 years", "65 - 69 years", "70 - 74 years", "75 - 79 years",
                "80 - 84 years", "85 years and over"
            ]
            existing_ages = [a for a in age_order if a in health_age_filtered["Age_Bracket"].unique()]

            health_age_filtered["Age_Bracket"] = pd.Categorical(
                health_age_filtered["Age_Bracket"],
                categories=existing_ages,
                ordered=True
            )
            health_age_filtered = health_age_filtered.sort_values(["Age_Bracket", "Region"])

            fig_health_age = px.bar(
                health_age_filtered,
                x="Age_Bracket",
                y="Percentage",
                color="Region",
                barmode="group",
                text="Percentage",
                labels={"Percentage": "Share of age group (%)", "Age_Bracket": "Age group"},
                title=f"General health: '{selected_rating}' by age — {year}",
                category_orders={"Region": REGIONS, "Age_Bracket": existing_ages},
            )
            fig_health_age.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_health_age.update_layout(
                height=520,
                margin=dict(l=20, r=20, t=60, b=120),
                legend_title_text="",
            )
            fig_health_age.update_xaxes(tickangle=-45)
            st.plotly_chart(fig_health_age, width="stretch", config={"displayModeBar": False})

            st.caption(f"Percentage of each age group reporting '{selected_rating}' general health.")
