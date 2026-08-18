"""Interactive Fire & Rescue Proximity view."""

from datetime import date, timedelta
from html import escape
from pathlib import Path

import altair as alt
import numpy as np
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


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "processed" / "fire-and-rescue"
CRASHES_FILE = DATA_DIR / "fire_rescue_crashes.parquet"
CELLS_FILE = DATA_DIR / "fire_rescue_cells.parquet"
STATIONS_FILE = DATA_DIR / "fire_stations.parquet"

DAYPARTS = ["All day", "Overnight", "Morning", "Afternoon", "Evening"]
SEVERITIES = [
    "Fatal Injury",
    "Suspected Serious Injury",
    "Possible Injury",
]
SEVERITY_ORDER = [
    "Fatal Injury",
    "Suspected Serious Injury",
    "Suspected Minor Injury",
    "Possible Injury",
    "No Apparent Injury",
]
DEFAULT_SEVERITIES = ["Suspected Serious Injury", "Fatal Injury"]
SEVERITY_SHORT = {
    "Fatal Injury": "Fatal",
    "Suspected Serious Injury": "Serious",
    "Suspected Minor Injury": "Minor",
    "Possible Injury": "Possible",
    "No Apparent Injury": "No apparent",
}
EARTH_RADIUS_KM = 6371.0088


def _bound_date_range(
    start_date: date,
    end_date: date,
    minimum_date: date,
    maximum_date: date,
) -> tuple[date, date]:
    """Keep a selected duration while ending no later than the available data."""
    if end_date > maximum_date:
        start_date -= end_date - maximum_date
        end_date = maximum_date
    return max(start_date, minimum_date), end_date


def _bound_date_range_state(
    key: str,
    minimum_date: date,
    maximum_date: date,
) -> None:
    """Apply the dataset bounds immediately after the date widget changes."""
    selected = st.session_state.get(key)
    if isinstance(selected, (tuple, list)) and len(selected) == 2:
        st.session_state[key] = _bound_date_range(
            selected[0], selected[1], minimum_date, maximum_date
        )


@st.cache_data
def load_fire_rescue_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the committed deployment datasets."""
    return (
        pd.read_parquet(CRASHES_FILE),
        pd.read_parquet(CELLS_FILE),
        pd.read_parquet(STATIONS_FILE),
    )


def aggregate_cells(filtered: pd.DataFrame, cells: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the active crash subset while retaining stable cell proximity."""
    if filtered.empty:
        return cells.head(0).assign(
            crash_count=pd.Series(dtype="int64"),
            serious_count=pd.Series(dtype="int64"),
            fatal_count=pd.Series(dtype="int64"),
            severity_breakdown=pd.Series(dtype="string"),
            first_crash=pd.Series(dtype="datetime64[ns]"),
            last_crash=pd.Series(dtype="datetime64[ns]"),
            common_roads=pd.Series(dtype="string"),
        )

    working = filtered.assign(
        serious_count=filtered["severity"].eq("Suspected Serious Injury").astype(int),
        fatal_count=filtered["severity"].eq("Fatal Injury").astype(int),
    )
    summary = working.groupby("cell_id", as_index=False).agg(
        crash_count=("report_number", "size"),
        serious_count=("serious_count", "sum"),
        fatal_count=("fatal_count", "sum"),
        first_crash=("crash_datetime", "min"),
        last_crash=("crash_datetime", "max"),
    )
    severity_counts = (
        working.groupby(["cell_id", "severity"], as_index=False)
        .size()
        .assign(
            severity=lambda frame: pd.Categorical(
                frame["severity"], categories=SEVERITY_ORDER, ordered=True
            )
        )
        .sort_values(["cell_id", "severity"])
    )
    severity_counts["label"] = (
        severity_counts["severity"].map(SEVERITY_SHORT).astype("string")
        + ": "
        + severity_counts["size"].astype("string")
    )
    breakdowns = severity_counts.groupby("cell_id", as_index=False)["label"].agg(
        severity_breakdown=lambda labels: " · ".join(labels)
    )

    road_counts = (
        working.dropna(subset=["road_name"])
        .groupby(["cell_id", "road_name"], as_index=False)
        .size()
        .sort_values(["cell_id", "size", "road_name"], ascending=[True, False, True])
        .groupby("cell_id", as_index=False)
        .head(3)
    )
    roads = road_counts.groupby("cell_id", as_index=False)["road_name"].agg(
        common_roads=lambda values: ", ".join(values)
    )
    return (
        cells.merge(summary, on="cell_id", how="inner", validate="one_to_one")
        .merge(breakdowns, on="cell_id", how="left", validate="one_to_one")
        .merge(roads, on="cell_id", how="left", validate="one_to_one")
        .fillna({"common_roads": "Not recorded"})
    )


def station_distance_matrix(
    crashes: pd.DataFrame, stations: pd.DataFrame
) -> np.ndarray:
    """Return exact Haversine distances from crashes to stations."""
    crash_lat = np.radians(crashes["latitude"].to_numpy())[:, None]
    crash_lon = np.radians(crashes["longitude"].to_numpy())[:, None]
    station_lat = np.radians(stations["station_latitude"].to_numpy())[None, :]
    station_lon = np.radians(stations["station_longitude"].to_numpy())[None, :]
    a = (
        np.sin((crash_lat - station_lat) / 2) ** 2
        + np.cos(crash_lat)
        * np.cos(station_lat)
        * np.sin((crash_lon - station_lon) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def aggregate_station_radius(
    crashes: pd.DataFrame, stations: pd.DataFrame, radius_km: float
) -> pd.DataFrame:
    """Count filtered crashes inside each station's straight-line radius."""
    within = station_distance_matrix(crashes, stations) <= radius_km
    injury = crashes["severity"].ne("No Apparent Injury").to_numpy()[:, None]
    fatal = crashes["severity"].eq("Fatal Injury").to_numpy()[:, None]
    return stations.assign(
        crash_count=within.sum(axis=0),
        injury_count=(within & injury).sum(axis=0),
        fatal_count=(within & fatal).sum(axis=0),
    )


def crashes_in_station_radius(
    crashes: pd.DataFrame,
    stations: pd.DataFrame,
    station_id: str | None,
    radius_km: float,
) -> pd.DataFrame:
    """Return filtered crashes inside one selected station radius."""
    selected = stations[stations["station_id"].eq(station_id)]
    if selected.empty:
        return crashes.head(0)
    within = station_distance_matrix(crashes, selected).ravel() <= radius_km
    return crashes.loc[within].copy()


def _event_selection(event: object) -> object:
    if isinstance(event, dict):
        return event.get("selection", {})
    return getattr(event, "selection", {})


def _map_selection_from_event(event: object) -> tuple[str | None, str | None]:
    selection = _event_selection(event)
    objects = (
        selection.get("objects", {})
        if isinstance(selection, dict)
        else getattr(selection, "objects", {})
    )
    cells = objects.get("crash-cells", [])
    incidents = objects.get("cell-crashes", [])
    stations = objects.get("fire-stations", [])
    cell_id = str((cells or incidents)[0]["cell_id"]) if cells or incidents else None
    station_id = str(stations[0]["station_id"]) if stations else None
    return cell_id, station_id


def _altair_selection_value(
    event: object, selection_names: list[str], field: str
) -> str | None:
    selection = _event_selection(event)
    for name in selection_names:
        selected = selection.get(name, []) if selection is not None else []
        if isinstance(selected, list) and selected:
            return str(selected[0][field])
        if isinstance(selected, dict):
            values = selected.get(field, [])
            if values:
                return str(values[0])
    return None


def _set_selection(cell_id: str | None, station_id: str | None) -> None:
    st.session_state["fire_rescue_selected_cell"] = cell_id
    st.session_state["fire_rescue_selected_station"] = station_id


def _map_selection_callback(key: str) -> None:
    cell_id, station_id = _map_selection_from_event(st.session_state.get(key, {}))
    _set_selection(cell_id, station_id)
    st.session_state["fire_rescue_zoom_to_station"] = station_id is not None
    st.session_state["fire_rescue_map_generation"] += 1
    st.session_state["fire_rescue_scatter_generation"] += 1


def _scatter_selection_callback(key: str) -> None:
    cell_id = _altair_selection_value(
        st.session_state.get(key, {}), ["cell_pick"], "cell_id"
    )
    if cell_id:
        _set_selection(cell_id, None)
        st.session_state["fire_rescue_zoom_to_station"] = False
        st.session_state["fire_rescue_map_generation"] += 1


def _station_bar_selection_callback(key: str) -> None:
    event = st.session_state.get(key, {})
    clicked = _altair_selection_value(event, ["station_pick"], "station_id")
    if clicked:
        _set_selection(None, clicked)
        st.session_state["fire_rescue_zoom_to_station"] = True
        st.session_state["fire_rescue_bar_generation"] += 1
        st.session_state["fire_rescue_map_generation"] += 1
        st.session_state["fire_rescue_scatter_generation"] += 1


def build_map(
    cells: pd.DataFrame,
    stations: pd.DataFrame,
    filtered_crashes: pd.DataFrame,
    selected_cell: str | None,
    selected_station: str | None,
    radius_km: float,
    zoom_to_station: bool,
) -> pdk.Deck:
    """Build the crash-demand map and optional selected-station radius."""
    demand = cells.copy()
    color_position = (
        (demand["crash_count"] - demand["crash_count"].min())
        / max(demand["crash_count"].max() - demand["crash_count"].min(), 1)
    )
    demand["fill_color"] = colors.map_fill_colors(color_position)
    demand["title"] = "Grid cell " + demand["cell_id"]
    demand["line_1"] = demand["crash_count"].map(
        lambda count: f"Filtered crashes: {count}"
    )
    demand["line_2"] = demand["severity_breakdown"]
    demand["line_3"] = demand.apply(
        lambda row: (
            f"Nearest station: {row['nearest_station_name']} "
            f"({row['nearest_station_distance_km']:.2f} km)"
        ),
        axis=1,
    )
    if selected_cell:
        base_demand = demand[
            ~demand["cell_id"].eq(selected_cell)
        ].copy()
    else:
        base_demand = demand.copy()
    station_points = stations.copy()
    station_points["title"] = station_points["station_name"]
    station_points["line_1"] = station_points["address"]
    station_points["line_2"] = station_points["city"]
    station_points["line_3"] = "Mapped fire station"
    station_points["map_symbol"] = "+"
    selected_station_row = stations[stations["station_id"].eq(selected_station)]
    radius_incidents = crashes_in_station_radius(
        filtered_crashes, stations, selected_station, radius_km
    )
    layers = []
    if not selected_station_row.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                selected_station_row,
                id="station-radius",
                get_position=["station_longitude", "station_latitude"],
                get_radius=radius_km * 1000,
                get_fill_color=colors.with_alpha(colors.STATION_RGB, 28),
                get_line_color=colors.with_alpha(colors.STATION_RGB, 210),
                line_width_min_pixels=2,
                stroked=True,
                pickable=False,
            )
        )
    layers.append(grid_cell_layer(base_demand, "crash-cells"))
    if not radius_incidents.empty:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                radius_incidents,
                id="station-radius-incidents",
                get_position=["longitude", "latitude"],
                get_radius=55,
                get_fill_color=colors.with_alpha(colors.STATION_RGB, 210),
                get_line_color=colors.with_alpha(colors.WHITE_RGB, 230),
                radius_min_pixels=3,
                radius_max_pixels=7,
                line_width_min_pixels=1,
                stroked=True,
                pickable=False,
            )
        )
    layers.append(
        pdk.Layer(
            "TextLayer",
            station_points,
            id="fire-stations",
            get_position=["station_longitude", "station_latitude"],
            get_text="map_symbol",
            get_size=32,
            get_color=colors.with_alpha(colors.STATION_RGB, 255),
            get_text_anchor="'middle'",
            get_alignment_baseline="'center'",
            font_weight=900,
            billboard=True,
            pickable=True,
            parameters={"depthTest": False},
        )
    )
    ring = selected_cell_layer(demand, selected_cell, "selected-cell", fill_alpha=12)
    incidents = crash_point_layer(
        filtered_crashes,
        selected_cell,
        "cell-crashes",
        (("severity", "Severity"),),
    )
    layers.extend(layer for layer in (ring, incidents) if layer is not None)
    view_state = cell_view_state(cells, selected_cell)
    if not selected_station_row.empty:
        layers.append(
            pdk.Layer(
                "TextLayer",
                selected_station_row.assign(map_symbol="+"),
                id="selected-station",
                get_position=["station_longitude", "station_latitude"],
                get_text="map_symbol",
                get_size=44,
                get_color=colors.with_alpha(colors.SELECTED_RGB, 255),
                get_text_anchor="'middle'",
                get_alignment_baseline="'center'",
                font_weight=900,
                billboard=True,
                pickable=False,
                parameters={"depthTest": False},
            )
        )
        if zoom_to_station:
            view_state = pdk.ViewState(
                latitude=float(selected_station_row.iloc[0]["station_latitude"]),
                longitude=float(selected_station_row.iloc[0]["station_longitude"]),
                zoom=float(10.5 - np.log2(radius_km / 3)),
                pitch=0,
            )
    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        map_provider="carto",
        map_style=pdk.map_styles.CARTO_LIGHT,
        tooltip={
            "html": "<b>{title}</b><br>{line_1}<br>{line_2}<br>{line_3}"
        },
    )


def build_gap_scatter(cells: pd.DataFrame, selected_cell: str | None) -> alt.Chart:
    """Build the demand-distance relationship without an arbitrary gap score."""
    point_selection = alt.selection_point(
        name="cell_pick", fields=["cell_id"], toggle=False, clear="dblclick", empty=False
    )
    zoom_selection = alt.selection_interval(name="cell_zoom", bind="scales")
    selected_expression = (
        point_selection | (alt.datum.cell_id == selected_cell)
        if selected_cell
        else point_selection
    )
    points = (
        alt.Chart(cells)
        .mark_circle(size=55, stroke="white", strokeWidth=0.8)
        .encode(
            x=alt.X(
                "nearest_station_distance_km:Q",
                title="Nearest mapped station (straight-line km)",
                scale=alt.Scale(zero=True),
            ),
            y=alt.Y(
                "crash_count:Q",
                title="Filtered crash count",
                scale=alt.Scale(zero=True),
            ),
            color=alt.condition(
                selected_expression,
                alt.value("#14202b"),
                alt.value("#d95f45"),
            ),
            opacity=alt.condition(
                selected_expression,
                alt.value(1),
                alt.value(0.68),
            ),
            tooltip=[
                alt.Tooltip("cell_id:N", title="Grid cell"),
                alt.Tooltip("nearest_station_distance_km:Q", title="Distance (km)", format=".2f"),
                alt.Tooltip("crash_count:Q", title="Filtered crashes"),
                alt.Tooltip("severity_breakdown:N", title="Severity breakdown"),
                alt.Tooltip("serious_count:Q", title="Serious"),
                alt.Tooltip("fatal_count:Q", title="Fatal"),
                alt.Tooltip("nearest_station_name:N", title="Nearest station"),
                alt.Tooltip("common_roads:N", title="Common roads"),
            ],
        )
        .add_params(point_selection, zoom_selection)
    )
    medians = pd.DataFrame(
        {
            "distance": [cells["nearest_station_distance_km"].median()],
            "count": [cells["crash_count"].median()],
        }
    )
    vertical = alt.Chart(medians).mark_rule(color="#8c99a5", strokeDash=[4, 4]).encode(x="distance:Q")
    horizontal = alt.Chart(medians).mark_rule(color="#8c99a5", strokeDash=[4, 4]).encode(y="count:Q")
    return (points + vertical + horizontal).properties(height=440)


def build_station_radius_bar(
    station_counts: pd.DataFrame,
    station_limit: int,
    selected_station: str | None,
    activity_mode: str,
) -> alt.Chart:
    """Rank stations by filtered crashes inside a chosen radius."""
    most_active = activity_mode == "Most active"
    plotted = (
        station_counts.nlargest(station_limit, "crash_count")
        if most_active
        else station_counts.nsmallest(station_limit, "crash_count")
    )
    station_pick = alt.selection_point(
        name="station_pick",
        fields=["station_id"],
        toggle=False,
        clear="dblclick",
        empty=False,
    )
    selected_expression = (
        alt.datum.station_id == selected_station
        if selected_station
        else station_pick
    )
    return (
        alt.Chart(plotted)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "crash_count:Q",
                title="Filtered crash count",
                scale=alt.Scale(zero=True),
            ),
            y=alt.Y(
                "station_name:N",
                title=None,
                sort="-x" if most_active else "x",
                axis=alt.Axis(labelLimit=240, labelOverlap=False),
            ),
            tooltip=[
                alt.Tooltip("station_name:N", title="Station"),
                alt.Tooltip("crash_count:Q", title="Filtered crashes"),
                alt.Tooltip("injury_count:Q", title="Injury crashes"),
                alt.Tooltip("fatal_count:Q", title="Fatal"),
                alt.Tooltip("address:N", title="Address"),
                alt.Tooltip("city:N", title="City"),
            ],
            color=alt.condition(
                selected_expression,
                alt.value("#14202b"),
                alt.value("#087f78"),
            ),
        )
        .add_params(station_pick)
        .properties(height=max(320, station_limit * 28))
    )


def render_map_legend(cells: pd.DataFrame, selected_station: str | None) -> None:
    """Render an explicit legend for every map visual encoding."""
    minimum = int(cells["crash_count"].min())
    maximum = int(cells["crash_count"].max())
    station_context = (
        """
        <span class="mce-legend-item">
            <span class="mce-legend-radius" aria-hidden="true"></span>
            Selected station radius and included incidents
        </span>
        """
        if selected_station
        else ""
    )
    st.markdown(
        f"""
        <section class="mce-viz-legend" aria-label="Map legend">
            <strong>Map legend</strong>
            <span class="mce-legend-item">
                <span class="mce-legend-gradient" aria-hidden="true"></span>
                Filtered crash count per grid cell: color ({minimum}–{maximum})
            </span>
            <span class="mce-legend-item">
                <span class="mce-legend-cross" aria-hidden="true">+</span>
                Mapped fire station (rescue cross)
            </span>
            <span class="mce-legend-item">
                <span class="mce-legend-ring" aria-hidden="true"></span>
                Selected grid cell
            </span>
            {station_context}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_scatter_legend() -> None:
    """Render the cell, selection, and reference-line scatterplot legend."""
    st.markdown(
        """
        <section class="mce-viz-legend" aria-label="Scatterplot legend">
            <strong>Scatterplot legend</strong>
            <span class="mce-legend-item">
                <span class="mce-legend-dot mce-legend-cell" aria-hidden="true"></span>
                Grid cell
            </span>
            <span class="mce-legend-item">
                <span class="mce-legend-dot mce-legend-selected" aria-hidden="true"></span>
                Selected grid cell
            </span>
            <span class="mce-legend-item">
                <span class="mce-legend-line" aria-hidden="true"></span>
                Visible-cell medians
            </span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_map_selection_box(
    cells: pd.DataFrame,
    stations: pd.DataFrame,
    station_counts: pd.DataFrame,
    selected_cell: str | None,
    selected_station: str | None,
    radius_km: float,
) -> None:
    """Overlay compact selected-cell or selected-station details on the map."""
    selected_cells = cells[cells["cell_id"].eq(selected_cell)]
    selected_stations = stations[stations["station_id"].eq(selected_station)]
    if not selected_cells.empty:
        row = selected_cells.iloc[0]
        title = f"Grid cell {row['cell_id']}"
        primary = f"{row['crash_count']:,} filtered crashes · {row['severity_breakdown']}"
        secondary = (
            f"Nearest: {row['nearest_station_name']} · "
            f"{row['nearest_station_distance_km']:.2f} km straight-line"
        )
        detail = (
            f"{row['first_crash']:%b %d, %Y}–{row['last_crash']:%b %d, %Y} · "
            f"Roads: {row['common_roads']}"
        )
    elif not selected_stations.empty:
        row = selected_stations.iloc[0]
        counts = station_counts[station_counts["station_id"].eq(selected_station)].iloc[0]
        title = str(row["station_name"])
        primary = f"{counts['crash_count']:,} filtered crashes within {radius_km:g} km"
        secondary = (
            f"{counts['injury_count']:,} injury crashes · {counts['fatal_count']:,} fatal"
        )
        detail = f"{row['address']}, {row['city']} · Straight-line radius"
    else:
        return
    st.markdown(
        f"""
        <section class="mce-map-selection-box" aria-label="Current map selection">
            <strong>{escape(title)}</strong>
            <span>{escape(primary)}</span>
            <span>{escape(secondary)}</span>
            <small>{escape(detail)}</small>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_fire_rescue_view() -> None:
    """Render the connected Fire & Rescue Proximity analysis."""
    st.markdown(
        """
        <div class="mce-view-heading">
            <h2>Where are crashes farther from mapped fire stations?</h2>
            <p>Filter by maximum recorded injury severity and compare crash demand with straight-line station proximity. This is not a response-time measure.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    crashes, cells, stations = load_fire_rescue_data()
    minimum_date = crashes["crash_datetime"].min().date()
    maximum_date = crashes["crash_datetime"].max().date()
    default_start_date = max(minimum_date, maximum_date - timedelta(days=365 * 5))
    date_range_key = f"fire_rescue_date_range_{maximum_date.isoformat()}"
    st.session_state.setdefault(
            date_range_key, (default_start_date, maximum_date)
        )

    stored_date_range = st.session_state.get(date_range_key)
    if isinstance(stored_date_range, (tuple, list)) and len(stored_date_range) == 2:
        stored_start_date, stored_end_date = stored_date_range
        st.session_state[date_range_key] = _bound_date_range(
            stored_start_date,
            stored_end_date,
            minimum_date,
            maximum_date,
        )

    date_column, daypart_column, severity_column, sample_column = st.columns(
        [1.4, 1, 1.35, 0.8], gap="medium"
    )
    with date_column:
        date_range = st.date_input(
            "Crash date range",
            min_value=minimum_date,
            max_value=max(maximum_date, date.today()),
            key=date_range_key,
            on_change=_bound_date_range_state,
            args=(date_range_key, minimum_date, maximum_date),
        )
    with daypart_column:
        daypart = st.selectbox("Time of day", DAYPARTS, key="fire_rescue_daypart")
    with severity_column:
        severities = st.multiselect(
            "Maximum injury severity",
            SEVERITIES,
            default=DEFAULT_SEVERITIES,
            key="fire_rescue_severity",
        )
    with sample_column:
        minimum_sample = st.number_input(
            "Minimum crashes per map cell",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
            key="fire_rescue_minimum_sample",
        )

    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        st.info("Choose both a start and end date.")
        return
    start_date, end_date = date_range
    filtered = crashes[
        crashes["crash_datetime"].dt.date.between(start_date, end_date)
        & crashes["severity"].isin(severities)
    ]
    if daypart != "All day":
        filtered = filtered[filtered["daypart"].eq(daypart)]

    render_fire_rescue_visuals(
        filtered,
        cells,
        stations,
        int(minimum_sample),
        end_date,
    )


@st.fragment
def render_fire_rescue_visuals(
    filtered: pd.DataFrame,
    cells: pd.DataFrame,
    stations: pd.DataFrame,
    minimum_sample: int,
    end_date: date,
) -> None:
    """Render only the linked charts that need to update on selection."""
    visible_cells = aggregate_cells(filtered, cells)
    visible_cells = visible_cells[
        visible_cells["crash_count"].ge(minimum_sample)
    ].reset_index(drop=True)
    if visible_cells.empty:
        st.warning("No grid cells meet the current filters and minimum sample.")
        return

    map_generation = st.session_state.setdefault("fire_rescue_map_generation", 0)
    scatter_generation = st.session_state.setdefault("fire_rescue_scatter_generation", 0)
    bar_generation = st.session_state.setdefault("fire_rescue_bar_generation", 0)
    zoom_to_station = st.session_state.setdefault("fire_rescue_zoom_to_station", False)
    selected_cell = st.session_state.get("fire_rescue_selected_cell")
    selected_station = st.session_state.get("fire_rescue_selected_station")
    radius_km = st.session_state.get("fire_rescue_station_radius", 3.0)
    if selected_cell and selected_cell not in set(visible_cells["cell_id"]):
        _set_selection(None, None)
        st.session_state["fire_rescue_map_generation"] = map_generation + 1
        st.session_state["fire_rescue_scatter_generation"] = scatter_generation + 1
        st.rerun()
    if selected_station and selected_station not in set(stations["station_id"]):
        _set_selection(None, None)
        st.session_state["fire_rescue_zoom_to_station"] = False
        st.rerun()

    summary, clear = st.columns([3.4, 1])
    with summary:
        st.caption(
            f"{len(filtered):,} filtered crashes · {len(visible_cells):,} visible cells · "
            f"{len(stations)} mapped stations · distances are straight-line kilometres"
        )
    with clear:
        if st.button(
            "Clear map selection",
            disabled=selected_cell is None and selected_station is None,
            width="stretch",
            key="fire_rescue_clear_selection",
        ):
            _set_selection(None, None)
            st.session_state["fire_rescue_zoom_to_station"] = False
            st.session_state["fire_rescue_map_generation"] = map_generation + 1
            st.session_state["fire_rescue_scatter_generation"] = scatter_generation + 1
            st.rerun()
    station_counts = aggregate_station_radius(filtered, stations, radius_km)

    map_column, scatter_column = st.columns([1.65, 0.9], gap="medium")
    with map_column:
        st.subheader(
            "Crash demand and mapped stations",
            help="Explore crash clusters across the county. See how fire stations are spread to cover crashes."
            )
        render_map_legend(visible_cells, selected_station)
        map_key = f"fire_rescue_map_{map_generation}"
        st.pydeck_chart(
            build_map(
                visible_cells,
                stations,
                filtered,
                selected_cell,
                selected_station,
                radius_km,
                zoom_to_station,
            ),
            key=map_key,
            on_select=lambda: _map_selection_callback(map_key),
            selection_mode="single-object",
            height=500,
        )
        render_map_selection_box(
            visible_cells,
            stations,
            station_counts,
            selected_cell,
            selected_station,
            radius_km,
        )
    with scatter_column:
        st.subheader(
            "Demand versus station proximity",
            help="Cells toward the upper-right combine more crashes with greater distance."
            )
        render_scatter_legend()
        scatter_key = f"fire_rescue_scatter_{scatter_generation}"
        st.altair_chart(
            build_gap_scatter(visible_cells, selected_cell),
            key=scatter_key,
            on_select=lambda: _scatter_selection_callback(scatter_key),
            selection_mode="cell_pick",
        )

    st.subheader(
        "Filtered crashes near mapped stations",
        help="Use the controls below to rank stations and change the radius used for the bar chart and map radius overlay."
        )
    activity_column, station_limit_column, radius_column = st.columns(3)
    with activity_column:
        activity_mode = st.selectbox(
            "Station activity",
            ["Most active", "Least active"],
            key="fire_rescue_station_activity",
        )
    with station_limit_column:
        station_limit = st.slider(
            "Stations shown",
            5,
            len(stations),
            15,
            key="fire_rescue_station_limit",
        )
    with radius_column:
        radius_km = st.slider(
            "Station radius (km)",
            1.0,
            5.0,
            3.0,
            0.5,
            key="fire_rescue_station_radius",
        )
    station_counts = aggregate_station_radius(filtered, stations, radius_km)
    rank_label = "Top" if activity_mode == "Most active" else "Bottom"
    st.caption(
        f"{rank_label} {station_limit} mapped stations within {radius_km:g} km. Each station is counted "
        "independently, so crashes can appear in more than one bar where radii overlap. "
        "This is proximity, not workload or response coverage."
    )
    st.markdown("#### Station bar chart")
    bar_key = f"fire_rescue_station_bar_{bar_generation}"
    st.altair_chart(
        build_station_radius_bar(
            station_counts,
            station_limit,
            selected_station,
            activity_mode,
        ),
        key=bar_key,
        on_select=lambda: _station_bar_selection_callback(bar_key),
        selection_mode=["station_pick"],
        width="stretch",
    )

    if end_date.year == 2026:
        st.caption("The 2026 source snapshot ends on August 5 and is incomplete for annual comparisons.")
