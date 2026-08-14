from pathlib import Path
import unittest
from datetime import date

import pandas as pd
from streamlit.testing.v1 import AppTest

from ui.fire_rescue import (
    _bound_date_range,
    _map_selection_from_event,
    aggregate_station_radius,
    build_map,
    build_station_radius_bar,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class LayoutPrototypeTest(unittest.TestCase):
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
        self.assertEqual(deck.layers[0].id, "map-background")

    def test_app_renders_connected_fire_rescue_view(self) -> None:
        app = AppTest.from_file(str(PROJECT_ROOT / "app.py")).run(timeout=15)

        self.assertFalse(app.exception)
        self.assertEqual(
            [tab.label for tab in app.tabs],
            [
                "Safety Hotspots",
                "Fire & Rescue Proximity",
                "Police Breathalyzers",
                "Vehicles & Injuries",
            ],
        )
        dates = {widget.label: widget for widget in app.date_input}
        self.assertTrue(dates["From"].disabled)
        self.assertTrue(dates["To"].disabled)
        self.assertFalse(dates["Crash date range"].disabled)
        selectboxes = {widget.label: widget for widget in app.selectbox}
        self.assertTrue(selectboxes["Area"].disabled)
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
            ["Clear selection", "Clear map selection", "Clear alcohol selection"],
        )
        self.assertTrue(all(button.disabled for button in app.button))

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

        rendered_text = "\n".join(markdown.value for markdown in app.markdown)
        for expected_text in (
            "Fire &amp; Rescue and alcohol analyses connected",
            "Overview first",
            "Zoom and filter",
            "Details on demand",
            "Crash hotspot map",
            "Crash timing",
            "Where are crashes farther from mapped fire stations?",
            "Map legend",
            "Filtered crash count: color",
            "Mapped fire station (rescue cross)",
            "Scatterplot legend",
            "Visible-cell medians",
            "Alcohol-related crashes by grid cell",
            "Injury distribution by vehicle age",
            "Planned interaction:",
            "No visualization is rendered",
        ):
            with self.subTest(expected_text=expected_text):
                self.assertIn(expected_text, rendered_text)


if __name__ == "__main__":
    unittest.main()
