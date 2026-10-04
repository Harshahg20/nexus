-- =============================================================================
-- 016_interactive_scenarios.sql
-- NEXUS — Interactive Scenario Parameterization
--
-- Transforms hard-coded literal views into table-driven parameterization so
-- the Streamlit UI can change supplier, capacity loss, and duration in real
-- time without touching SQL.
--
-- Design:
--   SCENARIOS.SCENARIO_PARAMS (table)  →  stores user-chosen values
--   V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS (view)  →  reads from table
--   V_ACTIVE_PORT_DISRUPTION_PARAMETERS  (view)  →  reads from table
--   All downstream views (V_SUPPLIER_FAILURE_PART_SUPPLY, etc.) are
--   unaffected — they already reference the parameter views above.
--
-- Deployment: run AFTER 006_scenario_engine.sql and 010_port_disruption_engine.sql
-- =============================================================================

USE DATABASE NEXUS_DB;
USE SCHEMA SCENARIOS;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. SCENARIO_PARAMS — user-modifiable scenario parameters table
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS NEXUS_DB.SCENARIOS.SCENARIO_PARAMS (
    scenario_type  VARCHAR(50)   NOT NULL,
    param_key      VARCHAR(100)  NOT NULL,
    param_value    VARCHAR(500)  NOT NULL,
    updated_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_by     VARCHAR(200)  DEFAULT CURRENT_USER(),
    PRIMARY KEY (scenario_type, param_key)
);

-- Seed default values — identical to the original hard-coded literals
MERGE INTO NEXUS_DB.SCENARIOS.SCENARIO_PARAMS t
USING (
    SELECT 'SUPPLIER_FAILURE' AS scenario_type, 'supplier_id'            AS param_key, 'SUP-001'    AS param_value UNION ALL
    SELECT 'SUPPLIER_FAILURE',                   'capacity_reduction_pct',               '100'                     UNION ALL
    SELECT 'SUPPLIER_FAILURE',                   'duration_days',                        '14'                      UNION ALL
    SELECT 'SUPPLIER_FAILURE',                   'start_date',                           '2026-09-18'              UNION ALL
    SELECT 'PORT_DISRUPTION',                    'port_id',                              'PORT-TYO'                UNION ALL
    SELECT 'PORT_DISRUPTION',                    'disruption_pct',                       '100'                     UNION ALL
    SELECT 'PORT_DISRUPTION',                    'duration_days',                        '7'                       UNION ALL
    SELECT 'PORT_DISRUPTION',                    'start_date',                           '2026-09-18'
) s ON t.scenario_type = s.scenario_type AND t.param_key = s.param_key
WHEN MATCHED THEN UPDATE SET
    t.param_value = s.param_value,
    t.updated_at  = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (scenario_type, param_key, param_value)
    VALUES (s.scenario_type, s.param_key, s.param_value);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS — now reads from SCENARIO_PARAMS
--    Replaces the hard-coded literal view in 006_scenario_engine.sql.
--    All downstream views that reference this view automatically pick up
--    the new parameters without any additional changes.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS AS
WITH p AS (
    SELECT
        MAX(CASE WHEN param_key = 'supplier_id'            THEN param_value END)                      AS supplier_id,
        MAX(CASE WHEN param_key = 'capacity_reduction_pct' THEN param_value::NUMBER(8,4) END)         AS capacity_reduction_pct,
        MAX(CASE WHEN param_key = 'duration_days'          THEN param_value::NUMBER(10,0) END)        AS duration_days,
        MAX(CASE WHEN param_key = 'start_date'             THEN TRY_TO_DATE(param_value) END)         AS start_date
    FROM NEXUS_DB.SCENARIOS.SCENARIO_PARAMS
    WHERE scenario_type = 'SUPPLIER_FAILURE'
)
SELECT
    COALESCE(supplier_id,            'SUP-001')::VARCHAR        AS failed_supplier_id,
    COALESCE(capacity_reduction_pct, 100)::NUMBER(8,4)          AS capacity_reduction_pct,
    COALESCE(duration_days,          14)::NUMBER(10,0)          AS duration_days,
    COALESCE(start_date,             '2026-09-18'::DATE)        AS start_date
FROM p;

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. V_ACTIVE_PORT_DISRUPTION_PARAMETERS — now reads from SCENARIO_PARAMS
--    Replaces the hard-coded literal view in 010_port_disruption_engine.sql.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW NEXUS_DB.SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS AS
WITH p AS (
    SELECT
        MAX(CASE WHEN param_key = 'port_id'        THEN param_value END)                  AS port_id,
        MAX(CASE WHEN param_key = 'disruption_pct' THEN param_value::NUMBER(8,4) END)     AS disruption_pct,
        MAX(CASE WHEN param_key = 'duration_days'  THEN param_value::NUMBER(10,0) END)    AS duration_days,
        MAX(CASE WHEN param_key = 'start_date'     THEN TRY_TO_DATE(param_value) END)     AS start_date
    FROM NEXUS_DB.SCENARIOS.SCENARIO_PARAMS
    WHERE scenario_type = 'PORT_DISRUPTION'
)
SELECT
    COALESCE(port_id,        'PORT-TYO')::VARCHAR         AS disrupted_port_id,
    COALESCE(disruption_pct, 100)::NUMBER(8,4)            AS disruption_pct,
    COALESCE(duration_days,  7)::NUMBER(10,0)             AS duration_days,
    COALESCE(start_date,     '2026-09-18'::DATE)          AS start_date
FROM p;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. V_AVAILABLE_SUPPLIERS — drives the supplier dropdown in the UI
--    Note: RAW.SUPPLIERS uses REGION (not SUPPLIER_REGION) and STATUS (not SUPPLIER_STATUS)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW NEXUS_DB.SCENARIOS.V_AVAILABLE_SUPPLIERS AS
SELECT
    s.supplier_id,
    s.supplier_name,
    s.risk_tier,
    s.region          AS supplier_region,
    COUNT(sp.part_id) AS qualified_part_count
FROM NEXUS_DB.RAW.SUPPLIERS s
JOIN NEXUS_DB.RAW.SUPPLIER_PARTS sp
  ON sp.supplier_id = s.supplier_id
 AND sp.qualification_status = 'QUALIFIED'
WHERE s.status = 'ACTIVE'
GROUP BY s.supplier_id, s.supplier_name, s.risk_tier, s.region
ORDER BY s.risk_tier, s.supplier_id;

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. V_AVAILABLE_PORTS — drives the port dropdown in the UI
--    Note: RAW.PORTS uses REGION (not PORT_REGION) and STATUS (not PORT_STATUS)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW NEXUS_DB.SCENARIOS.V_AVAILABLE_PORTS AS
SELECT
    port_id,
    port_name,
    region     AS port_region,
    congestion_level,
    status     AS port_status
FROM NEXUS_DB.RAW.PORTS
WHERE status = 'ACTIVE'
ORDER BY port_id;

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. SCENARIO_PARAM_AUDIT — tracks every parameter change for governance
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS NEXUS_DB.SCENARIOS.SCENARIO_PARAM_AUDIT (
    audit_id       NUMBER AUTOINCREMENT PRIMARY KEY,
    scenario_type  VARCHAR(50),
    param_key      VARCHAR(100),
    old_value      VARCHAR(500),
    new_value      VARCHAR(500),
    changed_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    changed_by     VARCHAR(200)  DEFAULT CURRENT_USER()
);

-- Verification
SELECT 'SCENARIO_PARAMS seeded' AS status, COUNT(*) AS row_count
FROM NEXUS_DB.SCENARIOS.SCENARIO_PARAMS;

SELECT 'V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS' AS view_name, *
FROM NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS;

SELECT 'V_ACTIVE_PORT_DISRUPTION_PARAMETERS' AS view_name, *
FROM NEXUS_DB.SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS;
