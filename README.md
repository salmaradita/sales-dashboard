# Sales Performance Dashboard

Synthetic FMCG-style sales performance dashboard built on the existing **Parquet → DuckDB → Streamlit** architecture.

The project is designed for demo/development use. It contains no real company, brand, geography, sales-representative, or target-sales data.

## Project overview

The dashboard focuses on actual sales performance across:

- Sales trend
- Sales growth
- Sales contribution
- Brand and sub-brand performance
- Geographic performance
- Active outlet coverage
- Ranking / Top N analysis
- Contribution vs growth
- Dynamic business insights through the selected analysis views
- Interactive cascading filters
- Excel pivot export

The dashboard UI uses **10 juta+** only as a high-level scale description. This is a display statement and **does not mean the included demo Parquet contains 10 juta+ records**. The synthetic dataset remains intentionally lightweight for local development and demonstration.

## Data architecture

```text
Synthetic generator
       │
       ▼
Parquet
       │
       ▼
DuckDB aggregation
       │
       ▼
Streamlit dashboard
       │
       └── Excel pivot export
```

The dashboard queries Parquet directly through DuckDB and only materializes aggregated results needed for charts/tables.

## Synthetic data

`generate_demo.py` creates:

- Fictional RGM / Region / Province / City / Branch hierarchy
- Fictional Brand / Sub Brand / Product hierarchy
- Monthly sales periods for 2024–2026
- Synthetic active outlets
- Synthetic `ACTUAL` sales value
- Source-year and source-sheet fields for demo lineage

The geographic relationship is:

```text
RGM
└── Region
    └── Province
        └── City
            └── Branch
```

The product relationship is:

```text
Brand
└── Sub Brand
    └── Product
```

No MST Sales Rep field is generated.

No Target Sales field is generated.

The generator intentionally keeps the record count practical for demo/development workloads.

## Main files

### `app_demo.py`

Main Streamlit application.

Responsibilities:

- Detect demo Parquet automatically
- Build cascading filters
- Query DuckDB
- Calculate actual-sales KPIs
- Render sales trend
- Render contribution/ranking
- Render growth analysis
- Render contribution vs growth
- Render product/geographic detail
- Export the filtered pivot

### `generate_demo.py`

Creates the synthetic Parquet dataset:

```bash
python generate_demo.py
```

Output:

```text
demo_data/sales_demo.parquet
```

### `export_pivot.py`

Creates an Excel pivot from the Parquet dataset:

```bash
python export_pivot.py
```

Output:

```text
pivot_output.xlsx
```

The pivot uses:

```text
RGM
Region
Province
City
Branch
Brand
Sub Brand
Product
```

and exports:

- Sales Value
- Active Outlets
- Dropsize

### `requirements.txt`

Runtime dependencies for the dashboard and export/generation scripts.

## KPI definitions

### Total Sales Value

Sum of `ACTUAL` for the selected filter context.

### Active Outlets

Distinct count of `ACCOUNT COMPLETE`.

### Average Sales / Outlet

```text
Total Sales Value / Active Outlets
```

### Sales Growth

Growth between the two latest available periods inside the selected filter context:

```text
(Current Sales / Previous Sales) - 1
```

If a previous comparable period is not available, growth is shown as unavailable.

### Dropsize

```text
Sales Value / Active Outlets
```

No target-related metric is used.

## Dashboard filters

The dashboard provides cascading filters for:

- Year
- Month
- RGM
- Region
- Province
- City
- Branch
- Brand
- Sub Brand
- Product

The available options are refreshed from DuckDB based on the preceding filter context.

## Performance approach

The project keeps the existing architecture and focuses on efficient aggregation:

- Parquet remains the storage layer.
- DuckDB performs aggregation and filtering.
- Streamlit `st.cache_data` caches repeatable queries.
- The dashboard does not load the entire Parquet dataset into Pandas for visualization.
- Charts receive aggregated data rather than raw transaction-level data.
- The demo dataset remains lightweight.

## Installation

```bash
pip install -r requirements.txt
```

## Run the dashboard

If the demo dataset does not exist yet:

```bash
python generate_demo.py
```

Then:

```bash
streamlit run app_demo.py
```

## Export the pivot

```bash
python export_pivot.py
```

## Data privacy / dummy data

All product and geographic names in the demo generator are fictional. The project does not depend on real FMCG brand names or real geographic names.

The dashboard also does not include MST Sales Rep or target-sales functionality.
