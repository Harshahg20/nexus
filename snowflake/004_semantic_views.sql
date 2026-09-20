-- NEXUS governed analytical views.
-- These views establish a deterministic foundation before Cortex Agent integration.

USE DATABASE NEXUS_DB;

CREATE SCHEMA IF NOT EXISTS SEMANTIC;
CREATE SCHEMA IF NOT EXISTS ANALYTICS;
CREATE SCHEMA IF NOT EXISTS SCENARIOS;

CREATE OR REPLACE VIEW ANALYTICS.SUPPLY_CHAIN_RISK AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.sla_tier,
    o.product_id,
    p.product_name,
    o.plant_id,
    o.quantity AS order_quantity,
    o.order_value,
    o.due_date,
    o.priority,
    o.status AS order_status
FROM RAW.ORDERS o
JOIN RAW.CUSTOMERS c ON c.customer_id = o.customer_id
JOIN RAW.PRODUCTS p ON p.product_id = o.product_id;

-- SOURCING GOVERNANCE: Use RAW.SUPPLIER_PARTS as the authoritative supplier-part
-- qualification relationship. Historical shipment activity alone does not
-- establish that a supplier is an approved source for a part. Only records with
-- qualification_status = 'QUALIFIED' represent governed sourcing relationships.
CREATE OR REPLACE VIEW ANALYTICS.SUPPLIER_PART_DEPENDENCY AS
SELECT DISTINCT
    s.supplier_id,
    s.supplier_name,
    s.risk_tier,
    s.status AS supplier_status,
    p.part_id,
    p.part_name,
    p.criticality,
    p.unit_cost
FROM RAW.SUPPLIERS s
JOIN RAW.SUPPLIER_PARTS sp
    ON sp.supplier_id = s.supplier_id
    AND sp.qualification_status = 'QUALIFIED'
JOIN RAW.PARTS p ON p.part_id = sp.part_id;

CREATE OR REPLACE VIEW ANALYTICS.PART_PLANT_INVENTORY AS
SELECT
    i.plant_id,
    pl.plant_name,
    i.part_id,
    p.part_name,
    p.criticality,
    i.on_hand_units,
    i.safety_stock_units,
    i.daily_consumption,
    ROUND(i.on_hand_units / NULLIF(i.daily_consumption,0), 2) AS inventory_coverage_days,
    GREATEST(i.on_hand_units - i.safety_stock_units, 0) AS usable_inventory_units
FROM RAW.INVENTORY i
JOIN RAW.PLANTS pl ON pl.plant_id = i.plant_id
JOIN RAW.PARTS p ON p.part_id = i.part_id;

CREATE OR REPLACE VIEW ANALYTICS.PRODUCT_DEPENDENCY AS
SELECT
    pp.product_id,
    pr.product_name,
    pp.part_id,
    p.part_name,
    p.criticality,
    pp.units_per_product,
    pp.is_critical_path
FROM RAW.PRODUCT_PARTS pp
JOIN RAW.PRODUCTS pr ON pr.product_id = pp.product_id
JOIN RAW.PARTS p ON p.part_id = pp.part_id;

CREATE OR REPLACE VIEW ANALYTICS.ORDER_PART_REQUIREMENTS AS
SELECT
    o.order_id,
    o.customer_id,
    o.product_id,
    o.plant_id,
    pp.part_id,
    pp.units_per_product,
    o.quantity AS order_quantity,
    o.quantity * pp.units_per_product AS required_part_units,
    o.order_value,
    o.due_date,
    o.sla_tier,
    o.priority
FROM RAW.ORDERS o
JOIN RAW.PRODUCT_PARTS pp ON pp.product_id = o.product_id;

CREATE OR REPLACE VIEW ANALYTICS.SUPPLIER_CONCENTRATION AS
SELECT
    part_id,
    COUNT(DISTINCT supplier_id) AS qualified_supplier_count,
    COUNT(DISTINCT supplier_id) = 1 AS is_single_source
FROM ANALYTICS.SUPPLIER_PART_DEPENDENCY
WHERE supplier_status = 'ACTIVE'
GROUP BY part_id;

CREATE OR REPLACE VIEW ANALYTICS.DELAYED_SHIPMENTS AS
SELECT
    sh.shipment_id,
    sh.supplier_id,
    s.supplier_name,
    sh.part_id,
    p.part_name,
    sh.plant_id,
    pl.plant_name,
    sh.port_id,
    po.port_name,
    sh.quantity,
    sh.ship_date,
    sh.expected_arrival,
    sh.status
FROM RAW.SHIPMENTS sh
JOIN RAW.SUPPLIERS s ON s.supplier_id = sh.supplier_id
JOIN RAW.PARTS p ON p.part_id = sh.part_id
JOIN RAW.PLANTS pl ON pl.plant_id = sh.plant_id
JOIN RAW.PORTS po ON po.port_id = sh.port_id
WHERE sh.status = 'DELAYED';

-- Canonical governed question helper views.
CREATE OR REPLACE VIEW SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY AS
SELECT DISTINCT
    o.customer_id,
    c.customer_name,
    o.order_id,
    o.product_id,
    pr.product_name,
    pp.part_id,
    pp.part_name,
    sp.supplier_id,
    sp.supplier_name,
    sp.criticality
FROM RAW.ORDERS o
JOIN RAW.CUSTOMERS c ON c.customer_id = o.customer_id
JOIN RAW.PRODUCT_PARTS pp0 ON pp0.product_id = o.product_id
JOIN RAW.PARTS pp ON pp.part_id = pp0.part_id
JOIN ANALYTICS.SUPPLIER_PART_DEPENDENCY sp ON sp.part_id = pp.part_id
JOIN RAW.PRODUCTS pr ON pr.product_id = o.product_id;

CREATE OR REPLACE VIEW SEMANTIC.V_SHIPMENT_EXPOSURE AS
SELECT
    sh.shipment_id,
    sh.supplier_id,
    s.supplier_name,
    sh.part_id,
    p.part_name,
    sh.plant_id,
    pl.plant_name,
    sh.port_id,
    po.port_name,
    sh.quantity,
    sh.expected_arrival,
    sh.status
FROM RAW.SHIPMENTS sh
JOIN RAW.SUPPLIERS s ON s.supplier_id = sh.supplier_id
JOIN RAW.PARTS p ON p.part_id = sh.part_id
JOIN RAW.PLANTS pl ON pl.plant_id = sh.plant_id
JOIN RAW.PORTS po ON po.port_id = sh.port_id;
