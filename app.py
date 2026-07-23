import streamlit as st


st.set_page_config(
    page_title="Montgomery County Crash Explorer",
    page_icon="🚦",
    layout="wide",
)

st.title("Montgomery County Crash Explorer")
st.caption("Interactive views for crash patterns, response coverage, enforcement priorities, and vehicles.")

with st.sidebar:
    st.header("Filters")
    st.info("Shared filters will be added after the processed-data contract is finalized.")

hotspots, responders, owls, vehicles = st.tabs(
    ["Safety hotspots", "First responders", "Police OWLs", "Vehicles & injuries"]
)

with hotspots:
    st.header("When, where, and under which conditions do crashes occur?")
    st.info("Map, timeline, and condition views go here.")

with responders:
    st.header("Where are crash-response coverage gaps?")
    st.info("Existing stations, severe-crash hotspots, and coverage views go here.")

with owls:
    st.header("Where should police OWLs be prioritized?")
    st.warning("Define what an OWL is and its placement objective before implementing this view.")

with vehicles:
    st.header("How do vehicle make and age relate to driver injury severity?")
    st.info("Vehicle-age and manufacturer views go here.")
