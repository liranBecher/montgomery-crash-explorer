import streamlit as st

from ui.components import render_placeholder_card, render_view_header


def render_safety_view() -> None:
    render_view_header(
        "When, where, and under which conditions do crashes occur?",
        "Identify concentrated crash locations and the conditions that distinguish them.",
        "Crash severity",
        "safety_severity",
    )
    map_column, detail_column = st.columns([1.65, 0.8], gap="medium")
    with map_column:
        render_placeholder_card(
            "Crash hotspot map",
            "A geographic view of crash concentration across Montgomery County.",
            height=360,
            interaction_note="Selecting a hotspot will update the condition and time views.",
        )
    with detail_column:
        render_placeholder_card(
            "Hotspot fingerprint",
            "A comparison of road, light, surface, and weather conditions.",
            height=360,
            interaction_note="This panel will compare the selected hotspot with the county baseline.",
        )
    render_placeholder_card(
        "Crash timing",
        "A day-of-week and time-of-day view for the selected location.",
        height=280,
        interaction_note="Selecting a time window will filter the map and condition view.",
    )


def render_responder_view() -> None:
    render_view_header(
        "Where are historical crash-response coverage gaps?",
        "Compare severe-crash demand with existing first-responder locations.",
        "Time of day",
        "responder_daypart",
    )
    map_column, detail_column = st.columns([1.65, 0.8], gap="medium")
    with map_column:
        render_placeholder_card(
            "Crash demand and responder locations",
            "A map combining severe-crash concentration with existing response locations.",
            height=430,
            interaction_note="Map selections will update the coverage-gap summary.",
        )
    with detail_column:
        render_placeholder_card(
            "Candidate coverage gaps",
            "Areas where historical crash demand may be farther from existing responders.",
            height=430,
            interaction_note="Candidates will appear only after the coverage method is finalized.",
        )


def render_alcohol_enforcement_view() -> None:
    render_view_header(
        "Where and when should police breathalyzer enforcement be prioritized?",
        "Police breathalyzers detect alcohol levels; this view will examine alcohol-related crash patterns.",
        "Alcohol-related measure",
        "alcohol_enforcement_measure",
    )
    map_column, detail_column = st.columns([1.2, 1], gap="medium")
    with map_column:
        render_placeholder_card(
            "Alcohol-related crash concentration",
            "A geographic view of alcohol-related crash volume and share.",
            height=430,
            interaction_note="Selecting an area will update the enforcement-time view.",
        )
    with detail_column:
        render_placeholder_card(
            "Breathalyzer enforcement windows",
            "A day-of-week and time-of-day view of alcohol-related crash activity.",
            height=430,
            interaction_note="Priority windows will appear only after the analysis is implemented.",
        )


def render_vehicle_view() -> None:
    render_view_header(
        "How are vehicle age and make associated with driver injury severity?",
        "Compare injury outcomes across vehicle age groups and manufacturers.",
        "Vehicle body type",
        "vehicle_body_type",
    )
    age_column, make_column = st.columns(2, gap="medium")
    with age_column:
        render_placeholder_card(
            "Injury distribution by vehicle age",
            "A proportional comparison of driver injury severity across vehicle age groups.",
            height=430,
            interaction_note="Selecting an age group will update the manufacturer comparison.",
        )
    with make_column:
        render_placeholder_card(
            "Serious injury share by make and age",
            "A matrix comparing serious-injury share while retaining sample-size context.",
            height=430,
            interaction_note="Selecting a cell will reveal its full injury distribution and sample size.",
        )
