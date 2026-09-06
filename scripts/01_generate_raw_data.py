"""
Step 1: Generate a realistic (but intentionally messy) retail sales dataset.

Why synthetic?  Real Superstore-style data needs a Kaggle login. This script
creates a comparable dataset with real-world problems baked in so the cleaning
step actually has work to do:
  - mixed date formats             - inconsistent category casing / whitespace
  - missing values                 - exact duplicate rows
  - sales stored as "$1,234.50"    - negative quantities (data-entry errors)
"""
import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "retail_sales_raw.csv"
N_ORDERS = 6000
START, END = date(2024, 1, 1), date(2025, 12, 31)

# ---------- reference data ----------
REGIONS = {
    "West":    ["California", "Washington", "Oregon", "Arizona"],
    "East":    ["New York", "Pennsylvania", "Massachusetts", "New Jersey"],
    "Central": ["Texas", "Illinois", "Michigan", "Ohio"],
    "South":   ["Florida", "Georgia", "North Carolina", "Tennessee"],
}
CITIES = {
    "California": ["Los Angeles", "San Francisco", "San Diego"],
    "Washington": ["Seattle", "Spokane"], "Oregon": ["Portland"], "Arizona": ["Phoenix"],
    "New York": ["New York City", "Buffalo"], "Pennsylvania": ["Philadelphia", "Pittsburgh"],
    "Massachusetts": ["Boston"], "New Jersey": ["Newark"],
    "Texas": ["Houston", "Dallas", "Austin"], "Illinois": ["Chicago"],
    "Michigan": ["Detroit"], "Ohio": ["Columbus"],
    "Florida": ["Miami", "Orlando"], "Georgia": ["Atlanta"],
    "North Carolina": ["Charlotte"], "Tennessee": ["Nashville"],
}
# category -> sub_category -> (product names, price range, margin range)
CATALOG = {
    "Furniture": {
        "Chairs":      (["Ergonomic Office Chair", "Folding Chair", "Executive Chair"], (60, 400), (0.05, 0.20)),
        "Tables":      (["Standing Desk", "Conference Table", "Coffee Table"], (120, 900), (-0.05, 0.15)),
        "Bookcases":   (["5-Shelf Bookcase", "Corner Bookcase"], (80, 350), (-0.10, 0.12)),
    },
    "Office Supplies": {
        "Paper":       (["A4 Copy Paper 500", "Sticky Notes Pack", "Notebook Set"], (5, 40), (0.25, 0.45)),
        "Binders":     (["3-Ring Binder", "Presentation Binder"], (4, 30), (0.10, 0.35)),
        "Storage":     (["File Cabinet", "Desk Organizer", "Storage Box"], (15, 200), (0.15, 0.30)),
        "Art":         (["Marker Set", "Highlighter Pack"], (3, 25), (0.20, 0.40)),
    },
    "Technology": {
        "Phones":      (["Smartphone X", "Desk Phone", "Wireless Headset"], (50, 900), (0.10, 0.30)),
        "Accessories": (["USB-C Hub", "Wireless Mouse", "Mechanical Keyboard"], (15, 150), (0.20, 0.45)),
        "Machines":    (["Laser Printer", "Label Maker", "Document Scanner"], (100, 1500), (0.00, 0.25)),
    },
}
SEGMENTS = ["Consumer", "Corporate", "Home Office"]
SHIP_MODES = ["Standard Class", "Second Class", "First Class", "Same Day"]
PAYMENTS = ["Credit Card", "Debit Card", "PayPal", "Cash on Delivery"]
FIRST = ["Aarav", "Priya", "John", "Emily", "Michael", "Sara", "David", "Ananya", "Chris", "Nina",
         "Rahul", "Laura", "Kevin", "Meera", "Daniel", "Sofia", "Arjun", "Olivia", "James", "Isha"]
LAST = ["Sharma", "Smith", "Patel", "Johnson", "Brown", "Verma", "Williams", "Singh", "Davis", "Khan"]

# 800 customers, each with a fixed segment + home state
customers = []
for i in range(1, 801):
    region = random.choice(list(REGIONS))
    state = random.choice(REGIONS[region])
    customers.append({
        "customer_id": f"CUST-{i:04d}",
        "customer_name": f"{random.choice(FIRST)} {random.choice(LAST)}",
        "segment": random.choices(SEGMENTS, weights=[0.5, 0.3, 0.2])[0],
        "region": region, "state": state, "city": random.choice(CITIES[state]),
    })

# ---------- seasonality: more orders in Nov/Dec, fewer in Feb ----------
month_weight = {1: 0.8, 2: 0.7, 3: 0.9, 4: 0.9, 5: 1.0, 6: 1.0,
                7: 0.95, 8: 1.0, 9: 1.1, 10: 1.2, 11: 1.5, 12: 1.6}
all_days = [START + timedelta(d) for d in range((END - START).days + 1)]
day_weights = [month_weight[d.month] * (1.15 if d.year == 2025 else 1.0) for d in all_days]

rows = []
for i in range(1, N_ORDERS + 1):
    cust = random.choice(customers)
    order_date = random.choices(all_days, weights=day_weights)[0]
    ship_mode = random.choices(SHIP_MODES, weights=[0.6, 0.2, 0.15, 0.05])[0]
    ship_days = {"Standard Class": 5, "Second Class": 3, "First Class": 2, "Same Day": 0}[ship_mode]
    ship_date = order_date + timedelta(days=ship_days + random.randint(0, 2))

    category = random.choices(list(CATALOG), weights=[0.25, 0.5, 0.25])[0]
    sub_cat = random.choice(list(CATALOG[category]))
    products, (lo, hi), (m_lo, m_hi) = CATALOG[category][sub_cat]
    product = random.choice(products)

    quantity = int(np.clip(np.random.poisson(2.5) + 1, 1, 14))
    unit_price = round(random.uniform(lo, hi), 2)
    discount = random.choices([0, 0.1, 0.2, 0.3, 0.5], weights=[0.5, 0.2, 0.15, 0.1, 0.05])[0]
    sales = round(unit_price * quantity * (1 - discount), 2)
    margin = random.uniform(m_lo, m_hi) - discount * 0.6      # heavy discount kills profit
    profit = round(sales * margin, 2)

    rows.append({
        "order_id": f"ORD-{order_date.year}-{i:05d}",
        "order_date": order_date.isoformat(),
        "ship_date": ship_date.isoformat(),
        "ship_mode": ship_mode,
        **cust,
        "category": category, "sub_category": sub_cat, "product_name": product,
        "quantity": quantity, "unit_price": unit_price, "discount": discount,
        "sales": sales, "profit": profit,
        "payment_method": random.choice(PAYMENTS),
    })

df = pd.DataFrame(rows)

# ================= inject real-world messiness =================
rng = np.random.default_rng(SEED)
n = len(df)

# 1) mixed date formats in ~15% of rows  (DD/MM/YYYY instead of ISO)
idx = rng.choice(n, int(n * 0.15), replace=False)
df.loc[idx, "order_date"] = pd.to_datetime(df.loc[idx, "order_date"]).dt.strftime("%d/%m/%Y")

# 2) inconsistent casing / whitespace in category (~10%)
idx = rng.choice(n, int(n * 0.10), replace=False)
df.loc[idx, "category"] = df.loc[idx, "category"].apply(
    lambda s: random.choice([s.lower(), s.upper(), f"  {s} ", s.title()]))

# 3) sales stored as currency text in ~8% of rows  -> "$1,234.50"
df["sales"] = df["sales"].astype(object)
idx = rng.choice(n, int(n * 0.08), replace=False)
df.loc[idx, "sales"] = df.loc[idx, "sales"].apply(lambda v: f"${v:,.2f}")

# 4) missing values: segment 3%, city 2%, ship_mode 1.5%
for col, frac in [("segment", 0.03), ("city", 0.02), ("ship_mode", 0.015)]:
    idx = rng.choice(n, int(n * frac), replace=False)
    df.loc[idx, col] = np.nan

# 5) negative quantity typos (~0.5%)
idx = rng.choice(n, int(n * 0.005), replace=False)
df.loc[idx, "quantity"] = -df.loc[idx, "quantity"]

# 6) exact duplicate rows (~2%)
dups = df.sample(int(n * 0.02), random_state=SEED)
df = pd.concat([df, dups], ignore_index=True).sample(frac=1, random_state=SEED).reset_index(drop=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)
print(f"Wrote {len(df):,} rows x {df.shape[1]} cols -> {OUT}")
