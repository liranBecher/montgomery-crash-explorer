from datetime import timedelta
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PROJECT_ROOT
    / "preprocess"
    / "safety-hotspots"
    / "preprocess_safety_hotspots.py"
)
SPEC = spec_from_file_location("safety_hotspots_preprocessing", MODULE_PATH)
preprocessing = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preprocessing)


class SafetyHotspotsPreprocessingTest(unittest.TestCase):
    def test_transforms_severity_time_grid_and_categories(self) -> None:
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
        self.assertEqual(
            severity.set_index("Report Number")["severity_rank"].to_dict(),
            {"A": 3, "B": 4, "C": 2},
        )

        crashes = pd.DataFrame(
            {
                "Crash Date/Time": ["01/05/2026 11:30:00 PM"],
                "latitude": [39.109],
                "longitude": [-77.201],
            }
        )
        timed = preprocessing.add_time_fields(crashes)
        self.assertEqual(timed.loc[0, "weekday"], "Monday")
        self.assertEqual(timed.loc[0, "weekday_index"], 0)
        self.assertEqual(timed.loc[0, "hour"], 23)
        gridded = preprocessing.assign_grid_cells(timed)
        self.assertEqual(gridded.loc[0, "cell_id"], "39.10:-77.21")

        routes = preprocessing.group_categories(
            pd.Series(["County", " county route ", None]),
            preprocessing.ROUTE_GROUP,
            "Route Type",
        )
        self.assertEqual(routes.tolist(), ["County", "County", "Not recorded"])
        lights = preprocessing.group_categories(
            pd.Series(["DARK LIGHTS ON", "Dark - Lighted"]),
            preprocessing.LIGHT_GROUP,
            "Light",
        )
        self.assertEqual(lights.tolist(), ["Dark - lighted", "Dark - lighted"])

        with self.assertRaisesRegex(ValueError, "Unknown Weather label"):
            preprocessing.group_categories(
                pd.Series(["VOLCANIC ASH"]), preprocessing.WEATHER_GROUP, "Weather"
            )

    def test_committed_parquet_contract_and_chart_aggregations(self) -> None:
        crashes = pd.read_parquet(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "safety-hotspots"
            / "safety_crashes.parquet"
        )
        preprocessing.validate_output(crashes)

        self.assertEqual(len(crashes), 122367)
        self.assertEqual(crashes["cell_id"].nunique(), 1262)
        self.assertEqual(int(crashes["serious_or_fatal"].sum()), 2819)
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

        end_date = crashes["crash_datetime"].max().date()
        start_date = end_date - timedelta(days=365 * 5)
        recent = crashes[
            crashes["crash_datetime"].dt.date.between(start_date, end_date)
        ]
        self.assertEqual((start_date.isoformat(), end_date.isoformat()), ("2021-08-06", "2026-08-05"))
        self.assertEqual(len(recent), 50570)
        self.assertEqual(int(recent["serious_or_fatal"].sum()), 1178)

        map_counts = recent.groupby("cell_id").size()
        self.assertEqual(int(map_counts.sum()), len(recent))
        for column in (
            "route_group",
            "weather_group",
            "surface_group",
            "light_group",
        ):
            self.assertEqual(int(recent[column].value_counts().sum()), len(recent))
            self.assertLessEqual(crashes[column].nunique(), 8)

        timing_index = pd.MultiIndex.from_product(
            [range(7), range(24)], names=["weekday_index", "hour"]
        )
        timing = recent.groupby(["weekday_index", "hour"]).size().reindex(
            timing_index, fill_value=0
        )
        self.assertEqual(len(timing), 168)
        self.assertEqual(int(timing.sum()), len(recent))


if __name__ == "__main__":
    unittest.main()
