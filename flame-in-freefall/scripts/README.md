# Data pipeline

Everything the dashboard shows comes from these scripts. No value is typed by hand.

## Inputs

There are two entry points, and they overlap on purpose:

1. **NASA PSI API** (`psi.nasa.gov/geode-py/ws/repo`) — investigation metadata,
   publications, file manifests, and the `Experimental table` CSVs.
2. **Team-collected CSVs** in `incoming/` — the same tables, downloaded by hand
   when the PSI download endpoint refused. One file (PSI-10 Normal Flame) was
   copy-pasted from the browser and saved as CSV.

Do not open the CSVs in Excel and re-save them: Excel rewrites decimal
separators and turns numbers into dates.

## Order of execution

Run from the project root.

| # | Script | Input | Output |
|---|---|---|---|
| 1 | `fetch_psi_tables.py` | PSI API | `incoming/api/*.csv` |
| 2 | `build_dataset.py` | `data/detail/*.json` | `data/investigations.json` |
| 3 | `parse_team_tables.py` | `incoming/*.csv` | `data/experimental/*.json` |
| 4 | `merge_experimental.py` | `data/experimental/*.json` | merged into `investigations.json` |
| 5 | `extract_physics.py` | PSI text + publications | `data/physics.json` |
| 6 | `ingest_findings.py` | team findings spreadsheet | `data/findings.json` |
| 7 | `score.py` | all of the above | `data/dashboard_data.json` |
| 8 | `export_frontend.py` | `data/dashboard_data.json` | `data/dashboard_data.frontend.json` |
| 9 | `build_dashboard.py` | `data/dashboard_data.json` | `dashboard/index.html` (prototype) |
| 10 | `build_qa_sheet.py` | parsed ranges | `handoff/QA_spotcheck.xlsx` |
| 11 | `parse_experimental_tables.py` | legacy parser, superseded by #3 | — |

`parse_team_tables.py` must run before `merge_experimental.py`.

## What each script does

| Script | Purpose |
|---|---|
| `fetch_psi_tables.py` | Downloads every `Experimental table` file from PSI through the documented API endpoint |
| `build_dataset.py` | Normalises raw PSI responses: title, platform, hardware, publications, file manifest |
| `parse_team_tables.py` | Per-file column mapping, unit conversion (mmHg, bar, atm, mole fraction), min/max per investigation |
| `merge_experimental.py` | Attaches parsed ranges to `data/investigations.json` |
| `extract_physics.py` | Sends PSI descriptions and publication metadata to a model, returns structured fields with verbatim quotes |
| `ingest_findings.py` | Cleans the team's spreadsheet, drops unsourced entries |
| `score.py` | Five-part relevance model across four environments |
| `export_frontend.py` | Reshapes the scored records into the JSON the React app imports |
| `build_dashboard.py` | Renders the static HTML prototype with data inlined |
| `build_qa_sheet.py` | Spot-check workbook: every extreme value traced to a row and cell |

## AI usage

Only one stage uses a model: `extract_physics.py`.

- Input: PSI text descriptions and publication metadata.
- Output: fuel type, materials, airflow, and conditions missing from the tables.
- Every extracted value carries a verbatim quote, so it can be checked against
  the source text.
- All numeric ranges come from the experimental tables and are parsed
  deterministically.
- `score.py` is rule-based and does not call any model.

`data/physics.json` is the canonical output used by the dashboard. Re-running
the extraction may produce slightly different values, because model output is
not deterministic.

## Environment

Copy `.env.example` to `.env` and fill in what you need:

| Variable | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | only for step 5 | model access for parameter extraction |
| `PSI_LLM_MODEL` | no | defaults to `gpt-4o-mini` |

Steps 1–4 and 6–11 need no credentials. The PSI API is open.

## Data provenance

- `data/detail/` — raw PSI API responses (24 files, ~20 MB, not committed)
- `data/experimental/` — parsed ranges, one file per investigation
- `data/dashboard_data.json` — the single file the frontend consumes

## Scoring model

Each investigation is scored for one environment at a time:

| Part | Max | Meaning |
|---|---|---|
| Oxygen fit | 35 | documented O2 range covers the target |
| Pressure fit | 25 | documented pressure range covers the target |
| Material fit | 20 | fuel state matches the environment's material class |
| Fire-safety framing | 12 | the study is explicitly about fire safety |
| Flight platform | 8 | flown in microgravity |

A planned test matrix is discounted by 25%: a plan is not evidence that a
condition was observed.
