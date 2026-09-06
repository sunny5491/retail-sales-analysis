# Data Quality Report

- Raw rows: **6,120**  ->  Clean rows: **6,000**
- Columns: 27 (8 derived columns added)
- Date range: 2024-01-01 to 2025-12-31

| Issue found | Rows affected | Action taken |
|---|---:|---|
| Exact duplicate rows | 120 | dropped |
| order_date in DD/MM/YYYY format | 900 | parsed to datetime |
| category casing / whitespace | 452 | strip + title-case |
| sales stored as '$1,234.50' text | 480 | stripped symbols -> float |
| negative quantity | 30 | abs() - treated as sign typo |
| missing segment | 180 | filled from same customer (180), 'Unknown' (0) |
| missing city | 120 | filled from same customer (120), 'Unknown' (0) |
| missing ship_mode | 90 | inferred from ship_date - order_date |

## Post-clean validation
- order_id unique: PASS
- no nulls: PASS
- quantity > 0, sales > 0, ship_days >= 0: PASS
- category limited to 3 canonical values: PASS