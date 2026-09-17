-- NEXUS port disruption engine
-- Propagation:
-- Port -> inbound shipment -> plant/part supply -> order fulfillment -> customer exposure.
-- A disrupted port blocks shipments whose expected arrival falls inside the disruption window.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE VIEW SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS AS
SELECT
    'PORT-TYO'::VARCHAR AS disrupted_port_id,
    100::NUMBER(8,4) AS disruption_pct,
    7::NUMBER(10,0) AS duration_days,
    '2026-09-18'::DATE AS start_date;

CREATE OR REPLACE VIEW SCENARIOS.V_PORT_DISRUPTION_PART_SUPPLY AS
WITH p AS (
    SELECT * FROM SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS
),
base AS (
    SELECT * FROM SCENARIOS.V_BASELINE_PART_SUPPLY
),
blocked AS (
    SELECT
        sh.plant_id,
        sh.part_id,
        SUM(sh.quantity * p.disruption_pct / 100) AS blocked_inbound_units
    FROM RAW.SHIPMENTS sh
    CROSS JOIN p
    WHERE sh.port_id = p.disrupted_port_id
      AND sh.status IN ('IN_TRANSIT','DELAYED')
      AND sh.expected_arrival > p.start_date
      AND sh.expected_arrival <= DATEADD(day, p.duration_days, p.start_date)
    GROUP BY sh.plant_id, sh.part_id
)
SELECT
    b.plant_id,
    b.part_id,
    b.usable_inventory_units,
    b.inbound_units,
    COALESCE(bl.blocked_inbound_units,0) AS blocked_inbound_units,
    GREATEST(b.baseline_available_units - COALESCE(bl.blocked_inbound_units,0),0) AS scenario_available_units
FROM base b
LEFT JOIN blocked bl
  ON bl.plant_id = b.plant_id
 AND bl.part_id = b.part_id;

CREATE OR REPLACE VIEW SCENARIOS.V_PORT_DISRUPTION_ORDER_PART_ALLOCATION AS
WITH demand AS (
    SELECT * FROM SCENARIOS.V_ORDER_PART_DEMAND
),
supply AS (
    SELECT plant_id, part_id, scenario_available_units
    FROM SCENARIOS.V_PORT_DISRUPTION_PART_SUPPLY
),
ranked AS (
    SELECT
        d.*,
        COALESCE(s.scenario_available_units,0) AS available_part_units,
        COALESCE(SUM(d.required_part_units) OVER (
            PARTITION BY d.plant_id, d.part_id
            ORDER BY d.due_date,
                     CASE d.priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END,
                     d.order_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
        ),0) AS prior_required_part_units
    FROM demand d
    LEFT JOIN supply s
      ON s.plant_id = d.plant_id
     AND s.part_id = d.part_id
)
SELECT
    r.*,
    GREATEST(LEAST(r.required_part_units, r.available_part_units - r.prior_required_part_units),0) AS allocated_part_units,
    GREATEST(r.required_part_units - GREATEST(LEAST(r.required_part_units, r.available_part_units - r.prior_required_part_units),0),0) AS unmet_part_units
FROM ranked r;

CREATE OR REPLACE VIEW SCENARIOS.V_PORT_DISRUPTION_ORDER_IMPACT AS
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
    GREATEST(order_quantity - MIN(allocated_part_units / NULLIF(units_per_product,0)),0) AS at_risk_quantity,
    order_value * LEAST(GREATEST(order_quantity - MIN(allocated_part_units / NULLIF(units_per_product,0)),0) / NULLIF(order_quantity,0),1) AS at_risk_revenue,
    COUNT_IF(unmet_part_units > 0) AS shortage_part_count
FROM SCENARIOS.V_PORT_DISRUPTION_ORDER_PART_ALLOCATION
GROUP BY order_id, customer_id, product_id, plant_id, order_quantity, order_value, due_date, priority, sla_tier;

CREATE OR REPLACE VIEW SCENARIOS.V_PORT_DISRUPTION_IMPACT AS
SELECT
    p.disrupted_port_id,
    p.disruption_pct,
    p.duration_days,
    p.start_date,
    COUNT_IF(i.at_risk_quantity > 0) AS orders_at_risk,
    COUNT(DISTINCT IFF(i.at_risk_quantity > 0,i.customer_id,NULL)) AS customers_exposed,
    COUNT(DISTINCT IFF(i.at_risk_quantity > 0,i.plant_id,NULL)) AS affected_plants,
    COALESCE(SUM(IFF(i.at_risk_quantity > 0,i.at_risk_revenue,0)),0) AS revenue_exposure,
    COALESCE(SUM(IFF(i.at_risk_quantity > 0,i.at_risk_quantity,0)),0) AS units_at_risk
FROM SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS p
CROSS JOIN SCENARIOS.V_PORT_DISRUPTION_ORDER_IMPACT i
GROUP BY p.disrupted_port_id,p.disruption_pct,p.duration_days,p.start_date;

CREATE OR REPLACE VIEW SCENARIOS.V_PORT_DISRUPTION_CHAIN AS
SELECT DISTINCT
    p.disrupted_port_id,
    po.port_name,
    sh.shipment_id,
    sh.supplier_id,
    s.supplier_name,
    sh.part_id,
    pt.part_name,
    sh.plant_id,
    pl.plant_name,
    sh.quantity AS shipment_quantity,
    sh.expected_arrival,
    i.order_id,
    i.customer_id,
    c.customer_name,
    i.product_id,
    pr.product_name,
    i.at_risk_quantity,
    i.at_risk_revenue,
    i.sla_tier
FROM SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS p
JOIN RAW.SHIPMENTS sh ON sh.port_id = p.disrupted_port_id
JOIN RAW.PORTS po ON po.port_id = sh.port_id
JOIN RAW.SUPPLIERS s ON s.supplier_id = sh.supplier_id
JOIN RAW.PARTS pt ON pt.part_id = sh.part_id
JOIN RAW.PLANTS pl ON pl.plant_id = sh.plant_id
JOIN SCENARIOS.V_PORT_DISRUPTION_ORDER_IMPACT i
  ON i.plant_id = sh.plant_id
JOIN RAW.ORDERS o ON o.order_id = i.order_id
JOIN RAW.PRODUCTS pr ON pr.product_id = i.product_id
JOIN RAW.CUSTOMERS c ON c.customer_id = i.customer_id
WHERE sh.status IN ('IN_TRANSIT','DELAYED')
  AND sh.expected_arrival > p.start_date
  AND sh.expected_arrival <= DATEADD(day,p.duration_days,p.start_date)
  AND i.at_risk_quantity > 0;

-- Demo queries:
-- SELECT * FROM SCENARIOS.V_PORT_DISRUPTION_IMPACT;
-- SELECT * FROM SCENARIOS.V_PORT_DISRUPTION_CHAIN;
