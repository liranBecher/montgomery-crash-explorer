# Police Breathalyzers preprocessing

Run from the project root:

```powershell
.venv\Scripts\python.exe preprocess\police-breathalyzers\preprocess_police_breathalyzers.py
```

The script writes `alcohol_crashes.parquet` and `alcohol_cells.parquet` under
`data/processed/police-breathalyzers`.

A crash is `alcohol_related` when any driver label records alcohol as present
or contributing, suspects alcohol use, or records a combined substance as
present or contributing. Explicit "not suspect" and "none detected" labels
are not alcohol-related. Missing, unknown, N/A, and other labels remain
`Unknown`. The original combined source labels are retained in
`substance_labels` for auditing.

Cell shares use all geocoded crashes in the cell as the denominator. The
classification is descriptive of the police crash record; it is not a blood
alcohol measurement or a causal finding.
