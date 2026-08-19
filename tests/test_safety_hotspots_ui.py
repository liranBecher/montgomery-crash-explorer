import unittest
from unittest.mock import patch

import pandas as pd

from ui.safety_hotspots import (
    _map_selection_callback,
    _map_cell_from_event,
    _time_from_event,
    aggregate_cells,
    aggregate_fingerprint,
    aggregate_timing,
    build_fingerprint,
    build_heatmap,
    build_map,
    build_hotspot_signature_svg,
    calculate_signature_scores,
    filter_safety_conditions,
)


class SafetyHotspotsUiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.crashes = pd.DataFrame(
            {
                "report_number": ["A", "B", "C", "D"],
                "crash_datetime": pd.to_datetime(
                    ["2026-01-05 01:00", "2026-01-05 01:30", "2026-01-06 02:00", "2026-01-07 03:00"]
                ),
                "cell_id": ["39.00:-77.10", "39.00:-77.10", "39.01:-77.11", "39.02:-77.12"],
                "latitude": [39.001, 39.002, 39.011, 39.021],
                "longitude": [-77.101, -77.102, -77.111, -77.121],
                "severity": ["No Apparent Injury", "Suspected Serious Injury", "No Apparent Injury", "No Apparent Injury"],
                "weekday": ["Monday", "Monday", "Tuesday", "Wednesday"],
                "hour": [1, 1, 2, 3],
                "serious_or_fatal": [False, True, False, False],
                "road_name": ["A ROAD", "A ROAD", "B ROAD", pd.NA],
                "route_group": ["County", "County", "State / US", "Not recorded"],
                "weather_group": ["Clear", "Rain", "Clear", "Not recorded"],
                "surface_group": ["Dry", "Wet", "Dry", "Not recorded"],
                "light_group": ["Daylight", "Dark - lighted", "Daylight", "Not recorded"],
            }
        )

    def test_aggregates_cells_conditions_and_complete_timing(self) -> None:
        cells = aggregate_cells(self.crashes).set_index("cell_id")
        self.assertEqual(cells.loc["39.00:-77.10", "crash_count"], 2)
        self.assertEqual(cells.loc["39.00:-77.10", "serious_or_fatal_count"], 1)
        self.assertAlmostEqual(cells.loc["39.00:-77.10", "center_latitude"], 39.005)

        fingerprint = aggregate_fingerprint(self.crashes, "39.00:-77.10")
        self.assertEqual(set(fingerprint["family"]), {"Weather", "Surface", "Light"})
        not_recorded = fingerprint[
            fingerprint["category"].eq("Not recorded")
            & fingerprint["geography"].eq("County average")
        ]
        self.assertEqual(len(not_recorded), 3)
        county_baseline = fingerprint[
            fingerprint["family"].eq("Weather")
            & fingerprint["category"].eq("Clear")
            & fingerprint["geography"].eq("County average")
        ].iloc[0]
        self.assertEqual(county_baseline["share_pct"], 50)

        baseline_only = aggregate_fingerprint(self.crashes)
        self.assertEqual(set(baseline_only["family"]), {"Weather", "Surface", "Light"})
        self.assertEqual(
            baseline_only[baseline_only["family"].eq("Weather") & baseline_only["category"].eq("Clear")]["geography"].unique().tolist(),
            ["County average"],
        )

        timing = aggregate_timing(self.crashes, "Countywide", "Jan 1–Jan 31")
        self.assertEqual(len(timing), 7 * 24)
        monday_one = timing[timing["weekday"].eq("Monday") & timing["hour"].eq(1)].iloc[0]
        self.assertEqual(monday_one["crash_count"], 2)
        self.assertEqual(monday_one["share_pct"], 50)

    def test_filters_safety_conditions_across_families(self) -> None:
        filtered = filter_safety_conditions(
            self.crashes,
            {"Weather": ["Clear"], "Surface": ["Dry"], "Light": ["Daylight"]},
        )
        self.assertEqual(filtered["report_number"].tolist(), ["A", "C"])
        self.assertEqual(
            len(filter_safety_conditions(self.crashes, {"Weather": []})),
            len(self.crashes),
        )

    def test_builds_linked_views_and_parses_selections(self) -> None:
        cells = aggregate_cells(self.crashes)
        fingerprint = aggregate_fingerprint(self.crashes, "39.00:-77.10")
        timing = aggregate_timing(self.crashes, "Countywide", "Jan 1–Jan 31")
        deck = build_map(cells, self.crashes, "39.00:-77.10", "Jan 1–Jan 31")
        default_deck = build_map(cells, self.crashes, None, "Jan 1–Jan 31")
        heatmap = build_heatmap(timing, "Monday", 1).to_dict()
        comparison = build_fingerprint(fingerprint).to_dict()

        self.assertEqual(
            [layer.id for layer in deck.layers],
            ["safety-cells", "selected-safety-cell", "safety-crashes"],
        )
        self.assertEqual(deck.initial_view_state.zoom, 13.0)
        self.assertAlmostEqual(deck.initial_view_state.latitude, 39.005)
        self.assertEqual([layer.id for layer in default_deck.layers], ["safety-cells"])
        self.assertEqual(
            (
                default_deck.initial_view_state.latitude,
                default_deck.initial_view_state.longitude,
                default_deck.initial_view_state.zoom,
            ),
            (39.12, -77.13, 8.6),
        )
        self.assertEqual(heatmap["params"][0]["name"], "safety_time_pick")
        self.assertEqual(len(comparison["hconcat"]), 3)
        self.assertEqual(
            _map_cell_from_event(
                {"selection": {"objects": {"safety-cells": [{"cell_id": "39.00:-77.10"}]}}}
            ),
            "39.00:-77.10",
        )
        self.assertEqual(
            _map_cell_from_event(
                {"selection": {"objects": {"safety-crashes": [{"cell_id": "39.00:-77.10"}]}}}
            ),
            "39.00:-77.10",
        )
        self.assertEqual(
            _time_from_event(
                {"selection": {"safety_time_pick": [{"weekday": "Monday", "hour": 1}]}}
            ),
            ("Monday", 1),
        )

    def test_calculates_hotspot_signature_scores(self) -> None:
        fingerprint = aggregate_fingerprint(self.crashes, "39.00:-77.10")
        scores = calculate_signature_scores(fingerprint)

        self.assertIn("Weather", scores["families"])
        self.assertGreater(scores["overall"], 0)
        self.assertEqual(scores["selected_sample_size"], 2)
        self.assertEqual(scores["county_sample_size"], 4)
        self.assertIn("largest_differences", scores["families"]["Weather"])

    def test_builds_empty_and_selected_signature_svg(self) -> None:
        empty_svg = build_hotspot_signature_svg({"selected_cell": None, "families": {}})
        self.assertIn("Select a hotspot", empty_svg)
        self.assertIn("mce-fingerprint-empty", empty_svg)

        fingerprint = aggregate_fingerprint(self.crashes, "39.00:-77.10")
        selected_svg = build_hotspot_signature_svg(calculate_signature_scores(fingerprint))
        self.assertIn("Weather", selected_svg)
        self.assertIn("mce-fingerprint-ridge", selected_svg)
        self.assertIn('pathLength="1"', selected_svg)
        self.assertIn("stroke-dasharray=", selected_svg)
        self.assertIn("Colored area — similarity to county", selected_svg)
        self.assertNotIn("--family-opacity", selected_svg)
        self.assertEqual(selected_svg.count('class="mce-fingerprint-ridge ridge-fill"'), 3)

        summary = {
            "cell_id": "39.00:-77.10",
            "crash_count": 2,
            "county_share_pct": 50.0,
            "serious_or_fatal_count": 1,
        }
        selected_svg = build_hotspot_signature_svg(
            calculate_signature_scores(fingerprint), summary
        )
        self.assertIn('class="content"', selected_svg)
        self.assertIn("Fewer than 30 crashes;<br>compare percentages cautiously.", selected_svg)

        summary["crash_count"] = 30
        selected_svg = build_hotspot_signature_svg(
            calculate_signature_scores(fingerprint), summary
        )
        self.assertNotIn("Fewer than 30 crashes", selected_svg)

    def test_map_selection_remounts_map_for_semantic_zoom(self) -> None:
        state = {
            "map": {
                "selection": {
                    "objects": {"safety-cells": [{"cell_id": "39.00:-77.10"}]}
                }
            },
            "safety_map_generation": 2,
            "safety_heatmap_generation": 4,
        }
        with patch("ui.safety_hotspots.st.session_state", state):
            _map_selection_callback("map")

        self.assertEqual(state["safety_selected_cell"], "39.00:-77.10")
        self.assertEqual(state["safety_map_generation"], 3)


if __name__ == "__main__":
    unittest.main()
