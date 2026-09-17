-- NEXUS mitigation comparison engine.
-- Compares transparent alternatives after a supplier disruption.
-- It does not declare a universal winner; it exposes cost/protection trade-offs.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COMPARISON AS
WITH
parameters AS (
    SELECT
        'SUP-001'::VARCHAR AS failed_supplier_id,
        14::NUMBER AS duration_days
),

failed_parts AS (
    SELECT DISTINCT sp.part_id
    FROM RAW.SUPPLIER_PARTS sp
    CROSS JOIN parameters x
    WHERE sp.supplier_id = x.failed_supplier_id
      AND sp.qualification_status = 'QUALIFIED'
),

exposed_orders AS (
    SELECT DISTINCT
        o.order_id,
        o.customer_id,
        o.product_id,
        o.plant_id,
        o.quantity,
        o.order_value
    FROM RAW.ORDERS o
    JOIN RAW.PRODUCT_PARTS pp ON pp.product_id = o.product_id
    JOIN failed_parts fp ON fp.part_id = pp.part_id
),

base AS (
    SELECT
        COUNT(DISTINCT order_id) AS exposed_orders,
        COUNT(DISTINCT customer_id) AS exposed_customers,
        COALESCE(SUM(order_value),0) AS exposed_revenue
    FROM exposed_orders
),

alternate_capacity AS (
    SELECT
        fp.part_id,
        SUM(q.max_daily_capacity_units) AS alternate_capacity
    FROM failed_parts fp
    JOIN ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS q
      ON q.part_id = fp.part_id
    CROSS JOIN parameters x
    WHERE q.supplier_id <> x.failed_supplier_id
    GROUP BY fp.part_id
),

alternate AS (
    SELECT
        'ALTERNATE_SUPPLIER' AS mitigation_type,
        COALESCE(SUM(ac.alternate_capacity),0) AS available_capacity,
        COALESCE(SUM(ac.alternate_capacity),0) * 14 AS available_units,
        COALESCE(SUM(q.unit_cost * q.max_daily_capacity_units * 14),0) AS incremental_cost
    FROM alternate_capacity ac
    JOIN ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS q ON q.part_id = ac.part_id
    CROSS JOIN parameters x
    WHERE q.supplier_id <> x.failed_supplier_id
),

expedite AS (
    SELECT
        'EXPEDITE_SHIPMENT' AS mitigation_type,
        COALESCE(SUM(sh.quantity),0) AS available_capacity,
        COALESCE(SUM(sh.quantity),0) AS available_units,
        COALESCE(SUM(sh.quantity * p.unit_cost * 0.25),0) AS incremental_cost
    FROM RAW.SHIPMENTS sh
    JOIN failed_parts fp ON fp.part_id = sh.part_id
    JOIN RAW.PARTS p ON p.part_id = sh.part_id
    WHERE sh.status IN ('IN_TRANSIT','DELAYED')
),

reallocation AS (
    SELECT
        'INVENTORY_REALLOCATION' AS mitigation_type,
        COALESCE(SUM(GREATEST(i.on_hand_units - i.safety_stock_units,0)),0) AS available_capacity,
        COALESCE(SUM(GREATEST(i.on_hand_units - i.safety_stock_units,0)),0) AS available_units,
        0::NUMBER(18,2) AS incremental_cost
    FROM RAW.INVENTORY i
    JOIN failed_parts fp ON fp.part_id = i.part_id
),

no_action AS (
    SELECT
        'NO_ACTION' AS mitigation_type,
        0::NUMBER AS available_capacity,
        0::NUMBER AS available_units,
        0::NUMBER(18,2) AS incremental_cost
),

options AS (
    SELECT * FROM no_action
    UNION ALL SELECT * FROM alternate
    UNION ALL SELECT * FROM expedite
    UNION ALL SELECT * FROM reallocation
)

SELECT
    o.mitigation_type,
    o.available_capacity,
    o.available_units,
    o.incremental_cost,
    b.exposed_orders,
    b.exposed_customers,
    b.exposed_revenue,
    LEAST(
        b.exposed_revenue,
        b.exposed_revenue * (o.available_units / NULLIF(o.available_units + 1,0))
    ) AS modeled_revenue_protected,
    GREATEST(
        b.exposed_revenue - LEAST(
            b.exposed_revenue,
            b.exposed_revenue * (o.available_units / NULLIF(o.available_units + 1,0))
        ),
        0
    ) AS modeled_remaining_revenue_exposure,
    'Modeled estimate based on available capacity/inventory; validate operational constraints before execution.' AS calculation_note
FROM options o
CROSS JOIN base b;

-- The UI/agent should present this as a comparison table and explain that
-- values are modeled estimates, not executed actions or observed outcomes.
