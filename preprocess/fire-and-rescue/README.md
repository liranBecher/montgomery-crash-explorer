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

Run the pipeline from the repository root:

```powershell
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
8. Calculate the Haversine distance from each cell center to its nearest mapped
   station.

The current snapshot produces 122,367 classified crashes with valid coordinates,
1,262 occupied cells, and 37 usable stations. Of those crashes, 2,819 are
suspected-serious or fatal. Station 27, the Public Safety Training Academy, is
the one excluded station record because its source coordinates are missing.

## Outputs

All outputs are stored together under `data/processed/fire-and-rescue/`.

### `fire_rescue_crashes.parquet`

One row per classified crash: report number, timestamp and derived time
fields, severity, coordinates, road name, and cell ID.

### `fire_rescue_cells.parquet`

One row per occupied grid cell: center coordinates, nearest station ID/name,
and straight-line distance in kilometres.

### `fire_stations.parquet`

One row per mapped station with usable coordinates: station ID/name, address,
city, latitude, and longitude.

## Limitations

Distance is straight-line proximity from a grid-cell center. It is not road
travel time, dispatch history, a service area, or evidence about staffing,
availability, or actual response performance. The 2026 data ends on August 5
and is incomplete for annual comparisons.
