"""Interactive Safety Hotspots overview."""

from datetime import date, timedelta
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from . import colors
from .map_layers import (
    cell_view_state,
    crash_point_layer,
    grid_cell_layer,
    selected_cell_layer,
)


CRASHES_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "processed"
    / "safety-hotspots"
    / "safety_crashes.parquet"
)
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
HOTSPOT_MODES = {
    "All classified crashes": False,
    "Suspected-serious and fatal crashes": True,
}
CONDITION_FAMILIES = {
    "Weather": (
        "weather_group",
        [
            "Clear", "Cloudy", "Rain", "Winter precipitation", "Fog / smoke",
            "Wind", "Other / unknown", "Not recorded",
        ],
    ),
    "Surface": (
        "surface_group",
        [
            "Dry", "Wet", "Snow / slush", "Ice / frost", "Standing water",
            "Loose / contaminated", "Other / unknown", "Not recorded",
        ],
    ),
    "Light": (
        "light_group",
        [
            "Daylight", "Dark - lighted", "Dark - unlighted", "Dawn / dusk",
            "Dark - unknown", "Other / unknown", "Not recorded",
        ],
    ),
}


@st.cache_data
def load_safety_hotspots_data() -> pd.DataFrame:
    """Load the committed deployment dataset."""
    return pd.read_parquet(CRASHES_FILE)


def _cell_centers(cell_ids: pd.Series) -> pd.DataFrame:
    cells = pd.DataFrame({"cell_id": cell_ids.drop_duplicates().sort_values()})
    parts = cells["cell_id"].str.split(":", expand=True).astype(float)
    return cells.assign(
        center_latitude=parts[0] + 0.005,
        center_longitude=parts[1] + 0.005,
    )


def aggregate_cells(crashes: pd.DataFrame) -> pd.DataFrame:
    """Summarize the active crashes by the shared 0.01-degree grid."""
    if crashes.empty:
        return pd.DataFrame(
            columns=[
                "cell_id", "center_latitude", "center_longitude", "crash_count",
                "serious_or_fatal_count", "first_crash", "last_crash", "common_roads",
                "county_share_pct",
            ]
        )
    summary = crashes.groupby("cell_id", as_index=False).agg(
        crash_count=("report_number", "size"),
        serious_or_fatal_count=("serious_or_fatal", "sum"),
        first_crash=("crash_datetime", "min"),
        last_crash=("crash_datetime", "max"),
    )
    roads = (
        crashes.dropna(subset=["road_name"])
        .groupby(["cell_id", "road_name"], as_index=False)
        .size()
        .sort_values(["cell_id", "size", "road_name"], ascending=[True, False, True])
        .groupby("cell_id", as_index=False)
        .head(3)
        .groupby("cell_id", as_index=False)["road_name"]
        .agg(common_roads=lambda values: ", ".join(values))
    )
    return (
        _cell_centers(crashes["cell_id"])
        .merge(summary, on="cell_id", validate="one_to_one")
        .merge(roads, on="cell_id", how="left", validate="one_to_one")
        .fillna({"common_roads": "Not recorded"})
        .assign(county_share_pct=lambda frame: frame["crash_count"].div(len(crashes)).mul(100))
    )


def aggregate_fingerprint(crashes: pd.DataFrame, selected_cell: str | None = None) -> pd.DataFrame:
    """Compare the active county baseline against an optional selected hotspot."""
    selected = crashes[crashes["cell_id"].eq(selected_cell)] if selected_cell else crashes.iloc[0:0]
    frames = []
    for family, (column, categories) in CONDITION_FAMILIES.items():
        county_counts = crashes[column].value_counts().reindex(categories, fill_value=0)
        order = county_counts.sort_values(ascending=False, kind="stable").index.tolist()
        frames.append(
            pd.DataFrame(
                {
                    "family": family,
                    "category": categories,
                    "geography": "County baseline",
                    "crash_count": county_counts.to_numpy(),
                    "share_pct": county_counts.div(len(crashes) or 1).mul(100).to_numpy(),
                    "sample_size": len(crashes),
                    "category_order": [order.index(category) for category in categories],
                }
            )
        )
        if selected_cell is not None:
            selected_counts = selected[column].value_counts().reindex(categories, fill_value=0)
            frames.append(
                pd.DataFrame(
                    {
                        "family": family,
                        "category": categories,
                        "geography": "Selected hotspot",
                        "crash_count": selected_counts.to_numpy(),
                        "share_pct": selected_counts.div(len(selected) or 1).mul(100).to_numpy(),
                        "sample_size": len(selected),
                        "category_order": [order.index(category) for category in categories],
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def summarize_route_type(crashes: pd.DataFrame, selected_cell: str | None) -> str:
    """Return the dominant route type for the selected grid cell, if any."""
    if selected_cell is None:
        return "Not selected"
    selected = crashes[crashes["cell_id"].eq(selected_cell)]
    if selected.empty:
        return "Not recorded"
    route_type = selected["route_group"].fillna("Not recorded").astype(str)
    return route_type.value_counts().idxmax()


def aggregate_timing(
    crashes: pd.DataFrame, geography: str, date_range: str
) -> pd.DataFrame:
    """Return a complete 7-by-24 crash timing grid."""
    complete = pd.MultiIndex.from_product(
        [WEEKDAYS, range(24)], names=["weekday", "hour"]
    ).to_frame(index=False)
    counts = crashes.groupby(["weekday", "hour"], as_index=False).agg(
        crash_count=("report_number", "size")
    )
    timing = complete.merge(counts, how="left").fillna({"crash_count": 0})
    timing["crash_count"] = timing["crash_count"].astype("int64")
    return timing.assign(
        share_pct=timing["crash_count"].div(len(crashes) or 1).mul(100),
        geography=geography,
        date_range=date_range,
    )


def _selection(event: object) -> object:
    return event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})


def _map_cell_from_event(event: object) -> str | None:
    selection = _selection(event)
    objects = selection.get("objects", {}) if isinstance(selection, dict) else getattr(selection, "objects", {})
    selected = objects.get("safety-cells", []) or objects.get("safety-crashes", [])
    return str(selected[0]["cell_id"]) if selected else None


def _time_from_event(event: object) -> tuple[str | None, int | None]:
    selected = _selection(event).get("safety_time_pick", [])
    if isinstance(selected, list) and selected:
        return str(selected[0]["weekday"]), int(selected[0]["hour"])
    if isinstance(selected, dict):
        weekdays, hours = selected.get("weekday", []), selected.get("hour", [])
        if weekdays and hours:
            return str(weekdays[0]), int(hours[0])
    return None, None


def _map_selection_callback(key: str) -> None:
    st.session_state["safety_selected_cell"] = _map_cell_from_event(st.session_state.get(key, {}))
    st.session_state["safety_map_generation"] += 1
    st.session_state["safety_heatmap_generation"] += 1


def _time_selection_callback(key: str) -> None:
    weekday, hour = _time_from_event(st.session_state.get(key, {}))
    st.session_state["safety_selected_weekday"] = weekday
    st.session_state["safety_selected_hour"] = hour
    st.session_state["safety_map_generation"] += 1


def build_map(
    cells: pd.DataFrame,
    crashes: pd.DataFrame,
    selected_cell: str | None,
    date_range: str,
) -> pdk.Deck:
    """Build the selectable hotspot map."""
    plotted = cells.copy()
    minimum, maximum = plotted["crash_count"].min(), plotted["crash_count"].max()
    position = (plotted["crash_count"] - minimum) / max(maximum - minimum, 1)
    plotted["fill_color"] = colors.map_fill_colors(position)
    plotted["title"] = "Grid cell " + plotted["cell_id"]
    plotted["date_range"] = date_range
    plotted["line_1"] = plotted["crash_count"].map(lambda value: f"Crashes: {value:,}")
    plotted["line_2"] = plotted["county_share_pct"].map(lambda value: f"County share: {value:.2f}%")
    plotted["line_3"] = plotted["serious_or_fatal_count"].map(lambda value: f"Serious/fatal: {value:,}")
    plotted["line_4"] = date_range
    plotted["line_5"] = "Roads: " + plotted["common_roads"].astype(str)
    layers = [grid_cell_layer(plotted, "safety-cells")]
    ring = selected_cell_layer(cells, selected_cell, "selected-safety-cell")
    incidents = crash_point_layer(
        crashes,
        selected_cell,
        "safety-crashes",
        (("severity", "Severity"), ("weather_group", "Weather")),
    )
    layers.extend(layer for layer in (ring, incidents) if layer is not None)
    return pdk.Deck(
        layers=layers,
        initial_view_state=cell_view_state(cells, selected_cell),
        map_provider="carto",
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={
            "html": "<b>{title}</b><br>{line_1}<br>{line_2}<br>{line_3}<br>{line_4}<br>{line_5}"
        },
        description="Map of classified crash concentrations by grid cell",
    )


def build_fingerprint(fingerprint: pd.DataFrame) -> alt.VConcatChart:
    """Build four grouped horizontal condition comparisons."""
    charts = []
    for family in CONDITION_FAMILIES:
        plotted = fingerprint[fingerprint["family"].eq(family)]
        order = (
            plotted[plotted["geography"].eq("County baseline")]
            .sort_values("category_order")["category"]
            .tolist()
        )
        charts.append(
            alt.Chart(plotted)
            .mark_bar(cornerRadiusEnd=2)
            .encode(
                x=alt.X("share_pct:Q", title="Share of crashes (%)", scale=alt.Scale(zero=True)),
                y=alt.Y("category:N", title=None, sort=order, axis=alt.Axis(labelLimit=150)),
                yOffset=alt.YOffset("geography:N"),
                color=alt.Color(
                    "geography:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["Selected hotspot", "County baseline"],
                        range=["#d95f45", "#69aaa4"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("family:N", title="Condition"),
                    alt.Tooltip("category:N", title="Category"),
                    alt.Tooltip("geography:N", title="Geography"),
                    alt.Tooltip("crash_count:Q", title="Crashes"),
                    alt.Tooltip("share_pct:Q", title="Share (%)", format=".2f"),
                    alt.Tooltip("sample_size:Q", title="Sample size"),
                ],
            )
            .properties(title=family, height=max(120, len(order) * 17))
        )
    return alt.vconcat(*charts, spacing=14).resolve_scale(y="independent")


def build_heatmap(
    timing: pd.DataFrame, selected_weekday: str | None, selected_hour: int | None
) -> alt.Chart:
    """Build the linked weekday-by-hour crash-count heatmap."""
    time_pick = alt.selection_point(
        name="safety_time_pick",
        fields=["weekday", "hour"],
        toggle=False,
        clear="dblclick",
        empty=False,
    )
    selected = (
        (alt.datum.weekday == selected_weekday) & (alt.datum.hour == selected_hour)
        if selected_weekday is not None
        else time_pick
    )
    return (
        alt.Chart(timing)
        .mark_rect(cornerRadius=2)
        .encode(
            x=alt.X(
                "hour:O",
                title="Hour of day",
                sort=list(range(24)),
                axis=alt.Axis(labelExpr="(datum.value < 10 ? '0' : '') + datum.value + ':00'", labelAngle=-45),
            ),
            y=alt.Y("weekday:N", title=None, sort=WEEKDAYS),
            color=alt.Color(
                "crash_count:Q",
                title="Crash count",
                scale=alt.Scale(range=colors.HEATMAP_RANGE, zero=True),
            ),
            stroke=alt.condition(selected, alt.value("#14202b"), alt.value("#ffffff")),
            strokeWidth=alt.condition(selected, alt.value(3), alt.value(0.5)),
            tooltip=[
                alt.Tooltip("weekday:N", title="Day"),
                alt.Tooltip("hour:O", title="Hour"),
                alt.Tooltip("crash_count:Q", title="Crashes"),
                alt.Tooltip("share_pct:Q", title="Share (%)", format=".2f"),
                alt.Tooltip("geography:N", title="Geography"),
                alt.Tooltip("date_range:N", title="Date range"),
            ],
        )
        .add_params(time_pick)
        .properties(height=300)
    )


def _render_map_legend(cells: pd.DataFrame) -> None:
    st.markdown(
        f"""
        <section class="mce-viz-legend" aria-label="Safety hotspot map legend">
            <strong>Map legend</strong>
            <span class="mce-legend-item"><span class="mce-legend-gradient" aria-hidden="true"></span>Crash count: {int(cells['crash_count'].min())}–{int(cells['crash_count'].max())}; uniform marker size</span>
            <span class="mce-legend-item"><span class="mce-legend-ring" aria-hidden="true"></span>Selected grid cell</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_safety_hotspots_view() -> None:
    """Render the connected Safety Hotspots analysis."""
    st.markdown(
        """
        <div class="mce-view-heading">
            <h2>Where, when, and under which conditions do crashes concentrate?</h2>
            <p>Select a roughly 1 km grid cell to compare its recorded conditions with the county baseline and inspect its crash timing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    crashes = load_safety_hotspots_data()
    minimum_date = crashes["crash_datetime"].min().date()
    maximum_date = crashes["crash_datetime"].max().date()
    date_key = f"safety_date_range_{maximum_date.isoformat()}"
    st.session_state.setdefault(
        date_key, (max(minimum_date, maximum_date - timedelta(days=365 * 5)), maximum_date)
    )

    date_column, mode_column = st.columns([1.35, 1], gap="medium")
    with date_column:
        date_range = st.date_input(
            "Safety crash date range",
            min_value=minimum_date,
            max_value=max(maximum_date, date.today()),
            key=date_key,
        )
    with mode_column:
        mode = st.selectbox("Hotspot mode", HOTSPOT_MODES, key="safety_hotspot_mode")
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Choose both a start and end date.")
        return

    start_date, end_date = date_range
    filtered = crashes[crashes["crash_datetime"].dt.date.between(start_date, end_date)]
    if HOTSPOT_MODES[mode]:
        filtered = filtered[filtered["serious_or_fatal"]]
    render_safety_hotspots_visuals(filtered, mode, start_date, end_date)


@st.fragment
def render_safety_hotspots_visuals(
    filtered: pd.DataFrame, mode: str, start_date: date, end_date: date
) -> None:
    """Render linked map, condition comparison, and timing views."""
    map_generation = st.session_state.setdefault("safety_map_generation", 0)
    heatmap_generation = st.session_state.setdefault("safety_heatmap_generation", 0)
    selected_cell = st.session_state.get("safety_selected_cell")
    selected_weekday = st.session_state.get("safety_selected_weekday")
    selected_hour = st.session_state.get("safety_selected_hour")
    date_label = f"{start_date:%b %d, %Y}–{end_date:%b %d, %Y}"

    linked = filtered
    if selected_weekday is not None:
        linked = linked[
            linked["weekday"].eq(selected_weekday) & linked["hour"].eq(selected_hour)
        ]
    mapped = aggregate_cells(linked)
    if selected_cell and selected_cell not in set(mapped["cell_id"]):
        st.session_state["safety_selected_cell"] = None
        selected_cell = None

    timing_crashes = filtered if selected_cell is None else filtered[filtered["cell_id"].eq(selected_cell)]
    geography = f"Grid cell {selected_cell}" if selected_cell else "Countywide"
    timing = aggregate_timing(timing_crashes, geography, date_label)

    summary, clear = st.columns([3.5, 1])
    with summary:
        time_context = f" · {selected_weekday} {selected_hour:02d}:00" if selected_weekday else ""
        st.caption(
            f"{len(filtered):,} {mode.lower()} · {len(mapped):,} visible cells · {geography}{time_context}"
        )
    with clear:
        if st.button(
            "Clear hotspot selection",
            disabled=selected_cell is None and selected_weekday is None,
            width="stretch",
            key="safety_clear_selection",
        ):
            st.session_state["safety_selected_cell"] = None
            st.session_state["safety_selected_weekday"] = None
            st.session_state["safety_selected_hour"] = None
            st.session_state["safety_map_generation"] = map_generation + 1
            st.session_state["safety_heatmap_generation"] = heatmap_generation + 1
            st.rerun()

    map_column, fingerprint_column = st.columns([1.25, 1], gap="medium")
    with map_column:
        st.subheader("Crash hotspots by grid cell")
        if mapped.empty:
            st.warning("No crashes match the selected time window.")
        else:
            _render_map_legend(mapped)
            map_key = f"safety_map_{map_generation}"
            st.pydeck_chart(
                build_map(mapped, linked, selected_cell, date_label),
                key=map_key,
                on_select=lambda: _map_selection_callback(map_key),
                selection_mode="single-object",
                height=590,
            )
            if selected_cell and selected_cell in set(mapped["cell_id"]):
                row = mapped[mapped["cell_id"].eq(selected_cell)].iloc[0]
                route_type = summarize_route_type(filtered, selected_cell)
                st.markdown(
                    f"""
                    <section class="mce-map-selection-box" aria-label="Current safety hotspot selection">
                        <strong>Grid cell {escape(selected_cell)}</strong>
                        <span>{row['crash_count']:,} crashes · {row['county_share_pct']:.2f}% of active county crashes</span>
                        <span>{row['serious_or_fatal_count']:,} suspected-serious/fatal</span>
                        <small>Route type: {escape(route_type)}</small>
                        <small>Roads: {escape(str(row['common_roads']))}</small>
                    </section>
                    """,
                    unsafe_allow_html=True,
                )
        st.subheader("Crash timing")
        st.caption("Select a weekday-hour cell to filter the map and fingerprint; double-click the heatmap to clear the time selection.")
        heatmap_key = f"safety_heatmap_{heatmap_generation}"
        st.altair_chart(
            build_heatmap(timing, selected_weekday, selected_hour),
            key=heatmap_key,
            on_select=lambda: _time_selection_callback(heatmap_key),
            selection_mode="safety_time_pick",
            width="stretch",
        )
    with fingerprint_column:
        st.subheader("Hotspot fingerprint")
        fingerprint = aggregate_fingerprint(linked, selected_cell)
        if selected_cell is None:
            st.caption(f"County baseline n={len(linked):,} · categories sorted by county share")
        else:
            selected_size = len(linked[linked["cell_id"].eq(selected_cell)])
            st.caption(
                f"Selected hotspot n={selected_size:,} · county baseline n={len(linked):,} · categories sorted by county share"
            )
        st.altair_chart(build_fingerprint(fingerprint), width="stretch")
        if selected_cell is not None and len(linked[linked["cell_id"].eq(selected_cell)]) < 30:
            st.warning("This selected hotspot has fewer than 30 crashes; compare percentages cautiously.")

    st.caption(
        "All classified crashes excludes records without joinable person-level injury severity. The county fingerprint baseline includes the selected cell. Grid cells are 0.01° (approximately 1 km); results describe recorded crashes, not underlying exposure or causal risk."
    )
    if end_date.year == 2026:
        st.caption("The 2026 source snapshot ends on August 5 and is incomplete for annual comparisons.")
