-- NEXUS validation layer
-- These views expose deterministic checks for demo QA and agent grounding.
USE DATABASE NEXUS_DB;

CREATE OR REPLACE VIEW ANALYTICS.V_SCENARIO_VALIDATION AS
SELECT 'SUPPLIER_FAILURE_NO_NEGATIVE_RISK' AS check_name,
       COUNT_IF(at_risk_quantity < 0 OR at_risk_revenue < 0) AS failures,
       IFF(COUNT_IF(at_risk_quantity < 0 OR at_risk_revenue < 0)=0,'PASS','FAIL') AS status
FROM SCENARIOS.V_ORDER_IMPACT
UNION ALL
SELECT 'SUPPLIER_FAILURE_REVENUE_BOUNDED',
       COUNT_IF(at_risk_revenue < 0 OR at_risk_revenue > order_value + 0.01),
       IFF(COUNT_IF(at_risk_revenue < 0 OR at_risk_revenue > order_value + 0.01)=0,'PASS','FAIL')
FROM SCENARIOS.V_ORDER_IMPACT
UNION ALL
SELECT 'SUPPLIER_FAILURE_ALLOCATION_NOT_OVER_DEMAND',
       COUNT_IF(allocated_part_units > required_part_units + 0.01),
       IFF(COUNT_IF(allocated_part_units > required_part_units + 0.01)=0,'PASS','FAIL')
FROM SCENARIOS.V_ORDER_PART_ALLOCATION
UNION ALL
SELECT 'SUPPLIER_FAILURE_ALLOCATION_NOT_OVER_SUPPLY',
       COUNT(*)
         FROM (
           SELECT plant_id,part_id,
                  MAX(available_part_units) AS available_units,
                  SUM(allocated_part_units) AS allocated_units
           FROM SCENARIOS.V_ORDER_PART_ALLOCATION
           GROUP BY plant_id,part_id
           HAVING SUM(allocated_part_units) > MAX(available_part_units) + 0.01
         ),
       IFF(COUNT(*)=0,'PASS','FAIL')
FROM SCENARIOS.V_ORDER_PART_ALLOCATION
UNION ALL
SELECT 'SUPPLIER_FAILURE_TRACE_ONLY_FOR_SHORTAGE',
       COUNT_IF(unmet_part_units <= 0),
       IFF(COUNT_IF(unmet_part_units <= 0)=0,'PASS','FAIL')
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
