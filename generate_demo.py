"""
generate_demo.py
Jalankan sekali untuk membuat data dummy:
    python generate_demo.py

Output: demo_data/sales_demo.parquet (~500K baris, struktur identik data asli)
"""

import pandas as pd
import numpy as np
import random
import os
from pathlib import Path

random.seed(42)
np.random.seed(42)

# ── Dimensi dummy ─────────────────────────────────────────────────────────────
SUB_REGIONS = {
    "JAWA BARAT":  ["C11#BANDUNG","C12#TASIKMALAYA","C13#SUKABUMI",
                    "C14#CIMAREME","C16#GARUT","C17#SUBANG",
                    "C18#SUMEDANG","C40#CIANJUR","C45#BANJARAN",
                    "C46#PURWAKARTA","C55#JATIBARANG","C15#MM BANDUNG"],
    "JABOTABEK":   ["C01#JATIBARU","C02#MM JABOTABEK","C03#BEKASI",
                    "C04#PONDOK UNGU","C05#SELATAN","C06#TANGERANG",
                    "C07#SERANG","C08#BOGOR","C09#KARAWANG",
                    "C10#DAAN MOGOT","C19#PANDEGLANG","C20#DEPOK",
                    "C39#SERPONG","C43#BALARAJA","C49#TAMBUN","C50#REMPOA"],
    "JAWA TENGAH": ["C21#SEMARANG","C22#YOGYAKARTA","C23#PURWOKERTO",
                    "C24#TEGAL","C26#KUDUS","C42#SOLO","C48#CILACAP"],
    "JAWA TIMUR":  ["C25#MM JATIM","C30#SURABAYA","C31#KRIAN",
                    "C32#MALANG","C34#JEMBER","C35#KEDIRI",
                    "C47#BLITAR","C54#SURABAYA BARAT"],
    "SUMATERA":    ["C28#LAMPUNG","C33#BENGKULU","C51#MEDAN",
                    "C52#JAMBI","C53#PALEMBANG","C56#PEKANBARU"],
    "SULAWESI":    ["C71#MAKASSAR","C72#PALOPO","C99#AGEN"],
    "KALIMANTAN":  ["C57#BALIKPAPAN","C61#PONTIANAK","C99#AGEN"],
    "LUAR PULAU":  ["C41#DENPASAR"],
}

SUBBRAND_LIST = [
    # RELAXA family
    "RELAXA TWISH MINT BAG","RELAXA TWISH FRUIT BAG","RELAXA TWISH COLA BAG",
    "RELAXA CUWI MINT BAG","RELAXA CUWI FRUIT BAG",
    "RELAXA PLAY ORANGE BAG","RELAXA PLAY GRAPE BAG",
    "RELAXA ORIGINAL ROLL","RELAXA MINT ROLL","RELAXA FRUIT ROLL",
    # KAPAL API family
    "KAPAL API SPECIAL MIX BOX","KAPAL API GRANDE BOX","KAPAL API SOLID BOX",
    # ESPRESSO
    "ESPRESSO LATTE BOX","ESPRESSO AMERICANO BOX",
    # BONTEA
    "BONTEA GREEN ORIGINAL BAG","BONTEA GREEN LEMON TPL",
    # GINGERBON
    "GINGERBON ORIGINAL BAG","GINGERBON HONEY BAG",
    # BONKOPI
    "BONKOPI ORIGINAL BOX","BONKOPI LATTE BOX",
    # DELBI'S family
    "DELBI'S DELICA CHOCO DIP TIN","DELBI'S FILIPE PIZZA DUS",
    "DELBI'S BELLA BUTTER DUS",
    # LOVY
    "LOVY COOKIES CHOCO BOX","LOVY COOKIES VANILLA BOX",
    # OATBITS
    "OATBITS ORIGINAL BOX","OATBITS HONEY BOX","OATBITS CHOCO BOX",
]

MST_TYPES = ["TSRS","TSSP","TMFS","TSBP","TSES","TSSB","TESB","TESP"]
MONTHS    = ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"]

# Jumlah account per branch (realistis)
def n_accounts(branch):
    if "MM" in branch: return 15
    return random.randint(80, 350)

# ── Generate data ─────────────────────────────────────────────────────────────
print("Generating dummy data...")
rows = []
account_pool = {}  # branch → list of account IDs

for sr, branches in SUB_REGIONS.items():
    for branch in branches:
        accs = [f"ACC{sr[:3].replace(' ','')}{i:04d}"
                for i in range(n_accounts(branch))]
        account_pool[branch] = accs

YEARS = [2024, 2025, 2026]
MAX_MONTH = {2024: 12, 2025: 12, 2026: 7}   # 2026 data s/d Juli

for year in YEARS:
    print(f"  Year {year}...")
    max_m = MAX_MONTH[year]
    for month_idx in range(max_m):
        month = MONTHS[month_idx]
        # Tren: naik dari 2024 ke 2026, ada seasonal
        seasonal = 1 + 0.15 * np.sin((month_idx - 3) * np.pi / 6)
        year_growth = {2024: 1.0, 2025: 1.12, 2026: 1.08}[year]

        for sr, branches in SUB_REGIONS.items():
            for branch in branches:
                accs = account_pool[branch]
                # Tidak semua account aktif tiap bulan
                active_accs = random.sample(accs, max(1, int(len(accs) * random.uniform(0.6, 0.95))))

                for acc in active_accs:
                    # Pilih 1-3 subbrand per account per bulan
                    n_sb = random.choices([1,2,3], weights=[0.5,0.35,0.15])[0]
                    subbrands = random.sample(SUBBRAND_LIST, n_sb)

                    for sb in subbrands:
                        # Base ACTUAL tergantung sub region dan subbrand
                        base = random.randint(50, 800)
                        actual = int(base * seasonal * year_growth * random.uniform(0.7, 1.3))
                        if actual <= 0: actual = 1

                        rows.append({
                            "SUB REGION":         sr,
                            "BRANCH":             branch,
                            "MST SALESREP NUMBER": random.choice(MST_TYPES) + str(random.randint(100,999)),
                            "ACCOUNT COMPLETE":   acc,
                            "SUBBRAND LIST":      sb,
                            "ITEM DESCRIPTION":   sb + " 100G",
                            "YEAR TRX":           str(year),
                            "MONTH TRX":          month,
                            "ACTUAL":             str(actual),
                            "YEAR SOURCE_FILE":   str(year),
                            "SOURCE_SHEET":       f"{month}{str(year)[2:]}",
                        })

print(f"  Total rows: {len(rows):,}")

df = pd.DataFrame(rows)
print(f"  DataFrame shape: {df.shape}")

# Simpan ke Parquet
os.makedirs("demo_data", exist_ok=True)
df.to_parquet("demo_data/sales_demo.parquet", index=False)
print(f"\n✅ Selesai! File tersimpan di: demo_data/sales_demo.parquet")
print(f"   Size: {os.path.getsize('demo_data/sales_demo.parquet') / 1024 / 1024:.1f} MB")
print(f"   Rows: {len(df):,}")
