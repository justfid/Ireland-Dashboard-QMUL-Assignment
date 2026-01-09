from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.common import ensure_cols, ROI, NI, REGIONS


#chart height constants
CHART_HEIGHT_STANDARD = 600
CHART_HEIGHT_MEDIUM = 520
CHART_HEIGHT_SMALL = 450
CHART_HEIGHT_LARGE = 500
CHART_HEIGHT_TABLE = 460

#page config
st.set_page_config(
    page_title="Cultural Identity",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

#paths
CLEAN_DIR = Path("data/cleaned/cultural_identity")
RELIGION_PATH = CLEAN_DIR / "religion.csv"
RELIGION_BY_AGE_PATH = CLEAN_DIR / "religion_by_age.csv"
ETHNICITY_PATH = CLEAN_DIR / "ethnicity.csv"
MARRIAGE_PATH = CLEAN_DIR / "marriage.csv"
LANGUAGES_PATH = CLEAN_DIR / "languages.csv"
MIGRATION_PATH = CLEAN_DIR / "migration.csv"


#page header
st.title("🌍 Cultural Identity")
st.write(
    "This section examines cultural characteristics including religion, ethnicity, languages, marriage patterns, and migration origins across both jurisdictions."
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
        key="cultural_display_mode",
    )


#religion
st.header("Religion")

if not RELIGION_PATH.exists():
    st.info("Religion data not yet integrated.")
else:
    rel_all = pd.read_csv(RELIGION_PATH)
    ensure_cols(rel_all, ["Year", "Region", "Religion", "Percentage", "Absolute"])

    rel_all["Year"] = rel_all["Year"].astype(str).str.strip()
    rel_all["Region"] = rel_all["Region"].astype(str).str.strip()
    rel_all["Religion"] = rel_all["Religion"].astype(str).str.strip()
    rel_all["Percentage"] = pd.to_numeric(rel_all["Percentage"], errors="coerce")
    rel_all["Absolute"] = pd.to_numeric(rel_all["Absolute"], errors="coerce")

    rel_all = rel_all[rel_all["Region"].isin(regions)].copy()

    if rel_all.empty:
        st.info("Religion file is present but contains no rows after filtering.")
    else:
        year = rel_all["Year"].iloc[0]
        
        #define religion order (largest first, not stated last)
        rel_order = [
            "Roman Catholic",
            "Protestant and Other Christian religion, n.e.s.",
            "No religion",
            "Islam",
            "Hindu",
            "Other stated religions (1)",
            "Not stated"
        ]
        existing_rel = [r for r in rel_order if r in rel_all["Religion"].unique()]
        
        rel_all["Religion"] = pd.Categorical(rel_all["Religion"], categories=existing_rel, ordered=True)
        rel_all = rel_all.sort_values(["Region", "Religion"])

        use_log_scale_rel = st.checkbox("Use logarithmic scale", value=False, help="Logarithmic scale improves visibility of smaller religious groups", key="rel_log")

        rel_filtered = rel_all.copy()
        filtered_rel = existing_rel

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

        scale_suffix = "log scale" if use_log_scale_rel else "linear scale"

        fig_rel = px.bar(
            rel_filtered,
            x="Religion",
            y=metric_col,
            color="Region",
            barmode="group",
            text=metric_col,
            labels={metric_col: value_label, "Religion": ""},
            title=f"Religious affiliation by region — {year} ({title_suffix}, {scale_suffix})",
            category_orders={"Region": REGIONS, "Religion": filtered_rel},
            log_y=use_log_scale_rel,
        )
        fig_rel.update_traces(texttemplate=text_tmpl, textposition="outside")
        fig_rel.update_layout(
            height=CHART_HEIGHT_STANDARD,
            margin=dict(l=20, r=20, t=60, b=120),
            legend_title_text="",
        )
        fig_rel.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_rel, width="stretch", config={"displayModeBar": False})
        
        if use_log_scale_rel:
            st.caption("Logarithmic scale used to improve visibility of smaller religious groups.")
        else:
            st.caption("Linear scale shows the relative distribution of religious affiliations.")
        
        #religion by age subsection
        st.subheader("Religious Affiliation by Age")
        
        if not RELIGION_BY_AGE_PATH.exists():
            st.info("Religion by age data not yet integrated.")
        else:
            rel_age_all = pd.read_csv(RELIGION_BY_AGE_PATH)
            ensure_cols(rel_age_all, ["Year", "Region", "Religion", "Age_Bracket", "Percentage"])
            
            rel_age_all["Year"] = rel_age_all["Year"].astype(str).str.strip()
            rel_age_all["Region"] = rel_age_all["Region"].astype(str).str.strip()
            rel_age_all["Religion"] = rel_age_all["Religion"].astype(str).str.strip()
            rel_age_all["Age_Bracket"] = rel_age_all["Age_Bracket"].astype(str).str.strip()
            rel_age_all["Percentage"] = pd.to_numeric(rel_age_all["Percentage"], errors="coerce")
            
            rel_age_all = rel_age_all[rel_age_all["Region"].isin(regions)].copy()
            
            if rel_age_all.empty:
                st.info("Religion by age file is present but contains no rows after filtering.")
            else:
                #get unique religions for dropdown
                religions_available = [
                    "Roman Catholic",
                    "Protestant and Other Christian religion, n.e.s.",
                    "No religion",
                    "Islam",
                    "Hindu",
                    "Other stated religions (1)",
                    "Not stated"
                ]
                religions_in_data = [r for r in religions_available if r in rel_age_all["Religion"].unique()]
                
                selected_religion = st.selectbox(
                    "Select Religion",
                    religions_in_data,
                    index=0,
                    key="rel_age_selector"
                )
                
                #filter to selected religion
                rel_age_filtered = rel_age_all[rel_age_all["Religion"] == selected_religion].copy()
                
                #define age bracket order
                age_order = [
                    "0 - 4 years", "5 - 9 years", "10 - 14 years", "15 - 19 years",
                    "20 - 24 years", "25 - 29 years", "30 - 34 years", "35 - 39 years",
                    "40 - 44 years", "45 - 49 years", "50 - 54 years", "55 - 59 years",
                    "60 - 64 years", "65 - 69 years", "70 - 74 years", "75 - 79 years",
                    "80 - 84 years", "85 years and over"
                ]
                existing_ages = [a for a in age_order if a in rel_age_filtered["Age_Bracket"].unique()]
                rel_age_filtered["Age_Bracket"] = pd.Categorical(rel_age_filtered["Age_Bracket"], categories=existing_ages, ordered=True)
                rel_age_filtered = rel_age_filtered.sort_values(["Age_Bracket"])
                
                #create diverging data for population pyramid style
                rel_age_roi = rel_age_filtered[rel_age_filtered["Region"] == ROI].copy()
                rel_age_ni = rel_age_filtered[rel_age_filtered["Region"] == NI].copy()
                
                #make ROI values negative for left side
                rel_age_roi["Percentage_Display"] = -rel_age_roi["Percentage"]
                rel_age_ni["Percentage_Display"] = rel_age_ni["Percentage"]
                
                #combine for plotting
                rel_age_diverging = pd.concat([rel_age_roi, rel_age_ni])
                
                fig_rel_age = px.bar(
                    rel_age_diverging,
                    y="Age_Bracket",
                    x="Percentage_Display",
                    color="Region",
                    orientation="h",
                    text="Percentage",
                    labels={"Percentage_Display": "Percentage of age group (%)", "Age_Bracket": "Age Group"},
                    title=f'"{selected_religion}" age distribution by region — {year}',
                    category_orders={"Region": REGIONS, "Age_Bracket": list(reversed(existing_ages))},
                )
                fig_rel_age.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
                fig_rel_age.update_layout(
                    height=CHART_HEIGHT_STANDARD,
                    margin=dict(l=20, r=20, t=60, b=20),
                    legend_title_text="",
                    xaxis=dict(
                        tickvals=[-20, -15, -10, -5, 0, 5, 10, 15, 20],
                        ticktext=["20", "15", "10", "5", "0", "5", "10", "15", "20"]
                    )
                )
                st.plotly_chart(fig_rel_age, width="stretch", config={"displayModeBar": False})
                
                st.caption(f"Population distribution showing the share of each age group identifying as {selected_religion}. {ROI} (left) and {NI} (right).")

st.divider()


#ethnicity
st.header("Ethnicity")

if not ETHNICITY_PATH.exists():
    st.info("Ethnicity data not yet integrated.")
else:
    eth_all = pd.read_csv(ETHNICITY_PATH)
    ensure_cols(eth_all, ["Year", "Region", "Ethnicity", "Percentage", "Absolute"])

    eth_all["Year"] = eth_all["Year"].astype(str).str.strip()
    eth_all["Region"] = eth_all["Region"].astype(str).str.strip()
    eth_all["Ethnicity"] = eth_all["Ethnicity"].astype(str).str.strip()
    eth_all["Percentage"] = pd.to_numeric(eth_all["Percentage"], errors="coerce")
    eth_all["Absolute"] = pd.to_numeric(eth_all["Absolute"], errors="coerce")

    eth_all = eth_all[eth_all["Region"].isin(regions)].copy()

    if eth_all.empty:
        st.info("Ethnicity file is present but contains no rows after filtering.")
    else:
        year = eth_all["Year"].iloc[0]
        
        #define ethnicity order
        eth_order = ["White", "Irish Traveller", "Asian", "Black", "Other including mixed background", "Not stated"]
        existing_eth = [e for e in eth_order if e in eth_all["Ethnicity"].unique()]
        
        eth_all["Ethnicity"] = pd.Categorical(eth_all["Ethnicity"], categories=existing_eth, ordered=True)
        eth_all = eth_all.sort_values(["Region", "Ethnicity"])

        col1, col2 = st.columns(2)
        with col1:
            exclude_white = st.checkbox("Exclude White", value=False, help="Focus on minority ethnic groups only")
        with col2:
            use_log_scale = st.checkbox("Use logarithmic scale", value=False, help="Logarithmic scale improves visibility of smaller ethnic groups")

        #filter data based on exclude_white
        if exclude_white:
            eth_filtered = eth_all[eth_all["Ethnicity"] != "White"].copy()
            #recategorize without white
            filtered_eth = [e for e in existing_eth if e != "White"]
            eth_filtered["Ethnicity"] = pd.Categorical(eth_filtered["Ethnicity"], categories=filtered_eth, ordered=True)
        else:
            eth_filtered = eth_all.copy()
            filtered_eth = existing_eth

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

        scale_suffix = "log scale" if use_log_scale else "linear scale"
        group_label = "minority groups" if exclude_white else "ethnic groups"

        fig_eth = px.bar(
            eth_filtered,
            x="Ethnicity",
            y=metric_col,
            color="Region",
            barmode="group",
            text=metric_col,
            labels={metric_col: value_label, "Ethnicity": ""},
            title=f"{'Minority' if exclude_white else 'Ethnic'} groups by region — {year} ({title_suffix}, {scale_suffix})",
            category_orders={"Region": REGIONS, "Ethnicity": filtered_eth},
            log_y=use_log_scale,
        )
        fig_eth.update_traces(texttemplate=text_tmpl, textposition="outside")
        fig_eth.update_layout(
            height=CHART_HEIGHT_STANDARD,
            margin=dict(l=20, r=20, t=60, b=120),
            legend_title_text="",
        )
        fig_eth.update_xaxes(tickangle=-45)
        st.plotly_chart(fig_eth, width="stretch", config={"displayModeBar": False})
        
        if exclude_white:
            st.caption("Showing minority ethnic groups only (White excluded). This view highlights diversity among non-White populations.")
        elif use_log_scale:
            st.caption("Logarithmic scale used to improve visibility of smaller ethnic groups.")
        else:
            st.caption("Linear scale shows the relative dominance of the White ethnic group.")

st.divider()


#languages
st.header("Languages")

if not LANGUAGES_PATH.exists():
    st.info("Languages data not yet integrated.")
else:
    lang_all = pd.read_csv(LANGUAGES_PATH)
    ensure_cols(lang_all, ["Year", "Region", "Language", "Percentage", "Absolute"])
    
    lang_all["Year"] = lang_all["Year"].astype(int)
    lang_all["Region"] = lang_all["Region"].astype(str).str.strip()
    lang_all["Language"] = lang_all["Language"].astype(str).str.strip()
    lang_all["Percentage"] = pd.to_numeric(lang_all["Percentage"], errors="coerce")
    lang_all["Absolute"] = pd.to_numeric(lang_all["Absolute"], errors="coerce")
    
    lang_all = lang_all[lang_all["Region"].isin(regions)].copy()
    
    if lang_all.empty:
        st.info("Languages file is present but contains no rows after filtering.")
    else:
        year = lang_all["Year"].iloc[0]
        
        st.write(
            "Languages spoken as the main language (other than English) among residents aged 3 years and over. "
            "This data reflects linguistic diversity and migration patterns."
        )
        st.write("")
        
        #sort by percentage descending
        lang_all = lang_all.sort_values("Percentage", ascending=True)
        
        if display_mode == "Absolute numbers":
            metric_col = "Absolute"
            value_label = "Population (count)"
            text_tmpl = "%{text:,.0f}"
            title_suffix = "absolute"
        else:
            metric_col = "Percentage"
            value_label = "Share (%)"
            text_tmpl = "%{text:.1f}%"
            title_suffix = "percent"
        
        fig_lang = px.bar(
            lang_all,
            y="Language",
            x=metric_col,
            color="Region",
            orientation="h",
            barmode="group",
            text=metric_col,
            labels={metric_col: value_label, "Language": ""},
            title=f"Main languages spoken (other than English) by region — {year} ({title_suffix})",
            category_orders={"Region": REGIONS},
        )
        fig_lang.update_traces(texttemplate=text_tmpl, textposition="outside")
        fig_lang.update_layout(
            height=CHART_HEIGHT_STANDARD,
            margin=dict(l=20, r=20, t=60, b=60),
            legend_title_text="",
        )
        st.plotly_chart(fig_lang, use_container_width=True, config={"displayModeBar": False})
        
        st.caption(f"Population aged 3 years and over who speak these languages as their main language — {year}.")

st.divider()


#migration (country of origin)
st.header("Migration")

if not MIGRATION_PATH.exists():
    st.info("Migration data not yet integrated.")
else:
    mig_all = pd.read_csv(MIGRATION_PATH)
    ensure_cols(mig_all, ["Year", "Region", "Country", "Percentage", "Absolute"])
    
    mig_all["Year"] = mig_all["Year"].astype(str).str.strip()
    mig_all["Region"] = mig_all["Region"].astype(str).str.strip()
    mig_all["Country"] = mig_all["Country"].astype(str).str.strip()
    mig_all["Percentage"] = pd.to_numeric(mig_all["Percentage"], errors="coerce")
    mig_all["Absolute"] = pd.to_numeric(mig_all["Absolute"], errors="coerce")
    
    if mig_all.empty:
        st.info("Migration file is present but contains no rows.")
    else:
        year = mig_all["Year"].iloc[0]
        
        st.write(
            "The tables below show the top 12 places of birth for residents in each region. "
            "This includes individuals born in the region itself as well as those born abroad, "
            "providing insight into migration patterns and population diversity."
        )
        st.write("")
        
        #split data by region
        mig_roi = mig_all[mig_all["Region"] == ROI].copy()
        mig_ni = mig_all[mig_all["Region"] == NI].copy()
        
        #sort by percentage descending
        mig_roi = mig_roi.sort_values("Percentage", ascending=False)
        mig_ni = mig_ni.sort_values("Percentage", ascending=False)
        
        #create side by side columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"{ROI}")
            if display_mode == "Absolute numbers":
                display_df_roi = mig_roi[["Country", "Absolute"]].copy()
                display_df_roi["Absolute"] = display_df_roi["Absolute"].apply(lambda x: f"{x:,.0f}")
                display_df_roi = display_df_roi.rename(columns={"Country": "Place of Birth", "Absolute": "Population"})
            else:
                display_df_roi = mig_roi[["Country", "Percentage"]].copy()
                display_df_roi["Percentage"] = display_df_roi["Percentage"].apply(lambda x: f"{x:.2f}%")
                display_df_roi = display_df_roi.rename(columns={"Country": "Place of Birth", "Percentage": "Share (%)"})
            
            st.dataframe(display_df_roi, hide_index=True, use_container_width=True, height=CHART_HEIGHT_TABLE)
        
        with col2:
            st.subheader(f"{NI}")
            if display_mode == "Absolute numbers":
                display_df_ni = mig_ni[["Country", "Absolute"]].copy()
                display_df_ni["Absolute"] = display_df_ni["Absolute"].apply(lambda x: f"{x:,.0f}")
                display_df_ni = display_df_ni.rename(columns={"Country": "Place of Birth", "Absolute": "Population"})
            else:
                display_df_ni = mig_ni[["Country", "Percentage"]].copy()
                display_df_ni["Percentage"] = display_df_ni["Percentage"].apply(lambda x: f"{x:.2f}%")
                display_df_ni = display_df_ni.rename(columns={"Country": "Place of Birth", "Percentage": "Share (%)"})
            
            st.dataframe(display_df_ni, hide_index=True, use_container_width=True, height=CHART_HEIGHT_TABLE)
        
        st.caption(f"Top places of birth for residents — {year}.")

st.divider()


#marriage
st.header("Marriage")
st.write("Marriage patterns and trends over a 20-year period, showing changes in marital status across both regions.")

if not MARRIAGE_PATH.exists():
    st.info("Marriage data not yet integrated.")
else:
    mar_all = pd.read_csv(MARRIAGE_PATH)
    ensure_cols(mar_all, ["Year", "Sex", "Status", "Region", "Percentage", "Absolute"])
    
    mar_all["Year"] = mar_all["Year"].astype(str).str.strip()
    mar_all["Sex"] = mar_all["Sex"].astype(str).str.strip()
    mar_all["Status"] = mar_all["Status"].astype(str).str.strip()
    mar_all["Region"] = mar_all["Region"].astype(str).str.strip()
    mar_all["Percentage"] = pd.to_numeric(mar_all["Percentage"], errors="coerce")
    mar_all["Absolute"] = pd.to_numeric(mar_all["Absolute"], errors="coerce")
    
    mar_all = mar_all[mar_all["Region"].isin(regions)].copy()
    
    if mar_all.empty:
        st.info("Marriage file is present but contains no rows after filtering.")
    else:
        #sex selection toggle
        sex_selection = st.radio(
            "Select demographic",
            ["Both sexes", "Male", "Female"],
            horizontal=True,
            key="marriage_sex_toggle"
        )
        
        #filter by selected sex
        mar_filtered = mar_all[mar_all["Sex"] == sex_selection].copy()
        
        #define status order
        status_order = ["Single", "Married", "Separated", "Divorced", "Widowed"]
        existing_statuses = [s for s in status_order if s in mar_filtered["Status"].unique()]
        mar_filtered["Status"] = pd.Categorical(mar_filtered["Status"], categories=existing_statuses, ordered=True)
        mar_filtered = mar_filtered.sort_values(["Year", "Region", "Status"])
        
        #time series graph
        st.subheader("Marital Status Trends Over Time")
        
        #status selector
        selected_status = st.selectbox(
            "Select marital status to display",
            existing_statuses,
            index=existing_statuses.index("Married"),
            key="marriage_status_selector"
        )
        
        #filter to selected status
        mar_time_filtered = mar_filtered[mar_filtered["Status"] == selected_status].copy()
        
        fig_mar_time = px.line(
            mar_time_filtered,
            x="Year",
            y="Percentage",
            color="Region",
            markers=True,
            labels={"Percentage": "Share of population (%)", "Year": "Census Year"},
            category_orders={"Region": REGIONS},
        )
        fig_mar_time.update_layout(
            height=CHART_HEIGHT_LARGE,
            margin=dict(l=20, r=20, t=60, b=60),
            legend_title_text="",
        )
        st.plotly_chart(fig_mar_time, use_container_width=True, config={"displayModeBar": False})
        
        st.caption("Census years: 2002 (2001/2002), 2011, 2022 (2021/2022). Latter year shown for cross-border census periods.")
        
        #pie charts for latest year
        latest_year = mar_filtered["Year"].max()
        mar_latest = mar_filtered[mar_filtered["Year"] == latest_year].copy()
        
        st.subheader(f"Marital Status Distribution — {latest_year}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            mar_roi = mar_latest[mar_latest["Region"] == ROI].copy()
            if not mar_roi.empty:
                fig_roi = px.pie(
                    mar_roi,
                    values=metric_col,
                    names="Status",
                    title=f"{ROI}",
                    category_orders={"Status": existing_statuses},
                )
                fig_roi.update_traces(textposition="inside", textinfo="percent+label")
                fig_roi.update_layout(
                    height=CHART_HEIGHT_SMALL,
                    margin=dict(l=20, r=20, t=60, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig_roi, use_container_width=True, config={"displayModeBar": False})
        
        with col2:
            mar_ni = mar_latest[mar_latest["Region"] == NI].copy()
            if not mar_ni.empty:
                fig_ni = px.pie(
                    mar_ni,
                    values=metric_col,
                    names="Status",
                    title=f"{NI}",
                    category_orders={"Status": existing_statuses},
                )
                fig_ni.update_traces(textposition="inside", textinfo="percent+label")
                fig_ni.update_layout(
                    height=CHART_HEIGHT_SMALL,
                    margin=dict(l=20, r=20, t=60, b=20),
                    showlegend=False,
                )
                st.plotly_chart(fig_ni, use_container_width=True, config={"displayModeBar": False})
        
        st.caption(f"Marital status distribution for {sex_selection.lower()} aged 15 years and over.")
