"""Shared semantic-zoom behavior for crash-cell maps."""

import pandas as pd
import pydeck as pdk

from . import colors


DEFAULT_LATITUDE = 39.12
DEFAULT_LONGITUDE = -77.13
DEFAULT_ZOOM = 8.6
SELECTED_CELL_ZOOM = 13.0


def cell_view_state(cells: pd.DataFrame, selected_cell: str | None) -> pdk.ViewState:
    """Return the county view or a view centered on the selected grid cell."""
    selected = (
        cells[cells["cell_id"].eq(selected_cell)]
        if selected_cell
        else cells.iloc[0:0]
    )
    if selected.empty:
        return pdk.ViewState(
            latitude=DEFAULT_LATITUDE,
            longitude=DEFAULT_LONGITUDE,
            zoom=DEFAULT_ZOOM,
            pitch=0,
        )
    row = selected.iloc[0]
    return pdk.ViewState(
        latitude=float(row["center_latitude"]),
        longitude=float(row["center_longitude"]),
        zoom=SELECTED_CELL_ZOOM,
        pitch=0,
    )


def grid_cell_layer(cells: pd.DataFrame, layer_id: str) -> pdk.Layer:
    """Build the shared selectable aggregate-cell layer."""
    return pdk.Layer(
        "ScatterplotLayer",
        cells,
        id=layer_id,
        get_position=["center_longitude", "center_latitude"],
        get_radius=260,
        get_fill_color="fill_color",
        get_line_color=colors.MAP_LINE_COLOR,
        radius_min_pixels=5,
        radius_max_pixels=24,
        line_width_min_pixels=1,
        stroked=True,
        pickable=True,
        auto_highlight=True,
    )


def selected_cell_layer(
    cells: pd.DataFrame,
    selected_cell: str | None,
    layer_id: str,
    fill_alpha: int = 25,
) -> pdk.Layer | None:
    """Build the shared selected-cell context ring when the cell is visible."""
    selected = (
        cells[cells["cell_id"].eq(selected_cell)]
        if selected_cell
        else cells.iloc[0:0]
    )
    if selected.empty:
        return None
    return pdk.Layer(
        "ScatterplotLayer",
        selected,
        id=layer_id,
        get_position=["center_longitude", "center_latitude"],
        get_radius=520,
        get_fill_color=colors.with_alpha(colors.SELECTED_RGB, fill_alpha),
        get_line_color=colors.with_alpha(colors.SELECTED_RGB, 255),
        line_width_min_pixels=3,
        stroked=True,
        pickable=False,
    )


def crash_point_layer(
    crashes: pd.DataFrame,
    selected_cell: str | None,
    layer_id: str,
    detail_fields: tuple[tuple[str, str], ...] = (),
) -> pdk.Layer | None:
    """Build consistently styled, tooltip-ready incidents for one selected cell."""
    selected = (
        crashes[crashes["cell_id"].eq(selected_cell)].copy()
        if selected_cell
        else crashes.iloc[0:0]
    )
    if selected.empty:
        return None

    report_numbers = selected.get(
        "report_number", pd.Series("", index=selected.index)
    ).astype(str)
    selected["title"] = "Crash " + report_numbers
    if "crash_datetime" in selected:
        selected["line_1"] = pd.to_datetime(selected["crash_datetime"]).dt.strftime(
            "%b %d, %Y · %I:%M %p"
        )
    else:
        selected["line_1"] = "Date/time not recorded"
    roads = selected.get("road_name", pd.Series(pd.NA, index=selected.index))
    selected["line_2"] = "Road: " + roads.astype("string").fillna("Not recorded")
    details = []
    for column, label in detail_fields:
        if column in selected:
            details.append(
                label + ": " + selected[column].astype("string").fillna("Not recorded")
            )
    selected["line_3"] = (
        pd.concat(details, axis=1).agg(" · ".join, axis=1) if details else ""
    )
    selected["line_4"] = ""
    selected["line_5"] = ""

    return pdk.Layer(
        "ScatterplotLayer",
        selected,
        id=layer_id,
        get_position=["longitude", "latitude"],
        get_radius=5,
        radius_units="'pixels'",
        get_fill_color=colors.with_alpha(colors.CRASH_POINT_RGB, 190),
        get_line_color=colors.with_alpha(colors.WHITE_RGB, 225),
        line_width_min_pixels=1,
        stroked=True,
        pickable=True,
        auto_highlight=True,
    )
