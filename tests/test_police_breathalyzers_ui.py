from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from ui.police_breathalyzers import (
    _map_selection_callback,
    _map_cell_from_event,
    _time_from_event,
    aggregate_cells,
    aggregate_timing,
    build_heatmap,
    build_map,
    effective_minimum_sample,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PoliceBreathalyzersUiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.crashes = pd.DataFrame(
            {
                "report_number": ["A", "B", "C", "D"],
                "crash_datetime": pd.to_datetime(
                    ["2026-01-05 01:00", "2026-01-05 01:30", "2026-01-06 02:00", "2026-01-07 03:00"]
                ),
                "cell_id": ["one", "one", "two", "three"],
                "latitude": [39.001, 39.002, 39.101, 39.201],
                "longitude": [-77.001, -77.002, -77.101, -77.201],
                "weekday": ["Monday", "Monday", "Tuesday", "Wednesday"],
                "hour": [1, 1, 2, 3],
                "alcohol_status": [
                    "Alcohol present/contributed",
                    "No alcohol indication",
                    "Suspected alcohol use",
                    "No alcohol indication",
                ],
                "road_name": ["A ROAD", "A ROAD", "B ROAD", "C ROAD"],
                "municipality": ["A", "A", "B", "C"],
            }
        )
        self.alcohol = self.crashes[
            self.crashes["alcohol_status"].isin(
                ["Alcohol present/contributed", "Suspected alcohol use"]
            )
        ]
        self.cells = pd.DataFrame(
            {
                "cell_id": ["one", "two", "three"],
                "center_latitude": [39.0, 39.1, 39.2],
                "center_longitude": [-77.0, -77.1, -77.2],
            }
        )

    def test_aggregates_counts_shares_and_complete_timing_grid(self) -> None:
        mapped = aggregate_cells(self.crashes, self.alcohol, self.cells).set_index("cell_id")
        self.assertEqual(mapped.loc["one", "alcohol_count"], 1)
        self.assertEqual(mapped.loc["one", "total_crashes"], 2)
        self.assertEqual(mapped.loc["one", "alcohol_share_pct"], 50.0)
        self.assertNotIn("three", mapped.index)

        timing = aggregate_timing(self.crashes, self.alcohol)
        self.assertEqual(len(timing), 7 * 24)
        monday_one = timing[timing["weekday"].eq("Monday") & timing["hour"].eq(1)].iloc[0]
        self.assertEqual(monday_one["alcohol_count"], 1)
        self.assertEqual(monday_one["alcohol_share_pct"], 50.0)

    def test_builds_linked_map_heatmap_and_parses_selections(self) -> None:
        mapped = aggregate_cells(self.crashes, self.alcohol, self.cells)
        timing = aggregate_timing(self.crashes, self.alcohol)
        deck = build_map(mapped, self.alcohol, "Alcohol-related crash share", "one")
        default_deck = build_map(
            mapped, self.alcohol, "Alcohol-related crash share", None
        )
        chart = build_heatmap(
            timing, "Alcohol-related crash count", "Monday", 1
        ).to_dict()

        self.assertEqual(
            [layer.id for layer in deck.layers],
            ["alcohol-cells", "selected-alcohol-cell", "alcohol-crashes"],
        )
        self.assertEqual(deck.initial_view_state.zoom, 13.0)
        self.assertEqual([layer.id for layer in default_deck.layers], ["alcohol-cells"])
        self.assertEqual(
            (
                default_deck.initial_view_state.latitude,
                default_deck.initial_view_state.longitude,
                default_deck.initial_view_state.zoom,
            ),
            (39.12, -77.13, 8.6),
        )
        self.assertEqual(chart["params"][0]["name"], "time_pick")
        self.assertEqual(
            _map_cell_from_event(
                {"selection": {"objects": {"alcohol-cells": [{"cell_id": "one"}]}}}
            ),
            "one",
        )
        self.assertEqual(
            _map_cell_from_event(
                {"selection": {"objects": {"alcohol-crashes": [{"cell_id": "one"}]}}}
            ),
            "one",
        )
        self.assertEqual(
            _time_from_event(
                {"selection": {"time_pick": [{"weekday": "Monday", "hour": 1}]}}
            ),
            ("Monday", 1),
        )
        self.assertEqual(effective_minimum_sample(5, "Monday"), 1)
        self.assertEqual(effective_minimum_sample(5, None), 5)

    def test_map_selection_remounts_map_for_semantic_zoom(self) -> None:
        state = {
            "map": {
                "selection": {"objects": {"alcohol-cells": [{"cell_id": "one"}]}}
            },
            "alcohol_map_generation": 1,
            "alcohol_heatmap_generation": 3,
        }
        with patch("ui.police_breathalyzers.st.session_state", state):
            _map_selection_callback("map")

        self.assertEqual(state["alcohol_selected_cell"], "one")
        self.assertEqual(state["alcohol_map_generation"], 2)


if __name__ == "__main__":
    unittest.main()
