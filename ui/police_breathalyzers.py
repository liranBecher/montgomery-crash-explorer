"""Interactive Police Breathalyzers view."""

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


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "police-breathalyzers"
CRASHES_FILE = DATA_DIR / "alcohol_crashes.parquet"
CELLS_FILE = DATA_DIR / "alcohol_cells.parquet"

ALCOHOL_STATUSES = [
    "Alcohol present/contributed",
    "Suspected alcohol use",
    "Combined substance",
]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MAP_MEASURES = {
    "Alcohol-related crash count": ("alcohol_count", "Alcohol-related crashes"),
    "Alcohol-related crash share": ("alcohol_share_pct", "Alcohol-related share (%)"),
}


def effective_minimum_sample(configured: int, selected_weekday: str | None) -> int:
    """Show every occupied map cell while a single heatmap window is active."""
    return 1 if selected_weekday is not None else configured


@st.cache_data
def load_police_breathalyzer_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the committed crash and cell datasets."""
    return pd.read_parquet(CRASHES_FILE), pd.read_parquet(CELLS_FILE)


def aggregate_cells(
    all_crashes: pd.DataFrame,
    alcohol_crashes: pd.DataFrame,
    cells: pd.DataFrame,
) -> pd.DataFrame:
    """Return counts and alcohol-related shares for occupied grid cells."""
    totals = all_crashes.groupby("cell_id", as_index=False).agg(
        total_crashes=("report_number", "size")
    )
    alcohol = alcohol_crashes.groupby("cell_id", as_index=False).agg(
        alcohol_count=("report_number", "size")
    )
    status_counts = (
        alcohol_crashes.groupby(["cell_id", "alcohol_status"], as_index=False)
        .size()
        .assign(label=lambda frame: frame["alcohol_status"] + ": " + frame["size"].astype(str))
        .groupby("cell_id", as_index=False)["label"]
        .agg(status_breakdown=lambda labels: " · ".join(labels))
    )
    roads = (
        alcohol_crashes.dropna(subset=["road_name"])
        .groupby(["cell_id", "road_name"], as_index=False)
        .size()
        .sort_values(["cell_id", "size", "road_name"], ascending=[True, False, True])
        .groupby("cell_id", as_index=False)
        .head(3)
        .groupby("cell_id", as_index=False)["road_name"]
        .agg(common_roads=lambda values: ", ".join(values))
    )
    return (
        cells[["cell_id", "center_latitude", "center_longitude"]]
        .merge(totals, on="cell_id", how="inner", validate="one_to_one")
        .merge(alcohol, on="cell_id", how="inner", validate="one_to_one")
        .merge(status_counts, on="cell_id", how="left", validate="one_to_one")
        .merge(roads, on="cell_id", how="left", validate="one_to_one")
        .fillna(
            {
                "alcohol_count": 0,
                "status_breakdown": "No selected alcohol-related crashes",
                "common_roads": "Not recorded",
            }
        )
        .assign(
            alcohol_count=lambda frame: frame["alcohol_count"].astype("int64"),
            alcohol_share_pct=lambda frame: (
                frame["alcohol_count"].div(frame["total_crashes"]).mul(100).round(2)
            ),
        )
    )


def aggregate_timing(
    all_crashes: pd.DataFrame, alcohol_crashes: pd.DataFrame
) -> pd.DataFrame:
    """Return a complete weekday-by-hour table for the active geography."""
    complete = pd.MultiIndex.from_product(
        [WEEKDAYS, range(24)], names=["weekday", "hour"]
    ).to_frame(index=False)
    totals = all_crashes.groupby(["weekday", "hour"], as_index=False).agg(
        total_crashes=("report_number", "size")
    )
    alcohol = alcohol_crashes.groupby(["weekday", "hour"], as_index=False).agg(
        alcohol_count=("report_number", "size")
    )
    result = complete.merge(totals, how="left").merge(alcohol, how="left").fillna(0)
    result[["total_crashes", "alcohol_count"]] = result[
        ["total_crashes", "alcohol_count"]
    ].astype("int64")
    result["alcohol_share_pct"] = (
        result["alcohol_count"]
        .div(result["total_crashes"].replace(0, pd.NA))
        .mul(100)
        .fillna(0)
        .round(2)
    )
    return result


def _selection(event: object) -> object:
    return event.get("selection", {}) if isinstance(event, dict) else getattr(event, "selection", {})


def _map_cell_from_event(event: object) -> str | None:
    selection = _selection(event)
    objects = selection.get("objects", {}) if isinstance(selection, dict) else getattr(selection, "objects", {})
    selected = objects.get("alcohol-cells", []) or objects.get("alcohol-crashes", [])
    return str(selected[0]["cell_id"]) if selected else None


def _time_from_event(event: object) -> tuple[str | None, int | None]:
    selection = _selection(event)
    selected = selection.get("time_pick", []) if selection is not None else []
    if isinstance(selected, list) and selected:
        return str(selected[0]["weekday"]), int(selected[0]["hour"])
    if isinstance(selected, dict):
        weekdays, hours = selected.get("weekday", []), selected.get("hour", [])
        if weekdays and hours:
            return str(weekdays[0]), int(hours[0])
    return None, None


def _map_selection_callback(key: str) -> None:
    st.session_state["alcohol_selected_cell"] = _map_cell_from_event(
        st.session_state.get(key, {})
    )
    st.session_state["alcohol_map_generation"] += 1
    st.session_state["alcohol_heatmap_generation"] += 1


def _time_selection_callback(key: str) -> None:
    weekday, hour = _time_from_event(st.session_state.get(key, {}))
    if weekday is not None:
        st.session_state["alcohol_selected_weekday"] = weekday
        st.session_state["alcohol_selected_hour"] = hour
        st.session_state["alcohol_map_generation"] += 1


def build_map(
    cells: pd.DataFrame,
    crashes: pd.DataFrame,
    measure: str,
    selected_cell: str | None,
) -> pdk.Deck:
    """Build the alcohol-related cell map."""
    value_column, value_label = MAP_MEASURES[measure]

    plotted = cells.copy()

    minimum = plotted[value_column].min()
    maximum = plotted[value_column].max()

    position = (
        plotted[value_column] - minimum
    ) / max(maximum - minimum, 1)

    plotted["fill_color"] = colors.map_fill_colors(position)
    plotted["original_fill_color"] = plotted["fill_color"]

    plotted["title"] = "Grid cell " + plotted["cell_id"]

    plotted["line_1"] = plotted["alcohol_count"].map(
        lambda value: f"Alcohol-related crashes: {value:,}"
    )

    plotted["line_2"] = plotted.apply(
        lambda row: (
            f"Share: {row['alcohol_share_pct']:.1f}% "
            f"of {row['total_crashes']:,} crashes"
        ),
        axis=1,
    )

    plotted["line_3"] = plotted["status_breakdown"]
    plotted["line_4"] = "Roads: " + plotted["common_roads"].astype(str)

    # Remove selected cell from the hoverable base layer
    if selected_cell:
        base_cells = plotted[
            ~plotted["cell_id"].eq(selected_cell)
        ].copy()
    else:
        base_cells = plotted.copy()

    layers = [
        grid_cell_layer(
            base_cells,
            "alcohol-cells",
        )
    ]

    ring = selected_cell_layer(
        plotted,
        selected_cell,
        "selected-alcohol-cell",
        fill_alpha=12,
    )

    incidents = crash_point_layer(
        crashes,
        selected_cell,
        "alcohol-crashes",
        (
            ("alcohol_status", "Alcohol status"),
            ("municipality", "Municipality"),
        ),
    )

    layers.extend(
        layer
        for layer in (ring, incidents)
        if layer is not None
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=cell_view_state(
            cells,
            selected_cell,
        ),
        map_provider="carto",
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={
            "html": (
                "<b>{title}</b><br>"
                "{line_1}<br>"
                "{line_2}<br>"
                "{line_3}<br>"
                "{line_4}"
            )
        },
        description=f"Map colored by {value_label.lower()}",
    )


def build_heatmap(
    timing: pd.DataFrame,
    measure: str,
    selected_weekday: str | None,
    selected_hour: int | None,
) -> alt.Chart:
    """Build the linked concentric weekday-by-hour alcohol timing heatmap."""
    import math

    value_column, value_label = MAP_MEASURES[measure]
    plotted = timing.copy()
    hour_order = list(range(6, 24)) + list(range(0, 6))
    hour_position = {hour: index for index, hour in enumerate(hour_order)}
    weekday_position = {day: index for index, day in enumerate(WEEKDAYS)}
    angle_step = 2 * math.pi / 24

    plotted["theta_start"] = plotted["hour"].map(
        lambda hour: hour_position[int(hour)] * angle_step
    )
    plotted["theta_end"] = plotted["theta_start"] + angle_step
    inner_radius, ring_width = 55, 24
    plotted["radius_inner"] = plotted["weekday"].map(
        lambda day: inner_radius + weekday_position[day] * ring_width
    )
    plotted["radius_outer"] = plotted["radius_inner"] + ring_width
    plotted["hour_label"] = plotted["hour"].map(lambda hour: f"{int(hour):02d}:00")

    time_pick = alt.selection_point(
        name="time_pick", fields=["weekday", "hour"], toggle=False,
        clear="dblclick", empty=False,
    )
    selected = (
        (alt.datum.weekday == selected_weekday) & (alt.datum.hour == selected_hour)
        if selected_weekday is not None else time_pick
    )
    heatmap = (
        alt.Chart(plotted).mark_arc(cornerRadius=1, padAngle=0.006).encode(
            theta=alt.Theta("theta_start:Q", scale=None),
            theta2=alt.Theta2("theta_end:Q"),
            radius=alt.Radius("radius_outer:Q", scale=None),
            radius2=alt.Radius2("radius_inner:Q"),
            color=alt.Color(
                f"{value_column}:Q", title=value_label,
                scale=alt.Scale(range=colors.HEATMAP_RANGE, zero=True),
            ),
            stroke=alt.condition(selected, alt.value("#14202b"), alt.value("#ffffff")),
            strokeWidth=alt.condition(selected, alt.value(3), alt.value(0.7)),
            opacity=alt.condition(selected, alt.value(1.0), alt.value(0.9)),
            tooltip=[
                alt.Tooltip("weekday:N", title="Day"),
                alt.Tooltip("hour_label:N", title="Hour"),
                alt.Tooltip("alcohol_count:Q", title="Alcohol-related crashes", format=","),
                alt.Tooltip("total_crashes:Q", title="All crashes", format=","),
                alt.Tooltip("alcohol_share_pct:Q", title="Alcohol-related share (%)", format=".2f"),
            ],
        ).add_params(time_pick)
    )

    label_hours = [6, 8, 10, 12, 14, 16, 18, 20, 22, 0, 2, 4]
    hour_labels = pd.DataFrame({"hour": label_hours, "label": [f"{hour:02d}:00" for hour in label_hours]})
    hour_labels["theta"] = hour_labels["hour"].map(
        lambda hour: (hour_position[int(hour)] + 0.5) * angle_step
    )
    # Keep labels just inside the outer ring so the left-side times are not clipped.
    hour_labels["radius"] = inner_radius + len(WEEKDAYS) * ring_width + 16
    hour_label_chart = alt.Chart(hour_labels).mark_text(
        fontSize=12, color="#5f6b76", baseline="middle"
    ).encode(
        theta=alt.Theta("theta:Q", scale=None),
        radius=alt.Radius("radius:Q", scale=None), text="label:N",
    )

    # Weekday labels centered on each ring
    weekday_labels = pd.DataFrame({
        "weekday": WEEKDAYS,
        "label": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    })
    weekday_labels["radius"] = weekday_labels["weekday"].map(
        lambda day: inner_radius + weekday_position[day] * ring_width + ring_width / 2
    )
    weekday_labels["theta"] = 0
    weekday_label_chart = alt.Chart(weekday_labels).mark_text(
        fontSize=11, fontWeight="bold", color="#5f6b76", align="right", dx=-5
    ).encode(
        theta=alt.Theta("theta:Q", scale=None),
        radius=alt.Radius("radius:Q", scale=None), text="label:N",
    )

    return alt.layer(heatmap, hour_label_chart, weekday_label_chart).properties(
        width=500, height=550
    )



def render_legend(cells: pd.DataFrame, measure: str) -> None:
    """Render the map's measure and selection legend."""
    value_column, value_label = MAP_MEASURES[measure]
    minimum, maximum = cells[value_column].min(), cells[value_column].max()
    formatted = f"{minimum:.1f}–{maximum:.1f}" if value_column.endswith("pct") else f"{int(minimum)}–{int(maximum)}"
    st.markdown(
        f"""
        <section class="mce-viz-legend" aria-label="Alcohol map legend">
            <strong>Map legend</strong>
            <span class="mce-legend-item"><span class="mce-legend-gradient" aria-hidden="true"></span>{escape(value_label)} per grid cell: {formatted}</span>
            <span class="mce-legend-item"><span class="mce-legend-ring" aria-hidden="true"></span>Selected grid cell</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_police_breathalyzers_view() -> None:
    """Render the connected alcohol-related crash analysis."""
    st.markdown(
        """
        <div class="mce-view-heading">
            <h2>Where and when are alcohol-related crashes recorded?</h2>
            <h6>Police Breathalyzers possible placements</h6>
            <p>Explore historical crash records with alcohol present, contributing, suspected, or included in a combined substance label.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    crashes, cells = load_police_breathalyzer_data()
    minimum_date = crashes["crash_datetime"].min().date()
    maximum_date = crashes["crash_datetime"].max().date()
    date_key = f"alcohol_date_range_{maximum_date.isoformat()}"
    st.session_state.setdefault(
        date_key, (max(minimum_date, maximum_date - timedelta(days=365 * 5)), maximum_date)
    )

    date_column, status_column, measure_column, sample_column = st.columns(
        [1.35, 1.6, 1.25, 0.9], gap="medium"
    )
    with date_column:
        date_range = st.date_input(
            "Alcohol crash date range",
            min_value=minimum_date,
            max_value=max(maximum_date, date.today()),
            key=date_key,
        )
    with status_column:
        statuses = st.multiselect(
            "Included alcohol records",
            ALCOHOL_STATUSES,
            default=ALCOHOL_STATUSES,
            key="alcohol_statuses",
        )
    with measure_column:
        measure = st.selectbox("Map and timing measure", MAP_MEASURES, key="alcohol_measure")
    with sample_column:
        minimum_sample = st.number_input(
            "Minimum all crashes per cell",
            min_value=1,
            max_value=100,
            value=3,
            key="alcohol_minimum_sample",
        )

    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Choose both a start and end date.")
        return
    if not statuses:
        st.info("Select at least one alcohol record category.")
        return
    start_date, end_date = date_range
    dated = crashes[crashes["crash_datetime"].dt.date.between(start_date, end_date)]
    alcohol = dated[dated["alcohol_status"].isin(statuses)]
    render_police_breathalyzer_visuals(
        dated, alcohol, cells, measure, int(minimum_sample), end_date
    )


@st.fragment
def render_police_breathalyzer_visuals(
    dated: pd.DataFrame,
    alcohol: pd.DataFrame,
    cells: pd.DataFrame,
    measure: str,
    minimum_sample: int,
    end_date: date,
) -> None:
    """Render linked map and heatmap selections without rerunning other tabs."""
    map_generation = st.session_state.setdefault("alcohol_map_generation", 0)
    heatmap_generation = st.session_state.setdefault("alcohol_heatmap_generation", 0)
    selected_cell = st.session_state.get("alcohol_selected_cell")
    selected_weekday = st.session_state.get("alcohol_selected_weekday")
    selected_hour = st.session_state.get("alcohol_selected_hour")

    map_all = dated
    map_alcohol = alcohol
    if selected_weekday is not None:
        map_all = map_all[
            map_all["weekday"].eq(selected_weekday) & map_all["hour"].eq(selected_hour)
        ]
        map_alcohol = map_alcohol[
            map_alcohol["weekday"].eq(selected_weekday) & map_alcohol["hour"].eq(selected_hour)
        ]
    active_minimum_sample = effective_minimum_sample(minimum_sample, selected_weekday)
    mapped = aggregate_cells(map_all, map_alcohol, cells)
    mapped = mapped[mapped["total_crashes"].ge(active_minimum_sample)].reset_index(drop=True)
    if selected_cell and selected_cell not in set(mapped["cell_id"]):
        st.session_state["alcohol_selected_cell"] = None
        selected_cell = None

    timing_all = dated if selected_cell is None else dated[dated["cell_id"].eq(selected_cell)]
    timing_alcohol = alcohol if selected_cell is None else alcohol[alcohol["cell_id"].eq(selected_cell)]
    timing = aggregate_timing(timing_all, timing_alcohol)

    summary, clear = st.columns([3.5, 1])
    with summary:
        geography = f"grid cell {selected_cell}" if selected_cell else "countywide"
        time_context = f" · {selected_weekday} {selected_hour:02d}:00" if selected_weekday else ""
        st.caption(
            f"{len(alcohol):,} selected alcohol-related crashes out of {len(dated):,} total · {geography}{time_context}"
            + (" · map minimum automatically reduced to 1 crash per cell" if selected_weekday else "")
        )
    with clear:
        if st.button(
            "Clear alcohol selection",
            disabled=selected_cell is None and selected_weekday is None,
            width="stretch",
            key="alcohol_clear_selection",
        ):
            st.session_state["alcohol_selected_cell"] = None
            st.session_state["alcohol_selected_weekday"] = None
            st.session_state["alcohol_selected_hour"] = None
            st.session_state["alcohol_map_generation"] = map_generation + 1
            st.session_state["alcohol_heatmap_generation"] = heatmap_generation + 1
            st.rerun()

    map_column, timing_column = st.columns([1.2, 1], gap="medium")
    with map_column:
        st.subheader(
            "Alcohol-related crashes by grid cell",
            help=(
                "Each grid tile represents an aggregated crash cell. Darker color means more "
                "crashes for the selected filtering. Click a cell to focus the timing chart "
                "on that cell."
            ),
        )
        if mapped.empty:
            st.warning("No grid cells meet the current filters and minimum sample. Try a lower minimum sample.")
        else:
            render_legend(mapped, measure)
            map_key = f"alcohol_map_{map_generation}"
            st.pydeck_chart(
                build_map(mapped, map_alcohol, measure, selected_cell),
                key=map_key,
                on_select=lambda: _map_selection_callback(map_key),
                selection_mode="single-object",
                height=500,
            )
            if selected_cell:
                row = mapped[mapped["cell_id"].eq(selected_cell)].iloc[0]
                st.markdown(
                    f"""
                    <section class="mce-map-selection-box" aria-label="Current alcohol map selection">
                        <strong>Grid cell {escape(selected_cell)}</strong>
                        <span>{row['alcohol_count']:,} alcohol-related of {row['total_crashes']:,} crashes · {row['alcohol_share_pct']:.1f}%</span>
                        <span>{escape(str(row['status_breakdown']))}</span>
                        <small>Common roads: {escape(str(row['common_roads']))}</small>
                    </section>
                    """,
                    unsafe_allow_html=True,
                )
    with timing_column:
        st.subheader(
            "Alcohol-related crash timing",
            help=(
                "Inner-to-outer rings are Monday through Sunday, and each radial segment is an hour. "
                "Darker color means more crashes for the selected measure. Click a weekday-hour "
                "segment to filter the map."
            ),
        )
        st.caption("Select a weekday-hour cell to filter the map; double-click the heatmap to clear its time selection.")
        heatmap_key = f"alcohol_heatmap_{heatmap_generation}"
        st.altair_chart(
            build_heatmap(timing, measure, selected_weekday, selected_hour),
            key=heatmap_key,
            on_select=lambda: _time_selection_callback(heatmap_key),
            selection_mode="time_pick",
            width="stretch",
        )
        st.caption("Weekday rings, inner → outer: Monday · Tuesday · Wednesday · Thursday · Friday · Saturday · Sunday. Radial segments show hours.")


    st.caption(
        "Alcohol-related includes recorded alcohol present/contributed, suspected alcohol use, and combined-substance labels selected above. Shares use all geocoded crashes in the same active cell and time window as the denominator. These are historical police records, not BAC tests, causal findings, or enforcement recommendations."
    )
    if end_date.year == 2026:
        st.caption("The 2026 source snapshot ends on August 5 and is incomplete for annual comparisons.")
