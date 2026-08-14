import streamlit as st

from ui.components import render_placeholder_card, render_view_header
from ui.fire_rescue import render_fire_rescue_view
from ui.police_breathalyzers import render_police_breathalyzers_view


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
    render_fire_rescue_view()


def render_alcohol_enforcement_view() -> None:
    render_police_breathalyzers_view()


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
