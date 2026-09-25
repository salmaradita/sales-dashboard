"""
export_pivot.py
Jalankan di folder yang sama dengan app.py:
    python export_pivot.py

Output: pivot_output.xlsx
Struktur kolom: OC 2024 Jan | OC 2024 Feb | ... | ACTUAL 2024 Jan | ... | Dropsize 2024 Jan | ...
Struktur baris: SUB REGION > BRANCH > BRAND > SUB BRAND > SUBBRAND LIST
"""

import duckdb
import pandas as pd
from itertools import product

# ── Konfigurasi ───────────────────────────────────────────────────────────────
DATA_PATH  = r"C:/Users/USER/Documents/0.1 OC/OUTPUT/*.parquet"
OUTPUT     = r"C:/Users/USER/Documents/pivot_output.xlsx"

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]
PACK_SUFFIXES = [
    "TOPLES","BAG","SCH","BOX","DUS","TIN","ROLL",
    "RTG","KLG","BCK","TPL","ROL","PACK","POUCH","KALENG"
]
BRAND_PREFIXES = sorted([
    "RELAXA TWISH","RELAXA CUWI","RELAXA PLAY","DELBI'S",
    "OATBITS","BONKOPI","LOVY","KAPAL API","ESPRESSO",
    "BONTEA","RELAXA","GINGERBON"
], key=len, reverse=True)

# ── Helper ────────────────────────────────────────────────────────────────────
def sub_brand(name):
    if not name: return name
    n = str(name).strip().upper()
    for s in PACK_SUFFIXES:
        if n.endswith(" " + s):
            n = n[:-(len(s)+1)].strip()
            break
    return n.title()

def brand(sb):
    if not sb: return sb
    n = str(sb).strip().upper()
    for b in BRAND_PREFIXES:
        if n.startswith(b.upper()):
            return b.title()
    return sb

month_case = "\n".join(
    f"WHEN \"MONTH TRX\" = '{m}' THEN {i+1}"
    for i, m in enumerate(MONTH_ORDER)
)

# ── Query data ────────────────────────────────────────────────────────────────
print("Membaca data dari parquet...")
df = duckdb.sql(f"""
    SELECT
        "SUB REGION"                                    AS sub_region,
        CASE WHEN POSITION('#' IN "BRANCH") > 0
             THEN SPLIT_PART("BRANCH", '#', 2)
             ELSE "BRANCH" END                          AS branch,
        "SUBBRAND LIST"                                 AS subbrand_list,
        CAST("YEAR TRX" AS VARCHAR)                     AS tahun,
        "MONTH TRX"                                     AS bulan,
        CASE {month_case} ELSE 99 END                   AS bulan_num,
        SUM(CAST("ACTUAL" AS DOUBLE))                   AS total_actual,
        COUNT(DISTINCT "ACCOUNT COMPLETE")              AS oc
    FROM read_parquet('{DATA_PATH}', union_by_name=True)
    GROUP BY sub_region, branch, subbrand_list, tahun, bulan, bulan_num
    ORDER BY sub_region, branch, subbrand_list, tahun, bulan_num
""").df()

print(f"  Data terbaca: {len(df):,} baris agregat")

# Tambah SUB BRAND dan BRAND
df["sub_brand_col"] = df["subbrand_list"].apply(sub_brand)
df["brand_col"]     = df["sub_brand_col"].apply(brand)
df["dropsize"]      = df["total_actual"] / df["oc"].replace(0, float("nan"))

# ── Bangun urutan kolom periode ───────────────────────────────────────────────
periods_df = (
    df[["tahun","bulan","bulan_num"]]
    .drop_duplicates()
    .sort_values(["tahun","bulan_num"])
)
years   = periods_df["tahun"].unique().tolist()
# Mapping tahun → list bulan yg ada
year_months = {}
for _, row in periods_df.iterrows():
    year_months.setdefault(row["tahun"], [])
    if row["bulan"] not in year_months[row["tahun"]]:
        year_months[row["tahun"]].append(row["bulan"])

# ── Baris index ───────────────────────────────────────────────────────────────
ROW_COLS  = ["sub_region","branch","brand_col","sub_brand_col","subbrand_list"]
ROW_NAMES = ["SUB REGION","BRANCH","BRAND","SUB BRAND","SUBBRAND LIST"]

# Pivot per metrik
def make_pivot(df, value_col, aggfunc="sum"):
    pv = df.pivot_table(
        index=ROW_COLS,
        columns=["tahun","bulan_num","bulan"],
        values=value_col,
        aggfunc=aggfunc
    )
    pv.index.names = ROW_NAMES
    # Hapus nama kolom MultiIndex
    pv.columns.names = [None, None, None]
    return pv

print("Membuat pivot ACTUAL...")
pv_actual   = make_pivot(df, "total_actual")
print("Membuat pivot OC...")
pv_oc       = make_pivot(df, "oc")
print("Menghitung Dropsize...")
pv_dropsize = pv_actual / pv_oc.replace(0, float("nan"))

# ── Gabung semua metrik dengan MultiIndex kolom berlapis ─────────────────────
# Struktur: Level 0 = Metrik (OC/ACTUAL/Dropsize)
#           Level 1 = Tahun (2024/2025/2026)
#           Level 2 = Bulan (Jan/Feb/...)

def add_metric_level(pv, metric_name):
    """Tambahkan level atas MultiIndex kolom dengan nama metrik."""
    cols = pv.columns  # MultiIndex (tahun, bulan_num, bulan)
    new_cols = pd.MultiIndex.from_tuples(
        [(metric_name, yr, bulan) for yr, bnum, bulan in cols],
        names=["Metrik","Tahun","Bulan"]
    )
    pv = pv.copy()
    pv.columns = new_cols
    return pv

pv_oc_m  = add_metric_level(pv_oc,       "OC")
pv_act_m = add_metric_level(pv_actual,   "ACTUAL")
pv_ds_m  = add_metric_level(pv_dropsize, "DROPSIZE")

# Gabung: OC dulu, lalu ACTUAL, lalu DROPSIZE
df_final = pd.concat([pv_oc_m, pv_act_m, pv_ds_m], axis=1).fillna(0)

print(f"  Ukuran tabel final: {df_final.shape[0]:,} baris × {df_final.shape[1]:,} kolom")

# ── Export ke Excel ───────────────────────────────────────────────────────────
print(f"Menyimpan ke {OUTPUT}...")

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    df_final.to_excel(writer, sheet_name="Pivot")

    # Format header agar lebih rapi
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    ws = writer.sheets["Pivot"]

    # Warna per metrik
    METRIC_COLORS = {
        "OC":       "DBEAFE",   # biru muda
        "ACTUAL":   "DCFCE7",   # hijau muda
        "DROPSIZE": "FEF9C3",   # kuning muda
    }

    # Header ada di baris 1-4 (MultiIndex 3 level + index kolom)
    # Baris 1 = Metrik, Baris 2 = Tahun, Baris 3 = Bulan
    # Baris 4 = data mulai (index baris ada di kolom 1-5)
    n_index_cols = len(ROW_NAMES)  # 5 kolom index baris

    # Warnai header berdasarkan metrik
    for col_idx in range(n_index_cols + 1, ws.max_column + 1):
        cell_metric = ws.cell(row=1, column=col_idx)
        metric = cell_metric.value
        if metric in METRIC_COLORS:
            fill = PatternFill("solid", fgColor=METRIC_COLORS[metric])
            cell_metric.fill = fill
            ws.cell(row=2, column=col_idx).fill = fill
            ws.cell(row=3, column=col_idx).fill = fill

    # Bold header
    for row in ws.iter_rows(min_row=1, max_row=3):
        for cell in row:
            cell.font  = Font(bold=True, size=9)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Bold dan freeze index baris
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row, min_col=1, max_col=n_index_cols):
        for cell in row:
            cell.font = Font(size=9)

    # Freeze pane setelah header 3 baris + 5 kolom index
    ws.freeze_panes = ws.cell(row=4, column=n_index_cols + 1)

    # Auto-width kolom index
    for i in range(1, n_index_cols + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20
    # Kolom data lebih sempit
    for i in range(n_index_cols + 1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = 9

    # Format angka kolom data
    from openpyxl.styles import numbers
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row,
                             min_col=n_index_cols+1, max_col=ws.max_column):
        for cell in row:
            if cell.value is not None:
                cell.number_format = "#,##0.00"
                cell.font = Font(size=9)
                cell.alignment = Alignment(horizontal="right")

    # Tinggi header
    ws.row_dimensions[1].height = 18
    ws.row_dimensions[2].height = 16
    ws.row_dimensions[3].height = 14

print("✅ Selesai!")
print(f"   File: {OUTPUT}")
print(f"   Sheet: Pivot")
print(f"   Baris data: {df_final.shape[0]:,}")
print(f"   Kolom (periode × metrik): {df_final.shape[1]:,}")
