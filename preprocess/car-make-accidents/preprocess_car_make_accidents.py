"""Build vehicle-make injury-severity percentages for visualization."""

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "car_make_accidents.csv"

MAKE_COLUMN = "Vehicle Make"
SEVERITY_COLUMN = "Injury Severity"
MAKE_ALIASES = {
    "TOYT": "TOYOTA",
    "HOND": "HONDA",
    "NISS": "NISSAN",
    "CHEV": "CHEVROLET",
    "CHEVY": "CHEVROLET",
    "HYUN": "HYUNDAI",
    "MERCEDES": "MERCEDES-BENZ",
    "MERZ": "MERCEDES-BENZ",
    "MERC": "MERCURY",
    "VOLKSWAGON": "VOLKSWAGEN",
    "VOLK": "VOLKSWAGEN",
    "VOLKS": "VOLKSWAGEN",
    "VW": "VOLKSWAGEN",
    "GILG": "GILLIG",
    "GILL": "GILLIG",
    "THOMAS": "THOMAS BUILT",
    "THOM": "THOMAS BUILT",
    "FRHT": "FREIGHTLINER",
    "ACUR": "ACURA",
    "SUBA": "SUBARU",
    "INFI": "INFINITI",
    "DODG": "DODGE",
    "LEXS": "LEXUS",
    "LEXU": "LEXUS",
    "MAZD": "MAZDA",
    "CHRY": "CHRYSLER",
    "CADI": "CADILLAC",
    "MITS": "MITSUBISHI",
    "VOLV": "VOLVO",
    "INTL": "INTERNATIONAL",
    "BUIC": "BUICK",
}
SEVERITY_ORDER = [
    "Fatal Injury",
    "Suspected Serious Injury",
    "Suspected Minor Injury",
    "Possible Injury",
    "No Apparent Injury",
]


def load_data() -> pd.DataFrame:
    """Load only the fields needed from the raw drivers crash data."""
    return pd.read_csv(
        RAW_DIR / "Crash_Reporting_-_Drivers_Data.csv",
        usecols=[MAKE_COLUMN, SEVERITY_COLUMN],
        low_memory=False,
    )


def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per make with severity percentages and sample size.

    Rows without a vehicle make or injury severity are excluded. Source data
    contains the same severity labels in different letter cases, so severity
    values and known vehicle-make aliases are normalized before aggregation.
    """
    required_columns = {MAKE_COLUMN, SEVERITY_COLUMN}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required column(s): {missing}")

    cleaned = df[[MAKE_COLUMN, SEVERITY_COLUMN]].copy()
    cleaned[MAKE_COLUMN] = cleaned[MAKE_COLUMN].astype("string").str.strip().str.upper()
    cleaned[MAKE_COLUMN] = cleaned[MAKE_COLUMN].replace(MAKE_ALIASES)
    cleaned[SEVERITY_COLUMN] = (
        cleaned[SEVERITY_COLUMN].astype("string").str.strip().str.title()
    )
    cleaned = cleaned.replace("", pd.NA).dropna(subset=[MAKE_COLUMN, SEVERITY_COLUMN])

    counts = pd.crosstab(cleaned[MAKE_COLUMN], cleaned[SEVERITY_COLUMN])
    n = counts.sum(axis=1)
    percentages = counts.div(n, axis=0).mul(100).round(2)

    known_severities = [column for column in SEVERITY_ORDER if column in percentages]
    other_severities = sorted(set(percentages.columns).difference(known_severities))
    percentages = percentages[known_severities + other_severities]

    result = percentages.reset_index()
    result.insert(1, "n", result[MAKE_COLUMN].map(n).astype("int64"))
    result.columns.name = None
    return result.sort_values(["n", MAKE_COLUMN], ascending=[False, True]).reset_index(
        drop=True
    )


def save(df: pd.DataFrame) -> None:
    """Write the single visualization dataset to the processed directory."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUTPUT_FILE}")


def main() -> None:
    df = load_data()
    df = transform(df)
    save(df)


if __name__ == "__main__":
    main()
