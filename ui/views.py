import streamlit as st

from ui.components import render_placeholder_card, render_view_header
from ui.fire_rescue import render_fire_rescue_view
from ui.police_breathalyzers import render_police_breathalyzers_view
from ui.safety_hotspots import render_safety_hotspots_view


def render_safety_view() -> None:
    render_safety_hotspots_view()


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
