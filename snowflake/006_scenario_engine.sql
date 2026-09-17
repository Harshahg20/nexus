-- NEXUS deterministic scenario engine
--
-- Design principle:
-- Supplier failure -> part availability -> order allocation -> customer exposure.
-- Every result is reproducible from explicit source relationships and quantities.

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

CREATE OR REPLACE VIEW SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS AS
SELECT
    'SUP-001'::VARCHAR AS failed_supplier_id,
    100::NUMBER(8,4) AS capacity_reduction_pct,
    14::NUMBER(10,0) AS duration_days,
    '2026-09-18'::DATE AS start_date;

CREATE OR REPLACE VIEW SCENARIOS.V_ORDER_PART_DEMAND AS
SELECT
    o.order_id,
    o.customer_id,
    o.product_id,
    o.plant_id,
    o.quantity AS order_quantity,
    o.order_value,
    o.due_date,
    o.priority,
    o.sla_tier,
    pp.part_id,
    pp.units_per_product,
    pp.is_critical_path,
    o.quantity * pp.units_per_product AS required_part_units
FROM RAW.ORDERS o
JOIN RAW.PRODUCT_PARTS pp ON pp.product_id = o.product_id
WHERE o.status = 'OPEN';

CREATE OR REPLACE VIEW SCENARIOS.V_BASELINE_PART_SUPPLY AS
WITH demand_horizon AS (
    SELECT plant_id, part_id, MAX(due_date) AS horizon_date
    FROM SCENARIOS.V_ORDER_PART_DEMAND
    GROUP BY plant_id, part_id
),
inventory AS (
    SELECT
        i.plant_id,
        i.part_id,
        GREATEST(i.on_hand_units - i.safety_stock_units, 0) AS usable_inventory_units
    FROM RAW.INVENTORY i
),
inbound AS (
    SELECT
        sh.plant_id,
        sh.part_id,
        SUM(sh.quantity) AS inbound_units
    FROM RAW.SHIPMENTS sh
    JOIN demand_horizon h
      ON h.plant_id = sh.plant_id
     AND h.part_id = sh.part_id
    WHERE sh.status IN ('IN_TRANSIT','DELAYED')
      AND sh.expected_arrival <= h.horizon_date
    GROUP BY sh.plant_id, sh.part_id
)
SELECT
    COALESCE(i.plant_id, b.plant_id) AS plant_id,
    COALESCE(i.part_id, b.part_id) AS part_id,
    COALESCE(i.usable_inventory_units, 0) AS usable_inventory_units,
    COALESCE(b.inbound_units, 0) AS inbound_units,
    COALESCE(i.usable_inventory_units, 0) + COALESCE(b.inbound_units, 0) AS baseline_available_units
FROM inventory i
FULL OUTER JOIN inbound b
  ON b.plant_id = i.plant_id
 AND b.part_id = i.part_id;

CREATE OR REPLACE VIEW SCENARIOS.V_SUPPLIER_FAILURE_PART_SUPPLY AS
WITH p AS (
    SELECT * FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS
),
failed_parts AS (
    SELECT DISTINCT sp.part_id
    FROM RAW.SUPPLIER_PARTS sp
    JOIN p ON p.failed_supplier_id = sp.supplier_id
    WHERE sp.qualification_status = 'QUALIFIED'
),
failed_inbound AS (
    SELECT
        sh.plant_id,
        sh.part_id,
        SUM(sh.quantity * (1 - p.capacity_reduction_pct / 100)) AS retained_failed_supplier_units
    FROM RAW.SHIPMENTS sh
    JOIN p ON p.failed_supplier_id = sh.supplier_id
    WHERE sh.status IN ('IN_TRANSIT','DELAYED')
      AND sh.expected_arrival > p.start_date
      AND sh.expected_arrival <= DATEADD(day, p.duration_days, p.start_date)
    GROUP BY sh.plant_id, sh.part_id
)
SELECT
    b.plant_id,
    b.part_id,
    b.usable_inventory_units,
    b.inbound_units,
    COALESCE(fi.retained_failed_supplier_units, 0) AS retained_failed_supplier_units,
    GREATEST(
        b.baseline_available_units
        - COALESCE(fi.retained_failed_supplier_units, 0),
        0
    ) AS scenario_available_units
FROM SCENARIOS.V_BASELINE_PART_SUPPLY b
JOIN failed_parts fp ON fp.part_id = b.part_id
LEFT JOIN failed_inbound fi
  ON fi.plant_id = b.plant_id
 AND fi.part_id = b.part_id;

-- Parts not sourced from the failed supplier retain baseline supply.
CREATE OR REPLACE VIEW SCENARIOS.V_SCENARIO_PART_SUPPLY AS
WITH failed AS (
    SELECT * FROM SCENARIOS.V_SUPPLIER_FAILURE_PART_SUPPLY
),
all_supply AS (
    SELECT * FROM SCENARIOS.V_BASELINE_PART_SUPPLY
)
SELECT
    a.plant_id,
    a.part_id,
    a.usable_inventory_units,
    a.inbound_units,
    COALESCE(f.retained_failed_supplier_units, 0) AS retained_failed_supplier_units,
    COALESCE(f.scenario_available_units, a.baseline_available_units) AS scenario_available_units
FROM all_supply a
LEFT JOIN failed f
  ON f.plant_id = a.plant_id
 AND f.part_id = a.part_id;

CREATE OR REPLACE VIEW SCENARIOS.V_ORDER_PART_ALLOCATION AS
WITH demand AS (
    SELECT * FROM SCENARIOS.V_ORDER_PART_DEMAND
),
supply AS (
    SELECT plant_id, part_id, scenario_available_units
    FROM SCENARIOS.V_SCENARIO_PART_SUPPLY
),
ranked AS (
    SELECT
        d.*,
        COALESCE(s.scenario_available_units, 0) AS available_part_units,
        COALESCE(
            SUM(d.required_part_units) OVER (
                PARTITION BY d.plant_id, d.part_id
                ORDER BY
                    d.due_date,
                    CASE d.priority
                        WHEN 'URGENT' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'NORMAL' THEN 3
                        ELSE 4
                    END,
                    d.order_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0
        ) AS prior_required_part_units
    FROM demand d
    LEFT JOIN supply s
      ON s.plant_id = d.plant_id
     AND s.part_id = d.part_id
)
SELECT
    r.*,
    GREATEST(
        LEAST(
            r.required_part_units,
            r.available_part_units - r.prior_required_part_units
        ),
        0
    ) AS allocated_part_units,
    GREATEST(
        r.required_part_units - GREATEST(
            LEAST(
                r.required_part_units,
                r.available_part_units - r.prior_required_part_units
            ),
            0
        ),
        0
    ) AS unmet_part_units
FROM ranked r;

CREATE OR REPLACE VIEW SCENARIOS.V_ORDER_IMPACT AS
SELECT
    order_id,
    customer_id,
    product_id,
    plant_id,
    order_quantity,
    order_value,
    due_date,
    priority,
    sla_tier,
    MIN(allocated_part_units / NULLIF(units_per_product,0)) AS fulfillable_quantity,
    GREATEST(
        order_quantity - MIN(allocated_part_units / NULLIF(units_per_product,0)),
        0
    ) AS at_risk_quantity,
    order_value * LEAST(
        GREATEST(
            order_quantity - MIN(allocated_part_units / NULLIF(units_per_product,0)),
            0
        ) / NULLIF(order_quantity,0),
        1
    ) AS at_risk_revenue,
    MAX(IFF(unmet_part_units > 0, 1, 0)) AS has_part_shortage,
    COUNT_IF(unmet_part_units > 0) AS shortage_part_count
FROM SCENARIOS.V_ORDER_PART_ALLOCATION
GROUP BY
    order_id, customer_id, product_id, plant_id, order_quantity,
    order_value, due_date, priority, sla_tier;

CREATE OR REPLACE VIEW SCENARIOS.V_SUPPLIER_FAILURE_IMPACT AS
SELECT
    p.failed_supplier_id AS supplier_id,
    p.capacity_reduction_pct,
    p.duration_days,
    p.start_date,
    COUNT_IF(oi.at_risk_quantity > 0) AS orders_at_risk,
    COUNT(DISTINCT IFF(oi.at_risk_quantity > 0, oi.customer_id, NULL)) AS customers_exposed,
    COUNT(DISTINCT IFF(oi.at_risk_quantity > 0, oi.plant_id, NULL)) AS affected_plants,
    COUNT(DISTINCT IFF(oa.unmet_part_units > 0, oa.part_id, NULL)) AS affected_parts,
    COALESCE(SUM(IFF(oi.at_risk_quantity > 0, oi.at_risk_revenue, 0)),0) AS revenue_exposure,
    COALESCE(SUM(IFF(oi.at_risk_quantity > 0, oi.at_risk_quantity, 0)),0) AS units_at_risk
FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS p
CROSS JOIN SCENARIOS.V_ORDER_IMPACT oi
LEFT JOIN SCENARIOS.V_ORDER_PART_ALLOCATION oa
  ON oa.order_id = oi.order_id
GROUP BY p.failed_supplier_id, p.capacity_reduction_pct, p.duration_days, p.start_date;

CREATE OR REPLACE VIEW SCENARIOS.V_SUPPLIER_FAILURE_CHAIN AS
SELECT DISTINCT
    d.supplier_id,
    s.supplier_name,
    d.part_id,
    p.part_name,
    p.criticality,
    pp.product_id,
    pr.product_name,
    o.order_id,
    o.customer_id,
    c.customer_name,
    o.plant_id,
    pl.plant_name,
    o.quantity AS order_quantity,
    oi.at_risk_quantity,
    oi.at_risk_revenue,
    o.sla_tier,
    o.priority
FROM RAW.SUPPLIER_PARTS d
JOIN RAW.SUPPLIERS s ON s.supplier_id = d.supplier_id
JOIN RAW.PARTS p ON p.part_id = d.part_id
JOIN RAW.PRODUCT_PARTS pp ON pp.part_id = d.part_id
JOIN RAW.PRODUCTS pr ON pr.product_id = pp.product_id
JOIN RAW.ORDERS o ON o.product_id = pp.product_id
JOIN RAW.CUSTOMERS c ON c.customer_id = o.customer_id
JOIN RAW.PLANTS pl ON pl.plant_id = o.plant_id
JOIN SCENARIOS.V_ORDER_IMPACT oi ON oi.order_id = o.order_id
JOIN SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS x ON x.failed_supplier_id = d.supplier_id
WHERE d.qualification_status = 'QUALIFIED'
  AND oi.at_risk_quantity > 0;

CREATE OR REPLACE VIEW ANALYTICS.EXECUTIVE_RISK_SUMMARY AS
SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    COALESCE(SUM(order_value),0) AS total_order_value,
    COUNT(DISTINCT customer_id) AS total_customers,
    COUNT(DISTINCT product_id) AS total_products
FROM RAW.ORDERS
WHERE status = 'OPEN';

-- Key deterministic questions:
-- SELECT * FROM SCENARIOS.V_SUPPLIER_FAILURE_IMPACT;
-- SELECT * FROM SCENARIOS.V_ORDER_IMPACT WHERE at_risk_quantity > 0 ORDER BY at_risk_revenue DESC;
-- SELECT * FROM SCENARIOS.V_SUPPLIER_FAILURE_CHAIN;
