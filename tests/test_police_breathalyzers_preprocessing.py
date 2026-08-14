from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    PROJECT_ROOT
    / "preprocess"
    / "police-breathalyzers"
    / "preprocess_police_breathalyzers.py"
)
SPEC = spec_from_file_location("police_breathalyzers_preprocessing", MODULE_PATH)
preprocessing = module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(preprocessing)


class PoliceBreathalyzersPreprocessingTest(unittest.TestCase):
    def test_classifies_every_alcohol_wording_without_false_negation_matches(self) -> None:
        values = pd.Series(
            [
                "ALCOHOL PRESENT, NONE DETECTED",
                "alcohol contributed",
                "Suspect of Alcohol Use, Not Suspect of Drug Use",
                "COMBINED SUBSTANCE PRESENT",
                "COMBINATION CONTRIBUTED",
                "Not Suspect of Alcohol Use, Suspect of Drug Use",
                pd.NA,
            ]
        )
        self.assertEqual(
            preprocessing.classify_alcohol_status(values).tolist(),
            [
                "Alcohol present/contributed",
                "Alcohol present/contributed",
                "Suspected alcohol use",
                "Combined substance",
                "Combined substance",
                "No alcohol indication",
                "Unknown",
            ],
        )

    def test_committed_parquet_contract(self) -> None:
        output_dir = PROJECT_ROOT / "data" / "processed" / "police-breathalyzers"
        crashes = pd.read_parquet(output_dir / "alcohol_crashes.parquet")
        cells = pd.read_parquet(output_dir / "alcohol_cells.parquet")

        self.assertEqual(len(crashes), 124119)
        self.assertEqual(len(cells), 1269)
        self.assertEqual(int(crashes["alcohol_related"].sum()), 6950)
        self.assertEqual(
            crashes["alcohol_status"].value_counts().to_dict(),
            {
                "No alcohol indication": 92969,
                "Unknown": 24200,
                "Alcohol present/contributed": 5486,
                "Suspected alcohol use": 1325,
                "Combined substance": 139,
            },
        )
        preprocessing.validate_outputs(crashes, cells)


if __name__ == "__main__":
    unittest.main()
