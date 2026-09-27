-- NEXUS deterministic mitigation comparison engine.
-- Each mitigation contributes explicit incremental part units. Units are first
-- distributed across plants by their share of required demand, then allocated
-- to orders using the same due-date/priority rules as the scenario engine.
--
-- Supported mitigation strategies:
--   NO_ACTION             — absorb the full disruption; baseline comparison.
--   ALTERNATE_SUPPLIER    — source from other qualified suppliers for the duration.
--   EXPEDITE_SHIPMENT     — rush in-transit shipments via alternate freight routes
--                           (models recovering shipments already en-route from the
--                            failed supplier; incremental cost = 25% of unit cost).
--   INVENTORY_REALLOCATION — transfer surplus inventory from non-deficit plants to
--                            deficit plants (incremental cost = 15% of unit cost
--                            for inter-plant logistics; bounded by actual surplus).

USE DATABASE NEXUS_DB;

-- ============================================================================
-- V_MITIGATION_PART_CAPACITY
-- Global incremental part units available under each mitigation strategy.
-- Grain: (part_id, mitigation_type) — one row per strategy per affected part.
-- ============================================================================
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

-- ── NO_ACTION ────────────────────────────────────────────────────────────────
none AS (
    SELECT
        fp.part_id,
        'NO_ACTION' AS mitigation_type,
        0::NUMBER(18,2) AS total_incremental_units,
        0::NUMBER(18,2) AS incremental_cost
    FROM failed_parts fp
),

-- ── ALTERNATE_SUPPLIER ───────────────────────────────────────────────────────
-- Qualified suppliers other than the failed one, for the duration of the window.
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

-- ── EXPEDITE_SHIPMENT ────────────────────────────────────────────────────────
-- Models recovering in-transit shipments from the failed supplier via alternate
-- freight routes (e.g., air freight instead of sea). Incremental cost = 25% of
-- unit cost applied to all recovered units. Assumption: goods are already
-- manufactured and in-transit; expedite pays for rerouting, not production.
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

-- ── INVENTORY_REALLOCATION ───────────────────────────────────────────────────
-- Cross-plant inventory transfer: plants with surplus (available > local demand)
-- share units with deficit plants. This does not add new units to the supply
-- chain — it redistributes what already exists.
--
-- Surplus calculation:
--   per-plant surplus = max(scenario_available_units − plant_required_demand, 0)
--   pooled surplus    = sum of surplus across all plants for the part
--
-- Reallocated units = min(pooled_surplus, global_shortage)
-- Incremental cost  = reallocated_units × unit_cost × 0.15 (logistics rate)
--
-- Source: V_SCENARIO_PART_SUPPLY (already in-scope supply) and
--         V_ORDER_PART_ALLOCATION (already-computed shortage per plant).

plant_surplus_supply AS (
    SELECT sp.plant_id, sp.part_id, sp.scenario_available_units
    FROM SCENARIOS.V_SCENARIO_PART_SUPPLY sp
    JOIN failed_parts fp ON fp.part_id = sp.part_id
),
plant_demand_agg AS (
    SELECT plant_id, part_id, SUM(required_part_units) AS plant_required_units
    FROM SCENARIOS.V_ORDER_PART_DEMAND
    GROUP BY plant_id, part_id
),
-- Net position per plant: how much is left after satisfying local demand?
plant_net_position AS (
    SELECT
        pss.plant_id,
        pss.part_id,
        GREATEST(
            pss.scenario_available_units - COALESCE(pda.plant_required_units, 0),
            0
        ) AS surplus_units
    FROM plant_surplus_supply pss
    LEFT JOIN plant_demand_agg pda
      ON pda.plant_id = pss.plant_id AND pda.part_id = pss.part_id
),
-- Pool surplus across all plants per part
global_surplus AS (
    SELECT part_id, SUM(surplus_units) AS pooled_surplus_units
    FROM plant_net_position
    GROUP BY part_id
),
-- Total unmet demand per part across all plants (from the unmitigated scenario)
global_shortage AS (
    SELECT part_id, SUM(unmet_part_units) AS total_unmet_units
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION
    WHERE unmet_part_units > 0
    GROUP BY part_id
),
realloc AS (
    SELECT
        fp.part_id,
        'INVENTORY_REALLOCATION' AS mitigation_type,
        -- Cannot move more than available surplus OR more than total shortage
        LEAST(
            COALESCE(gs.pooled_surplus_units, 0),
            COALESCE(gsh.total_unmet_units, 0)
        ) AS total_incremental_units,
        -- 15% logistics cost on transferred units
        LEAST(
            COALESCE(gs.pooled_surplus_units, 0),
            COALESCE(gsh.total_unmet_units, 0)
        ) * pt.unit_cost * 0.15 AS incremental_cost
    FROM failed_parts fp
    LEFT JOIN global_surplus gs ON gs.part_id = fp.part_id
    LEFT JOIN global_shortage gsh ON gsh.part_id = fp.part_id
    JOIN RAW.PARTS pt ON pt.part_id = fp.part_id
)

SELECT * FROM none
UNION ALL SELECT * FROM alternate
UNION ALL SELECT * FROM expedite
UNION ALL SELECT * FROM realloc;


-- ============================================================================
-- V_MITIGATION_PLANT_CAPACITY
-- Distributes global incremental units proportionally to each plant's demand
-- share. Prevents double-counting the same units across plants.
-- ============================================================================
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


-- ============================================================================
-- V_MITIGATION_ORDER_IMPACT
-- Re-runs the priority allocation adding incremental units per mitigation.
-- ============================================================================
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


-- ============================================================================
-- V_MITIGATION_ORDER_SUMMARY
-- Order-level risk under each mitigation strategy.
-- ============================================================================
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


-- ============================================================================
-- V_MITIGATION_COST
-- Aggregate incremental cost per mitigation strategy.
-- ============================================================================
CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COST AS
SELECT
    mitigation_type,
    SUM(incremental_cost) AS modeled_incremental_cost
FROM SCENARIOS.V_MITIGATION_PART_CAPACITY
GROUP BY mitigation_type;


-- ============================================================================
-- V_MITIGATION_COMPARISON
-- Side-by-side comparison of all four mitigation strategies.
-- Columns: orders_at_risk, customers_exposed, units_at_risk,
--          remaining_revenue_exposure, modeled_revenue_protected,
--          modeled_incremental_cost.
-- ============================================================================
CREATE OR REPLACE VIEW SCENARIOS.V_MITIGATION_COMPARISON AS
SELECT
    s.mitigation_type,
    COUNT_IF(s.at_risk_quantity > 0)                                        AS orders_at_risk,
    COUNT(DISTINCT IFF(s.at_risk_quantity > 0, s.customer_id, NULL))        AS customers_exposed,
    COALESCE(SUM(s.at_risk_quantity),0)                                      AS units_at_risk,
    COALESCE(SUM(s.at_risk_revenue),0)                                       AS remaining_revenue_exposure,
    (SELECT COALESCE(SUM(at_risk_revenue),0) FROM SCENARIOS.V_ORDER_IMPACT)
      - COALESCE(SUM(s.at_risk_revenue),0)                                  AS modeled_revenue_protected,
    c.modeled_incremental_cost,
    'Deterministic modeled outcome using explicit part capacity and priority-based order allocation; not an operational execution guarantee.' AS calculation_note
FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY s
JOIN SCENARIOS.V_MITIGATION_COST c
  ON c.mitigation_type = s.mitigation_type
GROUP BY s.mitigation_type, c.modeled_incremental_cost;


-- ============================================================================
-- V_INVENTORY_REALLOCATION_DETAIL
-- Shows per-part detail for the inventory reallocation strategy:
-- which parts have surplus, how much, and how much of the shortage it covers.
-- Useful for the evidence and drilldown views.
-- ============================================================================
CREATE OR REPLACE VIEW SCENARIOS.V_INVENTORY_REALLOCATION_DETAIL AS
WITH p AS (SELECT * FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS),
failed_parts AS (
    SELECT DISTINCT sp.part_id
    FROM RAW.SUPPLIER_PARTS sp
    JOIN p ON p.failed_supplier_id = sp.supplier_id
    WHERE sp.qualification_status = 'QUALIFIED'
),
plant_supply AS (
    SELECT sp.plant_id, sp.part_id, sp.scenario_available_units
    FROM SCENARIOS.V_SCENARIO_PART_SUPPLY sp
    JOIN failed_parts fp ON fp.part_id = sp.part_id
),
plant_demand_agg AS (
    SELECT plant_id, part_id, SUM(required_part_units) AS plant_required_units
    FROM SCENARIOS.V_ORDER_PART_DEMAND
    GROUP BY plant_id, part_id
),
plant_position AS (
    SELECT
        pss.plant_id,
        pl.plant_name,
        pss.part_id,
        pt.part_name,
        pt.unit_cost,
        pss.scenario_available_units,
        COALESCE(pda.plant_required_units, 0) AS local_demand_units,
        GREATEST(pss.scenario_available_units - COALESCE(pda.plant_required_units, 0), 0) AS surplus_units
    FROM plant_supply pss
    JOIN RAW.PLANTS pl ON pl.plant_id = pss.plant_id
    JOIN RAW.PARTS pt ON pt.part_id = pss.part_id
    LEFT JOIN plant_demand_agg pda ON pda.plant_id = pss.plant_id AND pda.part_id = pss.part_id
),
global_shortage AS (
    SELECT part_id, SUM(unmet_part_units) AS total_shortage_units
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION
    WHERE unmet_part_units > 0
    GROUP BY part_id
)
SELECT
    pp.plant_id,
    pp.plant_name,
    pp.part_id,
    pp.part_name,
    pp.unit_cost,
    pp.scenario_available_units,
    pp.local_demand_units,
    pp.surplus_units,
    COALESCE(gs.total_shortage_units, 0) AS global_shortage_units,
    LEAST(
        SUM(pp.surplus_units) OVER (PARTITION BY pp.part_id),
        COALESCE(gs.total_shortage_units, 0)
    ) AS reallocatable_units,
    LEAST(
        SUM(pp.surplus_units) OVER (PARTITION BY pp.part_id),
        COALESCE(gs.total_shortage_units, 0)
    ) * pp.unit_cost * 0.15 AS estimated_transfer_cost
FROM plant_position pp
LEFT JOIN global_shortage gs ON gs.part_id = pp.part_id
WHERE pp.surplus_units > 0
ORDER BY pp.part_id, pp.surplus_units DESC;


-- ============================================================================
-- Useful demo queries
-- ============================================================================
-- SELECT * FROM SCENARIOS.V_MITIGATION_COMPARISON ORDER BY mitigation_type;
-- SELECT * FROM SCENARIOS.V_MITIGATION_ORDER_SUMMARY WHERE at_risk_quantity > 0;
-- SELECT * FROM SCENARIOS.V_INVENTORY_REALLOCATION_DETAIL;
