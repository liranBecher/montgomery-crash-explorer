from datetime import date, timedelta
from html import escape
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import streamlit as st


STYLESHEET = Path(__file__).with_name("styles.css")
SHARED_CRASHES_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "police-breathalyzers"
    / "alcohol_crashes.parquet"
)
ALL_AREAS = "All Montgomery County"
UNINCORPORATED = "Unincorporated / not recorded"


class SharedFilters(NamedTuple):
    start_date: date
    end_date: date
    area: str
    report_numbers: frozenset[str] | None


@st.cache_data
def _load_shared_filter_data() -> pd.DataFrame:
    crashes = pd.read_parquet(
        SHARED_CRASHES_FILE,
        columns=["report_number", "crash_datetime", "municipality"],
    )
    crashes["area"] = crashes["municipality"].fillna(UNINCORPORATED).str.title()
    crashes.loc[crashes["municipality"].isna(), "area"] = UNINCORPORATED
    return crashes


def apply_shared_filters(crashes: pd.DataFrame, filters: SharedFilters) -> pd.DataFrame:
    """Apply the persistent sidebar subset to any crash dataset."""
    selected = crashes[
        crashes["crash_datetime"].dt.date.between(filters.start_date, filters.end_date)
    ]
    if filters.report_numbers is not None:
        selected = selected[selected["report_number"].isin(filters.report_numbers)]
    return selected


def _reset_shared_filters(start_date: date, end_date: date) -> None:
    st.session_state["filter_start_date"] = start_date
    st.session_state["filter_end_date"] = end_date
    st.session_state["filter_area"] = ALL_AREAS
    for key in tuple(st.session_state):
        if key.endswith(("_selected_cell", "_selected_station", "_selected_weekday", "_selected_hour")):
            st.session_state[key] = None


def load_styles() -> None:
    """Load the local, presentation-only stylesheet."""
    st.markdown(f"<style>{STYLESHEET.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_app_header() -> None:
    st.markdown(
        """
        <header class="mce-app-header">
            <div>
                <p class="mce-eyebrow">Montgomery County, Maryland</p>
                <h1>Crash Explorer</h1>
                <h5>An assistance system for exploring crash data in the Montgomery County area</h5>
                <p class="mce-subtitle">
                    Explore crash patterns, response coverage and alcohol enforcement.
                </p>
            </div>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> SharedFilters:
    crashes = _load_shared_filter_data()
    minimum_date = crashes["crash_datetime"].min().date()
    maximum_date = crashes["crash_datetime"].max().date()
    default_start_date = max(minimum_date, maximum_date - timedelta(days=365 * 5))
    areas = [ALL_AREAS, *sorted(crashes["area"].unique())]
    if not isinstance(st.session_state.get("filter_start_date"), date):
        st.session_state["filter_start_date"] = default_start_date
    if not isinstance(st.session_state.get("filter_end_date"), date):
        st.session_state["filter_end_date"] = maximum_date
    if st.session_state.get("filter_area") not in areas:
        st.session_state["filter_area"] = ALL_AREAS

    with st.sidebar:
        st.header("Shared filters")
        st.caption("Selections update every chart in all three analyses.")
        start_date = st.date_input(
            "From",
            min_value=minimum_date,
            max_value=maximum_date,
            key="filter_start_date",
        )
        end_date = st.date_input(
            "To",
            min_value=minimum_date,
            max_value=maximum_date,
            key="filter_end_date",
        )
        area = st.selectbox("Area", options=areas, key="filter_area")
        if start_date > end_date:
            st.error("From must be on or before To.")
        st.button(
            "Reset filters",
            use_container_width=True,
            on_click=_reset_shared_filters,
            args=(default_start_date, maximum_date),
        )

    report_numbers = None
    if area != ALL_AREAS:
        report_numbers = frozenset(crashes.loc[crashes["area"].eq(area), "report_number"])
    return SharedFilters(start_date, end_date, area, report_numbers)


def render_view_header(title: str, description: str, control_label: str, key: str) -> None:
    heading, control = st.columns([3, 1], gap="large")
    with heading:
        st.markdown(
            f"""
            <div class="mce-view-heading">
                <h2>{escape(title)}</h2>
                <p>{escape(description)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with control:
        st.selectbox(
            control_label,
            options=(),
            index=None,
            placeholder="Awaiting processed data",
            disabled=True,
            key=key,
        )
