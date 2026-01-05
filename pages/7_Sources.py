import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sources | ROI + NI Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📚 Data Sources")
st.write(
    "This page lists all data sources used in the dashboard. "
    "Sources are grouped by dashboard page and topic for clarity and traceability."
)


#load sources
sources_df = pd.read_csv("sources.csv")
sources_df.columns = [c.strip().title() for c in sources_df.columns]

required_cols = {"Page", "Topic", "Source", "Accessed", "Url"}
missing = required_cols - set(sources_df.columns)

if missing:
    st.error(f"Missing required columns in sources.csv: {', '.join(missing)}")
    st.stop()


#page order (matches sidebar)
page_order = [
    "Overview",
    "Demographics",
    "Economy",
    "Society",
    "Environment",
    "Capital Cities",
    "Sources",
]

pages_in_data = list(sources_df["Page"].dropna().unique())
ordered_pages = [p for p in page_order if p in pages_in_data]
ordered_pages += [p for p in pages_in_data if p not in page_order]


#grouped display
for page in ordered_pages:
    st.divider()
    st.header(page)

    page_df = sources_df[sources_df["Page"] == page]

    for topic in sorted(page_df["Topic"].unique()):
        st.subheader(topic)

        topic_df = page_df[page_df["Topic"] == topic]

        for _, row in topic_df.iterrows():
            left, right = st.columns([4, 1])

            with left:
                st.markdown(f"**{row['Source']}**")
                st.caption(f"Accessed: {row['Accessed']}")

            with right:
                if pd.notna(row["Url"]) and row["Url"].strip():
                    st.link_button("Open source", row["Url"])


#raw table
st.divider()
with st.expander("View full sources table (raw CSV)"):
    st.dataframe(
        sources_df,
        hide_index=True,
        use_container_width=True,
    )