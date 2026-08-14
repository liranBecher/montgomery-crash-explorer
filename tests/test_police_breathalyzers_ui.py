from pathlib import Path
import unittest

import pandas as pd

from ui.police_breathalyzers import (
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
                "report_number": ["A", "B", "C"],
                "cell_id": ["one", "one", "two"],
                "weekday": ["Monday", "Monday", "Tuesday"],
                "hour": [1, 1, 2],
                "alcohol_status": [
                    "Alcohol present/contributed",
                    "No alcohol indication",
                    "Suspected alcohol use",
                ],
                "road_name": ["A ROAD", "A ROAD", "B ROAD"],
            }
        )
        self.alcohol = self.crashes[
            self.crashes["alcohol_status"].isin(
                ["Alcohol present/contributed", "Suspected alcohol use"]
            )
        ]
        self.cells = pd.DataFrame(
            {
                "cell_id": ["one", "two"],
                "center_latitude": [39.0, 39.1],
                "center_longitude": [-77.0, -77.1],
            }
        )

    def test_aggregates_counts_shares_and_complete_timing_grid(self) -> None:
        mapped = aggregate_cells(self.crashes, self.alcohol, self.cells).set_index("cell_id")
        self.assertEqual(mapped.loc["one", "alcohol_count"], 1)
        self.assertEqual(mapped.loc["one", "total_crashes"], 2)
        self.assertEqual(mapped.loc["one", "alcohol_share_pct"], 50.0)

        timing = aggregate_timing(self.crashes, self.alcohol)
        self.assertEqual(len(timing), 7 * 24)
        monday_one = timing[timing["weekday"].eq("Monday") & timing["hour"].eq(1)].iloc[0]
        self.assertEqual(monday_one["alcohol_count"], 1)
        self.assertEqual(monday_one["alcohol_share_pct"], 50.0)

    def test_builds_linked_map_heatmap_and_parses_selections(self) -> None:
        mapped = aggregate_cells(self.crashes, self.alcohol, self.cells)
        timing = aggregate_timing(self.crashes, self.alcohol)
        deck = build_map(mapped, "Alcohol-related crash share", "one")
        chart = build_heatmap(
            timing, "Alcohol-related crash count", "Monday", 1
        ).to_dict()

        self.assertEqual([layer.id for layer in deck.layers], ["alcohol-cells", "selected-alcohol-cell"])
        self.assertEqual(chart["params"][0]["name"], "time_pick")
        self.assertEqual(
            _map_cell_from_event(
                {"selection": {"objects": {"alcohol-cells": [{"cell_id": "one"}]}}}
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


if __name__ == "__main__":
    unittest.main()
