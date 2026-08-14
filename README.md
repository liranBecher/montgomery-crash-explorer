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
| Public Streamlit interface and Fire & Rescue Proximity analysis | Data-backed views for the other three tabs |
| Four question-based tabs and responsive card layout | Data-backed charts for the other three tabs |
| Fire & Rescue filters and linked map/scatter selection | Shared cross-tab filters and selections |
| Planned interaction descriptions and automated layout test | Validated methods, findings, and recommendations |

The Fire & Rescue tab is connected to processed data. The other three tabs
remain interface prototypes and do not yet display findings.

## Run locally

Python 3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The committed Fire & Rescue Parquet files are required by the connected tab.
Its preprocessing script can regenerate them when the ignored raw CSVs are
available locally.

Run the current automated test with:

```powershell
python -m unittest discover -s tests -v
```

## Planned views

1. Safety hotspots by time, place, weather, road type, and light conditions
2. Serious/fatal crash proximity to mapped fire-station locations
3. Priority locations and times for police breathalyzer alcohol-level enforcement
4. Vehicle make/age and driver injury severity

Detailed encodings and linking behavior are specified in
[DESIGN_SPEC.md](./DESIGN_SPEC.md).

## Repository structure

```text
app.py                    # Streamlit entry point
ui/components.py          # Shared header, filters, guide, and placeholder cards
ui/views.py               # View routing and remaining placeholders
ui/fire_rescue.py         # Connected Fire & Rescue charts and interactions
ui/styles.css             # Presentation and responsive styling
tests/                    # Application and preprocessing contracts
data/raw/                 # Original local downloads; not modified by the app
preprocess/fire-and-rescue/ # Fire & Rescue preprocessing pipeline
data/processed/fire-and-rescue/ # Fire & Rescue deployment-ready Parquet outputs
output/report/            # Editable report artifact
```

## Technology status

### Confirmed current use

| Technology | Use |
| --- | --- |
| Python 3.12 | Application code and tests |
| Streamlit 1.60.0 | Browser UI, tabs, disabled controls, and deployment |
| pandas / PyArrow | Fire & Rescue transformation and Parquet storage |
| Altair | Interactive demand-distance scatterplot |
| PyDeck | Linked crash-demand and station-location map |
| HTML and CSS | Accessible structure, presentation, and responsive layout |
| GitHub | Source control and the public repository used by Streamlit Community Cloud |

### Declared for the data and visualization phase

| Library | Intended use |
| --- | --- |
| Plotly Express / Graph Objects | Interactive timelines, distributions, comparisons, and linked chart selections |

GeoPandas and Shapely are possible later additions for validated spatial work;
they are not current project dependencies.

Streamlit's built-in widgets and selection events are the planned interaction
layer. No separate JavaScript frontend or database is planned.

## Data storage

Raw downloads live in ignored `data/raw/`. The Fire & Rescue pipeline lives in
`preprocess/fire-and-rescue/`; its committed deployment outputs live in
`data/processed/fire-and-rescue/`.

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

## Deployment

Deploy `app.py` from the `main` branch on Streamlit Community Cloud. Choose
Python 3.12 and keep the app public for course submission.

## Current limitations

- The safety, alcohol-enforcement, and vehicle views remain interface placeholders.
- Fire-station proximity is straight-line distance, not travel time or measured
  emergency response performance.
- Planned alcohol-related and vehicle-age measures still require definitions
  and validation.
- Accessibility, browser compatibility, performance, and user comprehension
  have not yet been evaluated with live visualizations.
