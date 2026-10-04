-- =============================================================================
-- 017_resilience_score.sql
-- NEXUS — Supply Chain Resilience Score
--
-- Creates a composite 0–100 governance metric that summarises overall supply
-- chain health for executive-level monitoring.
--
-- Score Components (weights sum to 100):
--   Supplier Diversity     (30 pts) — dual-source coverage on critical parts
--   Revenue Buffer         (30 pts) — % of revenue not at risk in active scenario
--   Inventory Buffer       (20 pts) — average days of stock vs 14-day threshold
--   Mitigation Readiness   (20 pts) — % of parts with ≥ 2 qualified suppliers
--
-- Tier:
--   STRONG   ≥ 75   — resilient, monitor quarterly
--   MODERATE 50–74  — elevated risk, review monthly
--   CRITICAL  < 50  — urgent intervention required
--
-- Deployment: run AFTER 006_scenario_engine.sql and 016_interactive_scenarios.sql
-- =============================================================================

USE DATABASE NEXUS_DB;
USE SCHEMA ANALYTICS;

-- ─────────────────────────────────────────────────────────────────────────────
-- V_SUPPLY_CHAIN_RESILIENCE_SCORE — composite 0–100 governance score
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW NEXUS_DB.ANALYTICS.V_SUPPLY_CHAIN_RESILIENCE_SCORE AS
WITH

-- Component 1: Supplier Diversity — 30 points
-- Measures: what % of critical parts have ≥ 2 qualified suppliers?
-- 30 pts when every critical part is dual/multi-sourced; 0 when all are single-source.
supplier_diversity AS (
    SELECT
        COUNT_IF(qualified_supplier_count = 1 AND criticality = 'CRITICAL') AS single_source_critical,
        COUNT_IF(criticality = 'CRITICAL')                                   AS total_critical_parts,
        COUNT_IF(qualified_supplier_count >= 2 AND criticality = 'CRITICAL') AS dual_source_critical,
        30.0 * COUNT_IF(qualified_supplier_count >= 2 AND criticality = 'CRITICAL')
             / NULLIF(COUNT_IF(criticality = 'CRITICAL'), 0)                 AS diversity_score
    FROM (
        SELECT
            sp.part_id,
            p.criticality,
            COUNT(sp.supplier_id) AS qualified_supplier_count
        FROM NEXUS_DB.RAW.SUPPLIER_PARTS sp
        JOIN NEXUS_DB.RAW.PARTS p ON p.part_id = sp.part_id
        WHERE sp.qualification_status = 'QUALIFIED'
        GROUP BY sp.part_id, p.criticality
    )
),

-- Component 2: Revenue Buffer — 30 points
-- Measures: what % of open order revenue is NOT at risk under the active scenario?
-- 30 pts when no revenue is at risk; 0 when all revenue is at risk.
revenue_risk_data AS (
    SELECT
        COALESCE(SUM(order_value), 0) AS total_open_revenue
    FROM NEXUS_DB.RAW.ORDERS
    WHERE status = 'OPEN'
),
scenario_impact AS (
    SELECT COALESCE(revenue_exposure, 0) AS at_risk_revenue
    FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT
),
revenue_buffer AS (
    SELECT
        r.total_open_revenue,
        s.at_risk_revenue,
        ROUND(100.0 * s.at_risk_revenue / NULLIF(r.total_open_revenue, 0), 1) AS at_risk_pct,
        30.0 * GREATEST(1.0 - s.at_risk_revenue / NULLIF(r.total_open_revenue, 0), 0) AS revenue_score
    FROM revenue_risk_data r, scenario_impact s
),

-- Component 3: Inventory Buffer — 20 points
-- Measures: average days of inventory vs 14-day resilience threshold
-- 20 pts at ≥ 14 days average coverage; prorated below.
inventory_buffer AS (
    SELECT
        AVG(on_hand_units / NULLIF(daily_consumption, 0)) AS avg_coverage_days,
        COUNT_IF(on_hand_units < safety_stock_units)      AS below_safety_stock_count,
        COUNT(*)                                          AS total_inventory_records,
        20.0 * LEAST(
            AVG(on_hand_units / NULLIF(daily_consumption, 0)) / 14.0,
            1.0
        )                                                 AS inventory_score
    FROM NEXUS_DB.RAW.INVENTORY
    WHERE daily_consumption > 0
),

-- Component 4: Mitigation Readiness — 20 points
-- Measures: what % of ALL parts have ≥ 2 qualified suppliers (alternate available)?
mitigation_readiness AS (
    SELECT
        COUNT_IF(qualified_supplier_count >= 2) AS dual_source_parts,
        COUNT(*)                                AS total_sourced_parts,
        20.0 * COUNT_IF(qualified_supplier_count >= 2)
             / NULLIF(COUNT(*), 0)              AS mitigation_score
    FROM (
        SELECT part_id, COUNT(supplier_id) AS qualified_supplier_count
        FROM NEXUS_DB.RAW.SUPPLIER_PARTS
        WHERE qualification_status = 'QUALIFIED'
        GROUP BY part_id
    )
)

SELECT
    -- Composite score (0–100)
    ROUND(
        COALESCE(sd.diversity_score,    0) +
        COALESCE(rb.revenue_score,      0) +
        COALESCE(ib.inventory_score,    0) +
        COALESCE(mr.mitigation_score,   0),
        1
    ) AS resilience_score,

    -- Component scores
    ROUND(COALESCE(sd.diversity_score,  0), 1) AS supplier_diversity_score,
    ROUND(COALESCE(rb.revenue_score,    0), 1) AS revenue_buffer_score,
    ROUND(COALESCE(ib.inventory_score,  0), 1) AS inventory_buffer_score,
    ROUND(COALESCE(mr.mitigation_score, 0), 1) AS mitigation_readiness_score,

    -- Supporting facts for tooltip/drill-down
    sd.single_source_critical,
    sd.total_critical_parts,
    sd.dual_source_critical,
    rb.total_open_revenue,
    rb.at_risk_revenue,
    rb.at_risk_pct                           AS revenue_at_risk_pct,
    ROUND(ib.avg_coverage_days, 1)           AS avg_inventory_coverage_days,
    ib.below_safety_stock_count,
    mr.dual_source_parts,
    mr.total_sourced_parts,

    -- Tier classification
    CASE
        WHEN ROUND(
            COALESCE(sd.diversity_score, 0) + COALESCE(rb.revenue_score, 0) +
            COALESCE(ib.inventory_score, 0) + COALESCE(mr.mitigation_score, 0), 1
        ) >= 75 THEN 'STRONG'
        WHEN ROUND(
            COALESCE(sd.diversity_score, 0) + COALESCE(rb.revenue_score, 0) +
            COALESCE(ib.inventory_score, 0) + COALESCE(mr.mitigation_score, 0), 1
        ) >= 50 THEN 'MODERATE'
        ELSE 'CRITICAL'
    END AS resilience_tier

FROM supplier_diversity sd, revenue_buffer rb, inventory_buffer ib, mitigation_readiness mr;

-- ─────────────────────────────────────────────────────────────────────────────
-- Verification
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    resilience_score,
    resilience_tier,
    supplier_diversity_score,
    revenue_buffer_score,
    inventory_buffer_score,
    mitigation_readiness_score,
    single_source_critical,
    total_critical_parts,
    revenue_at_risk_pct,
    avg_inventory_coverage_days
FROM NEXUS_DB.ANALYTICS.V_SUPPLY_CHAIN_RESILIENCE_SCORE;
