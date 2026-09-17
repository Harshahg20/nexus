-- Golden queries used to validate the NEXUS MVP.

USE DATABASE NEXUS_DB;

-- Q1: Which customers depend on SUP-001?
SELECT DISTINCT
    customer_id,
    customer_name,
    product_id,
    product_name,
    part_id,
    part_name
FROM SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
WHERE supplier_id = 'SUP-001';

-- Q2: Which critical parts are single source?
SELECT
    s.part_id,
    p.part_name,
    p.criticality
FROM ANALYTICS.SUPPLIER_CONCENTRATION s
JOIN RAW.PARTS p ON p.part_id = s.part_id
WHERE is_single_source = TRUE;

-- Q3: Which parts have less than 7 days inventory?
SELECT *
FROM ANALYTICS.PART_PLANT_INVENTORY
WHERE inventory_coverage_days < 7;

-- Q4: Which shipments are delayed?
SELECT *
FROM ANALYTICS.DELAYED_SHIPMENTS;

-- Q5: Show dependency path for CUST-003.
SELECT DISTINCT
    customer_name,
    supplier_name,
    part_name,
    product_name
FROM SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
WHERE customer_id = 'CUST-003';

-- Q6: Which products depend on PART-104?
SELECT DISTINCT
    product_id,
    product_name
FROM ANALYTICS.PRODUCT_DEPENDENCY
WHERE part_id = 'PART-104';

-- Q7: Which suppliers provide PART-104?
SELECT DISTINCT
    supplier_id,
    supplier_name
FROM ANALYTICS.SUPPLIER_PART_DEPENDENCY
WHERE part_id = 'PART-104';

-- Q8: Supplier exposure estimation.
SELECT
    supplier_id,
    supplier_name,
    COUNT(DISTINCT customer_id) AS customers_exposed,
    COUNT(DISTINCT order_id) AS orders_exposed
FROM SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
GROUP BY supplier_id, supplier_name
ORDER BY orders_exposed DESC;
