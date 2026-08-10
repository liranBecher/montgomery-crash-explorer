import streamlit as st

from ui.components import (
    load_styles,
    render_app_header,
    render_exploration_guide,
    render_sidebar,
)
from ui.views import (
    render_alcohol_enforcement_view,
    render_responder_view,
    render_safety_view,
    render_vehicle_view,
)


st.set_page_config(
    page_title="Montgomery County Crash Explorer",
    page_icon="🚦",
    layout="wide",
)

load_styles()
render_app_header()
render_sidebar()
render_exploration_guide()

safety, responders, breathalyzers, vehicles = st.tabs(
    [
        "Safety Hotspots",
        "First Responders",
        "Police Breathalyzers",
        "Vehicles & Injuries",
    ]
)

with safety:
    render_safety_view()

with responders:
    render_responder_view()

with breathalyzers:
    render_alcohol_enforcement_view()

with vehicles:
    render_vehicle_view()
