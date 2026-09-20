-- NEXUS validation layer
-- These views expose deterministic checks for demo QA and agent grounding.
USE DATABASE NEXUS_DB;

-- NEXUS scenario validation checks.
-- Each row returns: check_name, status (PASS/FAIL), violation_count, description.
-- All five checks must return PASS in a valid deployment.
-- Expected valid state for all checks: status = 'PASS', violation_count = 0.
CREATE OR REPLACE VIEW ANALYTICS.V_SCENARIO_VALIDATION AS

-- 1. No negative at-risk quantity or revenue in the supplier-failure scenario.
SELECT
    'NO_NEGATIVE_RISK'                                             AS check_name,
    IFF(COUNT_IF(at_risk_quantity < 0 OR at_risk_revenue < 0) = 0, 'PASS', 'FAIL') AS status,
    COUNT_IF(at_risk_quantity < 0 OR at_risk_revenue < 0)         AS violation_count,
    'Orders with at_risk_quantity < 0 or at_risk_revenue < 0'     AS description
FROM SCENARIOS.V_ORDER_IMPACT

UNION ALL

-- 2. At-risk revenue must not exceed order value and must not be negative.
SELECT
    'REVENUE_RISK_NOT_OVER_ORDER_VALUE',
    IFF(COUNT_IF(at_risk_revenue < -0.01 OR at_risk_revenue > order_value + 0.01) = 0, 'PASS', 'FAIL'),
    COUNT_IF(at_risk_revenue < -0.01 OR at_risk_revenue > order_value + 0.01),
    'Orders where at_risk_revenue < 0 or at_risk_revenue > order_value'
FROM SCENARIOS.V_ORDER_IMPACT

UNION ALL

-- 3. Part allocation per order row must not exceed that row's required part units.
SELECT
    'ALLOCATION_NOT_OVER_DEMAND',
    IFF(COUNT_IF(allocated_part_units > required_part_units + 0.01) = 0, 'PASS', 'FAIL'),
    COUNT_IF(allocated_part_units > required_part_units + 0.01),
    'Allocation rows where allocated_part_units exceeds required_part_units'
FROM SCENARIOS.V_ORDER_PART_ALLOCATION

UNION ALL

-- 4. Total allocation per plant/part must not exceed scenario available supply.
--    The subquery counts plant/part violations; COUNT(*) here counts those rows only.
SELECT
    'ALLOCATION_NOT_OVER_SUPPLY',
    IFF(COUNT(*) = 0, 'PASS', 'FAIL'),
    COUNT(*),
    'Plant/part combinations where SUM(allocated_part_units) > MAX(available_part_units)'
FROM (
    SELECT plant_id, part_id,
           MAX(available_part_units) AS available_units,
           SUM(allocated_part_units) AS total_allocated
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION
    GROUP BY plant_id, part_id
    HAVING SUM(allocated_part_units) > MAX(available_part_units) + 0.01
)

UNION ALL

-- 5. Every row in the supplier-failure chain must represent an actual unmet shortage.
--    Chain rows with unmet_part_units <= 0 indicate a trace without a real shortage.
SELECT
    'SUPPLIER_FAILURE_TRACE_ONLY_FOR_ACTUAL_SHORTAGES',
    IFF(COUNT_IF(unmet_part_units <= 0) = 0, 'PASS', 'FAIL'),
    COUNT_IF(unmet_part_units <= 0),
    'Supplier failure chain rows where unmet_part_units is zero or negative'
FROM SCENARIOS.V_SUPPLIER_FAILURE_CHAIN;

CREATE OR REPLACE VIEW ANALYTICS.V_NEXUS_EVIDENCE_SUPPLIER_FAILURE AS
SELECT
    'SUPPLIER_FAILURE' AS scenario_type,
    x.failed_supplier_id AS target_entity_id,
    x.duration_days,
    x.capacity_reduction_pct,
    x.start_date,
    oi.orders_at_risk,
    oi.customers_exposed,
    oi.affected_plants,
    oi.affected_parts,
    oi.revenue_exposure,
    oi.units_at_risk
FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS x
JOIN SCENARIOS.V_SUPPLIER_FAILURE_IMPACT oi
  ON oi.supplier_id=x.failed_supplier_id;

CREATE OR REPLACE VIEW ANALYTICS.V_NEXUS_EVIDENCE_PORT_DISRUPTION AS
SELECT
    'PORT_DISRUPTION' AS scenario_type,
    x.disrupted_port_id AS target_entity_id,
    x.duration_days,
    x.disruption_pct,
    x.start_date,
    i.orders_at_risk,
    i.customers_exposed,
    i.affected_plants,
    i.revenue_exposure,
    i.units_at_risk
FROM SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS x
JOIN SCENARIOS.V_PORT_DISRUPTION_IMPACT i
  ON i.disrupted_port_id=x.disrupted_port_id;

CREATE OR REPLACE VIEW ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG AS
SELECT 'orders_at_risk' AS metric_name,
       'Count of open orders with modeled unmet product quantity under the active scenario.' AS definition,
       'SCENARIOS.V_ORDER_IMPACT' AS source_view
UNION ALL
SELECT 'revenue_exposure',
       'Sum of modeled at-risk revenue for open orders with unmet quantity; capped at each order value.',
       'SCENARIOS.V_ORDER_IMPACT'
UNION ALL
SELECT 'customers_exposed',
       'Distinct customers with at least one modeled at-risk open order.',
       'SCENARIOS.V_ORDER_IMPACT'
UNION ALL
SELECT 'affected_parts',
       'Distinct parts with positive unmet part demand in the modeled scenario.',
       'SCENARIOS.V_ORDER_PART_ALLOCATION'
UNION ALL
SELECT 'inventory_coverage_days',
       'Usable inventory divided by average daily consumption; interpreted as modeled coverage.',
       'RAW.INVENTORY';
