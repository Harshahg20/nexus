-- NEXUS deterministic mitigation comparison engine.
--
-- Each mitigation contributes explicit incremental part units. Those units are
-- allocated to the same order demand model used by the scenario engine. This
-- makes protected revenue a consequence of fulfillment capacity, not a score.

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
-- Qualified alternate capacity is capped by the scenario duration.
alternate AS (
    SELECT
        fp.part_id,
        'ALTERNATE_SUPPLIER' AS mitigation_type,
        LEAST(
            SUM(q.max_daily_capacity_units),
            SUM(q.max_daily_capacity_units) * p.duration_days
        ) AS incremental_units,
        SUM(q.max_daily_capacity_units * p.duration_days * q.unit_cost) AS incremental_cost
    FROM failed_parts fp
    JOIN ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS q
      ON q.part_id = fp.part_id
    CROSS JOIN p
    WHERE q.supplier_id <> p.failed_supplier_id
    GROUP BY fp.part_id, p.duration_days
),
-- Expedite is limited to shipments from the failed supplier that are already
-- in transit/delayed. We treat the shipment quantity as recoverable units.
expedite AS (
    SELECT
        sh.part_id,
        'EXPEDITE_SHIPMENT' AS mitigation_type,
        SUM(sh.quantity) AS incremental_units,
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
        0::NUMBER(18,2) AS incremental_units,
        0::NUMBER(18,2) AS incremental_cost
    FROM failed_parts fp
)
SELECT * FROM none
UNION ALL SELECT * FROM alternate
UNION ALL SELECT * FROM expedite;

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
        COALESCE(m.incremental_units, 0) AS incremental_units,
        COALESCE(m.incremental_cost, 0) AS mitigation_part_cost
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION a
    LEFT JOIN SCENARIOS.V_MITIGATION_PART_CAPACITY m
      ON m.part_id = a.part_id
),
-- Re-rank orders after adding mitigation units. The allocation order remains
-- due date -> priority -> order id, so mitigation cannot double-count supply.
ranked AS (
    SELECT
        b.*,
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
        ) AS prior_required_units
    FROM base b
)
SELECT
    r.*,
    GREATEST(
        LEAST(
            r.required_part_units,
            r.available_part_units + r.incremental_units - COALESCE(r.prior_required_units,0)
        ),
        0
    ) AS mitigated_allocated_part_units,
    GREATEST(
        r.required_part_units - GREATEST(
            LEAST(
                r.required_part_units,
                r.available_part_units + r.incremental_units - COALESCE(r.prior_required_units,0)
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

CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COMPARISON AS
SELECT
    mitigation_type,
    COUNT_IF(at_risk_quantity > 0) AS orders_at_risk,
    COUNT(DISTINCT IFF(at_risk_quantity > 0, customer_id, NULL)) AS customers_exposed,
    COALESCE(SUM(at_risk_quantity),0) AS units_at_risk,
    COALESCE(SUM(at_risk_revenue),0) AS remaining_revenue_exposure,
    (SELECT COALESCE(SUM(at_risk_revenue),0)
       FROM SCENARIOS.V_ORDER_IMPACT) - COALESCE(SUM(at_risk_revenue),0) AS modeled_revenue_protected,
    MAX(mitigation_part_cost) AS modeled_incremental_cost,
    'Deterministic modeled outcome using explicit part capacity and priority-based order allocation; not an operational execution guarantee.' AS calculation_note
FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY
GROUP BY mitigation_type;

-- The UI should present this as a trade-off table, not a universal ranking.
-- Useful queries:
-- SELECT * FROM SCENARIOS.V_MITIGATION_COMPARISON;
-- SELECT * FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY WHERE at_risk_quantity > 0;
