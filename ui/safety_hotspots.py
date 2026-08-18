"""Interactive Safety Hotspots overview."""

from datetime import date, timedelta
from html import escape
from pathlib import Path
from statistics import mean

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

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
    """Compare the active county average against an optional selected hotspot."""
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
                    "geography": "County average",
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


def calculate_signature_scores(fingerprint: pd.DataFrame, selected_cell: str | None = None) -> dict:
    """Calculate total-variation distance for each crash-condition family."""
    selected = fingerprint[fingerprint["geography"].eq("Selected hotspot")]
    if fingerprint.empty or selected.empty:
        return {
            "selected_cell": selected_cell,
            "families": {},
            "overall": 0.0,
            "selected_sample_size": 0,
            "county_sample_size": 0,
        }

    county = fingerprint[fingerprint["geography"].eq("County average")]
    county_size = int(county["sample_size"].max()) if not county.empty else 0
    selected_size = int(selected["sample_size"].max()) if not selected.empty else 0
    family_scores: dict[str, dict] = {}

    for family in CONDITION_FAMILIES:
        county_family = county[county["family"].eq(family)]
        selected_family = selected[selected["family"].eq(family)]
        if county_family.empty:
            continue
        county_share = county_family.set_index("category")["share_pct"].div(100).to_dict()
        selected_share = selected_family.set_index("category")["share_pct"].div(100).to_dict() if not selected_family.empty else {}
        categories = sorted(set(county_share) | set(selected_share))
        distance = 0.5 * sum(abs(selected_share.get(category, 0.0) - county_share.get(category, 0.0)) for category in categories)

        deltas = []
        for category in categories:
            delta_pp = (selected_share.get(category, 0.0) - county_share.get(category, 0.0)) * 100.0
            if abs(delta_pp) > 0:
                deltas.append({"category": category, "delta_pp": round(float(delta_pp), 1)})
        family_scores[family] = {
            "distance": float(distance),
            "largest_differences": sorted(deltas, key=lambda item: abs(item["delta_pp"]), reverse=True)[:3],
            "selected_sample_size": selected_size,
            "county_sample_size": county_size,
        }

    overall = mean([family["distance"] for family in family_scores.values()]) if family_scores else 0.0
    return {
        "selected_cell": selected_cell,
        "families": family_scores,
        "overall": float(overall),
        "selected_sample_size": selected_size,
        "county_sample_size": county_size,
    }


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

    plotted = cells.copy()

    minimum = plotted["crash_count"].min()
    maximum = plotted["crash_count"].max()

    position = (
        plotted["crash_count"] - minimum
    ) / max(maximum - minimum, 1)

    # 1. COLOR
    plotted["fill_color"] = colors.map_fill_colors(position)
    plotted["original_fill_color"] = plotted["fill_color"]

    # 2. TOOLTIP FIELDS — DO THIS BEFORE MAKING base_cells
    plotted["title"] = "Grid cell " + plotted["cell_id"]
    plotted["date_range"] = date_range

    plotted["line_1"] = plotted["crash_count"].map(
        lambda value: f"Crashes: {value:,}"
    )

    plotted["line_2"] = plotted["county_share_pct"].map(
        lambda value: f"County share: {value:.2f}%"
    )

    plotted["line_3"] = plotted["serious_or_fatal_count"].map(
        lambda value: f"Serious/fatal: {value:,}"
    )

    plotted["line_4"] = date_range

    plotted["line_5"] = (
        "Roads: " + plotted["common_roads"].astype(str)
    )

    # 3. NOW remove selected cell from hoverable base layer
    if selected_cell:
        base_cells = plotted[
            ~plotted["cell_id"].eq(selected_cell)
        ].copy()
    else:
        base_cells = plotted.copy()

    # 4. BASE GRID
    layers = [
        grid_cell_layer(
            base_cells,
            "safety-cells",
        )
    ]

    # 5. SELECTED CELL
    ring = selected_cell_layer(
        plotted,
        selected_cell,
        "selected-safety-cell",
    )

    # 6. CRASH POINTS
    incidents = crash_point_layer(
        crashes,
        selected_cell,
        "safety-crashes",
        (
            ("severity", "Severity"),
            ("weather_group", "Weather"),
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
                "{line_4}<br>"
                "{line_5}"
            ),
        },
    )


def build_condition_chart(fingerprint: pd.DataFrame, family: str) -> alt.Chart:
    """Build one compact condition comparison for the three-column small-multiple row."""
    plotted = fingerprint[fingerprint["family"].eq(family)]
    order = (
        plotted[plotted["geography"].eq("County average")]
        .sort_values("category_order")["category"]
        .tolist()
    )
    return (
        alt.Chart(plotted)
        .mark_bar(cornerRadiusEnd=2)
        .encode(
            x=alt.X(
                "share_pct:Q",
                title="Share of crashes (%)",
                scale=alt.Scale(zero=True),
                axis=alt.Axis(grid=True, tickCount=5, labelFontSize=10),

            ),
            y=alt.Y(
                "category:N",
                title=None,
                sort=order,
                axis=alt.Axis(labelLimit=180, labelFontSize=12, labelAngle=-30, labelOverlap=False),
            ),
            yOffset=alt.YOffset("geography:N"),
            color=alt.Color(
                "geography:N",
                legend=None,
                scale=alt.Scale(
                    domain=["Selected hotspot", "County average"],
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
        .properties(title=family, height=max(250, len(order) * 15))
    )


def build_fingerprint(fingerprint: pd.DataFrame) -> alt.HConcatChart:
    """Backward-compatible combined condition comparison."""
    return alt.hconcat(
        *(build_condition_chart(fingerprint, family) for family in CONDITION_FAMILIES),
        spacing=12,
    ).resolve_scale(y="independent")

def build_heatmap(
    timing: pd.DataFrame, selected_weekday: str | None, selected_hour: int | None
) -> alt.Chart:
    """Build the linked weekday-by-hour crash-count heatmap in a compact footprint."""
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
                title=None,
                sort=list(range(24)),
                axis=alt.Axis(
                    labelExpr="datum.value % 2 === 0 ? (datum.value < 10 ? '0' : '') + datum.value + ':00' : ''",
                    labelAngle=-45,
                    labelFontSize=9,
                    tickSize=0,
                ),
            ),
            y=alt.Y(
                "weekday:N",
                title=None,
                sort=WEEKDAYS,
                axis=alt.Axis(labelFontSize=10),
            ),
            color=alt.Color(
                "crash_count:Q",
                title="Crash count",
                scale=alt.Scale(range=colors.HEATMAP_RANGE, zero=True),
                legend=alt.Legend(
                    orient="top",
                    direction="horizontal",
                    gradientLength=120,
                    titleAnchor="start",
                    labelFontSize=9,
                    titleFontSize=10,
                ),
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
        .properties(height=290)
    )

def build_hotspot_signature_svg(signature_scores: dict, selection_summary: dict | None = None) -> str:
    """Render the hotspot fingerprint markup as a standalone HTML/SVG component."""
    ridge_paths = {
        "Weather": [
            "M128,26a101.58,101.58,0,0,0-34,5.81,6,6,0,1,0,4,11.31A90.07,90.07,0,0,1,218,128a283.42,283.42,0,0,1-7,62.67,6,6,0,1,0,11.7,2.66A295.41,295.41,0,0,0,230,128,102.12,102.12,0,0,0,128,26Z",
            "M68,60.92A6,6,0,0,0,60,52a102.19,102.19,0,0,0-34,76,89.32,89.32,0,0,1-8.15,37.5,6,6,0,1,0,10.9,5A101.12,101.12,0,0,0,38,128,90.15,90.15,0,0,1,68,60.92Z",
        ],
        "Surface": [
            "M128,86a42.08,42.08,0,0,1,31.31,14,6,6,0,1,0,8.94-8A54,54,0,0,0,74,128a138.08,138.08,0,0,1-17.22,66.82,6,6,0,1,0,10.49,5.82A150.07,150.07,0,0,0,86,128,42,42,0,0,1,128,86Z",
            "M182,128a244.65,244.65,0,0,1-18.38,93.48,6,6,0,0,1-5.55,3.72,6.13,6.13,0,0,1-2.28-.45,6,6,0,0,1-3.27-7.84A232.64,232.64,0,0,0,170,128a6,6,0,0,1,12,0Z",
        ],
        "Light": [
            "M128,122a6,6,0,0,0-6,6,186.54,186.54,0,0,1-5.86,46.5,6,6,0,0,0,4.32,7.31,5.93,5.93,0,0,0,1.5.19,6,6,0,0,0,5.8-4.5A198.75,198.75,0,0,0,134,128,6,6,0,0,0,128,122Z",
            "M113.08,202.56a6,6,0,0,0-8,2.95c-2,4.24-4.09,8.47-6.36,12.57a6,6,0,0,0,2.34,8.15,5.88,5.88,0,0,0,2.9.76,6,6,0,0,0,5.25-3.09c2.42-4.36,4.7-8.87,6.78-13.39A6,6,0,0,0,113.08,202.56Z",
        ],
    }
    family_colors = {"Weather": "#2f8f88", "Surface": "#d95f45", "Light": "#3b82f6"}

    if not signature_scores.get("families"):
        empty_paths = "".join(
            f'<path class="mce-fingerprint-ridge ridge" d="{path}" />'
            for paths in ridge_paths.values()
            for path in paths
        )
        return """
            <style>
                * { box-sizing: border-box; }
                body { margin: 0; font-family: system-ui, sans-serif; color: #5d6b78; }
                .mce-fingerprint-empty { padding: 2px 0; }
                svg { display: block; width: 100%; height: 125px; }
                .ridge { fill: #9aabb4; fill-opacity: .32; stroke: rgba(20,32,43,0.9); stroke-width: 1.3; stroke-linejoin: round; stroke-linecap: round; }
                .copy { display: grid; gap: 2px; font-size: 12px; line-height: 1.25; }
                .copy strong { color: #14202b; }
            </style>
            <div class="mce-fingerprint-empty" aria-label="Hotspot fingerprint empty state">
                <svg viewBox="0 0 256 256" role="img" aria-label="Empty hotspot fingerprint">
                    __EMPTY_PATHS__
                </svg>
                <div class="copy">
                    <strong>Select a hotspot on the map to reveal its crash fingerprint.</strong>
                    <span>The outline will summarize how its conditions differ from the county.</span>
                </div>
            </div>
        """.replace("__EMPTY_PATHS__", empty_paths)

    groups = []
    tooltips = []
    for family, paths in ridge_paths.items():
        details = signature_scores["families"][family]
        score = details["distance"]
        similarity = 1.0 - score
        opacity = 0.18 + similarity * 0.82
        differences = "".join(
            f"<li>{escape(item['category'])}: {item['delta_pp']:+.1f} pp</li>"
            for item in details["largest_differences"]
        ) or "<li>No category-level difference</li>"
        paths_html = "".join(f'<path class="mce-fingerprint-ridge ridge" d="{path}" />' for path in paths)
        hit_paths_html = "".join(f'<path class="hit-area" d="{path}" />' for path in paths)
        tooltip_id = family.lower()
        groups.append(
            f'<g class="ridge-group {tooltip_id} {tooltip_id}-target" data-family="{tooltip_id}" tabindex="0" '
            f'role="img" aria-label="{family}: {score:.1%} difference from county" '
            f'style="--family-color:{family_colors[family]};--family-opacity:{opacity:.2f}">{paths_html}{hit_paths_html}</g>'
        )
        tooltips.append(
            f'<div class="tooltip {tooltip_id}" role="tooltip"><strong>{family}</strong>'
            f'<span>Difference from county: {score:.1%}</span><ul>{differences}</ul>'
            f'<small>Selected n={details["selected_sample_size"]:,} · County n={details["county_sample_size"]:,}</small></div>'
        )

    overall_difference = signature_scores["overall"]
    similarity = 1.0 - overall_difference
    if selection_summary:
        caution_html = (
            '<span class="sample-caution">Fewer than 30 crashes; compare percentages cautiously.</span>'
            if selection_summary["crash_count"] < 30
            else ""
        )
        selection_html = (
            f'<div class="selection-meta"><strong>Grid cell {escape(str(selection_summary["cell_id"]))}</strong>'
            f'<span>{selection_summary["crash_count"]:,} crashes · {selection_summary["county_share_pct"]:.2f}% of active county crashes · '
            f'{selection_summary["serious_or_fatal_count"]:,} serious/fatal</span>{caution_html}</div>'
        )
    else:
        selection_html = '<div class="selection-meta" aria-hidden="true"></div>'

    return f"""
        <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; font-family: system-ui, sans-serif; color: #344451; }}
            .card {{ padding: 2px 0; }}
            .header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                color: #14202b;
                font-size: 13px;
                font-weight: 700;
            }}
            .summary {{ display: grid; text-align: right; white-space: nowrap; }}
            .summary strong {{ font-size: 18px; }}
            .summary small {{ color: #5d6b78; font-size: 11px; font-weight: 400; }}
            .content {{
                display: grid; grid-template-columns: minmax(180px, .9fr) minmax(245px, 1.1fr);
                align-items: start; gap: 24px; margin-top: 5px;
            }}
            .figure {{ position: relative; }}
            svg {{
                display: block; width: 100%; height: 142px;
            }}
            .ridge-group {{
                cursor: help; outline: none;
            }}
            .ridge-group .ridge {{
                fill: var(--family-color);
                fill-opacity: var(--family-opacity);
                stroke: var(--family-color);
                stroke-width: 4;
                stroke-linejoin: round;
                stroke-linecap: round;
                transition: fill-opacity .15s ease, filter .15s ease;
            }}
            .hit-area {{
                fill: transparent; stroke: transparent; stroke-width: 16px; pointer-events: all;
            }}
            .ridge-group:hover .ridge, .ridge-group:focus .ridge {{
                filter: drop-shadow(0 0 2px rgba(20,32,43,.28));
            }}
            svg:has(.ridge-group:hover) .ridge-group:not(:hover) .ridge,
            svg:has(.ridge-group:focus) .ridge-group:not(:focus) .ridge {{
                fill-opacity: .10;
            }}
            .card:has(.weather-target:is(:hover,:focus)) .ridge-group:not(.weather) .ridge,
            .card:has(.surface-target:is(:hover,:focus)) .ridge-group:not(.surface) .ridge,
            .card:has(.light-target:is(:hover,:focus)) .ridge-group:not(.light) .ridge {{
                fill-opacity: .10;
            }}
            .card:has(.weather-target:is(:hover,:focus)) .weather .ridge,
            .card:has(.surface-target:is(:hover,:focus)) .surface .ridge,
            .card:has(.light-target:is(:hover,:focus)) .light .ridge {{
                filter: drop-shadow(0 0 2px rgba(20,32,43,.28));
                cursor: help; outline: none;
            }}
            .tooltip {{
                position: absolute; top: 10px; left: 10px; z-index: 2;
                display: grid; gap: 3px; width: min(310px, calc(100% - 20px));
                padding: 9px 11px; border: 1px solid rgba(100, 118, 116, 0.28);
                border-radius: 8px; background: rgba(246, 240, 230, 0.96);
                color: #344451; font-size: 12px;
                box-shadow: 0 6px 18px rgba(40, 56, 49, .12);
                opacity: 0; pointer-events: none; transition: opacity .12s ease;
            }}
            .tooltip strong {{ color: #14202b; font-size: 13px; }}
            .tooltip ul {{ margin: 2px 0; padding-left: 18px; }}
            .card:has(.weather-target:is(:hover,:focus)) .tooltip.weather,
            .card:has(.surface-target:is(:hover,:focus)) .tooltip.surface,
            .card:has(.light-target:is(:hover,:focus)) .tooltip.light {{ opacity: 1; }}
            .legend {{
                display: grid; align-content: start; gap: 7px;
                padding-top: 8px; font-size: 11px;
            }}
            .legend-row {{ display: flex; align-items: center; gap: 7px; min-width: 0; }}
            .line {{ width: 28px; border-top: 3px solid #a8b5a9; flex: 0 0 auto; }}
            .faint {{ opacity: .2; }} .solid {{ opacity: 1; }}
            .zone {{
                min-width: 51px; padding: 2px 5px; border: 1px solid #9db1bb;
                border-radius: 999px; color: #5d6b78; font-size: 9px;
                font-weight: 700; letter-spacing: .04em; text-align: center;
            }}
            .family-swatch {{
                width: 22px; border-top: 4px solid var(--swatch-color); flex: 0 0 auto;
            }}
            .family-target {{ cursor: help; border-radius: 5px; outline: none; }}
            .family-target:is(:hover,:focus) {{ color: #14202b; font-weight: 600; }}
            .selection-meta {{
                display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; min-height: 27px;
                margin-top: 4px; padding-top: 4px;
                border-top: 1px solid rgba(100,118,116,.18); font-size: 11px; line-height: 1.2;
            }}
            .selection-meta strong {{ color: #14202b; font-size: 12px; }}
            .sample-caution {{
                margin-left: auto; padding: 2px 7px; border-radius: 999px;
                background: #f3f3d9; color: #7a6200; font-size: 10px;
            }}
        </style>
        <div class="card" aria-label="Hotspot fingerprint visualization">
            <div class="header">
                <strong>Difference from county average</strong>
                <span class="summary"><strong>{similarity:.1%} similar</strong><small>{overall_difference:.1%} average difference</small></span>
            </div>
            <div class="content">
                <div class="figure">
                    <svg viewBox="0 0 256 256" role="img" aria-label="Crash fingerprint for the selected hotspot">
                        {''.join(groups)}
                    </svg>
                    {''.join(tooltips)}
                </div>
                <div class="legend" aria-label="Fingerprint legend">
                    <div class="legend-row"><span class="line faint"></span><span>Faint fill — more different</span></div>
                    <div class="legend-row"><span class="line solid"></span><span>Solid outline — fixed reference</span></div>
                    <div class="legend-row family-target weather-target" tabindex="0"><span class="family-swatch" style="--swatch-color:{family_colors['Weather']}"></span><span>Weather · {1 - signature_scores['families']['Weather']['distance']:.1%} similar</span></div>
                    <div class="legend-row family-target surface-target" tabindex="0"><span class="family-swatch" style="--swatch-color:{family_colors['Surface']}"></span><span>Surface · {1 - signature_scores['families']['Surface']['distance']:.1%} similar</span></div>
                    <div class="legend-row family-target light-target" tabindex="0"><span class="family-swatch" style="--swatch-color:{family_colors['Light']}"></span><span>Light · {1 - signature_scores['families']['Light']['distance']:.1%} similar</span></div>
                </div>
            </div>
            {selection_html}
        </div>
    """


def _render_map_legend(cells: pd.DataFrame) -> None:
    """Render a thin legend strip visually attached to the map."""
    st.markdown(
        f"""
        <section class="mce-safety-map-legend" aria-label="Safety hotspot map legend">
            <strong>Map</strong>
            <span class="mce-legend-item"><span class="mce-legend-gradient" aria-hidden="true"></span>Crash count {int(cells['crash_count'].min())}–{int(cells['crash_count'].max())}</span>
            <span class="mce-legend-item"><span class="mce-legend-ring" aria-hidden="true"></span>Selected cell</span>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_section_title(title: str, help_text: str) -> None:
    st.markdown(
        f"""
        <div class="mce-safety-section-title">
            <h3>{escape(title)}</h3>
            <span class="mce-safety-help" title="{escape(help_text)}" aria-label="{escape(help_text)}">?</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_safety_layout_css() -> None:
    st.markdown(
        """
        <style>
            .mce-view-heading { margin-bottom: .35rem; }
            .mce-view-heading h2 { margin: 0 0 .18rem 0; }
            .mce-view-heading p { margin: 0; }
            .mce-safety-section-title {
                display: flex; align-items: center; gap: 6px; margin: 0 0 2px 0; min-height: 28px;
            }
            .mce-safety-section-title h3 {
                margin: 0; padding: 0; font-size: 1.18rem; line-height: 1.2; color: #14202b;
            }
            .mce-safety-help {
                display: inline-grid; place-items: center; width: 16px; height: 16px;
                border: 1px solid #8797a3; border-radius: 50%; color: #657582;
                font-size: 10px; font-weight: 700; cursor: help;
            }
            .mce-safety-map-legend {
                display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
                min-height: 28px; padding: 4px 8px; margin: 0 0 3px 0;
                border: 1px solid rgba(100,118,116,.22); border-radius: 7px;
                background: rgba(255,255,255,.62); color: #445460; font-size: 11px;
            }
            .mce-safety-map-legend strong { color: #14202b; font-size: 11px; }
            .mce-safety-map-legend .mce-legend-item { display: inline-flex; align-items: center; gap: 5px; }
            .mce-safety-map-legend .mce-legend-gradient {
                width: 34px; height: 8px; border-radius: 999px;
            }
            .mce-safety-map-legend .mce-legend-ring {
                width: 10px; height: 10px; border: 2px solid #14202b; border-radius: 2px;
            }
            .mce-safety-conditions-head {
                display: flex; align-items: center; justify-content: space-between; gap: 12px;
                margin: 2px 0 0 0;
            }
            .mce-safety-condition-legend {
                display: flex; align-items: center; justify-content: flex-end; gap: 12px;
                color: #5d6b78; font-size: 11px; flex-wrap: wrap;
            }
            .mce-condition-key { display: inline-flex; align-items: center; gap: 5px; }
            .mce-condition-swatch { width: 9px; height: 9px; border-radius: 1px; display: inline-block; }
            .mce-condition-swatch.selected { background: #d95f45; }
            .mce-condition-swatch.county { background: #69aaa4; }
            .mce-safety-context { color: #687985; font-size: 11px; margin: 0 0 3px 0; }
            hr.mce-safety-divider {
                margin: .32rem 0 .38rem 0; border: 0; border-top: 1px solid rgba(100,118,116,.18);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_safety_hotspots_view() -> None:
    """Render the connected Safety Hotspots analysis."""
    _render_safety_layout_css()
    st.markdown(
        """
        <div class="mce-view-heading">
            <h2>Where, when, and under which conditions do crashes concentrate?</h2>
            <p>Select a roughly 1 km grid cell to compare its recorded conditions with the county average and inspect its crash timing.</p>
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

    date_column, mode_column = st.columns([1.35, 1], gap="small")
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
    """Render the compact linked map, fingerprint, timing, and condition workspace."""
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
    fingerprint = aggregate_fingerprint(linked, selected_cell)
    selected_size = len(linked[linked["cell_id"].eq(selected_cell)]) if selected_cell else 0

    time_context = f" · {selected_weekday} {selected_hour:02d}:00" if selected_weekday else ""
    overview_context = (
        f"{len(filtered):,} {mode.lower()} · {len(mapped):,} visible cells · {geography}{time_context}"
    )

    map_column, analysis_column = st.columns([1.15, 0.95], gap="small")

    with map_column:
        title_column, clear_column = st.columns([4.2, 1.25], gap="small", vertical_alignment="center")
        with title_column:
            _render_section_title(
                "Crash hotspots by grid cell",
                "Each grid cell summarizes crashes in roughly one square kilometre. Darker color means more crashes for the active filters. Click a cell to inspect it.",
            )
        with clear_column:
            if st.button(
                "Clear selection",
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

        st.markdown(f'<div class="mce-safety-context">{escape(overview_context)}</div>', unsafe_allow_html=True)
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
                height=505,
            )

    with analysis_column:
        _render_section_title(
            "Hotspot fingerprint",
            "The fingerprint summarizes how the selected hotspot differs from the county average. More opaque zones are more similar; hover a ridge or legend item for details.",
        )

        selection_summary = None
        if selected_cell and selected_cell in set(mapped["cell_id"]):
            row = mapped[mapped["cell_id"].eq(selected_cell)].iloc[0]
            selection_summary = {
                "cell_id": selected_cell,
                "crash_count": int(row["crash_count"]),
                "county_share_pct": float(row["county_share_pct"]),
                "serious_or_fatal_count": int(row["serious_or_fatal_count"]),
                "route_type": summarize_route_type(filtered, selected_cell),
                "common_roads": str(row["common_roads"]),
            }

        components.html(
            build_hotspot_signature_svg(
                calculate_signature_scores(fingerprint, selected_cell),
                selection_summary,
            ),
            height=225,
            scrolling=False,
        )

        st.markdown('<hr class="mce-safety-divider">', unsafe_allow_html=True)
        _render_section_title(
            "Crash timing",
            "Select a weekday-hour cell to filter the map and fingerprint. Double-click the heatmap to clear the time selection.",
        )
        st.markdown(
            '<div class="mce-safety-context">Select a weekday-hour cell to filter the linked views; double-click to clear.</div>',
            unsafe_allow_html=True,
        )
        heatmap_key = f"safety_heatmap_{heatmap_generation}"
        st.altair_chart(
            build_heatmap(timing, selected_weekday, selected_hour),
            key=heatmap_key,
            on_select=lambda: _time_selection_callback(heatmap_key),
            selection_mode="safety_time_pick",
            width="stretch",
        )

    st.markdown(
        """
        <div class="mce-safety-conditions-head">
            <div class="mce-safety-section-title" style="margin:0">
                <h3>Crash conditions</h3>
                <span class="mce-safety-help" title="Compare the selected hotspot with the active county average for weather, road surface, and light conditions.">?</span>
            </div>
            <div class="mce-safety-condition-legend" aria-label="Crash conditions legend">
                <span class="mce-condition-key"><span class="mce-condition-swatch selected"></span>Selected hotspot</span>
                <span class="mce-condition-key"><span class="mce-condition-swatch county"></span>County average</span>
                <span>Share of crashes (%)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if selected_cell is None:
        condition_context = f"County average n={len(linked):,} · categories sorted by county share"
    else:
        condition_context = (
            f"Selected hotspot n={selected_size:,} · county average n={len(linked):,} · categories sorted by county share"
        )
    st.markdown(f'<div class="mce-safety-context">{escape(condition_context)}</div>', unsafe_allow_html=True)

    condition_columns = st.columns(3, gap="small")
    for column, family in zip(condition_columns, CONDITION_FAMILIES):
        with column:
            st.altair_chart(build_condition_chart(fingerprint, family), width="stretch")

    st.caption(
        "All classified crashes excludes records without joinable person-level injury severity. The county fingerprint average includes the selected cell. Grid cells are 0.01° (approximately 1 km); results describe recorded crashes, not underlying exposure or causal risk."
    )
    if end_date.year == 2026:
        st.caption("The 2026 source snapshot ends on August 5 and is incomplete for annual comparisons.")
