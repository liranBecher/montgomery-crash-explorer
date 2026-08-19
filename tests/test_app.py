from pathlib import Path
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from ui.fire_rescue import (
    _bound_date_range,
    _map_selection_callback,
    _map_selection_from_event,
    aggregate_station_radius,
    build_map,
    build_station_radius_bar,
)
from ui.components import SharedFilters, apply_shared_filters


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LayoutPrototypeTest(unittest.TestCase):
    def test_shared_filters_apply_dates_and_area_report_numbers(self) -> None:
        crashes = pd.DataFrame(
            {
                "report_number": ["A", "B", "C"],
                "crash_datetime": pd.to_datetime(
                    ["2025-01-01", "2025-06-01", "2026-01-01"]
                ),
            }
        )
        filters = SharedFilters(
            date(2025, 1, 1), date(2025, 12, 31), "Rockville", frozenset({"B", "C"})
        )

        self.assertEqual(
            apply_shared_filters(crashes, filters)["report_number"].tolist(),
            ["B"],
        )

    def test_date_presets_shift_to_the_last_available_date(self) -> None:
        self.assertEqual(
            _bound_date_range(
                date(2026, 8, 7),
                date(2026, 8, 14),
                date(2015, 1, 1),
                date(2026, 8, 5),
            ),
            (date(2026, 7, 29), date(2026, 8, 5)),
        )

    def test_map_selection_distinguishes_cells_stations_and_empty_space(self) -> None:
        self.assertEqual(
            _map_selection_from_event(
                {"selection": {"objects": {"crash-cells": [{"cell_id": "cell"}]}}}
            ),
            ("cell", None),
        )
        self.assertEqual(
            _map_selection_from_event(
                {"selection": {"objects": {"cell-crashes": [{"cell_id": "cell"}]}}}
            ),
            ("cell", None),
        )
        self.assertEqual(
            _map_selection_from_event(
                {"selection": {"objects": {"fire-stations": [{"station_id": "7"}]}}}
            ),
            (None, "7"),
        )
        self.assertEqual(
            _map_selection_from_event({"selection": {"objects": {}}}),
            (None, None),
        )
        self.assertEqual(
            _map_selection_from_event(
                {"selection": {"objects": {"map-background": [{}]}}}
            ),
            (None, None),
        )

    def test_fire_map_selection_remounts_map_for_selected_viewport(self) -> None:
        state = {
            "map": {
                "selection": {"objects": {"crash-cells": [{"cell_id": "cell"}]}}
            },
            "fire_rescue_map_generation": 5,
            "fire_rescue_scatter_generation": 2,
        }
        with patch("ui.fire_rescue.st.session_state", state):
            _map_selection_callback("map")

        self.assertEqual(state["fire_rescue_selected_cell"], "cell")
        self.assertEqual(state["fire_rescue_selected_station"], None)
        self.assertEqual(state["fire_rescue_map_generation"], 6)

    def test_station_radius_counts_overlapping_proximity(self) -> None:
        crashes = pd.DataFrame(
            {
                "latitude": [0.0, 0.02],
                "longitude": [0.0, 0.0],
                "severity": ["Fatal Injury", "Suspected Serious Injury"],
            }
        )
        stations = pd.DataFrame(
            {
                "station_name": ["A", "B"],
                "station_id": ["A", "B"],
                "address": ["1 Main St", "2 Main St"],
                "city": ["Test", "Test"],
                "station_latitude": [0.0, 0.01],
                "station_longitude": [0.0, 0.0],
            }
        )
        result = aggregate_station_radius(crashes, stations, 1.5)
        self.assertEqual(result["crash_count"].tolist(), [1, 2])
        self.assertEqual(result["injury_count"].tolist(), [1, 2])
        self.assertEqual(result["fatal_count"].tolist(), [1, 1])
        most = build_station_radius_bar(result, 1, None, "Most active")
        least = build_station_radius_bar(result, 1, None, "Least active")
        self.assertEqual(most.data["station_name"].tolist(), ["B"])
        self.assertEqual(least.data["station_name"].tolist(), ["A"])
        self.assertEqual(
            [parameter["name"] for parameter in most.to_dict()["params"]],
            ["station_pick"],
        )
        cells = pd.DataFrame(
            {
                "cell_id": ["cell"],
                "center_latitude": [0.0],
                "center_longitude": [0.0],
                "crash_count": [1],
                "severity_breakdown": ["Fatal: 1"],
                "nearest_station_name": ["A"],
                "nearest_station_distance_km": [0.0],
            }
        )
        deck = build_map(cells, stations, crashes, None, None, 1.5, False)
        self.assertEqual(deck.layers[0].id, "crash-cells")
        self.assertEqual(deck.initial_view_state.zoom, 8.6)

    def test_fire_map_semantic_zoom_preserves_station_zoom_priority(self) -> None:
        cells = pd.DataFrame(
            {
                "cell_id": ["cell"],
                "center_latitude": [39.105],
                "center_longitude": [-77.205],
                "crash_count": [1],
                "severity_breakdown": ["Fatal: 1"],
                "nearest_station_name": ["A"],
                "nearest_station_distance_km": [0.2],
            }
        )
        crashes = pd.DataFrame(
            {
                "report_number": ["A"],
                "crash_datetime": pd.to_datetime(["2026-01-05 01:00"]),
                "cell_id": ["cell"],
                "latitude": [39.101],
                "longitude": [-77.201],
                "road_name": ["A ROAD"],
                "severity": ["Fatal Injury"],
            }
        )
        stations = pd.DataFrame(
            {
                "station_name": ["A"],
                "station_id": ["A"],
                "address": ["1 Main St"],
                "city": ["Test"],
                "station_latitude": [39.2],
                "station_longitude": [-77.3],
            }
        )

        cell_deck = build_map(cells, stations, crashes, "cell", None, 3.0, False)
        self.assertEqual(cell_deck.initial_view_state.zoom, 13.0)
        self.assertEqual(
            [layer.id for layer in cell_deck.layers],
            ["crash-cells", "fire-stations", "selected-cell", "cell-crashes"],
        )
        station_deck = build_map(cells, stations, crashes, None, "A", 3.0, True)
        self.assertEqual(station_deck.initial_view_state.zoom, 10.5)
        self.assertAlmostEqual(station_deck.initial_view_state.latitude, 39.2)

    def test_app_renders_connected_fire_rescue_view(self) -> None:
        app = AppTest.from_file(str(PROJECT_ROOT / "app.py"))
        app.session_state["filter_start_date"] = None
        app.session_state["filter_end_date"] = None
        app.session_state["filter_area"] = None
        app.run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "Safety Hotspots",
                "Fire & Rescue Proximity",
                "Police Breathalyzers",
            ],
        )
        dates = {widget.label: widget for widget in app.date_input}
        self.assertFalse(dates["From"].disabled)
        self.assertFalse(dates["To"].disabled)
        self.assertEqual(set(dates), {"From", "To"})
        selectboxes = {widget.label: widget for widget in app.selectbox}
        self.assertFalse(selectboxes["Area"].disabled)
        self.assertIn("Rockville", selectboxes["Area"].options)
        self.assertFalse(selectboxes["Time of day"].disabled)
        self.assertEqual(selectboxes["Station activity"].value, "Most active")
        sliders = {widget.label: widget for widget in app.slider}
        self.assertEqual(sliders["Station radius (km)"].value, 3.0)
        self.assertEqual(sliders["Stations shown"].value, 15)
        self.assertIn(
            "Filtered crashes near mapped stations",
            [heading.value for heading in app.subheader],
        )
        severity = next(
            widget for widget in app.multiselect
            if widget.label == "Maximum injury severity"
        )
        self.assertCountEqual(
            severity.options,
            [
                "Fatal Injury",
                "Suspected Serious Injury",
                "Possible Injury",
            ],
        )
        self.assertTrue(
            any(
                "crashes can appear in more than one bar" in caption.value
                for caption in app.caption
            )
        )
        self.assertCountEqual(
            [button.label for button in app.button],
            [
                "Reset filters",
                "Clear selection",
                "Clear selection",
                "Clear selection",
            ],
        )
        self.assertFalse(next(button for button in app.button if button.label == "Reset filters").disabled)
        self.assertTrue(
            all(button.disabled for button in app.button if button.label == "Clear selection")
        )

        selectboxes["Time of day"].set_value("Overnight")
        selectboxes["Station activity"].set_value("Least active")
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(
            next(widget for widget in app.selectbox if widget.label == "Time of day").value,
            "Overnight",
        )
        self.assertTrue(
            any("Bottom 15 mapped stations" in caption.value for caption in app.caption)
        )

        next(widget for widget in app.selectbox if widget.label == "Time of day").set_value("All day")
        next(widget for widget in app.selectbox if widget.label == "Area").set_value("Rockville")
        app.run(timeout=15)
        self.assertFalse(app.exception)
        self.assertEqual(
            next(widget for widget in app.selectbox if widget.label == "Area").value,
            "Rockville",
        )

        rendered_text = "\n".join(
            [markdown.value for markdown in app.markdown]
            + [heading.value for heading in app.subheader]
        )
        for expected_text in (
            "Crash hotspots by grid cell",
            "Hotspot fingerprint",
            "Crash timing",
            "Where are crashes farther from mapped fire stations?",
            "Map legend",
            "Filtered crash count per grid cell: color",
            "Mapped fire station (rescue cross)",
            "Scatterplot legend",
            "Visible-cell medians",
            "Alcohol-related crashes by grid cell",
        ):
            with self.subTest(expected_text=expected_text):
                self.assertIn(expected_text, rendered_text)


if __name__ == "__main__":
    unittest.main()
