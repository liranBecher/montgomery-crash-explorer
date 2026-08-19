import streamlit as st

from ui.components import render_view_header
from ui.fire_rescue import render_fire_rescue_view
from ui.police_breathalyzers import render_police_breathalyzers_view
from ui.safety_hotspots import render_safety_hotspots_view


def render_safety_view() -> None:
    render_safety_hotspots_view()


def render_responder_view() -> None:
    render_fire_rescue_view()


def render_alcohol_enforcement_view() -> None:
    render_police_breathalyzers_view()