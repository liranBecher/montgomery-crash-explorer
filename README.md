# Montgomery County Crash Explorer

Interactive data-visualization course project built with Python and Streamlit.

- [Live interface prototype](https://montgomery-crash-explorer-udccs2e3zcwegytn8ypzsn.streamlit.app/)
- [Working report](https://docs.google.com/document/d/1lxUd-5fLB0UovdxjrY3h26qI2YNxPsfp/edit)
- [Project requirements](./PROJECT_REQUIREMENTS.md)
- [Visualization design specification](./DESIGN_SPEC.md)

## Research question

Where and when do crashes concentrate in Montgomery County, and which
recorded conditions, injury severity, fire-station proximity, and
alcohol-related patterns distinguish those concentrations?

The Safety Hotspots tab is the primary overview. The other tabs provide focused
follow-up analyses of fire-station proximity and alcohol-related patterns.

## Current status

| Implemented | Remaining work |
| --- | --- |
| Public Streamlit interface plus Safety Hotspots, Fire & Rescue, and Police Breathalyzers analyses | Final validated findings and recommendations |
| Three connected analyses with responsive maps and charts | Shared cross-tab chart selections |
| Safety, Fire & Rescue, and alcohol filters with linked chart selections | Accessibility, browser, performance, and comprehension evaluation |
| Automated preprocessing and interface contracts | — |

All three tabs are connected to processed data, share the sidebar date and area
filters, and provide linked local chart selections.

## Run locally

Python 3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The committed Safety Hotspots, Fire & Rescue, and Police Breathalyzers Parquet
files are required by the connected tabs. Their preprocessing scripts can
regenerate them when the ignored raw CSVs are available locally.

Run the current automated test with:

```powershell
python -m unittest discover -s tests -v
```

## Application views

1. Safety hotspots by time, place, weather, road type, and light conditions
2. Serious/fatal crash proximity to mapped fire-station locations
3. Priority locations and times for police breathalyzer alcohol-level enforcement

Detailed encodings and linking behavior are specified in
[DESIGN_SPEC.md](./DESIGN_SPEC.md).

## Repository structure

```text
app.py                    # Streamlit entry point
ui/components.py          # Shared header, sidebar, and presentation helpers
ui/views.py               # Three-tab view routing
ui/safety_hotspots.py     # Connected hotspot map, fingerprint, and timing views
ui/fire_rescue.py         # Connected Fire & Rescue charts and interactions
ui/police_breathalyzers.py # Connected alcohol map, timing, and interactions
ui/styles.css             # Presentation and responsive styling
tests/                    # Application and preprocessing contracts
data/raw/                 # Original local downloads; not modified by the app
preprocess/fire-and-rescue/ # Fire & Rescue preprocessing pipeline
data/processed/fire-and-rescue/ # Fire & Rescue deployment-ready Parquet outputs
preprocess/safety-hotspots/ # Safety Hotspots preprocessing pipeline
data/processed/safety-hotspots/ # Safety Hotspots deployment-ready Parquet output
preprocess/police-breathalyzers/ # Alcohol preprocessing pipeline
data/processed/police-breathalyzers/ # Alcohol deployment-ready Parquet outputs
output/report/            # Editable report artifact
```

## Technology status

### Confirmed current use

| Technology | Use |
| --- | --- |
| Python 3.12 | Application code and tests |
| Streamlit 1.60.0 | Browser UI, tabs, disabled controls, and deployment |
| pandas / PyArrow | Connected-view transformation and Parquet storage |
| Altair | Interactive comparisons, scatterplots, and timing heatmaps |
| PyDeck | Linked crash hotspot and station-location maps |
| HTML and CSS | Accessible structure, presentation, and responsive layout |
| GitHub | Source control and the public repository used by Streamlit Community Cloud |

GeoPandas and Shapely are possible later additions for validated spatial work;
they are not current project dependencies.

Streamlit's built-in widgets and selection events are the planned interaction
layer. No separate JavaScript frontend or database is planned.

## Data storage

Raw downloads live in ignored `data/raw/`. Connected-view pipelines live under
`preprocess/`; their committed deployment outputs live under `data/processed/`.

Raw source files stay in `data/raw/` so processing remains reproducible without
committing large originals. Compact processed files are committed with the app;
larger future data should be fetched from the source API and cached with
`st.cache_data` rather than introducing a database.

Only add another library to `requirements.txt` when implemented work requires
it.

## Data sources

- [Crash incidents](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Incidents-Data/bhju-22kf)
- [Drivers](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Drivers-Data/mmzv-x632)
- [Non-motorists](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Non-Motorists-Data/n7fk-dce5)
- [Fire stations](https://data.montgomerycountymd.gov/Public-Safety/Fire-Station/4cam-wimd/about_data)
- [OpenStreetMap road network](https://www.openstreetmap.org/copyright)

## Deployment

Deploy `app.py` from the `main` branch on Streamlit Community Cloud. Choose
Python 3.12 and keep the app public for course submission.

## Current limitations

- Fire-station proximity uses shortest drivable OpenStreetMap distance for the
  map and scatterplot, with straight-line distance retained as context and for
  station-radius circles. Neither measure is travel time or measured emergency
  response performance.
- The alcohol view describes historical recorded patterns; it does not measure
  blood alcohol level or establish where enforcement should occur.
- Accessibility, browser compatibility, performance, and user comprehension
  have not yet been evaluated with live visualizations.
