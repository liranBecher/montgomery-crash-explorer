# Montgomery County Crash Explorer

Interactive data-visualization course project built with Python and Streamlit.

- [Live interface prototype](https://montgomery-crash-explorer-udccs2e3zcwegytn8ypzsn.streamlit.app/)
- [Working report](https://docs.google.com/document/d/1lxUd-5fLB0UovdxjrY3h26qI2YNxPsfp/edit)
- [Project requirements](./PROJECT_REQUIREMENTS.md)
- [Visualization design specification](./DESIGN_SPEC.md)

## Research question

Where and when do crashes concentrate in Montgomery County, and which
conditions, response context, alcohol-related patterns, and vehicle
characteristics distinguish those crashes and their injury severity?

The Safety Hotspots tab is the primary overview. The other tabs provide focused
follow-up analyses of responder coverage, alcohol-related patterns, and vehicle
and injury characteristics.

## Current status

| Implemented | Not implemented yet |
| --- | --- |
| Public Streamlit interface prototype | Preprocessing pipeline and processed outputs |
| Four question-based tabs and responsive card layout | Data-backed charts, maps, axes, legends, and tooltips |
| Disabled shared and per-view controls with explicit empty states | Active filters, brushing, linking, and selection state |
| Planned interaction descriptions and automated layout test | Validated methods, findings, and recommendations |

The live site is an interface prototype, not a completed analytical system. It
does not currently display data or findings.

## Run locally

Python 3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The prototype runs without processed data. All analytical controls remain
disabled until the processed-data contract is finalized.

Run the current automated test with:

```powershell
python -m unittest discover -s tests -v
```

## Planned views

1. Safety hotspots by time, place, weather, road type, and light conditions
2. Crash-response coverage around existing first-responder locations
3. Priority locations and times for police breathalyzer alcohol-level enforcement
4. Vehicle make/age and driver injury severity

Detailed encodings and linking behavior are specified in
[DESIGN_SPEC.md](./DESIGN_SPEC.md).

## Repository structure

```text
app.py                    # Streamlit entry point
ui/components.py          # Shared header, filters, guide, and placeholder cards
ui/views.py               # Four question-based view layouts
ui/styles.css             # Presentation and responsive styling
tests/test_app.py         # Data-free Streamlit layout contract
data/raw/                 # Original local downloads; not modified by the app
data/processed/           # Future deployment-ready outputs
output/report/            # Editable report artifact
```

## Technology status

### Confirmed current use

| Technology | Use |
| --- | --- |
| Python 3.12 | Application code and tests |
| Streamlit 1.60.0 | Browser UI, tabs, disabled controls, and deployment |
| HTML and CSS | Accessible structure, presentation, and responsive layout |
| GitHub | Source control and the public repository used by Streamlit Community Cloud |

### Declared for the data and visualization phase

| Library | Intended use |
| --- | --- |
| pandas | Load, clean, join, reshape, and aggregate crash data |
| PyArrow | Store processed tables as compact Parquet files |
| Plotly Express / Graph Objects | Interactive timelines, distributions, comparisons, and linked chart selections |
| PyDeck | Crash-point, hotspot, station, and response-coverage map layers |

GeoPandas and Shapely are possible later additions for validated spatial work;
they are not current project dependencies.

Streamlit's built-in widgets and selection events are the planned interaction
layer. No separate JavaScript frontend or database is planned.

## Data storage

```text
data/
|-- raw/        # Original downloads; local only and ignored by Git
`-- processed/  # Future deployment-ready Parquet or GeoJSON files
```

Raw source files stay in `data/raw/` so processing remains reproducible without
committing large originals. The future deployed app will read compact processed
files from `data/processed/`. Files small enough for normal GitHub limits can be
committed with the app; larger data should be fetched from the source API and
cached with `st.cache_data` rather than introducing a database.

Only add another library to `requirements.txt` when implemented work requires
it.

## Data sources

- [Crash incidents](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Incidents-Data/bhju-22kf)
- [Drivers](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Drivers-Data/mmzv-x632)
- [Non-motorists](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Non-Motorists-Data/n7fk-dce5)
- [Fire stations](https://data.montgomerycountymd.gov/Public-Safety/Fire-Station/4cam-wimd/about_data)

## Deployment

Deploy `app.py` from the `main` branch on Streamlit Community Cloud. Choose
Python 3.12 and keep the app public for course submission.

## Current limitations

- No preprocessing method, join logic, missing-value policy, derived fields, or
  processed row counts have been implemented.
- The app contains no data marks or analytical results; controls and selection
  actions are intentionally disabled.
- Planned responder-coverage, alcohol-related, vehicle-age, and injury measures
  still require definitions and validation.
- Accessibility, browser compatibility, performance, and user comprehension
  have not yet been evaluated with live visualizations.
