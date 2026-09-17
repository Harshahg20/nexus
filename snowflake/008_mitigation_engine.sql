-- NEXUS deterministic mitigation comparison engine.
-- Each mitigation contributes explicit incremental part units. Units are first
-- distributed across plants by their share of required demand, then allocated
-- to orders using the same due-date/priority rules as the scenario engine.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_PART_CAPACITY AS
WITH p AS (
    SELECT * FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS
),
failed_parts AS (
    SELECT DISTINCT sp.part_id
    FROM RAW.SUPPLIER_PARTS sp
    JOIN p ON p.failed_supplier_id = sp.supplier_id
    WHERE sp.qualification_status = 'QUALIFIED'
),
alternate AS (
    SELECT
        fp.part_id,
        'ALTERNATE_SUPPLIER' AS mitigation_type,
        SUM(q.max_daily_capacity_units) * p.duration_days AS total_incremental_units,
        SUM(q.max_daily_capacity_units * p.duration_days * q.unit_cost) AS incremental_cost
    FROM failed_parts fp
    JOIN ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS q
      ON q.part_id = fp.part_id
    CROSS JOIN p
    WHERE q.supplier_id <> p.failed_supplier_id
    GROUP BY fp.part_id, p.duration_days
),
expedite AS (
    SELECT
        sh.part_id,
        'EXPEDITE_SHIPMENT' AS mitigation_type,
        SUM(sh.quantity) AS total_incremental_units,
        SUM(sh.quantity * pt.unit_cost * 0.25) AS incremental_cost
    FROM RAW.SHIPMENTS sh
    JOIN failed_parts fp ON fp.part_id = sh.part_id
    JOIN RAW.PARTS pt ON pt.part_id = sh.part_id
    JOIN p ON p.failed_supplier_id = sh.supplier_id
    WHERE sh.status IN ('IN_TRANSIT','DELAYED')
      AND sh.expected_arrival > p.start_date
      AND sh.expected_arrival <= DATEADD(day, p.duration_days, p.start_date)
    GROUP BY sh.part_id
),
none AS (
    SELECT
        fp.part_id,
        'NO_ACTION' AS mitigation_type,
        0::NUMBER(18,2) AS total_incremental_units,
        0::NUMBER(18,2) AS incremental_cost
    FROM failed_parts fp
)
SELECT * FROM none
UNION ALL SELECT * FROM alternate
UNION ALL SELECT * FROM expedite;

-- Supplier capacity is global by part. Allocate it across plants in proportion
-- to each plant's required part demand so the same units cannot be counted twice.
CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_PLANT_CAPACITY AS
WITH demand AS (
    SELECT
        plant_id,
        part_id,
        SUM(required_part_units) AS plant_required_units
    FROM SCENARIOS.V_ORDER_PART_DEMAND
    GROUP BY plant_id, part_id
),
total_demand AS (
    SELECT part_id, SUM(plant_required_units) AS total_required_units
    FROM demand
    GROUP BY part_id
)
SELECT
    d.plant_id,
    d.part_id,
    m.mitigation_type,
    m.total_incremental_units,
    m.incremental_cost,
    m.total_incremental_units
      * d.plant_required_units / NULLIF(t.total_required_units,0) AS plant_incremental_units
FROM demand d
JOIN total_demand t ON t.part_id = d.part_id
JOIN SCENARIOS.V_MITIGATION_PART_CAPACITY m ON m.part_id = d.part_id;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_ORDER_IMPACT AS
WITH base AS (
    SELECT
        a.order_id,
        a.customer_id,
        a.product_id,
        a.plant_id,
        a.order_quantity,
        a.order_value,
        a.due_date,
        a.priority,
        a.sla_tier,
        a.part_id,
        a.units_per_product,
        a.required_part_units,
        a.allocated_part_units,
        a.unmet_part_units,
        a.available_part_units,
        COALESCE(m.mitigation_type, 'NO_ACTION') AS mitigation_type,
        COALESCE(m.plant_incremental_units, 0) AS incremental_units
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION a
    LEFT JOIN SCENARIOS.V_MITIGATION_PLANT_CAPACITY m
      ON m.plant_id = a.plant_id
     AND m.part_id = a.part_id
),
ranked AS (
    SELECT
        b.*,
        COALESCE(
            SUM(b.required_part_units) OVER (
                PARTITION BY b.mitigation_type, b.plant_id, b.part_id
                ORDER BY
                    b.due_date,
                    CASE b.priority
                        WHEN 'URGENT' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'NORMAL' THEN 3
                        ELSE 4
                    END,
                    b.order_id
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
            ), 0
        ) AS prior_required_units
    FROM base b
)
SELECT
    r.*,
    GREATEST(
        LEAST(
            r.required_part_units,
            r.available_part_units + r.incremental_units - r.prior_required_units
        ),
        0
    ) AS mitigated_allocated_part_units,
    GREATEST(
        r.required_part_units - GREATEST(
            LEAST(
                r.required_part_units,
                r.available_part_units + r.incremental_units - r.prior_required_units
            ),
            0
        ),
        0
    ) AS mitigated_unmet_part_units
FROM ranked r;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_ORDER_SUMMARY AS
SELECT
    mitigation_type,
    order_id,
    customer_id,
    product_id,
    plant_id,
    order_quantity,
    order_value,
    due_date,
    priority,
    sla_tier,
    MIN(mitigated_allocated_part_units / NULLIF(units_per_product,0)) AS fulfillable_quantity,
    GREATEST(
        order_quantity - MIN(mitigated_allocated_part_units / NULLIF(units_per_product,0)),
        0
    ) AS at_risk_quantity,
    order_value * LEAST(
        GREATEST(
            order_quantity - MIN(mitigated_allocated_part_units / NULLIF(units_per_product,0)),
            0
        ) / NULLIF(order_quantity,0),
        1
    ) AS at_risk_revenue
FROM SCENARIOS.V_MITIGATION_ORDER_IMPACT
GROUP BY
    mitigation_type, order_id, customer_id, product_id, plant_id,
    order_quantity, order_value, due_date, priority, sla_tier;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COST AS
SELECT
    mitigation_type,
    SUM(incremental_cost) AS modeled_incremental_cost
FROM SCENARIOS.V_MITIGATION_PART_CAPACITY
GROUP BY mitigation_type;

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COMPARISON AS
SELECT
    s.mitigation_type,
    COUNT_IF(s.at_risk_quantity > 0) AS orders_at_risk,
    COUNT(DISTINCT IFF(s.at_risk_quantity > 0, s.customer_id, NULL)) AS customers_exposed,
    COALESCE(SUM(s.at_risk_quantity),0) AS units_at_risk,
    COALESCE(SUM(s.at_risk_revenue),0) AS remaining_revenue_exposure,
    (SELECT COALESCE(SUM(at_risk_revenue),0) FROM SCENARIOS.V_ORDER_IMPACT)
      - COALESCE(SUM(s.at_risk_revenue),0) AS modeled_revenue_protected,
    c.modeled_incremental_cost,
    'Deterministic modeled outcome using explicit part capacity and priority-based order allocation; not an operational execution guarantee.' AS calculation_note
FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY s
JOIN SCENARIOS.V_MITIGATION_COST c
  ON c.mitigation_type = s.mitigation_type
GROUP BY s.mitigation_type, c.modeled_incremental_cost;

-- Useful queries:
-- SELECT * FROM SCENARIOS.V_MITIGATION_COMPARISON;
-- SELECT * FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY WHERE at_risk_quantity > 0;
