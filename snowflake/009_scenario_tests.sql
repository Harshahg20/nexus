-- NEXUS scenario regression checks.
-- These queries are intended to be run after 001-008 in a test/demo environment.
-- A check returns PASS when its invariant holds.

USE DATABASE NEXUS_DB;

-- 1. Every BOM component must have at least one qualified source.
SELECT
    'BOM_PARTS_HAVE_SOURCE' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM RAW.PRODUCT_PARTS pp
WHERE NOT EXISTS (
    SELECT 1
    FROM RAW.SUPPLIER_PARTS sp
    WHERE sp.part_id = pp.part_id
      AND sp.qualification_status = 'QUALIFIED'
);

-- 2. Supplier-part primary relationship must not be duplicated.
SELECT
    'NO_DUPLICATE_SUPPLIER_PARTS' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM (
    SELECT supplier_id, part_id
    FROM RAW.SUPPLIER_PARTS
    GROUP BY supplier_id, part_id
    HAVING COUNT(*) > 1
);

-- 3. Allocation cannot exceed the scenario supply available to a plant/part.
SELECT
    'ALLOCATION_DOES_NOT_EXCEED_SUPPLY' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM (
    SELECT
        a.plant_id,
        a.part_id,
        MAX(a.available_part_units) AS available_units,
        SUM(a.allocated_part_units) AS allocated_units
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION a
    GROUP BY a.plant_id, a.part_id
    HAVING SUM(a.allocated_part_units) > MAX(a.available_part_units) + 0.0001
);

-- 4. An order cannot be shown with negative at-risk quantity.
SELECT
    'NO_NEGATIVE_ORDER_RISK' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM SCENARIOS.V_ORDER_IMPACT
WHERE at_risk_quantity < -0.0001;

-- 5. At-risk revenue cannot exceed order value or be negative.
SELECT
    'REVENUE_RISK_BOUNDS' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM SCENARIOS.V_ORDER_IMPACT
WHERE at_risk_revenue < -0.01
   OR at_risk_revenue > order_value + 0.01;

-- 6. Every impacted order must have a traceable shortage component.
SELECT
    'RISK_HAS_COMPONENT_TRACE' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM SCENARIOS.V_ORDER_IMPACT oi
WHERE oi.at_risk_quantity > 0
  AND NOT EXISTS (
      SELECT 1
      FROM SCENARIOS.V_ORDER_PART_ALLOCATION oa
      WHERE oa.order_id = oi.order_id
        AND oa.unmet_part_units > 0
  );

-- 7. Supplier failure must only trace to the failed supplier's qualified parts.
SELECT
    'TRACE_USES_QUALIFIED_FAILED_SUPPLIER' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL') AS result,
    COUNT(*) AS violations
FROM SCENARIOS.V_SUPPLIER_FAILURE_CHAIN ch
WHERE NOT EXISTS (
    SELECT 1
    FROM RAW.SUPPLIER_PARTS sp
    JOIN SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS p
      ON p.failed_supplier_id = sp.supplier_id
    WHERE sp.supplier_id = ch.supplier_id
      AND sp.part_id = ch.part_id
      AND sp.qualification_status = 'QUALIFIED'
);

-- 8. Sanity snapshot for demo QA.
SELECT
    'SCENARIO_SANITY_SNAPSHOT' AS test_name,
    (SELECT COUNT(*) FROM SCENARIOS.V_ORDER_PART_DEMAND) AS order_part_rows,
    (SELECT COUNT(*) FROM SCENARIOS.V_ORDER_IMPACT WHERE at_risk_quantity > 0) AS orders_at_risk,
    (SELECT COALESCE(SUM(at_risk_revenue),0) FROM SCENARIOS.V_ORDER_IMPACT) AS revenue_exposure,
    (SELECT COUNT(DISTINCT part_id) FROM SCENARIOS.V_ORDER_PART_ALLOCATION WHERE unmet_part_units > 0) AS affected_parts;
