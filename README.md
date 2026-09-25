# 📊 FMCG Sales Dashboard

> Internal sales analytics dashboard built with Python + Streamlit, designed to handle **15M+ rows** of transactional data efficiently without any paid BI tools or cloud subscriptions.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?logo=streamlit)
![DuckDB](https://img.shields.io/badge/DuckDB-0.10+-yellow)
![Plotly](https://img.shields.io/badge/Plotly-5.20+-purple?logo=plotly)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🎯 Problem Statement

A sales team at an FMCG company needed visibility into 15M+ rows of transactional data spanning 3 years, 8 regions, 50+ branches, and 30+ SKUs — **without a paid BI subscription**. The data lived in Parquet files on a local machine and needed to be accessible to the entire team securely.

**Constraints:**
- No cloud BI budget (no Tableau, Power BI, or Looker)
- Data must stay internal — not exposed to the internet
- Single machine as the data source

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Local Machine                     │
│                                                     │
│  Parquet files (15M rows)                          │
│       ↓                                             │
│  DuckDB  ──── SQL queries directly on disk         │
│       ↓        (no RAM overload)                   │
│  Streamlit ── Interactive dashboard UI             │
│       ↓                                             │
│  Tailscale ── VPN tunnel (team-only access)        │
└─────────────────────────────────────────────────────┘
         ↕  (secure, encrypted)
┌────────────────────┐
│   Team Members     │
│  (Tailscale VPN)   │
│  Browser → URL     │
└────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **YTD Comparison** | Year-over-year comparison (2024 vs 2025 vs 2026) with growth indicators ▲▼ |
| **Outlet Coverage** | `COUNT(DISTINCT ACCOUNT)` per region/brand — accurate, no double-counting |
| **Dropsize Analysis** | `ACTUAL ÷ OC` per dimension and period |
| **Historical Average** | `SUM(ACTUAL) ÷ COUNT(DISTINCT months)` per year per dimension |
| **Multi-layer Filter** | RGM, Sub Region, Branch, Brand, Sub Brand, Subbrand List, MST Salesrep |
| **Performance Trend** | Line chart with breakdown by RGM / Sub Region / Brand / Sub Brand |
| **Share of Total** | Pie chart with drill-down: Total → Category (Candy/Biscuit) → Brand → Sub Brand |
| **Pivot Export** | Excel with multi-level header: Metrik × Tahun × Bulan |
| **Secure Sharing** | Tailscale VPN — zero public internet exposure |

---

## 🔧 Tech Stack & Key Decisions

### Why DuckDB instead of Pandas?
```python
# ❌ Pandas — loads ALL 15M rows into RAM → likely crash or very slow
df = pd.read_parquet("data/*.parquet")

# ✅ DuckDB — SQL query directly on Parquet files, only loads what's needed
result = duckdb.sql("""
    SELECT "SUB REGION", SUM(CAST("ACTUAL" AS DOUBLE)) AS total
    FROM read_parquet('data/*.parquet', union_by_name=True)
    WHERE "YEAR TRX" = '2026'
    GROUP BY "SUB REGION"
""").df()
```

### Why Tailscale instead of cloud deploy?
- **Zero cost** — no server, no cloud hosting fee
- **Data never leaves the machine** — critical for sensitive sales data
- **Peer-to-peer VPN** — team connects directly to the host machine
- **Simple setup** — install app + login, done

### Accurate COUNT DISTINCT across dimensions
The trickiest part: when showing Outlet Coverage (unique accounts) broken down by Brand, a naive `SUM(oc_per_branch)` double-counts accounts that purchased from multiple branches under the same Brand.

**Solution:** Build a `CASE WHEN` mapping directly in SQL so `COUNT(DISTINCT)` runs at the correct aggregation level:
```sql
SELECT
    CASE WHEN "SUBBRAND LIST" = 'RELAXA TWISH MINT BAG' THEN 'Relaxa'
         WHEN "SUBBRAND LIST" = 'KAPAL API SPECIAL MIX BOX' THEN 'Kapal Api'
         -- ... all mappings
    END AS brand,
    COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage  -- accurate at brand level
FROM read_parquet('data/*.parquet', union_by_name=True)
GROUP BY brand
```

### Derived columns (Brand & Sub Brand)
Brand and Sub Brand are not stored in the raw data — they're derived from `SUBBRAND LIST` via string parsing:
```python
# "RELAXA TWISH MINT BAG" → Sub Brand: "Relaxa Twish Mint" → Brand: "Relaxa Twish"
PACK_SUFFIXES  = ["BAG","BOX","DUS","TIN","ROLL",...]  # packaging types to strip
BRAND_PREFIXES = ["RELAXA TWISH","KAPAL API","GINGERBON",...]  # longest-first matching
```

---

## 🚀 Quick Start

### 1. Clone & install
```bash
git clone https://github.com/yourusername/fmcg-sales-dashboard.git
cd fmcg-sales-dashboard
pip install -r requirements.txt
```

### 2. Generate demo data
```bash
python generate_demo.py
# Output: demo_data/sales_demo.parquet (~500K rows synthetic data)
```

### 3. Run dashboard
```bash
streamlit run app_demo.py
# Opens at http://localhost:8501
```

### 4. (Production) Point to real Parquet files
Edit `DATA_PATH` in `app_demo.py`:
```python
DATA_PATH = r"path/to/your/data/*.parquet"
```

---

## 📁 Project Structure

```
fmcg-sales-dashboard/
├── app_demo.py          # Main Streamlit app (auto-detects demo vs prod)
├── generate_demo.py     # Synthetic data generator
├── export_pivot.py      # Standalone pivot export script
├── requirements.txt
├── demo_data/
│   └── sales_demo.parquet   # Generated by generate_demo.py
└── README.md
```

---

## 📊 Dashboard Sections

1. **Summary** — Total rows, unique accounts, total ACTUAL, avg per period
2. **Performance Trend** — Line chart (Monthly/Yearly) with multi-dimension breakdown
3. **YTD Volume Performance** — Cross-year YTD bar chart with growth indicators
4. **Outlet Coverage** — Unique account count by Sub Region / Brand / Sub Brand
5. **Volume Performance** — Horizontal bar chart by dimension with Top-N slider
6. **Share of Total Volume** — Pie chart with category drill-down
7. **Pivot Export** — Download Excel with multi-level headers (Metrik × Year × Month)

---

## 🔒 Security (Production Setup)

For team sharing without cloud exposure:

```bash
# Install Tailscale on host machine
# tailscale.com/download

# Get your Tailscale IP
tailscale ip -4
# → e.g. 100.64.1.5

# Run dashboard bound to all interfaces
streamlit run app_demo.py --server.port 8501

# Team members: install Tailscale, join the same network
# Then open: http://100.64.1.5:8501
```

---

## 📝 Notes

- **Demo data** is fully synthetic — no real company data is included
- **RGM mapping** (Regional General Manager territory) is hardcoded from a lookup table pairing Sub Region + Branch to RGM name
- The `ACTUAL` column is stored as `VARCHAR` in source data — all numeric operations use explicit `CAST("ACTUAL" AS DOUBLE)`

---

## 👤 Author

Built as an internal tool for FMCG sales analytics.  
Data in this repository is entirely synthetic for portfolio demonstration purposes.
