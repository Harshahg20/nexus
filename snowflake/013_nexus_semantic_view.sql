-- =============================================================================
-- NEXUS Supply Chain Semantic View
-- File:    013_nexus_semantic_view.sql
-- Object:  NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN
-- =============================================================================
--
-- PURPOSE
-- -------
-- Defines the governed business-language layer for NEXUS conversational
-- analytics. Exposes the core supply-chain ontology — Supplier, Part, Plant,
-- Inventory, Port, Shipment, Product, Order, Customer — with governed metrics,
-- business synonyms, and AI SQL generation rules.
--
-- The Cortex Agent (Phase 3) targets this semantic view for all baseline
-- natural-language analytics. Scenario analysis (supplier failure, port
-- disruption, freight shock) is performed by the deterministic SCENARIOS
-- engine and is NOT exposed through this semantic view.
--
-- SEMANTIC MODEL SCOPE
-- --------------------
-- Logical tables  : 11 (all from NEXUS_DB.RAW)
-- Relationships   : 13 (explicit foreign-key paths through the ontology)
-- Facts           : 9  (row-level computed values and boolean filter flags)
-- Dimensions      : ~50 (business attributes for grouping and filtering)
-- Metrics         : 14 (governed aggregates)
-- Verified queries: 10
--
-- AUTHORITATIVE SOURCING RELATIONSHIP
-- ------------------------------------
-- RAW.SUPPLIER_PARTS is the authoritative supplier-part qualification table.
-- A supplier is considered qualified to supply a part ONLY when a record with
-- qualification_status = 'QUALIFIED' exists in SUPPLIER_PARTS.
-- SHIPMENT history alone does NOT establish supplier qualification.
-- This rule is enforced in FACTS, DIMENSIONS, and AI_SQL_GENERATION.
--
-- GRAIN OF MAJOR ENTITIES
-- -----------------------
-- suppliers         : one row per supplier_id
-- parts             : one row per part_id
-- plants            : one row per plant_id
-- inventory         : one row per (plant_id, part_id) — natural key
-- ports             : one row per port_id
-- shipments         : one row per shipment_id
-- products          : one row per product_id
-- product_parts     : one row per (product_id, part_id) — BOM entry
-- orders            : one row per order_id
-- customers         : one row per customer_id
-- supplier_parts    : one row per (supplier_id, part_id) — qualification entry
--
-- BASELINE vs. SCENARIO DISTINCTION
-- ------------------------------------
-- This semantic view exposes BASELINE, CURRENT-STATE analytics derived from
-- RAW tables. Metrics such as total_order_value and inventory_coverage_days
-- reflect actual observed data, not modeled disruption scenarios.
--
-- "Orders at risk" under a disruption scenario and "revenue exposure" due to
-- a supplier failure are MODELED outputs produced by:
--   SCENARIOS.V_ORDER_IMPACT
--   SCENARIOS.V_SUPPLIER_FAILURE_IMPACT
--   SCENARIOS.V_PORT_DISRUPTION_IMPACT
-- Those views are outside this semantic model and must not be presented as
-- observed baseline facts.
--
-- WHY SUPPLIER_PARTS IS AUTHORITATIVE (not SHIPMENTS)
-- -----------------------------------------------------
-- Historical shipment activity indicates that parts were shipped by a supplier
-- in the past; it does not mean the supplier is currently approved to supply
-- those parts. Qualification requires explicit review and approval, recorded
-- in SUPPLIER_PARTS. Using SHIPMENTS to infer qualification would silently
-- include expired or unapproved sources in dependency analysis, violating the
-- governance intent of the NEXUS data model.
--
-- WHY SCENARIO LOGIC IS OUTSIDE THIS SEMANTIC VIEW
-- -------------------------------------------------
-- Native Semantic View metrics are aggregate functions on observed RAW data.
-- Scenario impact (e.g., "orders at risk if SUP-001 fails for 14 days")
-- requires deterministic multi-step propagation: remove failed-supplier inbound
-- from baseline supply, re-run order allocation by priority, compute unmet
-- demand at order and customer level. This logic is encoded in the SCENARIOS
-- views (006–011). Embedding it here would either require complex subquery
-- logical tables (obscuring the model) or produce incorrect results.
-- The Cortex Agent tool contract explicitly separates governed baseline
-- analytics (this semantic view) from modeled scenario analysis (SCENARIOS).
--
-- DEPLOYMENT ORDER
-- ----------------
-- Must be run AFTER: 001, 002, 003, 004, 006, 007, 008, 009, 010, 011, 012
-- =============================================================================

USE DATABASE NEXUS_DB;
USE SCHEMA SEMANTIC;

CREATE OR REPLACE SEMANTIC VIEW NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN

-- =============================================================================
-- TABLES — 11 logical tables from the NEXUS RAW supply-chain ontology
-- =============================================================================
TABLES (

  -- Supplier: companies that provide parts to manufacturing plants.
  -- Risk tier and status drive sourcing risk analysis.
  suppliers AS NEXUS_DB.RAW.SUPPLIERS
    PRIMARY KEY (supplier_id)
    WITH SYNONYMS ('vendor', 'vendors', 'supplier list', 'source')
    COMMENT = 'Approved suppliers and vendors in the NEXUS supply chain. Grain: supplier_id.',

  -- Part: components consumed by plants to manufacture products.
  -- criticality = CRITICAL means a shortage directly stops production.
  parts AS NEXUS_DB.RAW.PARTS
    PRIMARY KEY (part_id)
    WITH SYNONYMS ('component', 'components', 'material', 'component part', 'raw material')
    COMMENT = 'Parts and components consumed in manufacturing. Grain: part_id.',

  -- Plant: manufacturing and assembly facilities that hold inventory and fulfil orders.
  plants AS NEXUS_DB.RAW.PLANTS
    PRIMARY KEY (plant_id)
    WITH SYNONYMS ('factory', 'factories', 'facility', 'facilities', 'manufacturing plant', 'site')
    COMMENT = 'Manufacturing and assembly plants. Grain: plant_id.',

  -- Inventory: on-hand stock of a specific part at a specific plant.
  -- The natural business key is (plant_id, part_id).
  inventory AS NEXUS_DB.RAW.INVENTORY
    PRIMARY KEY (inventory_id)
    UNIQUE (plant_id, part_id)
    WITH SYNONYMS ('stock', 'on-hand stock', 'parts inventory')
    COMMENT = 'On-hand inventory of a part at a plant. Grain: (plant_id, part_id). Coverage = on_hand_units / daily_consumption.',

  -- Port: logistics gateways through which inbound shipments pass.
  ports AS NEXUS_DB.RAW.PORTS
    PRIMARY KEY (port_id)
    WITH SYNONYMS ('logistics gateway', 'shipping port', 'harbour')
    COMMENT = 'Sea or logistics ports used by inbound shipments. Grain: port_id.',

  -- Shipment: a movement of a part from a supplier to a plant via a port.
  -- One shipment carries one part from one supplier to one plant.
  shipments AS NEXUS_DB.RAW.SHIPMENTS
    PRIMARY KEY (shipment_id)
    WITH SYNONYMS ('inbound shipment', 'delivery', 'inbound delivery', 'shipment record')
    COMMENT = 'Inbound shipment of a part from a supplier to a plant via a port. Grain: shipment_id.',

  -- Product: a finished good assembled from parts. Products fulfil orders.
  products AS NEXUS_DB.RAW.PRODUCTS
    PRIMARY KEY (product_id)
    WITH SYNONYMS ('finished good', 'finished goods', 'manufactured product', 'SKU')
    COMMENT = 'Finished products assembled from components. Grain: product_id.',

  -- Product-Part (BOM): the bill of materials mapping products to their component parts.
  -- is_critical_path = TRUE means a shortage of this part directly blocks product assembly.
  -- GRAIN WARNING: joining orders → products → product_parts → parts multiplies order rows
  -- by the number of BOM entries. Always aggregate order metrics at order_id grain.
  product_parts AS NEXUS_DB.RAW.PRODUCT_PARTS
    UNIQUE (product_id, part_id)
    WITH SYNONYMS ('bill of materials', 'BOM', 'product components', 'component list')
    COMMENT = 'Bill of materials: which parts and how many are required per product unit. Grain: (product_id, part_id). Joining orders through this table multiplies order rows by BOM depth.',

  -- Order: a customer demand record for a specific product at a specific plant.
  -- order_value is the total monetary value. Grain is order_id.
  orders AS NEXUS_DB.RAW.ORDERS
    PRIMARY KEY (order_id)
    WITH SYNONYMS ('customer order', 'sales order', 'demand', 'customer demand')
    COMMENT = 'Customer orders for finished products. Grain: order_id. Do not join through product_parts when computing order_value to prevent revenue multiplication.',

  -- Customer: the end buyer of products. Linked to orders.
  customers AS NEXUS_DB.RAW.CUSTOMERS
    PRIMARY KEY (customer_id)
    WITH SYNONYMS ('client', 'account', 'buyer', 'end customer')
    COMMENT = 'Customers who place orders for finished products. Grain: customer_id.',

  -- Supplier-Part Sourcing: the AUTHORITATIVE table for supplier qualification.
  -- Only records with qualification_status = QUALIFIED represent governed sourcing.
  -- CRITICAL GOVERNANCE RULE: use this table — not SHIPMENTS — to determine
  -- whether a supplier is approved to supply a part.
  supplier_parts AS NEXUS_DB.RAW.SUPPLIER_PARTS
    PRIMARY KEY (supplier_id, part_id)
    WITH SYNONYMS ('supplier qualification', 'sourcing relationship', 'approved source',
                   'supplier approval', 'qualified sourcing')
    COMMENT = 'Authoritative supplier-part qualification table. A supplier is qualified to supply a part only when qualification_status = QUALIFIED. Do not use SHIPMENTS to infer qualification. Grain: (supplier_id, part_id).'

)

-- =============================================================================
-- RELATIONSHIPS — 13 explicit joins through the supply-chain ontology
-- =============================================================================
RELATIONSHIPS (

  -- Supplier qualification: each SUPPLIER_PARTS row ties a supplier to a part.
  -- This is the governed Supplier → Part sourcing path.
  sourcing_to_supplier AS
    supplier_parts (supplier_id) REFERENCES suppliers (supplier_id),

  sourcing_to_part AS
    supplier_parts (part_id) REFERENCES parts (part_id),

  -- Inventory: each inventory record belongs to one plant and holds one part.
  inventory_to_plant AS
    inventory (plant_id) REFERENCES plants (plant_id),

  inventory_to_part AS
    inventory (part_id) REFERENCES parts (part_id),

  -- Shipment: each shipment comes from one supplier, carries one part,
  -- arrives at one plant, and passes through one port.
  shipment_to_supplier AS
    shipments (supplier_id) REFERENCES suppliers (supplier_id),

  shipment_to_part AS
    shipments (part_id) REFERENCES parts (part_id),

  shipment_to_plant AS
    shipments (plant_id) REFERENCES plants (plant_id),

  shipment_to_port AS
    shipments (port_id) REFERENCES ports (port_id),

  -- BOM: each product-part entry maps one product to one component.
  bom_to_product AS
    product_parts (product_id) REFERENCES products (product_id),

  bom_to_part AS
    product_parts (part_id) REFERENCES parts (part_id),

  -- Order: each order is for one product, fulfilled by one plant, placed by one customer.
  order_to_product AS
    orders (product_id) REFERENCES products (product_id),

  order_to_customer AS
    orders (customer_id) REFERENCES customers (customer_id),

  order_to_plant AS
    orders (plant_id) REFERENCES plants (plant_id)

)

-- =============================================================================
-- FACTS — Row-level computed values and boolean filter flags.
-- FACTS clause must precede DIMENSIONS.
-- =============================================================================
FACTS (

  -- ── Inventory facts ──────────────────────────────────────────────────────

  -- Usable inventory: on-hand units above safety stock. This is the quantity
  -- available for order fulfillment without touching the safety buffer.
  inventory.usable_inventory_units
    AS GREATEST(on_hand_units - safety_stock_units, 0)
    WITH SYNONYMS ('usable stock', 'fulfillable inventory', 'net available inventory',
                   'available above safety stock')
    COMMENT = 'On-hand inventory units above safety stock. Used in supply calculations.',

  -- Inventory coverage days: how many days of consumption can current stock support.
  -- Used as input to avg_coverage_days and min_coverage_days metrics.
  inventory.coverage_days
    AS on_hand_units / NULLIF(daily_consumption, 0)
    WITH SYNONYMS ('inventory days', 'days of stock', 'stock duration')
    COMMENT = 'Days of inventory remaining at current consumption rate (on_hand_units / daily_consumption). NULL when daily_consumption = 0.',

  -- Boolean flag: inventory below safety stock threshold.
  inventory.is_below_safety_stock
    LABELS = (FILTER)
    AS on_hand_units < safety_stock_units
    COMMENT = 'TRUE when on-hand inventory is below the safety stock level.',

  -- ── Shipment facts ───────────────────────────────────────────────────────

  -- Boolean flag: this shipment is DELAYED.
  shipments.is_delayed
    LABELS = (FILTER)
    AS status = 'DELAYED'
    WITH SYNONYMS ('delayed', 'late shipment', 'overdue')
    COMMENT = 'TRUE when shipment status is DELAYED.',

  -- Boolean flag: shipment is still in transit or delayed (not yet delivered).
  shipments.is_active_inbound
    LABELS = (FILTER)
    AS status IN ('IN_TRANSIT', 'DELAYED')
    WITH SYNONYMS ('in transit', 'active inbound', 'undelivered')
    COMMENT = 'TRUE when shipment is IN_TRANSIT or DELAYED (has not yet arrived).',

  -- ── Order facts ──────────────────────────────────────────────────────────

  -- Boolean flag: this order is open (awaiting fulfilment).
  orders.is_open
    LABELS = (FILTER)
    AS status = 'OPEN'
    WITH SYNONYMS ('open order', 'active order', 'unfulfilled order', 'pending order')
    COMMENT = 'TRUE when the order has OPEN status (not yet fulfilled or cancelled).',

  -- ── Supplier-part qualification fact ─────────────────────────────────────

  -- Boolean flag: this sourcing row represents an approved supplier.
  supplier_parts.is_qualified
    LABELS = (FILTER)
    AS qualification_status = 'QUALIFIED'
    WITH SYNONYMS ('qualified', 'approved source', 'qualified supplier', 'approved vendor')
    COMMENT = 'TRUE when the supplier is formally qualified to supply this part (QUALIFIED status).',

  -- ── Part criticality fact ─────────────────────────────────────────────────

  -- Boolean flag: this part is classified CRITICAL.
  parts.is_critical
    LABELS = (FILTER)
    AS criticality = 'CRITICAL'
    WITH SYNONYMS ('critical component', 'critical part', 'high-criticality')
    COMMENT = 'TRUE when the part has CRITICAL criticality — a shortage directly impacts production.',

  -- ── Supplier status fact ──────────────────────────────────────────────────

  -- Boolean flag: this supplier is currently active.
  suppliers.is_active
    LABELS = (FILTER)
    AS status = 'ACTIVE'
    COMMENT = 'TRUE when the supplier is currently ACTIVE in the supply chain.'

)

-- =============================================================================
-- DIMENSIONS — Business attributes for grouping, filtering, and entity resolution.
-- =============================================================================
DIMENSIONS (

  -- ── Supplier dimensions ──────────────────────────────────────────────────

  suppliers.supplier_id AS suppliers.supplier_id
    WITH SYNONYMS ('supplier id', 'vendor id', 'supplier code', 'supplier identifier')
    COMMENT = 'Unique identifier for the supplier (e.g., SUP-001).',

  suppliers.supplier_name AS suppliers.supplier_name
    WITH SYNONYMS ('supplier', 'vendor', 'vendor name', 'supplier name')
    COMMENT = 'Business name of the supplier or vendor.',

  suppliers.supplier_region AS suppliers.region
    WITH SYNONYMS ('supplier country', 'vendor region', 'supplier geography', 'origin')
    COMMENT = 'Geographic region where the supplier operates (e.g., Japan, Germany).',

  suppliers.risk_tier AS suppliers.risk_tier
    WITH SYNONYMS ('supplier risk', 'vendor risk', 'risk level', 'supplier risk tier')
    COMMENT = 'Supplier risk classification: CRITICAL, HIGH, MEDIUM, or LOW.',

  suppliers.capacity_units AS suppliers.capacity_units
    WITH SYNONYMS ('supplier capacity', 'vendor capacity', 'available capacity')
    COMMENT = 'Maximum daily production capacity of the supplier in units.',

  suppliers.supplier_status AS suppliers.status
    WITH SYNONYMS ('vendor status', 'supplier active', 'active status')
    COMMENT = 'Operational status of the supplier: ACTIVE or INACTIVE.',

  -- ── Part dimensions ──────────────────────────────────────────────────────

  parts.part_id AS parts.part_id
    WITH SYNONYMS ('part id', 'component id', 'part code', 'part identifier')
    COMMENT = 'Unique identifier for the part or component (e.g., PART-104).',

  parts.part_name AS parts.part_name
    WITH SYNONYMS ('part', 'component', 'component name', 'part description')
    COMMENT = 'Descriptive name of the part or component.',

  parts.part_category AS parts.category
    WITH SYNONYMS ('component category', 'part type', 'part group')
    COMMENT = 'Category of the part (Electronics, Mechanical, IoT, Electrical, Energy).',

  parts.criticality AS parts.criticality
    WITH SYNONYMS ('part criticality', 'component criticality', 'part risk level')
    COMMENT = 'Criticality classification: CRITICAL, HIGH, MEDIUM, or LOW.',

  parts.unit_cost AS parts.unit_cost
    WITH SYNONYMS ('part cost', 'component cost', 'unit price', 'procurement price')
    COMMENT = 'Unit procurement cost of the part in USD.',

  -- ── Plant dimensions ─────────────────────────────────────────────────────

  plants.plant_id AS plants.plant_id
    WITH SYNONYMS ('plant id', 'factory id', 'facility id', 'plant identifier')
    COMMENT = 'Unique identifier for the manufacturing plant (e.g., PLT-001).',

  plants.plant_name AS plants.plant_name
    WITH SYNONYMS ('plant', 'factory', 'facility', 'manufacturing plant', 'site name')
    COMMENT = 'Name of the manufacturing plant or assembly facility.',

  plants.plant_region AS plants.region
    WITH SYNONYMS ('plant location', 'factory location', 'plant country', 'manufacturing region')
    COMMENT = 'Geographic region where the plant is located (e.g., Japan, India).',

  plants.plant_capacity AS plants.capacity_units
    WITH SYNONYMS ('plant capacity', 'facility capacity', 'production capacity')
    COMMENT = 'Maximum production capacity of the plant in units.',

  plants.plant_status AS plants.status
    WITH SYNONYMS ('facility status', 'plant active', 'factory status')
    COMMENT = 'Operational status of the plant: ACTIVE or INACTIVE.',

  -- ── Inventory dimensions ─────────────────────────────────────────────────

  inventory.inventory_id AS inventory.inventory_id
    COMMENT = 'Unique identifier for the inventory record.',

  inventory.plant_id AS inventory.plant_id
    COMMENT = 'Plant holding this inventory. Part of natural key (plant_id, part_id).',

  inventory.part_id AS inventory.part_id
    COMMENT = 'Part stored in this inventory record. Part of natural key (plant_id, part_id).',

  inventory.on_hand_units AS inventory.on_hand_units
    WITH SYNONYMS ('on hand', 'inventory units', 'stock quantity', 'available inventory',
                   'stock on hand', 'current inventory')
    COMMENT = 'Physical quantity of the part on hand at the plant.',

  inventory.safety_stock_units AS inventory.safety_stock_units
    WITH SYNONYMS ('safety stock', 'buffer inventory', 'minimum stock', 'safety buffer')
    COMMENT = 'Minimum inventory level required as a supply disruption buffer.',

  inventory.daily_consumption AS inventory.daily_consumption
    WITH SYNONYMS ('consumption rate', 'daily usage', 'daily demand', 'burn rate')
    COMMENT = 'Average daily consumption rate of the part at this plant.',

  -- ── Port dimensions ───────────────────────────────────────────────────────

  ports.port_id AS ports.port_id
    WITH SYNONYMS ('port id', 'port code', 'port identifier')
    COMMENT = 'Unique identifier for the logistics port (e.g., PORT-TYO).',

  ports.port_name AS ports.port_name
    WITH SYNONYMS ('port', 'harbour', 'shipping port', 'logistics port')
    COMMENT = 'Name of the logistics port (e.g., Tokyo Port).',

  ports.port_region AS ports.region
    WITH SYNONYMS ('port location', 'port country', 'port geography')
    COMMENT = 'Geographic region where the port is located.',

  ports.congestion_level AS ports.congestion_level
    WITH SYNONYMS ('port congestion', 'traffic level', 'port load')
    COMMENT = 'Current congestion level at the port: HIGH, MEDIUM, or LOW.',

  ports.port_status AS ports.status
    WITH SYNONYMS ('port active', 'port operational status')
    COMMENT = 'Operational status of the port: ACTIVE or INACTIVE.',

  -- ── Shipment dimensions ───────────────────────────────────────────────────

  shipments.shipment_id AS shipments.shipment_id
    WITH SYNONYMS ('shipment id', 'delivery id', 'shipment number')
    COMMENT = 'Unique identifier for the shipment (e.g., SHP-002).',

  shipments.supplier_id AS shipments.supplier_id
    COMMENT = 'Supplier who sent this shipment. Join to suppliers on supplier_id.',

  shipments.part_id AS shipments.part_id
    COMMENT = 'Part carried by this shipment. Join to parts on part_id.',

  shipments.plant_id AS shipments.plant_id
    COMMENT = 'Destination plant for this shipment. Join to plants on plant_id.',

  shipments.port_id AS shipments.port_id
    COMMENT = 'Port through which this shipment transits. Join to ports on port_id.',

  shipments.ship_date AS shipments.ship_date
    WITH SYNONYMS ('departure date', 'shipped date', 'dispatch date')
    COMMENT = 'Date when the shipment departed from the supplier facility.',

  shipments.expected_arrival AS shipments.expected_arrival
    WITH SYNONYMS ('ETA', 'arrival date', 'estimated arrival', 'expected delivery date',
                   'delivery ETA')
    COMMENT = 'Expected date when the shipment arrives at the destination plant.',

  shipments.shipment_status AS shipments.status
    WITH SYNONYMS ('delivery status', 'shipment state', 'transit status')
    COMMENT = 'Status of the shipment: IN_TRANSIT, DELAYED, or DELIVERED.',

  shipments.shipment_quantity AS shipments.quantity
    WITH SYNONYMS ('shipped quantity', 'inbound quantity', 'shipment units')
    COMMENT = 'Number of part units in this shipment.',

  -- ── Product dimensions ────────────────────────────────────────────────────

  products.product_id AS products.product_id
    WITH SYNONYMS ('product id', 'SKU id', 'finished good id', 'product identifier')
    COMMENT = 'Unique identifier for the finished product (e.g., PROD-001).',

  products.product_name AS products.product_name
    WITH SYNONYMS ('product', 'product name', 'finished good', 'item')
    COMMENT = 'Name of the finished product (e.g., Nexus Drive).',

  products.product_category AS products.category
    WITH SYNONYMS ('product type', 'product line', 'business category')
    COMMENT = 'Product category (Industrial Automation, Energy Systems, IoT, Mobility, Industrial Safety).',

  products.margin AS products.margin
    WITH SYNONYMS ('gross margin', 'product margin', 'profit margin')
    COMMENT = 'Gross margin rate for the product as a decimal (0 to 1).',

  -- ── Product-Part (BOM) dimensions ─────────────────────────────────────────

  product_parts.product_id AS product_parts.product_id
    COMMENT = 'Product identifier in this BOM entry. Part of grain (product_id, part_id).',

  product_parts.part_id AS product_parts.part_id
    COMMENT = 'Component part identifier in this BOM entry. Part of grain (product_id, part_id).',

  product_parts.units_per_product AS product_parts.units_per_product
    WITH SYNONYMS ('quantity per product', 'BOM quantity', 'components per unit',
                   'units required per product')
    COMMENT = 'Number of units of this part required to build one unit of the product.',

  product_parts.is_critical_path AS product_parts.is_critical_path
    WITH SYNONYMS ('critical BOM', 'on critical path', 'critical component path')
    COMMENT = 'TRUE when this part is on the critical manufacturing path — shortage blocks assembly.',

  -- ── Order dimensions ──────────────────────────────────────────────────────

  orders.order_id AS orders.order_id
    WITH SYNONYMS ('order id', 'order number', 'sales order number')
    COMMENT = 'Unique identifier for the customer order (e.g., ORD-001).',

  orders.customer_id AS orders.customer_id
    COMMENT = 'Customer who placed this order. Join to customers on customer_id.',

  orders.product_id AS orders.product_id
    COMMENT = 'Product ordered. Join to products on product_id.',

  orders.plant_id AS orders.plant_id
    COMMENT = 'Plant fulfilling this order. Join to plants on plant_id.',

  orders.order_date AS orders.order_date
    WITH SYNONYMS ('order placed date', 'purchase date', 'order creation date')
    COMMENT = 'Date when the customer placed the order.',

  orders.due_date AS orders.due_date
    WITH SYNONYMS ('required delivery date', 'ship-by date', 'fulfilment deadline')
    COMMENT = 'Date by which the order must be fulfilled to meet the SLA.',

  orders.priority AS orders.priority
    WITH SYNONYMS ('order priority', 'urgency', 'order urgency', 'fulfilment priority')
    COMMENT = 'Order priority level: URGENT, HIGH, or NORMAL.',

  orders.sla_tier AS orders.sla_tier
    WITH SYNONYMS ('SLA', 'service level', 'order SLA tier')
    COMMENT = 'Service level agreement tier for this order: PLATINUM, GOLD, or SILVER.',

  orders.order_status AS orders.status
    WITH SYNONYMS ('order state', 'fulfilment status', 'order condition')
    COMMENT = 'Order status: OPEN (unfulfilled), CLOSED, or CANCELLED.',

  orders.order_value AS orders.order_value
    WITH SYNONYMS ('revenue', 'order revenue', 'order amount', 'sale value', 'order total')
    COMMENT = 'Total monetary value of this order in USD. Grain: order_id. Do not sum after joining through product_parts.',

  orders.order_quantity AS orders.quantity
    WITH SYNONYMS ('order quantity', 'units ordered', 'product quantity', 'order units')
    COMMENT = 'Number of product units in this order.',

  -- ── Customer dimensions ───────────────────────────────────────────────────

  customers.customer_id AS customers.customer_id
    WITH SYNONYMS ('customer id', 'account id', 'client id')
    COMMENT = 'Unique identifier for the customer (e.g., CUST-003).',

  customers.customer_name AS customers.customer_name
    WITH SYNONYMS ('customer', 'client', 'account', 'buyer', 'client name', 'account name')
    COMMENT = 'Business name of the customer or client.',

  customers.segment AS customers.segment
    WITH SYNONYMS ('customer segment', 'market segment', 'account type', 'customer type')
    COMMENT = 'Customer market segment: Enterprise or Mid-Market.',

  customers.customer_region AS customers.region
    WITH SYNONYMS ('customer location', 'account region', 'buyer country', 'client geography')
    COMMENT = 'Geographic region of the customer (e.g., Japan, Singapore, India).',

  customers.customer_sla_tier AS customers.sla_tier
    WITH SYNONYMS ('customer SLA', 'account tier', 'service tier', 'customer tier')
    COMMENT = 'Customer SLA commitment tier: PLATINUM, GOLD, or SILVER.',

  -- ── Supplier-Part sourcing dimensions ─────────────────────────────────────

  supplier_parts.supplier_id AS supplier_parts.supplier_id
    COMMENT = 'Supplier in this qualification record. Part of grain (supplier_id, part_id).',

  supplier_parts.part_id AS supplier_parts.part_id
    COMMENT = 'Part in this qualification record. Part of grain (supplier_id, part_id).',

  supplier_parts.qualification_status AS supplier_parts.qualification_status
    WITH SYNONYMS ('sourcing status', 'supplier approval status', 'qualification',
                   'vendor qualification', 'sourcing approval')
    COMMENT = 'Qualification status: QUALIFIED means approved to supply. Use this to filter governed sourcing — do not use SHIPMENTS.',

  supplier_parts.max_daily_capacity_units AS supplier_parts.max_daily_capacity_units
    WITH SYNONYMS ('supplier daily capacity', 'daily supply limit', 'max capacity',
                   'sourcing capacity')
    COMMENT = 'Maximum units per day this supplier can deliver for this part under normal conditions.',

  supplier_parts.lead_time_days AS supplier_parts.lead_time_days
    WITH SYNONYMS ('lead time', 'replenishment lead time', 'supplier lead time', 'delivery lead')
    COMMENT = 'Calendar days from order placement to delivery for this supplier-part combination.',

  supplier_parts.sourcing_unit_cost AS supplier_parts.unit_cost
    WITH SYNONYMS ('sourcing cost', 'procurement cost', 'buy cost', 'supplier unit price')
    COMMENT = 'Unit cost when sourcing this part from this supplier.',

  supplier_parts.expedite_cost_pct AS supplier_parts.expedite_cost_pct
    WITH SYNONYMS ('expedite premium', 'rush surcharge', 'expedite cost fraction')
    COMMENT = 'Additional cost as a fraction of unit_cost when using expedited sourcing.'

)

-- =============================================================================
-- METRICS — Governed aggregate measures for supply-chain analytics.
--
-- IMPORTANT GRAIN RULES:
--   (1) Order-level metrics (total_order_value, open_order_count) aggregate
--       at order_id grain. Do not join through product_parts when computing
--       these metrics — doing so multiplies order_value by BOM row count.
--   (2) Inventory metrics aggregate at (plant_id, part_id) grain.
--   (3) Supplier metrics aggregate at supplier_id grain.
--   (4) Scenario-based metrics (orders at risk, scenario revenue exposure)
--       are NOT defined here. Use SCENARIOS.V_ORDER_IMPACT for those.
-- =============================================================================
METRICS (

  -- ── Order metrics ─────────────────────────────────────────────────────────

  orders.total_order_value
    AS SUM(order_value)
    WITH SYNONYMS ('total revenue', 'total order value', 'revenue', 'order revenue total')
    COMMENT = 'Sum of order_value across all orders in scope. Grain: order_id. Do not join through product_parts when using this metric.',

  orders.total_open_order_value
    AS SUM(CASE WHEN status = 'OPEN' THEN order_value ELSE 0 END)
    WITH SYNONYMS ('open order value', 'open revenue', 'baseline exposure', 'current revenue at stake')
    COMMENT = 'Total monetary value of open (unfulfilled) orders. Use as the baseline revenue exposure measure before scenario analysis.',

  orders.open_order_count
    AS COUNT_IF(status = 'OPEN')
    WITH SYNONYMS ('open orders', 'active orders', 'unfulfilled orders', 'orders in progress')
    COMMENT = 'Count of orders with OPEN status.',

  orders.total_order_quantity
    AS SUM(CASE WHEN status = 'OPEN' THEN quantity ELSE 0 END)
    WITH SYNONYMS ('open order quantity', 'units demanded', 'total demand', 'open demand')
    COMMENT = 'Total product units demanded across open orders.',

  -- ── Customer metrics ──────────────────────────────────────────────────────

  customers.customer_count
    AS COUNT(customer_id)
    WITH SYNONYMS ('number of customers', 'customer count', 'account count', 'buyers')
    COMMENT = 'Count of distinct customers.',

  -- ── Supplier metrics ──────────────────────────────────────────────────────

  suppliers.supplier_count
    AS COUNT(supplier_id)
    WITH SYNONYMS ('number of suppliers', 'vendor count', 'suppliers in scope')
    COMMENT = 'Count of distinct suppliers.',

  suppliers.active_supplier_count
    AS COUNT_IF(status = 'ACTIVE')
    WITH SYNONYMS ('active suppliers', 'active vendors', 'available suppliers')
    COMMENT = 'Count of suppliers with ACTIVE status.',

  -- ── Shipment metrics ──────────────────────────────────────────────────────

  shipments.delayed_shipment_count
    AS COUNT_IF(status = 'DELAYED')
    WITH SYNONYMS ('delayed shipments', 'late deliveries', 'shipment delays', 'delayed deliveries')
    COMMENT = 'Count of shipments with DELAYED status.',

  shipments.total_inbound_quantity
    AS SUM(CASE WHEN status IN ('IN_TRANSIT', 'DELAYED') THEN quantity ELSE 0 END)
    WITH SYNONYMS ('inbound units', 'in-transit quantity', 'expected inbound', 'pipeline quantity')
    COMMENT = 'Total units in active inbound shipments (IN_TRANSIT or DELAYED, not yet delivered).',

  -- ── Inventory metrics ─────────────────────────────────────────────────────

  inventory.total_on_hand_units
    AS SUM(on_hand_units)
    WITH SYNONYMS ('total inventory', 'total stock', 'on-hand total', 'total on hand units')
    COMMENT = 'Total on-hand inventory units across the selected plant/part scope.',

  inventory.total_usable_units
    AS SUM(GREATEST(on_hand_units - safety_stock_units, 0))
    WITH SYNONYMS ('usable stock total', 'net available inventory', 'fulfillable units')
    COMMENT = 'Total inventory above safety stock. This is the quantity available for order fulfilment.',

  inventory.avg_coverage_days
    AS AVG(inventory.coverage_days)
    WITH SYNONYMS ('average inventory coverage', 'average days of stock', 'avg stock days')
    COMMENT = 'Average inventory coverage days (on_hand_units / daily_consumption) across the selected scope. Low values identify replenishment urgency.',

  inventory.min_coverage_days
    AS MIN(inventory.coverage_days)
    WITH SYNONYMS ('minimum inventory coverage', 'lowest days of stock', 'critical coverage days',
                   'most at-risk coverage')
    COMMENT = 'Minimum inventory coverage days in scope — identifies the most at-risk plant/part combination. Coverage < 7 days is typically considered critical.',

  -- ── Supplier-part sourcing metrics ────────────────────────────────────────

  supplier_parts.qualified_source_count
    AS COUNT_IF(qualification_status = 'QUALIFIED')
    WITH SYNONYMS ('qualified suppliers', 'approved sources', 'sourcing options', 'supply sources')
    COMMENT = 'Count of qualified sourcing relationships. Filter by part_id to identify single-source parts (qualified_source_count = 1). Uses SUPPLIER_PARTS — not SHIPMENTS — as the authoritative qualification source.'

)

COMMENT = 'NEXUS Supply Chain Resilience semantic view. Governed business ontology for Supplier → Part → Plant → Inventory → Product → Order → Customer analytics. Baseline current-state metrics only; scenario-impact metrics (orders at risk under disruption) require SCENARIOS.V_ORDER_IMPACT and related views.'

-- =============================================================================
-- AI SQL GENERATION INSTRUCTIONS
-- These rules govern how Cortex Analyst generates SQL against this semantic view.
-- =============================================================================
AI_SQL_GENERATION
'NEXUS Supply Chain Semantic View — SQL Generation Rules

1. SUPPLIER QUALIFICATION (critical rule): Always use RAW.SUPPLIER_PARTS with
   qualification_status = QUALIFIED to determine which suppliers can supply which
   parts. Never infer supplier qualification from SHIPMENTS history alone.
   A shipment exists because parts were delivered; it does not prove the supplier
   is currently approved to supply that part.

2. PRODUCT-COMPONENT DEPENDENCIES: Always use RAW.PRODUCT_PARTS (exposed here as
   product_parts) to determine which parts are required by which products.

3. ORDER REVENUE GRAIN (critical rule): Aggregate order_value at order_id grain.
   When a query joins orders through product_parts (BOM), each order row appears
   once per BOM entry. SUM(order_value) over such a join multiplies revenue
   incorrectly. Use DISTINCT order_id or aggregate revenue separately.

4. ENTITY RESOLUTION: Resolve supplier names, part names, plant names, and
   customer names to their canonical IDs (supplier_id, part_id, plant_id,
   customer_id) before filtering. Use LIKE or case-insensitive matching when
   the user provides a partial name.

5. DEPENDENCY TRACING: For questions like "which customers depend on supplier X?",
   follow the governed ontology path:
   supplier_parts (supplier_id, qualification_status=QUALIFIED)
   → parts (part_id)
   → product_parts (part_id → product_id)
   → orders (product_id → order_id)
   → customers (customer_id)

6. BASELINE vs. SCENARIO DISTINCTION:
   - This semantic view provides BASELINE current-state analytics.
   - "Orders at risk" and "revenue exposure" under a disruption scenario are
     MODELED outputs. They must be fetched from SCENARIOS.V_ORDER_IMPACT,
     SCENARIOS.V_SUPPLIER_FAILURE_IMPACT, or SCENARIOS.V_PORT_DISRUPTION_IMPACT.
   - Always label scenario results as modeled. Never present modeled values as
     observed operational facts.

7. INVENTORY COVERAGE: Use on_hand_units / NULLIF(daily_consumption, 0) for
   coverage days. Handle NULLIF to avoid divide-by-zero. Coverage < 7 days
   is typically a risk threshold; always state this threshold explicitly.

8. SUPPLIER CONCENTRATION: To compute supplier concentration for a part, count
   DISTINCT supplier_id WHERE qualification_status = QUALIFIED from supplier_parts,
   grouped by part_id. Divide the demand served by a specific supplier by the
   total demand for critical parts. The result is a fraction (0–1), not a count.

9. SINGLE SOURCE RATIO: Count critical parts (criticality = CRITICAL) with
   exactly 1 qualified supplier, divided by the total count of critical parts.
   Source: GROUP BY part_id in supplier_parts WHERE qualification_status=QUALIFIED,
   HAVING COUNT(supplier_id) = 1.

10. SLA EXPOSURE: Group at-risk orders by sla_tier (from orders table) and sum
    order_value. For scenario-based SLA exposure, use SCENARIOS.V_ORDER_IMPACT.

11. AMBIGUOUS ENTITIES: If the user refers to a supplier, part, or customer by
    a name that matches multiple records, list the candidates and ask for
    clarification. Do not silently select one.

12. NO FABRICATION: Never invent supplier IDs, part IDs, order IDs, metric
    values, or scenario results. If the data is unavailable or the question
    cannot be answered from this semantic view, say so explicitly.

13. MULTIPLE RELATIONSHIP PATHS: When joining orders to parts through product_parts,
    specify the path explicitly (orders → products → product_parts → parts).
    Do not take a shortcut through shipments for BOM-based analysis.

14. PORT DISRUPTION DEPENDENCY: For questions about port disruption impact, trace
    through shipments (port_id) → plants → orders → customers. Port disruption
    blocks in-transit inbound shipments; it does not directly affect inventory
    already on hand.

15. MODELED OUTPUTS: Any metric or result produced by the SCENARIOS engine must
    be prefixed with "Modeled:" or explicitly noted as a scenario estimate, not
    an observed fact.'

-- =============================================================================
-- AI QUESTION CATEGORIZATION INSTRUCTIONS
-- =============================================================================
AI_QUESTION_CATEGORIZATION
'NEXUS question routing rules:

ANSWERABLE from this semantic view (baseline analytics):
- Current inventory levels, coverage days, safety stock status
- Which suppliers supply which parts (from SUPPLIER_PARTS qualification)
- Which parts are critical or single-sourced
- Which shipments are delayed
- Customer order values and SLA tiers
- Product-to-component dependencies (BOM)
- Supplier risk tiers and regions
- Dependency paths: supplier → part → product → order → customer

REQUIRES scenario engine (SCENARIOS views — beyond this semantic view):
- "What breaks if SUP-001 fails for 14 days?" → SCENARIOS.V_SUPPLIER_FAILURE_IMPACT
- "Which orders are at risk?" under a specific disruption → SCENARIOS.V_ORDER_IMPACT
- "How much revenue is exposed if PORT-TYO is unavailable?" → SCENARIOS.V_PORT_DISRUPTION_IMPACT
- Mitigation comparisons → SCENARIOS.V_MITIGATION_COMPARISON
- Freight shock impact → SCENARIOS.V_FREIGHT_SHOCK_SUMMARY

UNCLEAR — ask for clarification:
- Questions about an unknown entity name
- Questions that reference a metric not defined in this view
- Scenario questions without a specified duration or disruption percentage
- Questions that could refer to either baseline or modeled values without context'

-- =============================================================================
-- AI VERIFIED QUERIES — 10 grounded, deterministic reference queries.
-- SQL uses __table_alias notation and logical dimension names.
-- Single quotes within SQL are escaped as ''.
-- Verified: 2026-09-19 (Unix timestamp 1789776000).
-- =============================================================================
AI_VERIFIED_QUERIES (

  -- Q1: Suppliers of critical parts
  suppliers_of_critical_parts AS (
    QUESTION 'What suppliers provide critical parts?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION TRUE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT DISTINCT
    sp.supplier_id,
    s.supplier_name,
    s.region,
    s.risk_tier,
    sp.part_id,
    p.part_name,
    p.criticality,
    sp.qualification_status,
    sp.max_daily_capacity_units,
    sp.lead_time_days
FROM __supplier_parts AS sp
JOIN __suppliers AS s ON sp.supplier_id = s.supplier_id
JOIN __parts AS p ON sp.part_id = p.part_id
WHERE sp.qualification_status = ''QUALIFIED''
  AND p.criticality = ''CRITICAL''
ORDER BY p.part_id, s.supplier_name'
  ),

  -- Q2: Single-sourced parts
  single_sourced_parts AS (
    QUESTION 'Which parts are single sourced?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION TRUE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    sp.part_id,
    p.part_name,
    p.criticality,
    COUNT(sp.supplier_id) AS qualified_supplier_count
FROM __supplier_parts AS sp
JOIN __parts AS p ON sp.part_id = p.part_id
WHERE sp.qualification_status = ''QUALIFIED''
GROUP BY sp.part_id, p.part_name, p.criticality
HAVING COUNT(sp.supplier_id) = 1
ORDER BY p.criticality DESC, p.part_name'
  ),

  -- Q3: Plants with lowest inventory coverage
  plants_lowest_inventory_coverage AS (
    QUESTION 'Which plants have the lowest inventory coverage?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    i.plant_id,
    pl.plant_name,
    pl.region,
    i.part_id,
    p.part_name,
    p.criticality,
    i.on_hand_units,
    i.safety_stock_units,
    i.daily_consumption,
    ROUND(i.on_hand_units / NULLIF(i.daily_consumption, 0), 2) AS inventory_coverage_days
FROM __inventory AS i
JOIN __plants AS pl ON i.plant_id = pl.plant_id
JOIN __parts AS p ON i.part_id = p.part_id
WHERE i.daily_consumption > 0
ORDER BY inventory_coverage_days ASC
LIMIT 20'
  ),

  -- Q4: Delayed shipments
  delayed_shipments AS (
    QUESTION 'Which shipments are delayed?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION TRUE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    sh.shipment_id,
    sh.supplier_id,
    s.supplier_name,
    sh.part_id,
    p.part_name,
    p.criticality,
    sh.plant_id,
    pl.plant_name,
    sh.port_id,
    po.port_name,
    sh.quantity,
    sh.ship_date,
    sh.expected_arrival,
    sh.status
FROM __shipments AS sh
JOIN __suppliers AS s ON sh.supplier_id = s.supplier_id
JOIN __parts AS p ON sh.part_id = p.part_id
JOIN __plants AS pl ON sh.plant_id = pl.plant_id
JOIN __ports AS po ON sh.port_id = po.port_id
WHERE sh.status = ''DELAYED''
ORDER BY sh.expected_arrival'
  ),

  -- Q5: Customers with highest open order value
  customers_by_open_order_value AS (
    QUESTION 'Which customers have the highest open order value?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    o.customer_id,
    c.customer_name,
    c.sla_tier,
    c.segment,
    c.region,
    COUNT(o.order_id)      AS open_order_count,
    SUM(o.order_value)     AS total_open_order_value,
    SUM(o.quantity)  AS total_units_demanded
FROM __orders AS o
JOIN __customers AS c ON o.customer_id = c.customer_id
WHERE o.status = ''OPEN''
GROUP BY o.customer_id, c.customer_name, c.sla_tier, c.segment, c.region
ORDER BY total_open_order_value DESC'
  ),

  -- Q6: Open order exposure summarised by SLA tier
  open_order_exposure_by_sla AS (
    QUESTION 'What is the current revenue exposure by SLA tier?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    o.sla_tier,
    COUNT(DISTINCT o.customer_id)   AS customers_with_open_orders,
    COUNT(o.order_id)               AS open_order_count,
    SUM(o.order_value)              AS total_open_order_value,
    SUM(CASE WHEN o.priority = ''URGENT'' THEN o.order_value ELSE 0 END)
                                    AS urgent_open_order_value
FROM __orders AS o
WHERE o.status = ''OPEN''
GROUP BY o.sla_tier
ORDER BY total_open_order_value DESC'
  ),

  -- Q7: Parts supplied by SUP-001
  parts_supplied_by_sup001 AS (
    QUESTION 'Which parts are supplied by SUP-001?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    sp.part_id,
    p.part_name,
    p.criticality,
    p.category,
    sp.qualification_status,
    sp.max_daily_capacity_units,
    sp.lead_time_days,
    sp.unit_cost,
    sp.expedite_cost_pct
FROM __supplier_parts AS sp
JOIN __parts AS p ON sp.part_id = p.part_id
WHERE sp.supplier_id = ''SUP-001''
  AND sp.qualification_status = ''QUALIFIED''
ORDER BY p.criticality DESC, p.part_name'
  ),

  -- Q8: Products that depend on PART-104
  products_depending_on_part104 AS (
    QUESTION 'Which products depend on PART-104?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT
    pp.product_id,
    pr.product_name,
    pr.category,
    pp.units_per_product,
    pp.is_critical_path
FROM __product_parts AS pp
JOIN __products AS pr ON pp.product_id = pr.product_id
WHERE pp.part_id = ''PART-104''
ORDER BY pp.is_critical_path DESC, pr.product_name'
  ),

  -- Q9: Customers exposed to PART-104 dependency
  customers_exposed_to_part104 AS (
    QUESTION 'Which customers are exposed to a PART-104 shortage?'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT DISTINCT
    o.customer_id,
    c.customer_name,
    c.sla_tier,
    c.region,
    o.order_id,
    o.product_id,
    pr.product_name,
    o.order_value,
    o.due_date,
    o.priority
FROM __orders AS o
JOIN __customers AS c  ON o.customer_id = c.customer_id
JOIN __products AS pr  ON o.product_id  = pr.product_id
JOIN __product_parts AS pp ON pp.product_id = o.product_id
WHERE pp.part_id = ''PART-104''
  AND o.status = ''OPEN''
ORDER BY o.order_value DESC'
  ),

  -- Q10: Full supplier-to-customer dependency path for SUP-001
  sup001_dependency_chain AS (
    QUESTION 'Show the full dependency chain from SUP-001 to affected customers'
    VERIFIED_AT 1789776000
    ONBOARDING_QUESTION FALSE
    VERIFIED_BY '(owner = nexus-team)'
    SQL 'SELECT DISTINCT
    sp.supplier_id,
    s.supplier_name,
    s.risk_tier,
    sp.part_id,
    p.part_name,
    p.criticality,
    pp.product_id,
    pr.product_name,
    o.order_id,
    o.plant_id,
    o.customer_id,
    c.customer_name,
    c.sla_tier,
    o.order_value,
    o.due_date,
    o.priority
FROM __supplier_parts AS sp
JOIN __suppliers     AS s  ON sp.supplier_id  = s.supplier_id
JOIN __parts         AS p  ON sp.part_id      = p.part_id
JOIN __product_parts AS pp ON pp.part_id      = sp.part_id
JOIN __products      AS pr ON pr.product_id   = pp.product_id
JOIN __orders        AS o  ON o.product_id    = pp.product_id
JOIN __customers     AS c  ON c.customer_id   = o.customer_id
WHERE sp.supplier_id         = ''SUP-001''
  AND sp.qualification_status = ''QUALIFIED''
  AND o.status           = ''OPEN''
ORDER BY p.criticality DESC, o.order_value DESC'
  )

);
