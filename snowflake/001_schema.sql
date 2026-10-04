-- NEXUS Snowflake foundation
-- Creates the raw supply-chain entities plus scenario and analytics schemas.

CREATE DATABASE IF NOT EXISTS NEXUS_DB;
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.RAW;
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.SEMANTIC;
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.SCENARIOS;
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.ANALYTICS;
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.STREAMLIT_APP;

-- Stages
CREATE STAGE IF NOT EXISTS NEXUS_DB.STREAMLIT_APP.APP_STAGE
  COMMENT = 'Streamlit-in-Snowflake application files';

CREATE OR REPLACE TABLE NEXUS_DB.RAW.SUPPLIERS (
    supplier_id VARCHAR PRIMARY KEY,
    supplier_name VARCHAR NOT NULL,
    region VARCHAR,
    risk_tier VARCHAR,
    capacity_units NUMBER(18,0),
    status VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.PARTS (
    part_id VARCHAR PRIMARY KEY,
    part_name VARCHAR NOT NULL,
    category VARCHAR,
    criticality VARCHAR,
    unit_cost NUMBER(12,2)
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.PLANTS (
    plant_id VARCHAR PRIMARY KEY,
    plant_name VARCHAR NOT NULL,
    region VARCHAR,
    capacity_units NUMBER(18,0),
    status VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.INVENTORY (
    inventory_id VARCHAR PRIMARY KEY,
    plant_id VARCHAR NOT NULL,
    part_id VARCHAR NOT NULL,
    on_hand_units NUMBER(18,0),
    safety_stock_units NUMBER(18,0),
    daily_consumption NUMBER(18,2)
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.PORTS (
    port_id VARCHAR PRIMARY KEY,
    port_name VARCHAR NOT NULL,
    region VARCHAR,
    congestion_level VARCHAR,
    status VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.SHIPMENTS (
    shipment_id VARCHAR PRIMARY KEY,
    supplier_id VARCHAR NOT NULL,
    part_id VARCHAR NOT NULL,
    plant_id VARCHAR NOT NULL,
    port_id VARCHAR,
    quantity NUMBER(18,0),
    ship_date DATE,
    expected_arrival DATE,
    status VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.PRODUCTS (
    product_id VARCHAR PRIMARY KEY,
    product_name VARCHAR NOT NULL,
    category VARCHAR,
    margin NUMBER(8,4)
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.ORDERS (
    order_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR NOT NULL,
    product_id VARCHAR NOT NULL,
    plant_id VARCHAR NOT NULL,
    quantity NUMBER(18,0),
    order_value NUMBER(18,2),
    order_date DATE,
    due_date DATE,
    priority VARCHAR,
    sla_tier VARCHAR,
    status VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.RAW.CUSTOMERS (
    customer_id VARCHAR PRIMARY KEY,
    customer_name VARCHAR NOT NULL,
    segment VARCHAR,
    region VARCHAR,
    sla_tier VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.SCENARIOS.SCENARIO_DEFINITIONS (
    scenario_id VARCHAR PRIMARY KEY,
    scenario_type VARCHAR NOT NULL,
    scenario_name VARCHAR NOT NULL,
    target_entity_type VARCHAR,
    target_entity_id VARCHAR,
    capacity_reduction_pct NUMBER(8,4),
    duration_days NUMBER(10,0),
    freight_change_pct NUMBER(8,4),
    start_date DATE,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE NEXUS_DB.SCENARIOS.SCENARIO_IMPACTS (
    scenario_id VARCHAR,
    entity_type VARCHAR,
    entity_id VARCHAR,
    impact_type VARCHAR,
    baseline_value NUMBER(18,2),
    scenario_value NUMBER(18,2),
    impact_value NUMBER(18,2),
    calculation_note VARCHAR
);

CREATE OR REPLACE TABLE NEXUS_DB.SCENARIOS.MITIGATION_OPTIONS (
    scenario_id VARCHAR,
    mitigation_id VARCHAR,
    mitigation_type VARCHAR,
    description VARCHAR,
    incremental_cost NUMBER(18,2),
    orders_protected NUMBER(18,0),
    revenue_protected NUMBER(18,2),
    remaining_revenue_exposure NUMBER(18,2)
);
