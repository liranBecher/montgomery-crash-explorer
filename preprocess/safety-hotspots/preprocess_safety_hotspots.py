"""Build the processed crash dataset for the Safety Hotspots view."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "safety-hotspots"

INCIDENTS_FILE = RAW_DIR / "Crash_Reporting_-_Incidents_Data.csv"
DRIVERS_FILE = RAW_DIR / "Crash_Reporting_-_Drivers_Data.csv"
NON_MOTORISTS_FILE = RAW_DIR / "Crash_Reporting_-_Non-Motorists_Data.csv"
CRASHES_OUTPUT = OUTPUT_DIR / "safety_crashes.parquet"

GRID_SIZE_DEGREES = 0.01
LATITUDE_BOUNDS = (38.8, 39.4)
LONGITUDE_BOUNDS = (-77.6, -76.8)

SEVERITY_RANK = {
    "NO APPARENT INJURY": 0,
    "POSSIBLE INJURY": 1,
    "SUSPECTED MINOR INJURY": 2,
    "SUSPECTED SERIOUS INJURY": 3,
    "FATAL INJURY": 4,
}
OUTPUT_SEVERITY = {
    0: "No Apparent Injury",
    1: "Possible Injury",
    2: "Suspected Minor Injury",
    3: "Suspected Serious Injury",
    4: "Fatal Injury",
}
SERIOUS_OR_FATAL = {"Suspected Serious Injury", "Fatal Injury"}

ROUTE_GROUP = {
    "MARYLAND (STATE)": "State / US",
    "MARYLAND (STATE) ROUTE": "State / US",
    "US (STATE)": "State / US",
    "SPUR": "State / US",
    "INTERSTATE (STATE)": "Interstate",
    "COUNTY": "County",
    "COUNTY ROUTE": "County",
    "LOCAL ROUTE": "Municipal / local",
    "MUNICIPALITY": "Municipal / local",
    "MUNICIPALITY ROUTE": "Municipal / local",
    "RAMP": "Ramp",
    "CROSSOVER": "Other public / government",
    "GOVERNMENT": "Other public / government",
    "GOVERNMENT ROUTE": "Other public / government",
    "OTHER PUBLIC ROADWAY": "Other public / government",
    "SERVICE ROAD": "Other public / government",
    "BICYCLE ROUTE": "Bicycle / other",
    "PRIVATE ROUTE": "Bicycle / other",
    "UNKNOWN": "Bicycle / other",
}
WEATHER_GROUP = {
    "CLEAR": "Clear",
    "CLOUDY": "Cloudy",
    "RAIN": "Rain",
    "RAINING": "Rain",
    "BLOWING SNOW": "Winter precipitation",
    "FREEZING RAIN OR FREEZING DRIZZLE": "Winter precipitation",
    "SLEET": "Winter precipitation",
    "SLEET OR HAIL": "Winter precipitation",
    "SNOW": "Winter precipitation",
    "WINTRY MIX": "Winter precipitation",
    "FOG, SMOG, SMOKE": "Fog / smoke",
    "FOGGY": "Fog / smoke",
    "SEVERE CROSSWINDS": "Wind",
    "SEVERE WINDS": "Wind",
    "BLOWING SAND, SOIL, DIRT": "Other / unknown",
    "OTHER": "Other / unknown",
    "UNKNOWN": "Other / unknown",
}
SURFACE_GROUP = {
    "DRY": "Dry",
    "WET": "Wet",
    "SLUSH": "Snow / slush",
    "SNOW": "Snow / slush",
    "ICE": "Ice / frost",
    "ICE/FROST": "Ice / frost",
    "WATER (STANDING, MOVING)": "Standing water",
    "WATER(STANDING/MOVING)": "Standing water",
    "MUD, DIRT, GRAVEL": "Loose / contaminated",
    "OIL": "Loose / contaminated",
    "SAND": "Loose / contaminated",
    "OTHER": "Other / unknown",
    "UNKNOWN": "Other / unknown",
}
LIGHT_GROUP = {
    "DAYLIGHT": "Daylight",
    "DARK - LIGHTED": "Dark - lighted",
    "DARK LIGHTS ON": "Dark - lighted",
    "DARK - NOT LIGHTED": "Dark - unlighted",
    "DARK NO LIGHTS": "Dark - unlighted",
    "DAWN": "Dawn / dusk",
    "DUSK": "Dawn / dusk",
    "DARK - UNKNOWN LIGHTING": "Dark - unknown",
    "DARK -- UNKNOWN LIGHTING": "Dark - unknown",
    "OTHER": "Other / unknown",
    "UNKNOWN": "Other / unknown",
}

CATEGORY_GROUPS = {
    "route_group": set(ROUTE_GROUP.values()) | {"Not recorded"},
    "weather_group": set(WEATHER_GROUP.values()) | {"Not recorded"},
    "surface_group": set(SURFACE_GROUP.values()) | {"Not recorded"},
    "light_group": set(LIGHT_GROUP.values()) | {"Not recorded"},
}

OUTPUT_COLUMNS = [
    "report_number",
    "crash_datetime",
    "year",
    "month",
    "weekday",
    "weekday_index",
    "hour",
    "severity",
    "serious_or_fatal",
    "latitude",
    "longitude",
    "cell_id",
    "road_name",
    "cross_street_name",
    "route_group",
    "weather_group",
    "surface_group",
    "light_group",
]


def normalize_severity(values: pd.Series) -> pd.Series:
    """Normalize source severity labels without inventing missing values."""
    return values.astype("string").str.strip().str.upper().replace("", pd.NA)


def aggregate_max_severity(*person_tables: pd.DataFrame) -> pd.DataFrame:
    """Return the highest recorded person injury severity for each crash."""
    people = pd.concat(
        [table[["Report Number", "Injury Severity"]] for table in person_tables],
        ignore_index=True,
    )
    people["normalized_severity"] = normalize_severity(people["Injury Severity"])
    unknown = sorted(
        set(people["normalized_severity"].dropna()).difference(SEVERITY_RANK)
    )
    if unknown:
        raise ValueError(f"Unknown injury severity label(s): {', '.join(unknown)}")

    people["severity_rank"] = people["normalized_severity"].map(SEVERITY_RANK)
    return (
        people.groupby("Report Number", as_index=False, sort=False)["severity_rank"]
        .max()
        .dropna(subset=["severity_rank"])
    )


def group_categories(
    values: pd.Series, mapping: dict[str, str], source_column: str
) -> pd.Series:
    """Map an audited source vocabulary to compact display groups."""
    normalized = values.astype("string").str.strip().str.upper().replace("", pd.NA)
    unknown = sorted(set(normalized.dropna()).difference(mapping))
    if unknown:
        raise ValueError(f"Unknown {source_column} label(s): {', '.join(unknown)}")
    return normalized.map(mapping).fillna("Not recorded").astype("string")


def add_time_fields(crashes: pd.DataFrame) -> pd.DataFrame:
    """Parse the source timestamp and add fields needed by the linked views."""
    result = crashes.copy()
    result["crash_datetime"] = pd.to_datetime(
        result.pop("Crash Date/Time"),
        format="%m/%d/%Y %I:%M:%S %p",
        errors="raise",
    )
    result["year"] = result["crash_datetime"].dt.year.astype("int16")
    result["month"] = result["crash_datetime"].dt.month.astype("int8")
    result["weekday"] = result["crash_datetime"].dt.day_name().astype("string")
    result["weekday_index"] = result["crash_datetime"].dt.dayofweek.astype("int8")
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


def normalize_road_names(values: pd.Series) -> pd.Series:
    """Normalize road labels while retaining genuinely missing names."""
    return values.astype("string").str.strip().str.upper().replace("", pd.NA)


def load_and_transform() -> tuple[pd.DataFrame, dict[str, int]]:
    """Load the raw snapshot and return validated crash-level data."""
    incidents = pd.read_csv(
        INCIDENTS_FILE,
        usecols=[
            "Report Number",
            "Crash Date/Time",
            "Latitude",
            "Longitude",
            "Road Name",
            "Cross-Street Name",
            "Route Type",
            "Weather",
            "Surface Condition",
            "Light",
        ],
        low_memory=False,
    )
    if incidents["Report Number"].duplicated().any():
        raise ValueError("Incident report numbers must be unique")

    drivers = pd.read_csv(
        DRIVERS_FILE,
        usecols=["Report Number", "Injury Severity"],
        low_memory=False,
    )
    non_motorists = pd.read_csv(
        NON_MOTORISTS_FILE,
        usecols=["Report Number", "Injury Severity"],
        low_memory=False,
    )
    incident_reports = set(incidents["Report Number"])
    person_reports = set(drivers["Report Number"]).union(non_motorists["Report Number"])
    missing_incidents = person_reports.difference(incident_reports)
    if missing_incidents:
        raise ValueError(
            f"{len(missing_incidents)} person report(s) do not join to incidents"
        )

    severity = aggregate_max_severity(drivers, non_motorists)
    crashes = incidents.merge(severity, on="Report Number", how="inner", validate="one_to_one")
    classified_before_coordinates = len(crashes)

    crashes["latitude"] = pd.to_numeric(crashes.pop("Latitude"), errors="coerce")
    crashes["longitude"] = pd.to_numeric(crashes.pop("Longitude"), errors="coerce")
    valid_coordinates = crashes["latitude"].between(*LATITUDE_BOUNDS) & crashes[
        "longitude"
    ].between(*LONGITUDE_BOUNDS)
    excluded_coordinates = int((~valid_coordinates).sum())
    crashes = crashes.loc[valid_coordinates].copy()

    crashes["severity"] = crashes.pop("severity_rank").map(OUTPUT_SEVERITY)
    crashes["serious_or_fatal"] = crashes["severity"].isin(SERIOUS_OR_FATAL)
    crashes["road_name"] = normalize_road_names(crashes.pop("Road Name"))
    crashes["cross_street_name"] = normalize_road_names(
        crashes.pop("Cross-Street Name")
    )
    crashes["route_group"] = group_categories(
        crashes.pop("Route Type"), ROUTE_GROUP, "Route Type"
    )
    crashes["weather_group"] = group_categories(
        crashes.pop("Weather"), WEATHER_GROUP, "Weather"
    )
    crashes["surface_group"] = group_categories(
        crashes.pop("Surface Condition"), SURFACE_GROUP, "Surface Condition"
    )
    crashes["light_group"] = group_categories(
        crashes.pop("Light"), LIGHT_GROUP, "Light"
    )
    crashes = add_time_fields(crashes)
    crashes = assign_grid_cells(crashes)
    crashes = crashes.rename(columns={"Report Number": "report_number"})[
        OUTPUT_COLUMNS
    ].sort_values(["crash_datetime", "report_number"], ignore_index=True)

    quality = {
        "raw_incidents": len(incidents),
        "excluded_without_person_severity": len(incidents)
        - classified_before_coordinates,
        "classified_before_coordinate_validation": classified_before_coordinates,
        "excluded_crash_coordinates": excluded_coordinates,
        "processed_crashes": len(crashes),
        "processed_cells": crashes["cell_id"].nunique(),
        "serious_or_fatal_crashes": int(crashes["serious_or_fatal"].sum()),
    }
    return crashes, quality


def validate_output(crashes: pd.DataFrame) -> None:
    """Enforce the processed-data contract before the output is replaced."""
    if list(crashes.columns) != OUTPUT_COLUMNS:
        raise ValueError("Processed crashes do not match the required column order")
    if crashes["report_number"].duplicated().any():
        raise ValueError("Processed crash report numbers must be unique")
    required = [column for column in OUTPUT_COLUMNS if column not in {"road_name", "cross_street_name"}]
    if crashes[required].isna().any().any():
        raise ValueError("Processed crashes contain missing required values")
    if not set(crashes["severity"]).issubset(OUTPUT_SEVERITY.values()):
        raise ValueError("Processed crashes contain an unsupported severity")
    if not crashes["serious_or_fatal"].equals(
        crashes["severity"].isin(SERIOUS_OR_FATAL)
    ):
        raise ValueError("Serious/fatal flags do not match crash severity")
    for column, supported in CATEGORY_GROUPS.items():
        if not set(crashes[column]).issubset(supported):
            raise ValueError(f"Processed crashes contain an unsupported {column}")
    valid_coordinates = crashes["latitude"].between(*LATITUDE_BOUNDS) & crashes[
        "longitude"
    ].between(*LONGITUDE_BOUNDS)
    if not valid_coordinates.all():
        raise ValueError("Processed crashes contain coordinates outside county bounds")
    if not crashes["weekday_index"].between(0, 6).all() or not crashes["hour"].between(0, 23).all():
        raise ValueError("Processed crashes contain invalid time components")
    if not pd.MultiIndex.from_frame(
        crashes[["crash_datetime", "report_number"]]
    ).is_monotonic_increasing:
        raise ValueError("Processed crashes must have deterministic chronological ordering")


def main() -> None:
    crashes, quality = load_and_transform()
    validate_output(crashes)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crashes.to_parquet(CRASHES_OUTPUT, index=False)
    for name, count in quality.items():
        print(f"{name}: {count:,}")
    print(f"Saved output to {CRASHES_OUTPUT}")


if __name__ == "__main__":
    main()
