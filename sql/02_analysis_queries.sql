-- Step 3c: Business analysis queries.
-- Each query is separated by a "-- name: <query_name>" marker so that
-- scripts/04_run_sql.py can run them one by one and save the results.

-- name: 01_overall_kpis
-- Headline KPIs for the whole period
SELECT
    COUNT(*)                                   AS total_orders,
    COUNT(DISTINCT customer_id)                AS unique_customers,
    ROUND(SUM(sales), 2)                       AS total_sales,
    ROUND(SUM(profit), 2)                      AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(sales), 2) AS profit_margin_pct,
    ROUND(AVG(sales), 2)                       AS avg_order_value
FROM orders;

-- name: 02_sales_by_region
-- Which regions drive revenue and which are most profitable? (JOIN + GROUP BY)
SELECT
    c.region,
    COUNT(o.order_id)                              AS orders,
    ROUND(SUM(o.sales), 2)                         AS sales,
    ROUND(SUM(o.profit), 2)                        AS profit,
    ROUND(100.0 * SUM(o.profit) / SUM(o.sales), 2) AS margin_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.region
ORDER BY sales DESC;

-- name: 03_category_subcategory_breakdown
-- Sales and profit by category and sub-category, with share of total sales
SELECT
    p.category,
    p.sub_category,
    ROUND(SUM(o.sales), 2)                                   AS sales,
    ROUND(SUM(o.profit), 2)                                  AS profit,
    ROUND(100.0 * SUM(o.sales) / (SELECT SUM(sales) FROM orders), 2) AS pct_of_total_sales
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.category, p.sub_category
ORDER BY p.category, sales DESC;

-- name: 04_monthly_sales_trend
-- Month-by-month sales with a 3-month moving average (WINDOW FUNCTION)
WITH monthly AS (
    SELECT strftime('%Y-%m', order_date) AS year_month,
           ROUND(SUM(sales), 2)          AS sales,
           ROUND(SUM(profit), 2)         AS profit,
           COUNT(*)                      AS orders
    FROM orders
    GROUP BY year_month
)
SELECT
    year_month, orders, sales, profit,
    ROUND(AVG(sales) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
        AS sales_3mo_moving_avg,
    ROUND(SUM(sales) OVER (ORDER BY year_month), 2) AS cumulative_sales
FROM monthly
ORDER BY year_month;

-- name: 05_yoy_growth_by_month
-- Year-over-year growth: 2025 vs 2024 for the same calendar month (self-join via CTE)
WITH m AS (
    SELECT CAST(strftime('%Y', order_date) AS INTEGER) AS yr,
           CAST(strftime('%m', order_date) AS INTEGER) AS mo,
           SUM(sales) AS sales
    FROM orders
    GROUP BY yr, mo
)
SELECT
    cur.mo                                                   AS month,
    ROUND(prev.sales, 2)                                     AS sales_2024,
    ROUND(cur.sales, 2)                                      AS sales_2025,
    ROUND(100.0 * (cur.sales - prev.sales) / prev.sales, 2)  AS yoy_growth_pct
FROM m cur
JOIN m prev ON prev.mo = cur.mo AND prev.yr = cur.yr - 1
WHERE cur.yr = 2025
ORDER BY cur.mo;

-- name: 06_top_10_products
-- Best-selling products by revenue, ranked with RANK()
SELECT
    RANK() OVER (ORDER BY SUM(o.sales) DESC) AS rank,
    p.product_name,
    p.category,
    SUM(o.quantity)                          AS units_sold,
    ROUND(SUM(o.sales), 2)                   AS sales,
    ROUND(SUM(o.profit), 2)                  AS profit
FROM orders o
JOIN products p ON p.product_id = o.product_id
GROUP BY p.product_id
ORDER BY sales DESC
LIMIT 10;

-- name: 07_discount_impact_on_profit
-- Does discounting hurt margin?  Bucket by discount level.
SELECT
    discount,
    COUNT(*)                                        AS orders,
    ROUND(AVG(sales), 2)                            AS avg_sales,
    ROUND(AVG(profit), 2)                           AS avg_profit,
    ROUND(100.0 * SUM(profit) / SUM(sales), 2)      AS margin_pct,
    ROUND(100.0 * SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) / COUNT(*), 1)
                                                    AS loss_making_orders_pct
FROM orders
GROUP BY discount
ORDER BY discount;

-- name: 08_top_customers
-- Top 10 customers by lifetime value with recency (days since last order)
SELECT
    c.customer_id,
    c.customer_name,
    c.segment,
    c.region,
    COUNT(o.order_id)                                        AS orders,
    ROUND(SUM(o.sales), 2)                                   AS lifetime_sales,
    ROUND(SUM(o.profit), 2)                                  AS lifetime_profit,
    MAX(o.order_date)                                        AS last_order,
    CAST(julianday('2025-12-31') - julianday(MAX(o.order_date)) AS INTEGER) AS days_since_last_order
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.customer_id
ORDER BY lifetime_sales DESC
LIMIT 10;

-- name: 09_segment_performance
-- Customer segment comparison: how much each segment buys and how often
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                         AS customers,
    COUNT(o.order_id)                                     AS orders,
    ROUND(1.0 * COUNT(o.order_id) / COUNT(DISTINCT c.customer_id), 2) AS orders_per_customer,
    ROUND(SUM(o.sales), 2)                                AS sales,
    ROUND(AVG(o.sales), 2)                                AS avg_order_value,
    ROUND(100.0 * SUM(o.profit) / SUM(o.sales), 2)        AS margin_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.segment
ORDER BY sales DESC;

-- name: 10_shipping_performance
-- Average shipping time per ship mode and whether it matches the SLA
SELECT
    ship_mode,
    COUNT(*)                                                       AS orders,
    ROUND(AVG(julianday(ship_date) - julianday(order_date)), 2)    AS avg_ship_days,
    MAX(julianday(ship_date) - julianday(order_date))              AS max_ship_days,
    ROUND(SUM(sales), 2)                                           AS sales
FROM orders
GROUP BY ship_mode
ORDER BY avg_ship_days;

-- name: 11_loss_making_subcategories
-- Which sub-categories lose money in which region? (filter with HAVING)
SELECT
    c.region,
    p.sub_category,
    COUNT(*)                 AS orders,
    ROUND(SUM(o.sales), 2)   AS sales,
    ROUND(SUM(o.profit), 2)  AS profit
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN products  p ON p.product_id  = o.product_id
GROUP BY c.region, p.sub_category
HAVING SUM(o.profit) < 0
ORDER BY profit;
