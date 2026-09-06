"""Step 3d: Run every query in sql/02_analysis_queries.sql and save results as CSV."""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "retail_sales.db"
QUERIES = ROOT / "sql" / "02_analysis_queries.sql"
OUT = ROOT / "sql" / "results"
OUT.mkdir(exist_ok=True)

sql_text = QUERIES.read_text()
blocks = re.split(r"^-- name: ", sql_text, flags=re.M)[1:]     # first chunk is the header comment

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 20)

with sqlite3.connect(DB) as con:
    for block in blocks:
        name, query = block.split("\n", 1)
        name = name.strip()
        df = pd.read_sql_query(query, con)
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"\n=== {name} ({len(df)} rows) ===")
        print(df.to_string(index=False, max_rows=12))
