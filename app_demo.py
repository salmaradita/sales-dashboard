import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import io

st.set_page_config(page_title="FMCG Sales Dashboard", page_icon="📊", layout="wide")

# ── Path: otomatis deteksi demo vs prod ──────────────────────────────────────
import os
if os.path.exists("demo_data/sales_demo.parquet"):
    DATA_PATH = "demo_data/sales_demo.parquet"
    IS_DEMO   = True
else:
    DATA_PATH = r"C:/Users/USER/Documents/0.1 OC/OUTPUT/*.parquet"
    IS_DEMO   = False

st.markdown("""
<style>
[data-testid="metric-container"]{background:#f8f9fb;border-radius:10px;
  padding:12px 16px;border:1px solid #e9ecef}
[data-testid="metric-container"] label{font-size:12px !important;color:#6c757d !important}
</style>
""", unsafe_allow_html=True)

# ── Konstanta ─────────────────────────────────────────────────────────────────
MONTH_ORDER   = ["Jan","Feb","Mar","Apr","May","Jun",
                 "Jul","Aug","Sep","Oct","Nov","Dec"]
MST_OPTIONS   = ["TMFS","TSRS","TSBP","TSSP","TSES","TSSB","TESB","TESP"]
PACK_SUFFIXES = ["TOPLES","BAG","SCH","BOX","DUS","TIN","ROLL",
                 "RTG","KLG","BCK","TPL","ROL","PACK","POUCH","KALENG"]
BRAND_PREFIXES = sorted([
    "RELAXA TWISH","RELAXA CUWI","RELAXA PLAY","DELBI'S",
    "OATBITS","BONKOPI","LOVY","KAPAL API","ESPRESSO",
    "BONTEA","RELAXA","GINGERBON"
], key=len, reverse=True)
CANDY_BRANDS   = ["Relaxa Twish","Relaxa Cuwi","Relaxa Play","Relaxa",
                  "Espresso","Kapal Api","Bontea","Gingerbon","Bonkopi"]
BISCUIT_BRANDS = ["Delbi'S","Lovy","Oatbits"]
BRAND_CATEGORY = {b:"Candy" for b in CANDY_BRANDS}
BRAND_CATEGORY.update({b:"Biscuit" for b in BISCUIT_BRANDS})

RGM_LOOKUP_RAW = [
    ("JABAR 3","JAWA BARAT","C12#TASIKMALAYA"),
    ("JABAR 2","JAWA BARAT","C16#GARUT"),
    ("JABAR 2","JAWA BARAT","C18#SUMEDANG"),
    ("JABAR 2","JAWA BARAT","C11#BANDUNG"),
    ("JABAR 1","JAWA BARAT","C13#SUKABUMI"),
    ("JABAR 3","JAWA BARAT","C17#SUBANG"),
    ("JABAR 2","JAWA BARAT","C45#BANJARAN"),
    ("BMPP","SULAWESI","C71#MAKASSAR"),
    ("BMPP","SULAWESI","C72#PALOPO"),
    ("BMPP","KALIMANTAN","C61#PONTIANAK"),
    ("BMPP","LUAR PULAU","C41#DENPASAR"),
    ("JABOTABEK 2","JABOTABEK","C09#KARAWANG"),
    ("JABOTABEK 2","JABOTABEK","C03#BEKASI"),
    ("JABOTABEK 1","JABOTABEK","C08#BOGOR"),
    ("JABOTABEK 3","JABOTABEK","C10#DAAN MOGOT"),
    ("JABOTABEK 1","JABOTABEK","C50#REMPOA"),
    ("JABOTABEK 3","JABOTABEK","C43#BALARAJA"),
    ("JABOTABEK 3","JABOTABEK","C19#PANDEGLANG"),
    ("JABOTABEK 1","JABOTABEK","C39#SERPONG"),
    ("JABOTABEK 1","JABOTABEK","C05#SELATAN"),
    ("JABOTABEK 2","JABOTABEK","C04#PONDOK UNGU"),
    ("JATENG SELATAN","JAWA TENGAH","C23#PURWOKERTO"),
    ("JATENG SELATAN","JAWA TENGAH","C22#YOGYAKARTA"),
    ("JATENG SELATAN","JAWA TENGAH","C42#SOLO"),
    ("JATENG SELATAN","JAWA TENGAH","C48#CILACAP"),
    ("JABOTABEK 3","JABOTABEK","C07#SERANG"),
    ("JABOTABEK 2","JABOTABEK","C01#JATIBARU"),
    ("JABOTABEK 3","JABOTABEK","C06#TANGERANG"),
    ("JABOTABEK 1","JABOTABEK","C20#DEPOK"),
    ("JABOTABEK 2","JABOTABEK","C49#TAMBUN"),
    ("JABAR 1","JAWA BARAT","C14#CIMAREME"),
    ("JABAR 1","JAWA BARAT","C40#CIANJUR"),
    ("JABAR 1","JAWA BARAT","C46#PURWAKARTA"),
    ("JABAR 3","JAWA BARAT","C55#JATIBARANG"),
    ("JATIM UTARA","JAWA TIMUR","C30#SURABAYA"),
    ("JATIM UTARA","JAWA TIMUR","C31#KRIAN"),
    ("JATIM UTARA","JAWA TIMUR","C35#KEDIRI"),
    ("JATIM UTARA","JAWA TIMUR","C54#SURABAYA BARAT"),
    ("JATENG UTARA","JAWA TENGAH","C21#SEMARANG"),
    ("JATENG UTARA","JAWA TENGAH","C24#TEGAL"),
    ("JATENG UTARA","JAWA TENGAH","C26#KUDUS"),
    ("SUMATERA","SUMATERA","C53#PALEMBANG"),
    ("SUMATERA","SUMATERA","C28#LAMPUNG"),
    ("SUMATERA","SUMATERA","C56#PEKANBARU"),
    ("SUMATERA","SUMATERA","C51#MEDAN"),
    ("SUMATERA","SUMATERA","C52#JAMBI"),
    ("SUMATERA","SUMATERA","C33#BENGKULU"),
    ("JATIM SELATAN","JAWA TIMUR","C32#MALANG"),
    ("JATIM SELATAN","JAWA TIMUR","C34#JEMBER"),
    ("JATIM SELATAN","JAWA TIMUR","C47#BLITAR"),
    ("KALIMANTAN, DIRECT BALIKPAPAN & FMC","KALIMANTAN","C99#AGEN"),
    ("KALIMANTAN, DIRECT BALIKPAPAN & FMC","KALIMANTAN","C57#BALIKPAPAN"),
    ("NUSRA & PAPUA, FMM","PAPUA","C99#AGEN"),
    ("NUSRA & PAPUA, FMM","NUSA TENGGARA","C99#AGEN"),
    ("SULAWESI, GORONTALO, MALUKU","SULAWESI","C99#AGEN"),
    ("SULAWESI, GORONTALO, MALUKU","MALUKU","C99#AGEN"),
    ("MM ALL","JAWA BARAT","C15#MM BANDUNG"),
    ("MM ALL","JABOTABEK","C02#MM JABOTABEK"),
    ("MM ALL","JAWA TIMUR","C25#MM JATIM"),
]
df_rgm_lookup = pd.DataFrame(RGM_LOOKUP_RAW, columns=["RGM","SUB REGION","BRANCH"])
RGM_DICT      = {(r["SUB REGION"], r["BRANCH"]): r["RGM"] for _, r in df_rgm_lookup.iterrows()}
RGM_OPTIONS   = sorted(df_rgm_lookup["RGM"].unique().tolist())

# ── Helpers ───────────────────────────────────────────────────────────────────
def sql_esc(val): return str(val).replace("'","''")

def extract_sub_brand(name):
    if not name: return name
    n = str(name).strip().upper()
    for s in PACK_SUFFIXES:
        if n.endswith(" "+s): n = n[:-(len(s)+1)].strip(); break
    return n.title()

def extract_brand(sb):
    if not sb: return sb
    n = str(sb).strip().upper()
    for b in BRAND_PREFIXES:
        if n.startswith(b.upper()): return b.title()
    return sb

def month_to_num_sql(col='"MONTH TRX"'):
    cases = "\n".join(f"WHEN {col}='{m}' THEN {i+1}" for i,m in enumerate(MONTH_ORDER))
    return f"CASE {cases} ELSE 99 END"

def build_where(filters, mst_list, subbrand_lists):
    clauses = []
    for col, vals in filters.items():
        if vals:
            iv = ", ".join(f"'{sql_esc(v)}'" for v in vals)
            clauses.append(f'"{col}" IN ({iv})')
    if mst_list:
        ml = " OR ".join(f'"MST SALESREP NUMBER" LIKE \'%{sql_esc(m)}%\'' for m in mst_list)
        clauses.append(f"({ml})")
    if subbrand_lists:
        iv = ", ".join(f"'{sql_esc(v)}'" for v in subbrand_lists)
        clauses.append(f'"SUBBRAND LIST" IN ({iv})')
    return ("WHERE "+" AND ".join(clauses)) if clauses else ""

# ── Cache helpers ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_unique(col):
    rows = duckdb.sql(f"""
        SELECT DISTINCT "{col}" FROM read_parquet('{DATA_PATH}', union_by_name=True)
        WHERE "{col}" IS NOT NULL ORDER BY "{col}"
    """).fetchall()
    return [r[0] for r in rows]

@st.cache_data(show_spinner=False)
def get_subbrand_meta():
    vals = get_unique("SUBBRAND LIST")
    rows = []
    for v in vals:
        sb  = extract_sub_brand(v)
        br  = extract_brand(sb)
        cat = BRAND_CATEGORY.get(br,"Other")
        rows.append({"SUBBRAND LIST":v,"SUB BRAND":sb,"BRAND":br,"CATEGORY":cat})
    return pd.DataFrame(rows)

# ── Load metadata ─────────────────────────────────────────────────────────────
with st.spinner("Memuat data..."):
    df_meta      = get_subbrand_meta()
    opts_sr      = get_unique("SUB REGION")
    opts_branch  = get_unique("BRANCH")
    opts_sblist  = get_unique("SUBBRAND LIST")
    opts_year    = get_unique("YEAR TRX")
    opts_month   = [m for m in MONTH_ORDER if m in get_unique("MONTH TRX")]
    opts_subbrand= sorted(df_meta["SUB BRAND"].unique().tolist())
    opts_brand   = sorted(df_meta["BRAND"].unique().tolist())
    latest_year  = max(opts_year) if opts_year else None
    ytd_months_r = duckdb.sql(f"""
        SELECT DISTINCT "MONTH TRX" FROM read_parquet('{DATA_PATH}', union_by_name=True)
        WHERE CAST("YEAR TRX" AS VARCHAR)='{latest_year}'
    """).fetchall() if latest_year else []
    ytd_months      = [r[0] for r in ytd_months_r if r[0] in MONTH_ORDER]
    ytd_max_month_n = max([MONTH_ORDER.index(m)+1 for m in ytd_months]) if ytd_months else 12

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Filter")
    sel_year   = st.multiselect("📅 Tahun",            opts_year,  default=opts_year)
    sel_month  = st.multiselect("🗓️ Bulan",            opts_month)
    sel_sr     = st.multiselect("🗺️ Sub Region",       opts_sr)
    sel_branch = st.multiselect("🏢 Branch",           opts_branch)
    sel_brand  = st.multiselect("🏷️ Brand",            opts_brand)
    sel_sb     = st.multiselect("🔖 Sub Brand",        opts_subbrand)
    sel_sblist = st.multiselect("📦 Subbrand List",    opts_sblist)
    st.divider()
    st.subheader("🏷️ RGM")
    sel_rgm = st.multiselect("RGM", RGM_OPTIONS)
    st.divider()
    st.subheader("👤 MST Salesrep")
    sel_mst = st.multiselect("Tipe", MST_OPTIONS, default=MST_OPTIONS)
    st.divider()
    if st.button("🔄 Refresh cache"): st.cache_data.clear(); st.rerun()

# ── Resolve filters ───────────────────────────────────────────────────────────
df_meta_f = df_meta.copy()
if sel_brand: df_meta_f = df_meta_f[df_meta_f["BRAND"].isin(sel_brand)]
if sel_sb:    df_meta_f = df_meta_f[df_meta_f["SUB BRAND"].isin(sel_sb)]
resolved_sblist = list(df_meta_f["SUBBRAND LIST"].unique())
if sel_sblist:
    resolved_sblist = list(set(resolved_sblist)&set(sel_sblist)) if (sel_brand or sel_sb) else sel_sblist

rgm_branches, rgm_sr = [], []
if sel_rgm:
    flt = df_rgm_lookup[df_rgm_lookup["RGM"].isin(sel_rgm)]
    rgm_branches = flt["BRANCH"].tolist()
    rgm_sr       = flt["SUB REGION"].unique().tolist()

base_filters = {}
if sel_year:   base_filters["YEAR TRX"]  = [str(y) for y in sel_year]
if sel_month:  base_filters["MONTH TRX"] = sel_month
if sel_sr:     base_filters["SUB REGION"] = sel_sr
elif sel_rgm:  base_filters["SUB REGION"] = rgm_sr
if sel_branch: base_filters["BRANCH"]     = sel_branch
elif sel_rgm:  base_filters["BRANCH"]     = rgm_branches
WHERE         = build_where(base_filters, sel_mst, resolved_sblist)
base_no_year  = {k:v for k,v in base_filters.items() if k!="YEAR TRX"}
WHERE_NO_YEAR = build_where(base_no_year, sel_mst, resolved_sblist)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📊 FMCG Sales Dashboard")
if IS_DEMO:
    st.info("🎭 **Demo mode** — data sintetis, bukan data perusahaan sesungguhnya.")
st.caption(f"Sumber: `{DATA_PATH}`")

# ══════════════════════════════════════════════════════════════════════════════
# 1. SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📌 Summary")

@st.cache_data(show_spinner=False)
def get_metrics(where):
    return duckdb.sql(f"""
        SELECT COUNT(*), COUNT(DISTINCT "ACCOUNT COMPLETE"),
               SUM(CAST("ACTUAL" AS DOUBLE)),
               COUNT(DISTINCT CAST("YEAR TRX" AS VARCHAR)||'-'||"MONTH TRX")
        FROM read_parquet('{DATA_PATH}', union_by_name=True) {where}
    """).fetchone()

@st.cache_data(show_spinner=False)
def get_active_sblist(where):
    rows = duckdb.sql(f"""
        SELECT DISTINCT "SUBBRAND LIST" FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
    """).fetchall()
    active = [r[0] for r in rows if r[0]]
    sub = df_meta[df_meta["SUBBRAND LIST"].isin(active)]
    return sub["BRAND"].nunique(), sub["SUB BRAND"].nunique()

with st.spinner("Menghitung metrik..."):
    m = get_metrics(WHERE)
    total_brand, total_subbrand = get_active_sblist(WHERE)

total_actual = m[2] if m[2] else 0
n_periode    = m[3] if m[3] and m[3]>0 else 1
c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Baris",        f"{m[0]:,}")
c2.metric("Unique Account",     f"{m[1]:,}")
c3.metric("Total ACTUAL",       f"{total_actual:,.0f}")
c4.metric("Avg ACTUAL/Periode", f"{total_actual/n_periode:,.0f}")
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 2. PERFORMANCE TREND
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📈 Performance Trend")

tr1,tr2,tr3 = st.columns([2,2,2])
with tr1: axis_mode    = st.radio("Sumbu X",["Bulan & Tahun","Tahun"],horizontal=True)
with tr2: trend_metric = st.radio("Metrik",["Total ACTUAL","Outlet Coverage","Dropsize"],horizontal=True)
with tr3: color_by     = st.selectbox("Pecah warna per",
              ["(tidak ada)","RGM","SUB REGION","BRANCH","BRAND","SUB BRAND","SUBBRAND LIST"])

if trend_metric=="Total ACTUAL":    y_col,y_label = "total_actual","Total ACTUAL"
elif trend_metric=="Outlet Coverage": y_col,y_label = "outlet_coverage","Outlet Coverage"
else:                                y_col,y_label = "dropsize","Dropsize (Actual/OC)"

def month_case_sql(): return month_to_num_sql()

@st.cache_data(show_spinner=False)
def get_trend_base(where, axis, group_col=None):
    mn = month_case_sql()
    if group_col=="BRANCH":
        grp_expr = "CASE WHEN POSITION('#' IN \"BRANCH\")>0 THEN SPLIT_PART(\"BRANCH\",'#',2) ELSE \"BRANCH\" END"
        grp_sel = f", {grp_expr} AS kategori"; grp_by = f", {grp_expr}"
    elif group_col=="BRANCH_RAW":
        grp_sel = ', "BRANCH" AS kategori, "SUB REGION" AS sr_raw'
        grp_by  = ', "BRANCH", "SUB REGION"'
    elif group_col:
        grp_sel = f', "{group_col}" AS kategori'; grp_by = f', "{group_col}"'
    else:
        grp_sel = ""; grp_by = ""

    if axis=="Bulan & Tahun":
        df = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS tahun,
                   "MONTH TRX" AS bulan_str, {mn} AS bulan_num {grp_sel},
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                   COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
            GROUP BY tahun,bulan_str,bulan_num {grp_by} ORDER BY tahun,bulan_num
        """).df()
        df["periode"]  = df["bulan_str"]+" "+df["tahun"]
        df["sort_key"] = df["tahun"].astype(str)+df["bulan_num"].astype(str).str.zfill(2)
        df = df.sort_values("sort_key")
        df["dropsize"] = df["total_actual"]/df["outlet_coverage"].replace(0,float("nan"))
        x_order = list(dict.fromkeys(df["periode"].tolist()))
    else:
        df = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS periode {grp_sel},
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                   COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
            GROUP BY periode {grp_by} ORDER BY periode
        """).df()
        df["dropsize"] = df["total_actual"]/df["outlet_coverage"].replace(0,float("nan"))
        x_order = sorted(df["periode"].unique().tolist())
    return df, x_order

@st.cache_data(show_spinner=False)
def get_trend_exact(where, axis, grp_col, case_dict):
    mn = month_case_sql()
    cases_sql = "\n".join(f"WHEN \"{c}\" = '{sql_esc(k)}' THEN '{sql_esc(v)}'"
                          for (c,k),v in case_dict.items())
    dim_expr = f"CASE {cases_sql} ELSE 'Other' END"
    if axis=="Bulan & Tahun":
        df = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS tahun,
                   "MONTH TRX" AS bulan_str, {mn} AS bulan_num,
                   {dim_expr} AS kategori,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                   COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
            GROUP BY tahun,bulan_str,bulan_num,kategori ORDER BY tahun,bulan_num
        """).df()
        df["periode"]  = df["bulan_str"]+" "+df["tahun"]
        df["sort_key"] = df["tahun"].astype(str)+df["bulan_num"].astype(str).str.zfill(2)
        df = df.sort_values("sort_key")
        df["dropsize"] = df["total_actual"]/df["outlet_coverage"].replace(0,float("nan"))
        x_order = list(dict.fromkeys(df["periode"].tolist()))
    else:
        df = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS periode,
                   {dim_expr} AS kategori,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                   COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
            GROUP BY periode,kategori ORDER BY periode
        """).df()
        df["dropsize"] = df["total_actual"]/df["outlet_coverage"].replace(0,float("nan"))
        x_order = sorted(df["periode"].unique().tolist())
    return df, x_order

with st.spinner("Memuat tren..."):
    try:
        if color_by in ("BRAND","SUB BRAND"):
            mapping = df_meta[["SUBBRAND LIST",color_by]].drop_duplicates()
            case_dict = {("SUBBRAND LIST",r["SUBBRAND LIST"]):r[color_by] for _,r in mapping.iterrows()}
            df_tr, x_order = get_trend_exact(WHERE, axis_mode, color_by, case_dict)
            color_col = "kategori"
        elif color_by=="BRANCH":
            df_tr, x_order = get_trend_base(WHERE, axis_mode, "BRANCH")
            color_col = "kategori"
        elif color_by=="RGM":
            case_dict = {("SUB REGION",sr)+"#"+"BRANCH"+"#"+br: rgm
                         for (sr,br),rgm in RGM_DICT.items()}
            # Build proper CASE WHEN (SR,BR) → RGM
            mn = month_case_sql()
            cases_sql = "\n".join(
                f"WHEN \"SUB REGION\"='{sql_esc(sr)}' AND \"BRANCH\"='{sql_esc(br)}' THEN '{sql_esc(rgm)}'"
                for (sr,br),rgm in RGM_DICT.items()
            )
            dim_expr = f"CASE {cases_sql} ELSE 'LAINNYA' END"
            if axis_mode=="Bulan & Tahun":
                df_tr = duckdb.sql(f"""
                    SELECT CAST("YEAR TRX" AS VARCHAR) AS tahun,
                           "MONTH TRX" AS bulan_str, {mn} AS bulan_num,
                           {dim_expr} AS kategori,
                           SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                           COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
                    FROM read_parquet('{DATA_PATH}',union_by_name=True) {WHERE}
                    GROUP BY tahun,bulan_str,bulan_num,kategori ORDER BY tahun,bulan_num
                """).df()
                df_tr["periode"]  = df_tr["bulan_str"]+" "+df_tr["tahun"]
                df_tr["sort_key"] = df_tr["tahun"].astype(str)+df_tr["bulan_num"].astype(str).str.zfill(2)
                df_tr = df_tr.sort_values("sort_key")
                x_order = list(dict.fromkeys(df_tr["periode"].tolist()))
            else:
                df_tr = duckdb.sql(f"""
                    SELECT CAST("YEAR TRX" AS VARCHAR) AS periode,
                           {dim_expr} AS kategori,
                           SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                           COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage
                    FROM read_parquet('{DATA_PATH}',union_by_name=True) {WHERE}
                    GROUP BY periode,kategori ORDER BY periode
                """).df()
                x_order = sorted(df_tr["periode"].unique().tolist())
            df_tr["dropsize"] = df_tr["total_actual"]/df_tr["outlet_coverage"].replace(0,float("nan"))
            color_col = "kategori"
        elif color_by!="(tidak ada)":
            df_tr, x_order = get_trend_base(WHERE, axis_mode, color_by)
            color_col = "kategori"
        else:
            df_tr, x_order = get_trend_base(WHERE, axis_mode)
            color_col = None

        df_tr["periode"] = pd.Categorical(df_tr["periode"], categories=x_order, ordered=True)
        df_tr = df_tr.sort_values("periode")
        fig_line = px.line(df_tr, x="periode", y=y_col, color=color_col,
                           markers=True,
                           labels={"periode":axis_mode,y_col:y_label,"kategori":color_by},
                           height=420, category_orders={"periode":x_order})
        fig_line.update_xaxes(tickangle=-45)
        fig_line.update_layout(hovermode="x unified",
                               legend=dict(orientation="v",yanchor="middle",y=0.5,xanchor="left",x=1.01))
        st.plotly_chart(fig_line, use_container_width=True)

        # Tabel pivot di bawah chart
        pv_agg = "mean" if y_col=="dropsize" else "sum"
        if color_col:
            pivot = df_tr.pivot_table(index=color_col,columns="periode",values=y_col,aggfunc=pv_agg)
        else:
            pivot = df_tr.set_index("periode")[[y_col]].T
            pivot.index = [y_label]
        pivot = pivot.fillna(0)
        pivot = pivot[[c for c in x_order if c in pivot.columns]]
        fmt = "{:,.2f}" if y_col=="dropsize" else "{:,.0f}"
        st.dataframe(pivot.style.format(fmt), use_container_width=True, height=200)
    except Exception as e:
        st.error(f"❌ {e}")

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 3. YTD VOLUME PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 YTD Volume Performance")
st.caption(f"YTD s/d **{MONTH_ORDER[ytd_max_month_n-1]}** (bulan max di tahun {latest_year})")

@st.cache_data(show_spinner=False)
def get_ytd(dim_col, where_no_year, ytd_max):
    mn = month_to_num_sql()
    if dim_col in ("BRAND","SUB BRAND"):
        df = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS tahun, "SUBBRAND LIST",
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual
            FROM read_parquet('{DATA_PATH}',union_by_name=True)
            {where_no_year} AND ({mn})<={ytd_max}
            GROUP BY tahun,"SUBBRAND LIST"
        """).df()
        df = df.merge(df_meta[["SUBBRAND LIST","SUB BRAND","BRAND"]],on="SUBBRAND LIST",how="left")
        r = df.groupby(["tahun",dim_col],as_index=False)["total_actual"].sum()
        r = r.rename(columns={dim_col:"dimensi"})
    else:
        r = duckdb.sql(f"""
            SELECT CAST("YEAR TRX" AS VARCHAR) AS tahun,
                   "{dim_col}" AS dimensi,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual
            FROM read_parquet('{DATA_PATH}',union_by_name=True)
            {where_no_year} AND ({mn})<={ytd_max}
            GROUP BY tahun,"{dim_col}"
        """).df()
    return r

def render_ytd(dim_col):
    df_ytd = get_ytd(dim_col, WHERE_NO_YEAR, ytd_max_month_n)
    if df_ytd.empty: st.info("Tidak ada data."); return
    years = sorted(df_ytd["tahun"].unique().tolist())
    dims  = df_ytd.groupby("dimensi")["total_actual"].sum().sort_values(ascending=False).index.tolist()
    pivot = df_ytd.pivot_table(index="dimensi",columns="tahun",values="total_actual",aggfunc="sum").fillna(0)
    pivot = pivot.reindex(dims)
    rows  = []
    for dim in dims:
        row = {"Dimensi":dim}
        for yr in years: row[f"YTD {yr}"] = pivot.loc[dim,yr] if yr in pivot.columns else 0
        for i in range(1,len(years)):
            p,c = years[i-1],years[i]
            vp  = pivot.loc[dim,p] if p in pivot.columns else 0
            vc  = pivot.loc[dim,c] if c in pivot.columns else 0
            g   = (vc/vp-1) if vp!=0 else None
            row[f"Growth {p}→{c}"] = g
        rows.append(row)
    df_g = pd.DataFrame(rows).set_index("Dimensi")
    fig = go.Figure()
    colors = px.colors.qualitative.Set2
    ytd_cols = [c for c in df_g.columns if c.startswith("YTD")]
    for i,col in enumerate(ytd_cols):
        fig.add_trace(go.Bar(name=col.replace("YTD ",""),x=df_g.index.tolist(),
                             y=df_g[col].tolist(),marker_color=colors[i%len(colors)],
                             text=[f"{v:,.0f}" for v in df_g[col].tolist()],textposition="outside"))
    fig.update_layout(barmode="group",height=420,hovermode="x unified",
                      legend=dict(orientation="h",y=1.02),xaxis_title=dim_col,yaxis_title="Total ACTUAL YTD")
    st.plotly_chart(fig, use_container_width=True)
    gc = [c for c in df_g.columns if c.startswith("Growth")]
    df_show = df_g.copy()
    for c in gc:
        df_show[c] = df_show[c].apply(lambda v: f"{'▲' if v and v>=0 else '▼'} {abs(v):.1%}" if v is not None and not pd.isna(v) else "N/A")
    st.dataframe(df_show.style.format({c:"{:,.0f}" for c in ytd_cols}), use_container_width=True, height=260)

ytd_tabs = st.tabs(["Sub Region","Brand","Sub Brand"])
dim_map  = {"Sub Region":"SUB REGION","Brand":"BRAND","Sub Brand":"SUB BRAND"}
for tab,label in zip(ytd_tabs,["Sub Region","Brand","Sub Brand"]):
    with tab:
        with st.spinner(f"Memuat YTD {label}..."): render_ytd(dim_map[label])

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 4. OUTLET COVERAGE
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🎯 Outlet Coverage")

@st.cache_data(show_spinner=False)
def get_cov_raw(where):
    return duckdb.sql(f"""
        SELECT "SUB REGION" AS sub_region, "SUBBRAND LIST" AS subbrand_list,
               COUNT(DISTINCT "ACCOUNT COMPLETE") AS outlet_coverage,
               SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "SUB REGION","SUBBRAND LIST"
    """).df()

def render_cov(df_plot, x_col, label):
    if df_plot.empty: st.info("Tidak ada data."); return
    df_agg = df_plot.groupby(x_col,as_index=False).agg(
        outlet_coverage=("outlet_coverage","sum"),total_actual=("total_actual","sum")
    ).sort_values("outlet_coverage",ascending=False)
    fig = px.bar(df_agg,x=x_col,y="outlet_coverage",color="outlet_coverage",
                 color_continuous_scale="Blues",text="outlet_coverage",height=400,
                 labels={x_col:label,"outlet_coverage":"Outlet Coverage"})
    fig.update_traces(texttemplate="%{text:,}",textposition="outside")
    fig.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_agg.rename(columns={x_col:"dimensi"}).style.format(
        {"outlet_coverage":"{:,}","total_actual":"{:,.0f}"}), use_container_width=True, height=220)

with st.spinner("Memuat coverage..."):
    df_cov = get_cov_raw(WHERE)
    df_cov = df_cov.merge(df_meta[["SUBBRAND LIST","SUB BRAND","BRAND"]],
                          left_on="subbrand_list",right_on="SUBBRAND LIST",how="left")

for tab,col in zip(st.tabs(["Sub Region","Brand","Sub Brand"]),
                   ["sub_region","BRAND","SUB BRAND"]):
    with tab: render_cov(df_cov, col, col.replace("_"," ").title())

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 5. VOLUME PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 Volume Performance by Dimension")

@st.cache_data(show_spinner=False)
def get_actual_by(dim_col, where, topn):
    return duckdb.sql(f"""
        SELECT "{dim_col}" AS dimensi,
               SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
               COUNT(DISTINCT "ACCOUNT COMPLETE") AS unique_account
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "{dim_col}" ORDER BY total_actual DESC LIMIT {topn}
    """).df()

dim_tabs = st.tabs(["Sub Region","Branch","Brand","Sub Brand","Subbrand List","Item"])
dim_cfgs = [("SUB REGION",False),("BRANCH",False),("BRAND",True),
            ("SUB BRAND",True),("SUBBRAND LIST",False),("ITEM DESCRIPTION",False)]
for tab,(col,derived) in zip(dim_tabs,dim_cfgs):
    with tab:
        topn = st.slider("Top N",5,50,25,key=f"tn_{col}")
        with st.spinner(f"Memuat {col}..."):
            if derived:
                raw = duckdb.sql(f"""
                    SELECT "SUBBRAND LIST",
                           SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                           COUNT(DISTINCT "ACCOUNT COMPLETE") AS unique_account
                    FROM read_parquet('{DATA_PATH}',union_by_name=True) {WHERE}
                    GROUP BY "SUBBRAND LIST"
                """).df()
                raw = raw.merge(df_meta[["SUBBRAND LIST","SUB BRAND","BRAND"]],on="SUBBRAND LIST",how="left")
                df_d = raw.groupby(col,as_index=False).agg(
                    total_actual=("total_actual","sum"),unique_account=("unique_account","sum")
                ).sort_values("total_actual",ascending=False).head(topn)
                df_d.columns = ["dimensi","total_actual","unique_account"]
            else:
                df_d = get_actual_by(col, WHERE, topn)
        if not df_d.empty:
            fig_d = px.bar(df_d,x="total_actual",y="dimensi",orientation="h",
                           color="total_actual",color_continuous_scale="Teal",
                           labels={"dimensi":col,"total_actual":"Total ACTUAL"},
                           height=max(360,len(df_d)*30))
            fig_d.update_layout(yaxis={"categoryorder":"total ascending"},coloraxis_showscale=False)
            st.plotly_chart(fig_d, use_container_width=True)
            st.dataframe(df_d.style.format({"total_actual":"{:,.0f}","unique_account":"{:,}"}),
                         use_container_width=True, height=240)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 6. SHARE OF TOTAL VOLUME
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🥧 Share of Total Volume")
pie_dim = st.radio("Lihat kontribusi per",["Sub Region","Brand","Sub Brand","Subbrand List"],horizontal=True)

@st.cache_data(show_spinner=False)
def get_share_raw(where):
    return duckdb.sql(f"""
        SELECT "SUB REGION","SUBBRAND LIST",SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual
        FROM read_parquet('{DATA_PATH}',union_by_name=True) {where}
        GROUP BY "SUB REGION","SUBBRAND LIST"
    """).df()

with st.spinner("Memuat share..."):
    df_sh = get_share_raw(WHERE)
    df_sh = df_sh.merge(df_meta[["SUBBRAND LIST","SUB BRAND","BRAND","CATEGORY"]],on="SUBBRAND LIST",how="left")

if pie_dim=="Sub Region":
    df_p = df_sh.groupby("SUB REGION",as_index=False)["total_actual"].sum()
    df_p.columns = ["dimensi","total_actual"]
    st.plotly_chart(px.pie(df_p,names="dimensi",values="total_actual",hole=0.35,height=480).update_traces(
        textposition="inside",textinfo="percent+label"), use_container_width=True)
elif pie_dim=="Brand":
    df_br = df_sh.groupby("BRAND",as_index=False)["total_actual"].sum()
    cl,cr = st.columns(2)
    with cl:
        st.markdown("**Total Market**")
        st.plotly_chart(px.pie(df_br,names="BRAND",values="total_actual",hole=0.35,height=380).update_traces(
            textposition="inside",textinfo="percent+label"), use_container_width=True)
    with cr:
        st.markdown("**Per Kategori**")
        for cat in df_sh.groupby("CATEGORY")["total_actual"].sum().sort_values(ascending=False).index:
            df_cb = df_sh[df_sh["CATEGORY"]==cat].groupby("BRAND",as_index=False)["total_actual"].sum()
            if df_cb.empty: continue
            st.markdown(f"*{cat}*")
            st.plotly_chart(px.pie(df_cb,names="BRAND",values="total_actual",hole=0.3,height=280).update_traces(
                textposition="inside",textinfo="percent+label").update_layout(margin=dict(t=10,b=10,l=10,r=10),
                legend=dict(orientation="h",y=-0.2)), use_container_width=True)
elif pie_dim=="Sub Brand":
    df_sb = df_sh.groupby("SUB BRAND",as_index=False)["total_actual"].sum()
    cl,cr = st.columns(2)
    with cl:
        st.markdown("**Sub Brand Total Market**")
        st.plotly_chart(px.pie(df_sb.head(15),names="SUB BRAND",values="total_actual",hole=0.35,height=400).update_traces(
            textposition="inside",textinfo="percent+label"), use_container_width=True)
    with cr:
        st.markdown("**Portfolio per Brand**")
        for br in df_sh.groupby("BRAND")["total_actual"].sum().sort_values(ascending=False).index:
            df_bsb = df_sh[df_sh["BRAND"]==br].groupby("SUB BRAND",as_index=False)["total_actual"].sum()
            if df_bsb.empty: continue
            st.markdown(f"*{br}*")
            st.plotly_chart(px.pie(df_bsb,names="SUB BRAND",values="total_actual",hole=0.3,height=260).update_traces(
                textposition="inside",textinfo="percent+label").update_layout(margin=dict(t=10,b=10,l=10,r=10),
                legend=dict(orientation="h",y=-0.25)), use_container_width=True)
else:
    df_sl = df_sh.groupby("SUBBRAND LIST",as_index=False)["total_actual"].sum()
    cl,cr = st.columns(2)
    with cl:
        st.markdown("**Top 15 Subbrand List**")
        st.plotly_chart(px.pie(df_sl.sort_values("total_actual",ascending=False).head(15),
                               names="SUBBRAND LIST",values="total_actual",hole=0.35,height=420).update_traces(
            textposition="inside",textinfo="percent+label"), use_container_width=True)
    with cr:
        st.markdown("**Per Sub Brand**")
        for sb in df_sh.groupby("SUB BRAND")["total_actual"].sum().sort_values(ascending=False).index[:8]:
            df_ssb = df_sh[df_sh["SUB BRAND"]==sb].groupby("SUBBRAND LIST",as_index=False)["total_actual"].sum()
            if df_ssb.empty: continue
            st.markdown(f"*{sb}*")
            st.plotly_chart(px.pie(df_ssb,names="SUBBRAND LIST",values="total_actual",hole=0.3,height=260).update_traces(
                textposition="inside",textinfo="percent+label").update_layout(margin=dict(t=10,b=10,l=10,r=10),
                legend=dict(orientation="h",y=-0.25)), use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# 7. EXPORT PIVOT
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("⬇️ Export Pivot Table")
if st.button("Generate & Download Excel"):
    with st.spinner("Membuat pivot..."):
        mn = month_to_num_sql()
        df_exp = duckdb.sql(f"""
            SELECT "SUB REGION" AS sub_region,
                   CASE WHEN POSITION('#' IN "BRANCH")>0 THEN SPLIT_PART("BRANCH",'#',2) ELSE "BRANCH" END AS branch,
                   "SUBBRAND LIST" AS subbrand_list,
                   CAST("YEAR TRX" AS VARCHAR) AS tahun,
                   "MONTH TRX" AS bulan, {mn} AS bulan_num,
                   SUM(CAST("ACTUAL" AS DOUBLE)) AS total_actual,
                   COUNT(DISTINCT "ACCOUNT COMPLETE") AS oc
            FROM read_parquet('{DATA_PATH}',union_by_name=True) {WHERE}
            GROUP BY 1,2,3,4,5,6 ORDER BY 4,6
        """).df()
        df_exp = df_exp.merge(df_meta[["SUBBRAND LIST","SUB BRAND","BRAND"]],
                              left_on="subbrand_list",right_on="SUBBRAND LIST",how="left")
        df_exp["periode"]  = df_exp["bulan"]+" "+df_exp["tahun"]
        df_exp["dropsize"] = df_exp["total_actual"]/df_exp["oc"].replace(0,float("nan"))
        ROWS   = ["sub_region","branch","BRAND","SUB BRAND","subbrand_list"]
        PERIOD = df_exp.sort_values(["tahun","bulan_num"])["periode"].drop_duplicates().tolist()
        pv_a   = df_exp.pivot_table(index=ROWS,columns="periode",values="total_actual",aggfunc="sum").reindex(columns=PERIOD).fillna(0)
        pv_oc  = df_exp.pivot_table(index=ROWS,columns="periode",values="oc",aggfunc="sum").reindex(columns=PERIOD).fillna(0)
        pv_ds  = pv_a/pv_oc.replace(0,float("nan"))

        def add_level(pv, name):
            pv = pv.copy()
            pv.columns = pd.MultiIndex.from_tuples(
                [(name,c) for c in pv.columns], names=["Metrik","Periode"])
            return pv

        df_final = pd.concat([add_level(pv_a,"ACTUAL"),add_level(pv_oc,"OC"),add_level(pv_ds,"DROPSIZE")],axis=1).fillna(0)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf,engine="openpyxl") as w:
            df_final.to_excel(w,sheet_name="Pivot")
        buf.seek(0)
    st.download_button("📥 Download Excel", data=buf, file_name="pivot_fmcg.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("🔍 Preview data (500 baris)"):
    @st.cache_data(show_spinner=False)
    def get_sample(where):
        return duckdb.sql(f"SELECT * FROM read_parquet('{DATA_PATH}',union_by_name=True) {where} LIMIT 500").df()
    st.dataframe(get_sample(WHERE), use_container_width=True, height=380)
