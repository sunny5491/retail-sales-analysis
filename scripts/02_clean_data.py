"""
Step 2: Clean the raw retail dataset and produce a data-quality report.

Every fix is logged so the cleaning is auditable (JD: "monitor data quality,
identify inconsistencies, support validation and cleansing").
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "retail_sales_raw.csv"
CLEAN = ROOT / "data" / "cleaned" / "retail_sales_clean.csv"
REPORT = ROOT / "data" / "cleaned" / "data_quality_report.md"

log = []          # (issue, rows affected, action taken)

def note(issue, n, action):
    log.append((issue, int(n), action))
    print(f"  - {issue:<45} {n:>6} rows  -> {action}")

print("Loading raw data ...")
df = pd.read_csv(RAW)
raw_rows = len(df)
print(f"  raw shape: {df.shape}\n")

# ---------- 1. exact duplicates ----------
n_dup = df.duplicated().sum()
df = df.drop_duplicates().reset_index(drop=True)
note("Exact duplicate rows", n_dup, "dropped")

# ---------- 2. mixed date formats ----------
def parse_dates(s: pd.Series) -> pd.Series:
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")       # try ISO first
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")       # then DD/MM/YYYY
    return iso.fillna(dmy)

n_non_iso = (~df["order_date"].str.match(r"^\d{4}-\d{2}-\d{2}$")).sum()
df["order_date"] = parse_dates(df["order_date"])
df["ship_date"] = parse_dates(df["ship_date"])
note("order_date in DD/MM/YYYY format", n_non_iso, "parsed to datetime")
assert df["order_date"].isna().sum() == 0, "unparsed dates remain"

# ---------- 3. category text inconsistencies ----------
n_bad = (df["category"] != df["category"].str.strip().str.title()).sum()
df["category"] = df["category"].str.strip().str.title()
note("category casing / whitespace", n_bad, "strip + title-case")
assert set(df["category"].unique()) == {"Furniture", "Office Supplies", "Technology"}

# ---------- 4. sales stored as currency text ----------
sales_txt = df["sales"].astype(str)
n_cur = sales_txt.str.contains(r"[$,]").sum()
df["sales"] = pd.to_numeric(sales_txt.str.replace(r"[$,]", "", regex=True), errors="coerce")
note("sales stored as '$1,234.50' text", n_cur, "stripped symbols -> float")
assert df["sales"].isna().sum() == 0

# ---------- 5. negative quantities (data-entry sign errors) ----------
n_neg = (df["quantity"] < 0).sum()
df["quantity"] = df["quantity"].abs()
note("negative quantity", n_neg, "abs() - treated as sign typo")

# ---------- 6. missing values ----------
# segment & city are customer attributes -> fill from the same customer's other orders
for col in ["segment", "city"]:
    n_missing = df[col].isna().sum()
    lookup = df.dropna(subset=[col]).groupby("customer_id")[col].agg(lambda s: s.mode().iloc[0])
    df[col] = df[col].fillna(df["customer_id"].map(lookup))
    still = df[col].isna().sum()
    df[col] = df[col].fillna("Unknown")
    note(f"missing {col}", n_missing, f"filled from same customer ({n_missing - still}), 'Unknown' ({still})")

# ship_mode: infer from shipping duration, fallback to mode
n_missing = df["ship_mode"].isna().sum()
ship_days = (df["ship_date"] - df["order_date"]).dt.days
inferred = pd.cut(ship_days, bins=[-1, 1, 3, 5, 99],
                  labels=["Same Day", "First Class", "Second Class", "Standard Class"]).astype(str)
df["ship_mode"] = df["ship_mode"].fillna(inferred)
note("missing ship_mode", n_missing, "inferred from ship_date - order_date")

# ---------- 7. derived columns for analysis ----------
df["ship_days"] = (df["ship_date"] - df["order_date"]).dt.days
df["year"] = df["order_date"].dt.year
df["month"] = df["order_date"].dt.month
df["month_name"] = df["order_date"].dt.strftime("%b")
df["quarter"] = "Q" + df["order_date"].dt.quarter.astype(str)
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
df["profit_margin"] = (df["profit"] / df["sales"]).round(4)
df["is_profitable"] = df["profit"] > 0

# ---------- 8. final validation ----------
assert df["order_id"].is_unique, "order_id must be unique after de-dup"
assert (df["quantity"] > 0).all()
assert (df["sales"] > 0).all()
assert (df["ship_days"] >= 0).all()
assert df.isna().sum().sum() == 0, "nulls remain"

# ---------- save ----------
col_order = ["order_id", "order_date", "ship_date", "ship_days", "ship_mode", "year", "quarter",
             "month", "month_name", "year_month", "customer_id", "customer_name", "segment",
             "region", "state", "city", "category", "sub_category", "product_name", "quantity",
             "unit_price", "discount", "sales", "profit", "profit_margin", "is_profitable",
             "payment_method"]
df = df[col_order].sort_values("order_date").reset_index(drop=True)
CLEAN.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(CLEAN, index=False)

# ---------- data quality report ----------
lines = [
    "# Data Quality Report",
    "",
    f"- Raw rows: **{raw_rows:,}**  ->  Clean rows: **{len(df):,}**",
    f"- Columns: {df.shape[1]} (8 derived columns added)",
    f"- Date range: {df['order_date'].min().date()} to {df['order_date'].max().date()}",
    "",
    "| Issue found | Rows affected | Action taken |",
    "|---|---:|---|",
    *[f"| {i} | {n:,} | {a} |" for i, n, a in log],
    "",
    "## Post-clean validation",
    "- order_id unique: PASS",
    "- no nulls: PASS",
    "- quantity > 0, sales > 0, ship_days >= 0: PASS",
    "- category limited to 3 canonical values: PASS",
]
REPORT.write_text("\n".join(lines))
print(f"\nClean data -> {CLEAN}\nReport     -> {REPORT}")
print(f"\nFinal shape: {df.shape}")
