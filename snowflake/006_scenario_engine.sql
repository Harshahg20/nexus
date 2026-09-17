-- NEXUS Scenario Engine: deterministic supplier failure propagation.
-- This is intentionally SQL-first so scenario results are reproducible and explainable.
-- Example:
--   SUP-001 unavailable for 14 days => 100% capacity reduction.
-- Change the values in PARAMETERS to test another supplier/duration.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE TABLE SCENARIOS.SCENARIO_RUNS (
    scenario_run_id VARCHAR PRIMARY KEY,
    scenario_type VARCHAR NOT NULL,
    target_entity_id VARCHAR NOT NULL,
    capacity_reduction_pct NUMBER(8,4),
    duration_days NUMBER(10,0),
    start_date DATE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE VIEW SCENARIOS.V_SUPPLIER_FAILURE_IMPACT AS
WITH PARAMETERS AS (
    SELECT
        'SUP-001'::VARCHAR AS supplier_id,
        100::NUMBER(8,4) AS capacity_reduction_pct,
        14::NUMBER(10,0) AS duration_days
),

supplier_parts AS (
    SELECT DISTINCT
        sp.supplier_id,
        sp.part_id
    FROM ANALYTICS.SUPPLIER_PART_DEPENDENCY sp
    CROSS JOIN PARAMETERS x
    WHERE sp.supplier_id = x.supplier_id
      AND sp.supplier_status = 'ACTIVE'
),

part_inventory AS (
    SELECT
        i.plant_id,
        i.part_id,
        i.on_hand_units,
        i.safety_stock_units,
        i.daily_consumption,
        GREATEST(i.on_hand_units - i.safety_stock_units, 0) AS usable_inventory_units
    FROM RAW.INVENTORY i
    JOIN supplier_parts sp ON sp.part_id = i.part_id
),

projected_shortage AS (
    SELECT
        pi.plant_id,
        pi.part_id,
        pi.on_hand_units,
        pi.safety_stock_units,
        pi.daily_consumption,
        pi.usable_inventory_units,
        x.duration_days,
        GREATEST(
            (pi.daily_consumption * x.duration_days) - pi.usable_inventory_units,
            0
        ) AS projected_shortage_units
    FROM part_inventory pi
    CROSS JOIN PARAMETERS x
),

affected_products AS (
    SELECT DISTINCT
        pp.product_id,
        ps.plant_id,
        ps.part_id,
        ps.projected_shortage_units
    FROM projected_shortage ps
    JOIN RAW.PRODUCT_PARTS pp ON pp.part_id = ps.part_id
    WHERE ps.projected_shortage_units > 0
),

affected_orders AS (
    SELECT DISTINCT
        o.order_id,
        o.customer_id,
        o.product_id,
        o.plant_id,
        o.quantity,
        o.order_value,
        o.due_date,
        o.priority,
        o.sla_tier
    FROM RAW.ORDERS o
    JOIN affected_products ap
      ON ap.product_id = o.product_id
     AND ap.plant_id = o.plant_id
),

summary AS (
    SELECT
        (SELECT COUNT(DISTINCT part_id) FROM projected_shortage WHERE projected_shortage_units > 0) AS affected_parts,
        (SELECT COUNT(DISTINCT plant_id) FROM projected_shortage WHERE projected_shortage_units > 0) AS affected_plants,
        (SELECT COUNT(DISTINCT order_id) FROM affected_orders) AS orders_at_risk,
        (SELECT COUNT(DISTINCT customer_id) FROM affected_orders) AS customers_exposed,
        (SELECT COALESCE(SUM(order_value),0) FROM affected_orders) AS revenue_exposure
)
SELECT
    x.supplier_id,
    x.capacity_reduction_pct,
    x.duration_days,
    s.affected_parts,
    s.affected_plants,
    s.orders_at_risk,
    s.customers_exposed,
    s.revenue_exposure
FROM PARAMETERS x
CROSS JOIN summary s;

CREATE OR REPLACE VIEW SCENARIOS.V_SUPPLIER_FAILURE_CHAIN AS
WITH PARAMETERS AS (
    SELECT 'SUP-001'::VARCHAR AS supplier_id
),
base AS (
    SELECT DISTINCT
        d.supplier_id,
        d.supplier_name,
        d.part_id,
        d.part_name,
        d.criticality,
        pp.product_id,
        pp.product_name,
        o.order_id,
        o.customer_id,
        c.customer_name,
        o.plant_id,
        pl.plant_name,
        o.quantity,
        o.order_value,
        o.sla_tier
    FROM ANALYTICS.SUPPLIER_PART_DEPENDENCY d
    JOIN RAW.PRODUCT_PARTS pp ON pp.part_id = d.part_id
    JOIN RAW.ORDERS o ON o.product_id = pp.product_id
    JOIN RAW.CUSTOMERS c ON c.customer_id = o.customer_id
    JOIN RAW.PLANTS pl ON pl.plant_id = o.plant_id
    CROSS JOIN PARAMETERS x
    WHERE d.supplier_id = x.supplier_id
)
SELECT * FROM base;

-- Reusable baseline metrics for the command center.
CREATE OR REPLACE VIEW ANALYTICS.EXECUTIVE_RISK_SUMMARY AS
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    COALESCE(SUM(order_value),0) AS total_order_value,
    COUNT(DISTINCT customer_id) AS total_customers,
    COUNT(DISTINCT product_id) AS total_products
FROM RAW.ORDERS;

-- Deterministic scenario questions:
-- 1. SELECT * FROM SCENARIOS.V_SUPPLIER_FAILURE_IMPACT;
-- 2. SELECT * FROM SCENARIOS.V_SUPPLIER_FAILURE_CHAIN;
-- These views are deliberately transparent. Every result can be traced back
-- through the supplier -> part -> product -> order -> customer relationship.
