"""Build processed crash data for the Police Breathalyzers view."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "Crash_Reporting_-_Incidents_Data.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "police-breathalyzers"
CRASHES_OUTPUT = OUTPUT_DIR / "alcohol_crashes.parquet"
CELLS_OUTPUT = OUTPUT_DIR / "alcohol_cells.parquet"

GRID_SIZE_DEGREES = 0.01
LATITUDE_BOUNDS = (38.8, 39.4)
LONGITUDE_BOUNDS = (-77.6, -76.8)
SUBSTANCE_COLUMN = "Driver Substance Abuse"

TOKEN_STATUS = {
    "ALCOHOL PRESENT": "Alcohol present/contributed",
    "ALCOHOL CONTRIBUTED": "Alcohol present/contributed",
    "SUSPECT OF ALCOHOL USE": "Suspected alcohol use",
    "COMBINED SUBSTANCE PRESENT": "Combined substance",
    "COMBINATION CONTRIBUTED": "Combined substance",
    "NOT SUSPECT OF ALCOHOL USE": "No alcohol indication",
    "NONE DETECTED": "No alcohol indication",
    "ILLEGAL DRUG PRESENT": "No alcohol indication",
    "ILLEGAL DRUG CONTRIBUTED": "No alcohol indication",
    "MEDICATION PRESENT": "No alcohol indication",
    "MEDICATION CONTRIBUTED": "No alcohol indication",
    "SUSPECT OF DRUG USE": "No alcohol indication",
    "NOT SUSPECT OF DRUG USE": "No alcohol indication",
    "OTHER": "Unknown",
    "UNKNOWN": "Unknown",
    "N/A": "Unknown",
}
STATUS_PRIORITY = {
    "Unknown": 0,
    "No alcohol indication": 1,
    "Suspected alcohol use": 2,
    "Combined substance": 3,
    "Alcohol present/contributed": 4,
}
ALCOHOL_RELATED_STATUSES = {
    "Alcohol present/contributed",
    "Suspected alcohol use",
    "Combined substance",
}


def classify_alcohol_status(values: pd.Series) -> pd.Series:
    """Classify each crash from every comma-separated driver substance label."""
    tokens = values.astype("string").str.upper().str.split(",").explode().str.strip()
    unknown_tokens = sorted(set(tokens.dropna()).difference(TOKEN_STATUS))
    if unknown_tokens:
        raise ValueError(f"Unknown substance label(s): {', '.join(unknown_tokens)}")

    token_status = tokens.map(TOKEN_STATUS).fillna("Unknown")
    priority = token_status.map(STATUS_PRIORITY).groupby(level=0).max()
    return priority.map({rank: status for status, rank in STATUS_PRIORITY.items()})


def add_time_fields(crashes: pd.DataFrame) -> pd.DataFrame:
    """Parse the crash timestamp and add fields used by view filters."""
    result = crashes.copy()
    result["crash_datetime"] = pd.to_datetime(
        result.pop("Crash Date/Time"),
        format="%m/%d/%Y %I:%M:%S %p",
        errors="raise",
    )
    result["year"] = result["crash_datetime"].dt.year.astype("int16")
    result["month"] = result["crash_datetime"].dt.month.astype("int8")
    result["weekday"] = result["crash_datetime"].dt.day_name()
    result["hour"] = result["crash_datetime"].dt.hour.astype("int8")
    return result


def assign_grid_cells(crashes: pd.DataFrame) -> pd.DataFrame:
    """Assign stable approximately one-kilometre cells to crash points."""
    result = crashes.copy()
    cell_latitude = np.floor(result["latitude"] / GRID_SIZE_DEGREES) * GRID_SIZE_DEGREES
    cell_longitude = (
        np.floor(result["longitude"] / GRID_SIZE_DEGREES) * GRID_SIZE_DEGREES
    )
    result["cell_id"] = [
        f"{latitude:.2f}:{longitude:.2f}"
        for latitude, longitude in zip(cell_latitude, cell_longitude)
    ]
    return result


def build_cells(crashes: pd.DataFrame) -> pd.DataFrame:
    """Aggregate alcohol-related crash counts and shares by grid cell."""
    cells = (
        crashes.groupby("cell_id", as_index=False, sort=True)
        .agg(
            total_crashes=("report_number", "size"),
            alcohol_related_crashes=("alcohol_related", "sum"),
        )
    )
    parts = cells["cell_id"].str.split(":", expand=True).astype(float)
    cells["center_latitude"] = parts[0] + GRID_SIZE_DEGREES / 2
    cells["center_longitude"] = parts[1] + GRID_SIZE_DEGREES / 2
    cells["alcohol_related_share_pct"] = (
        cells["alcohol_related_crashes"].div(cells["total_crashes"]).mul(100).round(2)
    )
    return cells[
        [
            "cell_id",
            "center_latitude",
            "center_longitude",
            "total_crashes",
            "alcohol_related_crashes",
            "alcohol_related_share_pct",
        ]
    ]


def load_and_transform() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Load the raw incidents and return crash- and cell-level datasets."""
    incidents = pd.read_csv(
        RAW_FILE,
        usecols=[
            "Report Number",
            "Crash Date/Time",
            "Latitude",
            "Longitude",
            "Road Name",
            "Municipality",
            SUBSTANCE_COLUMN,
        ],
        low_memory=False,
    )
    if incidents["Report Number"].duplicated().any():
        raise ValueError("Incident report numbers must be unique")

    crashes = incidents.copy()
    crashes["alcohol_status"] = classify_alcohol_status(crashes[SUBSTANCE_COLUMN])
    crashes["alcohol_related"] = crashes["alcohol_status"].isin(
        ALCOHOL_RELATED_STATUSES
    )
    crashes["latitude"] = pd.to_numeric(crashes.pop("Latitude"), errors="coerce")
    crashes["longitude"] = pd.to_numeric(crashes.pop("Longitude"), errors="coerce")
    valid_coordinates = crashes["latitude"].between(*LATITUDE_BOUNDS) & crashes[
        "longitude"
    ].between(*LONGITUDE_BOUNDS)
    excluded_coordinates = int((~valid_coordinates).sum())
    crashes = crashes.loc[valid_coordinates].copy()

    crashes["road_name"] = (
        crashes.pop("Road Name").astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    crashes["municipality"] = (
        crashes.pop("Municipality").astype("string").str.strip().str.upper().replace("", pd.NA)
    )
    crashes["substance_labels"] = crashes.pop(SUBSTANCE_COLUMN).astype("string")
    crashes = add_time_fields(crashes)
    crashes = assign_grid_cells(crashes)
    crashes = crashes.rename(columns={"Report Number": "report_number"})[
        [
            "report_number",
            "crash_datetime",
            "year",
            "month",
            "weekday",
            "hour",
            "latitude",
            "longitude",
            "road_name",
            "municipality",
            "cell_id",
            "alcohol_status",
            "alcohol_related",
            "substance_labels",
        ]
    ].sort_values(["crash_datetime", "report_number"], ignore_index=True)

    cells = build_cells(crashes)
    quality = {
        "raw_incidents": len(incidents),
        "excluded_crash_coordinates": excluded_coordinates,
        "processed_crashes": len(crashes),
        "alcohol_related_crashes": int(crashes["alcohol_related"].sum()),
        "processed_cells": len(cells),
    }
    return crashes, cells, quality


def validate_outputs(crashes: pd.DataFrame, cells: pd.DataFrame) -> None:
    """Enforce the processed-data contract before files are replaced."""
    if crashes["report_number"].duplicated().any():
        raise ValueError("Processed crash report numbers must be unique")
    if crashes[["crash_datetime", "latitude", "longitude", "cell_id"]].isna().any().any():
        raise ValueError("Processed crashes contain missing required values")
    if not set(crashes["alcohol_status"]).issubset(STATUS_PRIORITY):
        raise ValueError("Processed crashes contain an unsupported alcohol status")
    if cells["cell_id"].duplicated().any():
        raise ValueError("Processed cells must be unique")
    if int(cells["total_crashes"].sum()) != len(crashes):
        raise ValueError("Cell crash counts do not match processed crashes")
    if int(cells["alcohol_related_crashes"].sum()) != int(
        crashes["alcohol_related"].sum()
    ):
        raise ValueError("Cell alcohol counts do not match processed crashes")


def main() -> None:
    crashes, cells, quality = load_and_transform()
    validate_outputs(crashes, cells)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crashes.to_parquet(CRASHES_OUTPUT, index=False)
    cells.to_parquet(CELLS_OUTPUT, index=False)
    for name, count in quality.items():
        print(f"{name}: {count:,}")
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
