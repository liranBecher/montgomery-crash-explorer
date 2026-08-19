from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

import networkx as nx
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PROJECT_ROOT
    / "preprocess"
    / "fire-and-rescue"
    / "preprocess_fire_and_rescue.py"
)
SPEC = spec_from_file_location("fire_rescue_preprocessing", MODULE_PATH)
preprocessing = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preprocessing)


class FireRescuePreprocessingTest(unittest.TestCase):
    def test_transforms_severity_time_grid_and_distance(self) -> None:
        drivers = pd.DataFrame(
            {
                "Report Number": ["A", "B", "C"],
                "Injury Severity": [
                    " suspected serious injury ",
                    "NO APPARENT INJURY",
                    "possible injury",
                ],
            }
        )
        non_motorists = pd.DataFrame(
            {
                "Report Number": ["B", "C"],
                "Injury Severity": ["Fatal Injury", "SUSPECTED MINOR INJURY"],
            }
        )
        severity = preprocessing.aggregate_max_severity(drivers, non_motorists)
        ranks = severity.set_index("Report Number")["severity_rank"].to_dict()
        self.assertEqual(ranks, {"A": 3, "B": 4, "C": 2})

        crashes = pd.DataFrame(
            {
                "Crash Date/Time": [
                    "01/01/2026 05:59:00 AM",
                    "01/01/2026 06:00:00 AM",
                    "01/01/2026 12:00:00 PM",
                    "01/01/2026 06:00:00 PM",
                ],
                "latitude": [39.101, 39.109, 39.111, 39.119],
                "longitude": [-77.201, -77.209, -77.211, -77.219],
            }
        )
        timed = preprocessing.add_time_fields(crashes)
        self.assertEqual(
            timed["daypart"].tolist(),
            ["Overnight", "Morning", "Afternoon", "Evening"],
        )
        gridded = preprocessing.assign_grid_cells(timed)
        self.assertEqual(gridded.loc[0, "cell_id"], "39.10:-77.21")

        cells = pd.DataFrame(
            {"cell_id": ["one"], "center_latitude": [39.0], "center_longitude": [-77.0]}
        )
        stations = pd.DataFrame(
            {
                "station_id": ["near", "far"],
                "station_name": ["Near station", "Far station"],
                "station_latitude": [39.01, 40.0],
                "station_longitude": [-77.0, -77.0],
            }
        )
        result = preprocessing.nearest_stations(cells, stations)
        self.assertEqual(result.loc[0, "nearest_station_id"], "near")
        self.assertAlmostEqual(result.loc[0, "nearest_station_distance_km"], 1.112, places=3)

    def test_road_proximity_respects_direction_and_station_access(self) -> None:
        graph = nx.DiGraph()
        graph.add_weighted_edges_from(
            [("crash-a", "station-a", 10), ("crash-a", "station-b", 5)],
            weight="length",
        )
        graph.add_weighted_edges_from(
            [("crash-b", "station-a", 100), ("crash-b", "station-b", 2)],
            weight="length",
        )

        distances, station_positions = preprocessing.road_proximity_from_nodes(
            graph,
            np.array(["crash-a", "crash-b"]),
            np.array([1.0, 1.0]),
            np.array(["station-a", "station-b"]),
            np.array([0.0, 20.0]),
        )

        np.testing.assert_allclose(distances, [0.011, 0.023])
        self.assertEqual(station_positions.tolist(), [0, 1])

    def test_committed_parquet_contract(self) -> None:
        output_dir = PROJECT_ROOT / "data" / "processed" / "fire-and-rescue"
        crashes = pd.read_parquet(output_dir / "fire_rescue_crashes.parquet")
        cells = pd.read_parquet(output_dir / "fire_rescue_cells.parquet")
        stations = pd.read_parquet(output_dir / "fire_stations.parquet")

        self.assertEqual(len(crashes), 122367)
        self.assertEqual(len(cells), 1262)
        self.assertEqual(len(stations), 37)
        self.assertTrue(
            {
                "nearest_road_station_id",
                "nearest_road_station_name",
                "nearest_road_station_distance_km",
                "road_snap_distance_m",
            }.issubset(crashes.columns)
        )
        self.assertEqual(
            crashes["severity"].value_counts().to_dict(),
            {
                "No Apparent Injury": 84205,
                "Possible Injury": 18496,
                "Suspected Minor Injury": 16847,
                "Suspected Serious Injury": 2450,
                "Fatal Injury": 369,
            },
        )
        preprocessing.validate_outputs(crashes, cells, stations)


if __name__ == "__main__":
    unittest.main()
