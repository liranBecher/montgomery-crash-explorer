"""Build the processed datasets for the Fire & Rescue Proximity view."""

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "fire-and-rescue"

INCIDENTS_FILE = RAW_DIR / "Crash_Reporting_-_Incidents_Data.csv"
DRIVERS_FILE = RAW_DIR / "Crash_Reporting_-_Drivers_Data.csv"
NON_MOTORISTS_FILE = RAW_DIR / "Crash_Reporting_-_Non-Motorists_Data.csv"
STATIONS_FILE = RAW_DIR / "Fire_Station.csv"
ROAD_GRAPH_FILE = RAW_DIR / "montgomery_drive_service.graphml"

CRASHES_OUTPUT = OUTPUT_DIR / "fire_rescue_crashes.parquet"
CELLS_OUTPUT = OUTPUT_DIR / "fire_rescue_cells.parquet"
STATIONS_OUTPUT = OUTPUT_DIR / "fire_stations.parquet"

GRID_SIZE_DEGREES = 0.01
EARTH_RADIUS_KM = 6371.0088
LATITUDE_BOUNDS = (38.8, 39.4)
LONGITUDE_BOUNDS = (-77.6, -76.8)
ROAD_GRAPH_BUFFER_DEGREES = 0.03

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


def add_time_fields(crashes: pd.DataFrame) -> pd.DataFrame:
    """Parse the source timestamp and add fields used by view filters."""
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
    result["daypart"] = pd.cut(
        result["hour"],
        bins=[-1, 5, 11, 17, 23],
        labels=["Overnight", "Morning", "Afternoon", "Evening"],
    ).astype("string")
    return result


def assign_grid_cells(crashes: pd.DataFrame) -> pd.DataFrame:
    """Assign stable approximately one-kilometre cells to crash points."""
    result = crashes.copy()
    result["cell_latitude_min"] = (
        np.floor(result["latitude"] / GRID_SIZE_DEGREES) * GRID_SIZE_DEGREES
    ).round(2)
    result["cell_longitude_min"] = (
        np.floor(result["longitude"] / GRID_SIZE_DEGREES) * GRID_SIZE_DEGREES
    ).round(2)
    result["cell_id"] = result.apply(
        lambda row: f"{row['cell_latitude_min']:.2f}:{row['cell_longitude_min']:.2f}",
        axis=1,
    )
    return result


def nearest_stations(cells: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    """Attach each cell center's nearest station using Haversine distance."""
    if cells.empty or stations.empty:
        raise ValueError("Cells and stations must both contain at least one row")

    latitudes = np.radians(cells["center_latitude"].to_numpy(dtype=float))[:, None]
    longitudes = np.radians(cells["center_longitude"].to_numpy(dtype=float))[:, None]
    station_latitudes = np.radians(
        stations["station_latitude"].to_numpy(dtype=float)
    )[None, :]
    station_longitudes = np.radians(
        stations["station_longitude"].to_numpy(dtype=float)
    )[None, :]

    latitude_delta = station_latitudes - latitudes
    longitude_delta = station_longitudes - longitudes
    haversine = np.sin(latitude_delta / 2) ** 2 + (
        np.cos(latitudes)
        * np.cos(station_latitudes)
        * np.sin(longitude_delta / 2) ** 2
    )
    distances = EARTH_RADIUS_KM * 2 * np.arcsin(np.sqrt(haversine))
    nearest_index = distances.argmin(axis=1)

    result = cells.copy()
    result["nearest_station_id"] = stations.iloc[nearest_index]["station_id"].to_numpy()
    result["nearest_station_name"] = stations.iloc[nearest_index][
        "station_name"
    ].to_numpy()
    result["nearest_station_distance_km"] = distances[
        np.arange(len(result)), nearest_index
    ].round(3)
    return result


def road_proximity_from_nodes(
    graph: object,
    crash_nodes: np.ndarray,
    crash_snap_m: np.ndarray,
    station_nodes: np.ndarray,
    station_snap_m: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return directed road distances and nearest-station row positions."""
    import networkx as nx

    reverse_graph = graph.reverse(copy=True)
    super_source = object()
    station_position_by_node: dict[object, int] = {}
    for position, (node, snap_m) in enumerate(zip(station_nodes, station_snap_m)):
        previous = station_position_by_node.get(node)
        if previous is None or snap_m < station_snap_m[previous]:
            station_position_by_node[node] = position
    reverse_graph.add_node(super_source)
    for node, position in station_position_by_node.items():
        reverse_graph.add_edge(
            super_source, node, length=float(station_snap_m[position])
        )

    predecessors, network_m = nx.dijkstra_predecessor_and_distance(
        reverse_graph, super_source, weight="length"
    )
    source_cache: dict[object, int] = {}

    def station_position(node: object) -> int:
        trail = []
        cursor = node
        while cursor not in source_cache:
            previous = predecessors.get(cursor)
            if not previous:
                raise ValueError(f"Road node {cursor!r} cannot reach a mapped station")
            if previous[0] == super_source:
                source_cache[cursor] = station_position_by_node[cursor]
                break
            trail.append(cursor)
            cursor = previous[0]
        position = source_cache[cursor]
        source_cache.update(dict.fromkeys(trail, position))
        return position

    unique_nodes, inverse = np.unique(crash_nodes, return_inverse=True)
    unique_station_positions = np.array(
        [station_position(node) for node in unique_nodes], dtype=int
    )
    network_distances_m = np.array(
        [network_m[node] for node in crash_nodes], dtype=float
    )
    return (
        (network_distances_m + crash_snap_m) / 1000,
        unique_station_positions[inverse],
    )


def add_road_proximity(
    crashes: pd.DataFrame, stations: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int | float]]:
    """Attach shortest drivable distance to the nearest mapped station."""
    import geopandas as gpd
    import osmnx as ox

    if ROAD_GRAPH_FILE.exists():
        graph = ox.load_graphml(ROAD_GRAPH_FILE)
    else:
        coordinates = pd.concat(
            [
                crashes[["longitude", "latitude"]],
                stations[["station_longitude", "station_latitude"]].rename(
                    columns={
                        "station_longitude": "longitude",
                        "station_latitude": "latitude",
                    }
                ),
            ],
            ignore_index=True,
        )
        bbox = (
            float(coordinates["longitude"].min() - ROAD_GRAPH_BUFFER_DEGREES),
            float(coordinates["latitude"].min() - ROAD_GRAPH_BUFFER_DEGREES),
            float(coordinates["longitude"].max() + ROAD_GRAPH_BUFFER_DEGREES),
            float(coordinates["latitude"].max() + ROAD_GRAPH_BUFFER_DEGREES),
        )
        ox.settings.use_cache = True
        ox.settings.cache_folder = RAW_DIR / "osmnx-cache"
        ox.settings.requests_timeout = 300
        graph = ox.graph.graph_from_bbox(
            bbox,
            network_type="drive_service",
            simplify=True,
            retain_all=False,
            truncate_by_edge=True,
        )
        ox.save_graphml(graph, ROAD_GRAPH_FILE)

    graph = ox.truncate.largest_component(graph, strongly=True)
    projected = ox.projection.project_graph(graph)
    graph_crs = projected.graph["crs"]

    def projected_xy(frame: pd.DataFrame, longitude: str, latitude: str):
        points = gpd.GeoSeries(
            gpd.points_from_xy(frame[longitude], frame[latitude]), crs="EPSG:4326"
        ).to_crs(graph_crs)
        return points.x.to_numpy(), points.y.to_numpy()

    crash_x, crash_y = projected_xy(crashes, "longitude", "latitude")
    station_x, station_y = projected_xy(
        stations, "station_longitude", "station_latitude"
    )
    crash_nodes, crash_snap_m = ox.distance.nearest_nodes(
        projected, crash_x, crash_y, return_dist=True
    )
    station_nodes, station_snap_m = ox.distance.nearest_nodes(
        projected, station_x, station_y, return_dist=True
    )
    road_distance_km, station_positions = road_proximity_from_nodes(
        projected,
        np.asarray(crash_nodes),
        np.asarray(crash_snap_m),
        np.asarray(station_nodes),
        np.asarray(station_snap_m),
    )

    result = crashes.copy()
    nearest = stations.iloc[station_positions]
    result["nearest_road_station_id"] = nearest["station_id"].to_numpy()
    result["nearest_road_station_name"] = nearest["station_name"].to_numpy()
    result["nearest_road_station_distance_km"] = road_distance_km.round(3)
    result["road_snap_distance_m"] = np.asarray(crash_snap_m).round(1)
    quality = {
        "road_graph_nodes": len(projected.nodes),
        "road_graph_edges": len(projected.edges),
        "maximum_crash_road_snap_m": float(np.max(crash_snap_m)),
        "maximum_station_road_snap_m": float(np.max(station_snap_m)),
    }
    return result, quality


def load_and_transform() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, int | float]
]:
    """Load the raw snapshot and return validated crash, cell, and station tables."""
    incidents = pd.read_csv(
        INCIDENTS_FILE,
        usecols=[
            "Report Number",
            "Crash Date/Time",
            "Latitude",
            "Longitude",
            "Road Name",
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
    classified = severity[severity["severity_rank"].isin(OUTPUT_SEVERITY)].copy()
    crashes = incidents.merge(
        classified, on="Report Number", how="inner", validate="one_to_one"
    )
    crashes["latitude"] = pd.to_numeric(crashes.pop("Latitude"), errors="coerce")
    crashes["longitude"] = pd.to_numeric(crashes.pop("Longitude"), errors="coerce")
    valid_coordinates = crashes["latitude"].between(*LATITUDE_BOUNDS) & crashes[
        "longitude"
    ].between(*LONGITUDE_BOUNDS)
    excluded_coordinates = int((~valid_coordinates).sum())
    crashes = crashes.loc[valid_coordinates].copy()

    crashes["severity"] = crashes.pop("severity_rank").map(OUTPUT_SEVERITY)
    crashes["road_name"] = (
        crashes.pop("Road Name").astype("string").str.strip().str.upper().replace("", pd.NA)
    )
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
            "daypart",
            "severity",
            "latitude",
            "longitude",
            "road_name",
            "cell_id",
        ]
    ].sort_values(["crash_datetime", "report_number"], ignore_index=True)

    raw_stations = pd.read_csv(STATIONS_FILE, low_memory=False)
    stations = raw_stations.rename(
        columns={
            "INFO": "station_id",
            "NAME": "station_name",
            "ADDRESS": "address",
            "CITY": "city",
            "LATITUDE": "station_latitude",
            "LONGITUDE": "station_longitude",
        }
    )
    stations["station_latitude"] = pd.to_numeric(
        stations["station_latitude"], errors="coerce"
    )
    stations["station_longitude"] = pd.to_numeric(
        stations["station_longitude"], errors="coerce"
    )
    valid_station_coordinates = stations["station_latitude"].between(
        *LATITUDE_BOUNDS
    ) & stations["station_longitude"].between(*LONGITUDE_BOUNDS)
    excluded_stations = int((~valid_station_coordinates).sum())
    stations = stations.loc[valid_station_coordinates].copy()
    stations["station_id"] = stations["station_id"].astype("string")
    stations = stations[
        [
            "station_id",
            "station_name",
            "address",
            "city",
            "station_latitude",
            "station_longitude",
        ]
    ].sort_values("station_id", ignore_index=True)

    crashes, road_quality = add_road_proximity(crashes, stations)

    cells = pd.DataFrame(
        {
            "cell_id": crashes["cell_id"].drop_duplicates().sort_values().to_numpy(),
        }
    )
    cell_parts = cells["cell_id"].str.split(":", expand=True).astype(float)
    cells["center_latitude"] = cell_parts[0] + GRID_SIZE_DEGREES / 2
    cells["center_longitude"] = cell_parts[1] + GRID_SIZE_DEGREES / 2
    cells = nearest_stations(cells, stations)

    quality = {
        "raw_incidents": len(incidents),
        "classified_before_coordinate_validation": len(classified),
        "excluded_crash_coordinates": excluded_coordinates,
        "processed_crashes": len(crashes),
        "processed_cells": len(cells),
        "raw_stations": len(raw_stations),
        "excluded_station_coordinates": excluded_stations,
        "processed_stations": len(stations),
        **road_quality,
    }
    return crashes, cells, stations, quality


def validate_outputs(
    crashes: pd.DataFrame, cells: pd.DataFrame, stations: pd.DataFrame
) -> None:
    """Enforce the processed-data contract before files are replaced."""
    if crashes["report_number"].duplicated().any():
        raise ValueError("Processed crash report numbers must be unique")
    if not set(crashes["severity"]).issubset(set(OUTPUT_SEVERITY.values())):
        raise ValueError("Processed crashes contain an unsupported severity")
    required_crash_fields = [
        "crash_datetime",
        "latitude",
        "longitude",
        "cell_id",
        "nearest_road_station_id",
        "nearest_road_station_name",
        "nearest_road_station_distance_km",
        "road_snap_distance_m",
    ]
    if crashes[required_crash_fields].isna().any().any():
        raise ValueError("Processed crashes contain missing required values")
    if cells["cell_id"].duplicated().any():
        raise ValueError("Processed cells must be unique")
    if not set(crashes["nearest_road_station_id"]).issubset(
        set(stations["station_id"])
    ):
        raise ValueError("A crash references an unknown road-nearest station")
    road_distances = crashes["nearest_road_station_distance_km"]
    if (
        road_distances.isna().any()
        or not np.isfinite(road_distances).all()
        or (road_distances < 0).any()
    ):
        raise ValueError("Crash road distances must be finite and non-negative")
    if (crashes["road_snap_distance_m"] > 1000).any():
        raise ValueError("A crash is more than 1 km from the drive network")
    if not set(cells["nearest_station_id"]).issubset(set(stations["station_id"])):
        raise ValueError("A cell references an unknown station")
    distances = cells["nearest_station_distance_km"]
    if distances.isna().any() or not np.isfinite(distances).all() or (distances < 0).any():
        raise ValueError("Cell distances must be finite and non-negative")


def main() -> None:
    crashes, cells, stations, quality = load_and_transform()
    validate_outputs(crashes, cells, stations)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    crashes.to_parquet(CRASHES_OUTPUT, index=False)
    cells.to_parquet(CELLS_OUTPUT, index=False)
    stations.to_parquet(STATIONS_OUTPUT, index=False)
    for name, count in quality.items():
        print(f"{name}: {count:,}")
    print(f"Saved outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
