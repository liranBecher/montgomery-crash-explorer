# Fire & Rescue Proximity data

This folder contains the reproducible preprocessing pipeline for the Fire &
Rescue Proximity tab. Its deployment-ready tables are written to
`data/processed/fire-and-rescue/`.

## Sources and current snapshot

| Source | Purpose | Current rows |
| --- | --- | ---: |
| Crash incidents | One record per reported crash, including time and coordinates | 124,208 |
| Drivers | Driver injury severity by crash | 218,689 |
| Non-motorists | Pedestrian, cyclist, and other non-motorist injury severity | 7,459 |
| Fire stations | Mapped Montgomery County fire-station locations | 38 |
| OpenStreetMap | Directed drivable road network | Cached GraphML extraction |

Run the pipeline from the repository root:

```powershell
python -m pip install -r preprocess/fire-and-rescue/requirements.txt
python preprocess/fire-and-rescue/preprocess_fire_and_rescue.py
```

## Processing method

1. Trim and uppercase person-level injury labels from the driver and
   non-motorist files.
2. Select the highest recorded injury severity within each crash.
3. Retain all five classified maximum-severity levels: no apparent, possible,
   suspected minor, suspected serious, and fatal injury.
4. Join classified crashes one-to-one to the incident table and parse the incident
   timestamp.
5. Derive year, month, weekday, hour, and four six-hour dayparts.
6. Validate crash and station coordinates against a broad Montgomery-area
   bounding box.
7. Assign crashes to fixed `0.01°` cells (approximately 0.9 × 1.1 km near
   Montgomery County).
8. Download and cache the OpenStreetMap `drive_service` network covering the
   validated coordinates, then retain its largest strongly connected component.
9. Snap crashes and stations to projected road nodes and calculate directed
   shortest drivable distance to the nearest station. Point-to-node connector
   distances are included.
10. Calculate the Haversine distance from each cell center to its nearest mapped
    station for secondary straight-line context.

The current snapshot produces 122,367 classified crashes with valid coordinates,
1,262 occupied cells, and 37 usable stations. Of those crashes, 2,819 are
suspected-serious or fatal. Station 27, the Public Safety Training Academy, is
the one excluded station record because its source coordinates are missing.

## Outputs

All outputs are stored together under `data/processed/fire-and-rescue/`.

### `fire_rescue_crashes.parquet`

One row per classified crash: report number, timestamp and derived time fields,
severity, coordinates, road name, cell ID, nearest road-network station,
shortest drivable distance, and road-snap distance.

### `fire_rescue_cells.parquet`

One row per occupied grid cell: center coordinates, nearest station ID/name,
and straight-line distance in kilometres.

### `fire_stations.parquet`

One row per mapped station with usable coordinates: station ID/name, address,
city, latitude, and longitude.

## Limitations

Road distance reflects the shortest path through the cached OpenStreetMap drive
network, not live traffic, apparatus restrictions, dispatch decisions, or travel
time. Crash and station coordinates are connected to their nearest strongly
connected road node; `road_snap_distance_m` exposes that approximation for QA.
The station-radius chart and circle remain Haversine straight-line measures.
None of these measures is evidence about staffing, availability, or actual
response performance. The 2026 data ends on August 5 and is incomplete for
annual comparisons.
