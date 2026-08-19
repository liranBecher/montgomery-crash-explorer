from ui.components import SharedFilters
from ui.fire_rescue import render_fire_rescue_view
from ui.police_breathalyzers import render_police_breathalyzers_view
from ui.safety_hotspots import render_safety_hotspots_view


def render_safety_view(shared_filters: SharedFilters) -> None:
    render_safety_hotspots_view(shared_filters)


def render_responder_view(shared_filters: SharedFilters) -> None:
    render_fire_rescue_view(shared_filters)


def render_alcohol_enforcement_view(shared_filters: SharedFilters) -> None:
    render_police_breathalyzers_view(shared_filters)
