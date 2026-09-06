-- Step 3a: Normalized schema for retail_sales.db (SQLite)
-- The flat cleaned CSV is split into 3 tables so that analysis queries
-- exercise real JOINs instead of working off one wide table.

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id    TEXT PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    segment        TEXT NOT NULL,
    region         TEXT NOT NULL,
    state          TEXT NOT NULL,
    city           TEXT NOT NULL
);

CREATE TABLE products (
    product_id     INTEGER PRIMARY KEY,
    product_name   TEXT NOT NULL,
    sub_category   TEXT NOT NULL,
    category       TEXT NOT NULL,
    UNIQUE (product_name, sub_category)
);

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    order_date      DATE NOT NULL,
    ship_date       DATE NOT NULL,
    ship_mode       TEXT NOT NULL,
    customer_id     TEXT NOT NULL REFERENCES customers(customer_id),
    product_id      INTEGER NOT NULL REFERENCES products(product_id),
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      REAL NOT NULL,
    discount        REAL NOT NULL,
    sales           REAL NOT NULL,
    profit          REAL NOT NULL,
    payment_method  TEXT NOT NULL
);

CREATE INDEX idx_orders_date     ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_product  ON orders(product_id);
