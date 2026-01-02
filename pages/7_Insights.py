from __future__ import annotations

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Insights & Recommendations | ROI + NI Dashboard",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💡 Insights & Recommendations")
st.write(
    "This page summarises the main insights from across the dashboard and outlines high-level recommendations "
    "and opportunities to extend the analysis. It is designed as an executive-style synthesis for users."
)
st.caption(
    "Interpretation is based on the indicators presented throughout the dashboard. "
    "Policy implications are framed as considerations, not prescriptions."
)

# Sidebar controls

with st.sidebar:
    st.header("View options")
    tone = st.radio("Detail level", ["Concise", "Detailed"], index=0)
    show_evidence = st.checkbox("Show evidence links to dashboard sections", value=True)
    show_export = st.checkbox("Show 'copy for write-up' boxes", value=True)

# Content (edit wording to match real data)
KEY_FINDINGS = [
    {
        "title": "Economic performance and household pressures can diverge",
        "summary": (
            "Differences in headline economic indicators (e.g., GDP per capita) do not always translate directly into "
            "everyday affordability. Housing costs and rent burden can materially shape lived living standards."
        ),
        "evidence": ["Economy → GDP per capita", "Society → Housing (rent burden, completions)"],
    },
    {
        "title": "Labour market trends are broadly positive, with differences in pace and resilience",
        "summary": (
            "Employment and unemployment trends improve over time in both jurisdictions, but the trajectories can differ, "
            "suggesting structural differences in labour markets and vulnerability to shocks."
        ),
        "evidence": ["Economy → Employment/unemployment"],
    },
    {
        "title": "Demographic structure influences demand for services and housing",
        "summary": (
            "Population age structure and dependency ratios shape demand for education, healthcare, and housing. "
            "Changes in working-age share and ageing trends have clear implications for planning and resource allocation."
        ),
        "evidence": ["Demographics → Population pyramid", "Demographics → Age dependency ratio", "Society → Health/Education/Housing"],
    },
    {
        "title": "NI identity and religion indicators provide crucial context (descriptive, not causal)",
        "summary": (
            "Identity and religion splits in NI add important context for understanding social patterns. "
            "They should be interpreted carefully and descriptively, avoiding causal claims without robust evidence."
        ),
        "evidence": ["Demographics → NI identity split", "Demographics → Religion split"],
    },
    {
        "title": "Environmental and urban factors matter; capital-city comparison adds practical context",
        "summary": (
            "Emissions, air quality, and weather patterns vary with geography, energy use, and urbanisation. "
            "City-level views (e.g., Dublin vs Belfast) help translate national differences into a human-scale comparison."
        ),
        "evidence": ["Environment → CO₂ emissions", "Environment → Air quality", "Environment → Weather patterns", "Capitals → Dublin vs Belfast"],
    },
]

POLICY_IMPLICATIONS = [
    {
        "title": "Treat housing affordability and supply as central determinants of living standards",
        "summary": (
            "Where rent burden is high and supply growth is weak, living standards can be constrained even when "
            "headline economic indicators are strong. Sustained focus on supply, planning, and delivery capacity "
            "is likely to be a high-impact lever."
        ),
        "evidence": ["Society → Housing (rent vs income, completions)", "Economy → GDP per capita (context)"],
    },
    {
        "title": "Align service planning with demographic pressures",
        "summary": (
            "Areas with higher youth dependency require education and childcare capacity; areas with higher old-age dependency "
            "require health and social care planning. Policy and budgeting should reflect these demographic realities."
        ),
        "evidence": ["Demographics → Age dependency ratio", "Society → Health/Education"],
    },
    {
        "title": "Support labour market participation through skills and opportunity pathways",
        "summary": (
            "Education outcomes and labour market performance are closely linked. Improving access to skills and progression routes "
            "can strengthen long-run employment resilience and reduce inequality between places."
        ),
        "evidence": ["Society → Education (attainment, early leavers)", "Economy → Employment/unemployment"],
    },
    {
        "title": "Use environmental monitoring to target high-impact interventions in cities",
        "summary": (
            "Air quality and emissions improvements are often most visible at the urban level. City monitoring can support "
            "evidence-based transport and energy interventions, with clear co-benefits for public health."
        ),
        "evidence": ["Environment → Air quality", "Environment → CO₂ emissions", "Capitals → City comparison"],
    },
]

# Future work: how the product/analysis could be extended for stakeholders
FUTURE_WORK = [
    {
        "title": "Greater geographic granularity",
        "summary": (
            "Extending the dashboard to county or local-authority level would help users identify within-region variation "
            "that national averages can mask, particularly for housing, health, and crime indicators."
        ),
    },
    {
        "title": "Longer historical coverage and structural break analysis",
        "summary": (
            "Adding longer time series would enable clearer identification of structural changes, such as the impact of "
            "economic shocks, major reforms, or demographic transitions."
        ),
    },
    {
        "title": "Linking outcomes across domains",
        "summary": (
            "Future versions could explore relationships between indicators (e.g., housing costs and health outcomes, "
            "education and labour market performance) to move from comparison towards explanation."
        ),
    },
    {
        "title": "User-driven benchmarking and peer comparison",
        "summary": (
            "Allowing benchmarking against additional regions or peer economies would add context and support comparative analysis "
            "for decision-makers."
        ),
    },
    {
        "title": "Improved accessibility and interpretability",
        "summary": (
            "Enhancements such as clearer annotations, glossary tooltips, and accessibility features would help ensure the dashboard "
            "is usable for non-technical audiences."
        ),
    },
]

# Helpers

def render_section(items: list[dict], label: str) -> None:
    if tone == "Concise":
        for i, item in enumerate(items, start=1):
            st.markdown(f"**{i}. {item['title']}**")
            st.caption(item["summary"])
            if show_evidence and "evidence" in item:
                st.caption("Evidence: " + " • ".join(item["evidence"]))
            st.markdown("")
    else:
        for i, item in enumerate(items, start=1):
            st.markdown(f"### {label} {i}. {item['title']}")
            st.write(item["summary"])
            if show_evidence and "evidence" in item:
                with st.expander("Evidence (where this appears in the dashboard)"):
                    for ev in item["evidence"]:
                        st.markdown(f"- {ev}")
            st.markdown("")

def export_markdown(items: list[dict], include_evidence: bool = False) -> str:
    lines: list[str] = []
    for item in items:
        if include_evidence and "evidence" in item:
            lines.append(
                f"- **{item['title']}** — {item['summary']}  \n"
                f"  _Evidence:_ {', '.join(item['evidence'])}"
            )
        else:
            lines.append(f"- **{item['title']}** — {item['summary']}")
    return "\n".join(lines)


# Render

st.subheader("🔍 Key Findings")
render_section(KEY_FINDINGS, "Finding")
if show_export:
    with st.expander("Copy for write-up: Key Findings (Markdown)"):
        st.code(export_markdown(KEY_FINDINGS, include_evidence=show_evidence), language="markdown")

st.divider()

st.subheader("🏛️ Policy Implications")
render_section(POLICY_IMPLICATIONS, "Implication")
if show_export:
    with st.expander("Copy for write-up: Policy Implications (Markdown)"):
        st.code(export_markdown(POLICY_IMPLICATIONS, include_evidence=show_evidence), language="markdown")

st.divider()

st.subheader("🔮 Future Work")
render_section(FUTURE_WORK, "Future work")
if show_export:
    with st.expander("Copy for write-up: Future Work (Markdown)"):
        st.code(export_markdown(FUTURE_WORK, include_evidence=False), language="markdown")

st.divider()

st.subheader("⚠️ Limitations & Interpretation Guidance")
st.warning(
    "Not all indicators are perfectly comparable across ROI and NI due to differences in definitions, "
    "data collection methods, and coverage. The dashboard should be used to support comparative understanding "
    "and question-generation, rather than definitive causal conclusions."
)

with st.expander("Optional: quick checklist (useful for an examiner/user)"):
    checklist = pd.DataFrame(
        {
            "Quality check": [
                "Each chart has a corresponding source listed in the Sources page",
                "Definitions/units are clear (e.g., per capita vs totals, £ vs € vs USD)",
                "Comparability notes included where necessary",
                "Key findings are supported by multiple indicators (triangulation)",
                "Limitations are acknowledged and avoid over-claiming causality",
            ],
            "Status": ["", "", "", "", ""],
        }
    )
    st.dataframe(checklist, hide_index=True, use_container_width=True)
