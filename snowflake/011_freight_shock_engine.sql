-- NEXUS freight shock engine
-- Models increased freight cost and compares qualified sourcing options.
-- This is a cost scenario, not an autonomous procurement action.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE VIEW SCENARIOS.V_ACTIVE_FREIGHT_SHOCK_PARAMETERS AS
SELECT
    30::NUMBER(8,4) AS freight_increase_pct,
    '2026-09-18'::DATE AS start_date,
    14::NUMBER(10,0) AS duration_days;

CREATE OR REPLACE VIEW SCENARIOS.V_FREIGHT_SHOCK_OPTION_COST AS
WITH p AS (SELECT * FROM SCENARIOS.V_ACTIVE_FREIGHT_SHOCK_PARAMETERS),
required AS (
    SELECT part_id, SUM(required_part_units) AS required_units
    FROM SCENARIOS.V_ORDER_PART_DEMAND
    GROUP BY part_id
),
options AS (
    SELECT
        q.part_id,
        q.supplier_id,
        q.supplier_name,
        q.unit_cost,
        q.max_daily_capacity_units,
        q.lead_time_days,
        q.expedite_cost_pct,
        r.required_units,
        GREATEST(r.required_units - q.max_daily_capacity_units * p.duration_days,0) AS uncovered_units,
        LEAST(r.required_units,q.max_daily_capacity_units * p.duration_days) AS protected_units,
        LEAST(r.required_units,q.max_daily_capacity_units * p.duration_days) * q.unit_cost * (1 + p.freight_increase_pct/100) AS modeled_freight_cost
    FROM required r
    JOIN ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS q ON q.part_id = r.part_id
    CROSS JOIN p
)
SELECT
    part_id,
    supplier_id,
    supplier_name,
    lead_time_days,
    required_units,
    protected_units,
    uncovered_units,
    modeled_freight_cost,
    'Modeled source capacity cost including configured freight increase; excludes contractual, tax and route-specific charges.' AS calculation_note
FROM options;

CREATE OR REPLACE VIEW SCENARIOS.V_FREIGHT_SHOCK_SUMMARY AS
WITH p AS (SELECT * FROM SCENARIOS.V_ACTIVE_FREIGHT_SHOCK_PARAMETERS),
parts AS (
    SELECT
        part_id,
        MIN(modeled_freight_cost) AS lowest_modeled_cost,
        SUM(protected_units) AS modeled_protected_units,
        SUM(uncovered_units) AS modeled_uncovered_units
    FROM SCENARIOS.V_FREIGHT_SHOCK_OPTION_COST
    GROUP BY part_id
)
SELECT
    p.freight_increase_pct,
    p.start_date,
    p.duration_days,
    COUNT(*) AS parts_analyzed,
    COALESCE(SUM(modeled_protected_units),0) AS modeled_protected_units,
    COALESCE(SUM(modeled_uncovered_units),0) AS modeled_uncovered_units,
    COALESCE(SUM(lowest_modeled_cost),0) AS modeled_minimum_source_cost
FROM p CROSS JOIN parts
GROUP BY p.freight_increase_pct,p.start_date,p.duration_days;

CREATE OR REPLACE VIEW SCENARIOS.V_FREIGHT_SHOCK_CHAIN AS
SELECT
    part_id,
    supplier_id,
    supplier_name,
    required_units,
    protected_units,
    uncovered_units,
    modeled_freight_cost,
    lead_time_days,
    calculation_note
FROM SCENARIOS.V_FREIGHT_SHOCK_OPTION_COST;

-- Demo:
-- SELECT * FROM SCENARIOS.V_FREIGHT_SHOCK_SUMMARY;
-- SELECT * FROM SCENARIOS.V_FREIGHT_SHOCK_CHAIN ORDER BY part_id, modeled_freight_cost;
