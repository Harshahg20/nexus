-- NEXUS extended scenario validation and regression tests — Phase 8
-- Run AFTER scripts 001–014 in a deployed NEXUS_DB environment.
-- Every SELECT returns: test_name, result (PASS/FAIL), violation_count, note.
-- A production-ready deployment must show result = 'PASS' for all tests.

USE DATABASE NEXUS_DB;

-- =============================================================================
-- GROUP A — DATA MODEL INTEGRITY
-- =============================================================================

-- A1. Every BOM component must have at least one QUALIFIED supplier.
SELECT
    'A1_BOM_PARTS_HAVE_QUALIFIED_SOURCE' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'BOM parts with no qualified supplier in SUPPLIER_PARTS' AS note
FROM RAW.PRODUCT_PARTS pp
WHERE NOT EXISTS (
    SELECT 1 FROM RAW.SUPPLIER_PARTS sp
    WHERE sp.part_id = pp.part_id AND sp.qualification_status = 'QUALIFIED'
);

-- A2. Supplier-part qualification must not have duplicated (supplier_id, part_id) PKs.
SELECT
    'A2_NO_DUPLICATE_SUPPLIER_PARTS'     AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Duplicate (supplier_id, part_id) rows in SUPPLIER_PARTS' AS note
FROM (
    SELECT supplier_id, part_id
    FROM RAW.SUPPLIER_PARTS
    GROUP BY supplier_id, part_id
    HAVING COUNT(*) > 1
);

-- A3. Every OPEN order references a valid product, customer, and plant.
SELECT
    'A3_OPEN_ORDERS_HAVE_VALID_REFERENCES' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')     AS result,
    COUNT(*)                               AS violation_count,
    'OPEN orders with missing product, customer, or plant' AS note
FROM RAW.ORDERS o
WHERE o.status = 'OPEN'
  AND (
      NOT EXISTS (SELECT 1 FROM RAW.PRODUCTS p WHERE p.product_id = o.product_id)
   OR NOT EXISTS (SELECT 1 FROM RAW.CUSTOMERS c WHERE c.customer_id = o.customer_id)
   OR NOT EXISTS (SELECT 1 FROM RAW.PLANTS pl WHERE pl.plant_id = o.plant_id)
  );

-- A4. Inventory records reference valid plants and parts.
SELECT
    'A4_INVENTORY_REFERENCES_VALID'      AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Inventory rows with missing plant or part reference' AS note
FROM RAW.INVENTORY i
WHERE NOT EXISTS (SELECT 1 FROM RAW.PLANTS pl WHERE pl.plant_id = i.plant_id)
   OR NOT EXISTS (SELECT 1 FROM RAW.PARTS p WHERE p.part_id = i.part_id);

-- A5. Safety stock must not exceed on-hand units by more than a reasonable amount.
--     (Very large deficits suggest seeding errors.)
SELECT
    'A5_SAFETY_STOCK_REASONABLE'         AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Inventory rows where safety_stock > 10x on_hand_units' AS note
FROM RAW.INVENTORY
WHERE safety_stock_units > on_hand_units * 10;

-- A6. All shipments reference valid supplier, part, plant, and port.
SELECT
    'A6_SHIPMENTS_HAVE_VALID_REFERENCES' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Shipments with missing supplier, part, plant, or port' AS note
FROM RAW.SHIPMENTS sh
WHERE NOT EXISTS (SELECT 1 FROM RAW.SUPPLIERS s WHERE s.supplier_id = sh.supplier_id)
   OR NOT EXISTS (SELECT 1 FROM RAW.PARTS p WHERE p.part_id = sh.part_id)
   OR NOT EXISTS (SELECT 1 FROM RAW.PLANTS pl WHERE pl.plant_id = sh.plant_id)
   OR (sh.port_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM RAW.PORTS po WHERE po.port_id = sh.port_id));

-- =============================================================================
-- GROUP B — SUPPLIER FAILURE SCENARIO INTEGRITY
-- =============================================================================

-- B1. Allocation per order-part row cannot exceed that row's required units.
SELECT
    'B1_ALLOCATION_NOT_OVER_DEMAND'      AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Order-part rows where allocated_part_units > required_part_units' AS note
FROM SCENARIOS.V_ORDER_PART_ALLOCATION
WHERE allocated_part_units > required_part_units + 0.0001;

-- B2. Total allocation per plant/part must not exceed scenario supply.
SELECT
    'B2_ALLOCATION_NOT_OVER_SUPPLY'      AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Plant/part groups where SUM(allocated) > MAX(available)' AS note
FROM (
    SELECT
        plant_id,
        part_id,
        MAX(available_part_units)     AS available_units,
        SUM(allocated_part_units)     AS allocated_units
    FROM SCENARIOS.V_ORDER_PART_ALLOCATION
    GROUP BY plant_id, part_id
    HAVING SUM(allocated_part_units) > MAX(available_part_units) + 0.0001
);

-- B3. No order can have negative at-risk quantity.
SELECT
    'B3_NO_NEGATIVE_ORDER_RISK'          AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Orders with at_risk_quantity < 0' AS note
FROM SCENARIOS.V_ORDER_IMPACT
WHERE at_risk_quantity < -0.0001;

-- B4. At-risk revenue cannot exceed order value or be negative.
SELECT
    'B4_REVENUE_RISK_BOUNDS'             AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Orders where at_risk_revenue < 0 or > order_value' AS note
FROM SCENARIOS.V_ORDER_IMPACT
WHERE at_risk_revenue < -0.01
   OR at_risk_revenue > order_value + 0.01;

-- B5. The active supplier failure must create at least one order at risk.
SELECT
    'B5_FAILURE_CREATES_IMPACT'          AS test_name,
    IFF(COUNT(*) > 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Count of orders at risk under active supplier failure (must be > 0)' AS note
FROM SCENARIOS.V_ORDER_IMPACT
WHERE at_risk_quantity > 0;

-- B6. Supplier failure chain only traces to the failed supplier's qualified parts.
SELECT
    'B6_CHAIN_USES_QUALIFIED_FAILED_SUPPLIER' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')         AS result,
    COUNT(*)                                    AS violation_count,
    'Chain rows whose part is NOT in the failed supplier''s qualified portfolio' AS note
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

-- B7. Every order in the chain has a confirmed unmet part demand.
SELECT
    'B7_CHAIN_ONLY_FOR_ACTUAL_SHORTAGES' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Chain rows where unmet_part_units <= 0 (trace without actual shortage)' AS note
FROM SCENARIOS.V_SUPPLIER_FAILURE_CHAIN
WHERE unmet_part_units <= 0;

-- B8. Scenario supply must not exceed baseline supply (failure can only reduce supply).
SELECT
    'B8_SCENARIO_SUPPLY_LE_BASELINE'     AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Plant/part rows where scenario_available_units > baseline_available_units' AS note
FROM SCENARIOS.V_SCENARIO_PART_SUPPLY s
JOIN SCENARIOS.V_BASELINE_PART_SUPPLY b
  ON b.plant_id = s.plant_id AND b.part_id = s.part_id
WHERE s.scenario_available_units > b.baseline_available_units + 0.0001;

-- =============================================================================
-- GROUP C — MITIGATION INTEGRITY
-- =============================================================================

-- C1. All four mitigation types must appear in the comparison.
SELECT
    'C1_ALL_FOUR_MITIGATIONS_PRESENT'    AS test_name,
    IFF(COUNT(DISTINCT mitigation_type) = 4, 'PASS', 'FAIL') AS result,
    COUNT(DISTINCT mitigation_type)       AS violation_count,
    'Distinct mitigation types in V_MITIGATION_COMPARISON (expect 4)' AS note
FROM SCENARIOS.V_MITIGATION_COMPARISON;

-- C2. NO_ACTION must have 0 incremental cost.
SELECT
    'C2_NO_ACTION_ZERO_COST'             AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'NO_ACTION rows with non-zero modeled_incremental_cost' AS note
FROM SCENARIOS.V_MITIGATION_COMPARISON
WHERE mitigation_type = 'NO_ACTION' AND ABS(modeled_incremental_cost) > 0.01;

-- C3. ALTERNATE_SUPPLIER must have lower remaining exposure than NO_ACTION.
SELECT
    'C3_ALTERNATE_BETTER_THAN_NO_ACTION' AS test_name,
    IFF(
        (SELECT remaining_revenue_exposure FROM SCENARIOS.V_MITIGATION_COMPARISON WHERE mitigation_type = 'ALTERNATE_SUPPLIER')
        <
        (SELECT remaining_revenue_exposure FROM SCENARIOS.V_MITIGATION_COMPARISON WHERE mitigation_type = 'NO_ACTION'),
        'PASS', 'FAIL'
    )                                    AS result,
    0                                    AS violation_count,
    'ALTERNATE_SUPPLIER remaining exposure should be < NO_ACTION remaining exposure' AS note;

-- C4. No mitigation strategy should show negative remaining revenue exposure.
SELECT
    'C4_NO_NEGATIVE_REMAINING_EXPOSURE'  AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Mitigation rows with remaining_revenue_exposure < 0' AS note
FROM SCENARIOS.V_MITIGATION_COMPARISON
WHERE remaining_revenue_exposure < -0.01;

-- C5. Modeled revenue protected must not exceed total baseline at-risk revenue.
SELECT
    'C5_PROTECTED_REVENUE_NOT_OVER_BASELINE' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')        AS result,
    COUNT(*)                                  AS violation_count,
    'Mitigation rows where revenue protected > total baseline at-risk revenue' AS note
FROM SCENARIOS.V_MITIGATION_COMPARISON
WHERE modeled_revenue_protected >
      (SELECT COALESCE(SUM(at_risk_revenue),0) FROM SCENARIOS.V_ORDER_IMPACT) + 0.01;

-- C6. INVENTORY_REALLOCATION incremental cost must be less than ALTERNATE_SUPPLIER cost.
--     (Reallocation uses existing stock at 15% logistics; alternate requires full procurement.)
SELECT
    'C6_REALLOC_CHEAPER_THAN_ALTERNATE'  AS test_name,
    IFF(
        (SELECT modeled_incremental_cost FROM SCENARIOS.V_MITIGATION_COMPARISON WHERE mitigation_type = 'INVENTORY_REALLOCATION')
        <=
        (SELECT modeled_incremental_cost FROM SCENARIOS.V_MITIGATION_COMPARISON WHERE mitigation_type = 'ALTERNATE_SUPPLIER'),
        'PASS', 'FAIL'
    )                                    AS result,
    0                                    AS violation_count,
    'INVENTORY_REALLOCATION cost should be <= ALTERNATE_SUPPLIER cost' AS note;

-- =============================================================================
-- GROUP D — PORT DISRUPTION INTEGRITY
-- =============================================================================

-- D1. Port disruption must create at least one at-risk order.
SELECT
    'D1_PORT_DISRUPTION_CREATES_IMPACT'  AS test_name,
    IFF(COUNT(*) > 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Count of at-risk orders under active port disruption (must be > 0)' AS note
FROM SCENARIOS.V_PORT_DISRUPTION_ORDER_IMPACT
WHERE at_risk_quantity > 0;

-- D2. Port disruption must not show negative revenue exposure.
SELECT
    'D2_PORT_DISRUPTION_NO_NEGATIVE_REVENUE' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')        AS result,
    COUNT(*)                                  AS violation_count,
    'Port disruption orders with at_risk_revenue < 0' AS note
FROM SCENARIOS.V_PORT_DISRUPTION_ORDER_IMPACT
WHERE at_risk_revenue < -0.01;

-- =============================================================================
-- GROUP E — FREIGHT SHOCK INTEGRITY
-- =============================================================================

-- E1. Freight shock must analyze at least one part.
SELECT
    'E1_FREIGHT_SHOCK_ANALYZES_PARTS'    AS test_name,
    IFF(parts_analyzed > 0, 'PASS', 'FAIL') AS result,
    parts_analyzed                        AS violation_count,
    'Number of parts analyzed in freight shock (must be > 0)' AS note
FROM SCENARIOS.V_FREIGHT_SHOCK_SUMMARY;

-- E2. Freight shock must not produce negative modeled costs.
SELECT
    'E2_FREIGHT_SHOCK_NO_NEGATIVE_COST'  AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Freight shock option rows with modeled_freight_cost < 0' AS note
FROM SCENARIOS.V_FREIGHT_SHOCK_CHAIN
WHERE modeled_freight_cost < -0.01;

-- =============================================================================
-- GROUP F — SEMANTIC VIEW & GOVERNANCE
-- =============================================================================

-- F1. SUPPLIER_PARTS must be used for dependency tracing, not SHIPMENTS alone.
--     Verify that the golden dependency query (V_CUSTOMER_SUPPLIER_DEPENDENCY)
--     only returns suppliers with QUALIFIED status.
SELECT
    'F1_DEPENDENCY_VIEW_USES_QUALIFIED_SUPPLIERS' AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')             AS result,
    COUNT(*)                                        AS violation_count,
    'Customer-supplier dependency rows for non-QUALIFIED suppliers' AS note
FROM SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY vcd
WHERE NOT EXISTS (
    SELECT 1
    FROM RAW.SUPPLIER_PARTS sp
    WHERE sp.supplier_id = vcd.supplier_id
      AND sp.qualification_status = 'QUALIFIED'
);

-- F2. All validation checks in V_SCENARIO_VALIDATION must be PASS.
SELECT
    'F2_VALIDATION_VIEW_ALL_PASS'        AS test_name,
    IFF(COUNT(*) = 0, 'PASS', 'FAIL')   AS result,
    COUNT(*)                             AS violation_count,
    'Checks in ANALYTICS.V_SCENARIO_VALIDATION that are not PASS' AS note
FROM ANALYTICS.V_SCENARIO_VALIDATION
WHERE status <> 'PASS';

-- =============================================================================
-- SUMMARY SNAPSHOT — Run last for a quick demo-readiness overview.
-- =============================================================================
SELECT
    'PHASE8_SANITY_SNAPSHOT'                                              AS test_name,
    (SELECT COUNT(*) FROM RAW.SUPPLIERS)                                   AS total_suppliers,
    (SELECT COUNT(*) FROM RAW.PARTS)                                       AS total_parts,
    (SELECT COUNT(*) FROM RAW.ORDERS WHERE status = 'OPEN')               AS open_orders,
    (SELECT COUNT(*) FROM SCENARIOS.V_ORDER_IMPACT WHERE at_risk_quantity > 0) AS orders_at_risk,
    (SELECT COALESCE(SUM(at_risk_revenue),0)
       FROM SCENARIOS.V_ORDER_IMPACT)                                      AS total_revenue_exposure,
    (SELECT COUNT(DISTINCT mitigation_type)
       FROM SCENARIOS.V_MITIGATION_COMPARISON)                            AS mitigation_strategies,
    (SELECT COUNT(*) FROM ANALYTICS.V_SCENARIO_VALIDATION WHERE status = 'PASS') AS validation_pass_count,
    (SELECT COUNT(*) FROM ANALYTICS.V_SCENARIO_VALIDATION WHERE status = 'FAIL') AS validation_fail_count;
