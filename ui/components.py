from html import escape
from pathlib import Path

import streamlit as st


STYLESHEET = Path(__file__).with_name("styles.css")


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
                    Explore crash patterns, response coverage, alcohol enforcement,
                    and vehicle-related injury severity.
                </p>
            </div>
            <span class="mce-status" role="status">
                Safety, Fire &amp; Rescue, and alcohol analyses connected
            </span>
        </header>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Shared filters")
        st.caption("Shared controls will activate as the remaining view is connected. Connected analyses currently use local controls.")
        st.date_input("From", value=None, disabled=True, key="filter_start_date")
        st.date_input("To", value=None, disabled=True, key="filter_end_date")
        st.selectbox(
            "Area",
            options=(),
            index=None,
            placeholder="Awaiting processed data",
            disabled=True,
            key="filter_area",
        )
        st.divider()
        st.markdown("**Current selection**")
        st.caption("No shared selection. Connected views show their local selection details.")
        st.button("Clear selection", disabled=True, use_container_width=True)
        st.caption("Shared selections will activate as the remaining views are connected.")


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


def render_placeholder_card(
    title: str,
    description: str,
    *,
    height: int,
    interaction_note: str,
) -> None:
    st.markdown(
        f"""
        <section class="mce-card" aria-label="{escape(title)}" style="min-height: {height}px">
            <div class="mce-card-heading">
                <h3>{escape(title)}</h3>
                <span class="mce-card-badge">Planned view</span>
            </div>
            <p>{escape(description)}</p>
            <div class="mce-empty-state" role="status">
                <span class="mce-empty-icon" aria-hidden="true"></span>
                <strong>No visualization is rendered</strong>
                <small>Connect validated processed data to activate this planned view.</small>
            </div>
            <p class="mce-interaction-note">
                <strong>Planned interaction:</strong> {escape(interaction_note)}
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )
