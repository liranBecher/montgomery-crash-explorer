# Montgomery County Crash Explorer

Course visualization project built with Python and Streamlit.

The original course brief is included as
[פרוייקט ויזואליזציה הוראות.pdf](./פרוייקט%20ויזואליזציה%20הוראות.pdf).
A structured English version is in [PROJECT_REQUIREMENTS.md](./PROJECT_REQUIREMENTS.md).

## Run locally

Python 3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The layout prototype runs without data. Its controls remain disabled until the
processed-data contract is finalized.

## Planned views

1. Safety hotspots by time, place, weather, road type, and light conditions
2. Crash-response coverage around existing first-responder locations
3. Priority locations and times for police breathalyzer alcohol-level enforcement
4. Vehicle make/age and driver injury severity

## Tech stack

### Application and deployment

| Technology | Use |
| --- | --- |
| Python 3.12 | Data preparation and application code |
| Streamlit | Browser UI, shared filters, interactive views, and deployment on Streamlit Community Cloud |
| GitHub | Source control and the public repository used by Streamlit Community Cloud |

### Data and geospatial processing

| Library | Use |
| --- | --- |
| pandas | Load, clean, join, reshape, and aggregate crash data |
| PyArrow | Store processed tables as compact Parquet files |
| GeoPandas | Spatial joins and geospatial table preparation |
| Shapely | Buffers, distances, and coverage geometry |

### Visualizations and maps

| Library | Use |
| --- | --- |
| Plotly Express / Graph Objects | Interactive timelines, distributions, comparisons, and linked chart selections |
| PyDeck | Crash-point, hotspot, station, and response-coverage map layers |

Streamlit's built-in widgets and selection events provide the interaction layer.
No separate JavaScript frontend or database is planned.

## Data storage

```text
data/
├── raw/        # Original downloads; local only and ignored by Git
└── processed/  # Clean deployment-ready Parquet or GeoJSON files
```

Raw source files stay in `data/raw/` so processing remains reproducible without
committing large originals. The deployed app reads compact processed files from
`data/processed/`. Files small enough for normal GitHub limits are committed with
the app; larger data should be fetched from the source API and cached with
`st.cache_data` rather than introducing a database.

Only add a listed library to `requirements.txt` when the view that needs it is
implemented.


## Data sources

- [Crash incidents](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Incidents-Data/bhju-22kf)
- [Drivers](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Drivers-Data/mmzv-x632)
- [Non-motorists](https://data.montgomerycountymd.gov/Public-Safety/Crash-Reporting-Non-Motorists-Data/n7fk-dce5)
- [Fire stations](https://data.montgomerycountymd.gov/Public-Safety/Fire-Station/4cam-wimd/about_data)

## Deployment

Deploy `app.py` from the `main` branch on Streamlit Community Cloud. Choose Python 3.12 and keep the app public for course submission.
