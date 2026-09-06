"""Step 3b: Load cleaned CSV into a normalized SQLite database (3 tables)."""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "cleaned" / "retail_sales_clean.csv"
DB = ROOT / "data" / "retail_sales.db"
SCHEMA = ROOT / "sql" / "01_schema.sql"

df = pd.read_csv(CLEAN)

customers = (df[["customer_id", "customer_name", "segment", "region", "state", "city"]]
             .drop_duplicates("customer_id").reset_index(drop=True))

products = (df[["product_name", "sub_category", "category"]]
            .drop_duplicates().sort_values(["category", "sub_category", "product_name"])
            .reset_index(drop=True))
products.insert(0, "product_id", range(1, len(products) + 1))

orders = df.merge(products, on=["product_name", "sub_category", "category"])[
    ["order_id", "order_date", "ship_date", "ship_mode", "customer_id", "product_id",
     "quantity", "unit_price", "discount", "sales", "profit", "payment_method"]]

DB.unlink(missing_ok=True)
with sqlite3.connect(DB) as con:
    con.executescript(SCHEMA.read_text())
    customers.to_sql("customers", con, if_exists="append", index=False)
    products.to_sql("products", con, if_exists="append", index=False)
    orders.to_sql("orders", con, if_exists="append", index=False)
    for t in ["customers", "products", "orders"]:
        print(f"{t:<10} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>6} rows")
print(f"\nDatabase -> {DB}")
