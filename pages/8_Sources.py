import streamlit as st
import pandas as pd

st.title("Sources")
"The sources for all the data used in the dashboard can be found here"

"You can horizontally scroll to see the link"
sources_df = pd.read_csv("sources.csv")

st.dataframe(sources_df, hide_index=True)