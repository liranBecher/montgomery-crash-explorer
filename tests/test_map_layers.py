import unittest
import json

import pandas as pd

from ui.map_layers import cell_view_state, crash_point_layer


class SharedMapLayersTest(unittest.TestCase):
    def test_default_and_selected_cell_viewports(self) -> None:
        cells = pd.DataFrame(
            {
                "cell_id": ["one"],
                "center_latitude": [39.005],
                "center_longitude": [-77.105],
            }
        )
        default = cell_view_state(cells, None)
        selected = cell_view_state(cells, "one")
        missing = cell_view_state(cells, "missing")

        self.assertEqual((default.latitude, default.longitude, default.zoom), (39.12, -77.13, 8.6))
        self.assertEqual((missing.latitude, missing.longitude, missing.zoom), (39.12, -77.13, 8.6))
        self.assertEqual((selected.latitude, selected.longitude, selected.zoom), (39.005, -77.105, 13.0))

    def test_crash_points_only_exist_for_a_selected_cell(self) -> None:
        crashes = pd.DataFrame(
            {
                "report_number": ["A", "B"],
                "crash_datetime": pd.to_datetime(["2026-01-01 12:00", "2026-01-02 13:00"]),
                "cell_id": ["one", "two"],
                "latitude": [39.0, 39.1],
                "longitude": [-77.0, -77.1],
                "road_name": ["A ROAD", "B ROAD"],
                "severity": ["Fatal Injury", "No Apparent Injury"],
            }
        )

        self.assertIsNone(crash_point_layer(crashes, None, "crashes"))
        layer = crash_point_layer(crashes, "one", "crashes", (("severity", "Severity"),))
        self.assertEqual(layer.id, "crashes")
        self.assertTrue(layer.pickable)
        self.assertEqual(len(layer.data), 1)
        self.assertEqual(json.loads(layer.to_json())["radiusUnits"], "pixels")


if __name__ == "__main__":
    unittest.main()
