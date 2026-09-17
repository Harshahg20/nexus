-- NEXUS explicit sourcing / qualification relationship.
-- This is separate from SHIPMENTS because historical shipment activity does not
-- prove that a supplier is an approved alternate source.

USE DATABASE NEXUS_DB;

CREATE OR REPLACE TABLE RAW.SUPPLIER_PARTS (
    supplier_id VARCHAR NOT NULL,
    part_id VARCHAR NOT NULL,
    qualification_status VARCHAR NOT NULL,
    max_daily_capacity_units NUMBER(18,2),
    unit_cost NUMBER(12,2),
    lead_time_days NUMBER(10,0),
    expedite_cost_pct NUMBER(8,4),
    effective_date DATE,
    PRIMARY KEY (supplier_id, part_id)
);

-- Seed deliberate sourcing patterns for scenario analysis.
INSERT INTO RAW.SUPPLIER_PARTS
    (supplier_id, part_id, qualification_status, max_daily_capacity_units,
     unit_cost, lead_time_days, expedite_cost_pct, effective_date)
SELECT * FROM VALUES
    ('SUP-001','PART-101','QUALIFIED',500,18.50,5,0.25,'2026-01-01'),
    ('SUP-002','PART-101','QUALIFIED',350,19.20,7,0.20,'2026-01-01'),
    ('SUP-001','PART-102','QUALIFIED',300,42.00,6,0.30,'2026-01-01'),
    ('SUP-003','PART-102','QUALIFIED',250,44.00,8,0.25,'2026-01-01'),
    ('SUP-001','PART-103','QUALIFIED',200,31.00,5,0.20,'2026-01-01'),
    ('SUP-004','PART-103','QUALIFIED',180,32.50,6,0.20,'2026-01-01'),
    ('SUP-002','PART-104','QUALIFIED',450,27.00,5,0.20,'2026-01-01'),
    ('SUP-005','PART-104','QUALIFIED',300,28.50,9,0.35,'2026-01-01'),
    ('SUP-002','PART-105','QUALIFIED',400,15.00,4,0.15,'2026-01-01'),
    ('SUP-006','PART-105','QUALIFIED',350,15.80,6,0.20,'2026-01-01'),
    ('SUP-003','PART-106','QUALIFIED',280,23.00,6,0.25,'2026-01-01'),
    ('SUP-007','PART-107','QUALIFIED',250,36.00,7,0.25,'2026-01-01'),
    ('SUP-008','PART-108','QUALIFIED',500,12.00,4,0.15,'2026-01-01'),
    ('SUP-009','PART-109','QUALIFIED',220,55.00,8,0.30,'2026-01-01'),
    ('SUP-010','PART-110','QUALIFIED',300,17.00,5,0.20,'2026-01-01'),
    ('SUP-001','PART-111','QUALIFIED',150,62.00,6,0.30,'2026-01-01'),
    ('SUP-004','PART-112','QUALIFIED',320,21.00,5,0.20,'2026-01-01'),
    ('SUP-005','PART-113','QUALIFIED',260,29.00,7,0.25,'2026-01-01'),
    ('SUP-006','PART-114','QUALIFIED',240,33.00,6,0.20,'2026-01-01'),
    ('SUP-007','PART-115','QUALIFIED',190,48.00,8,0.30,'2026-01-01'),
    ('SUP-008','PART-116','QUALIFIED',420,14.00,4,0.15,'2026-01-01'),
    ('SUP-009','PART-117','QUALIFIED',210,39.00,7,0.25,'2026-01-01'),
    ('SUP-010','PART-118','QUALIFIED',350,16.00,5,0.20,'2026-01-01'),
    ('SUP-003','PART-119','QUALIFIED',180,51.00,9,0.35,'2026-01-01'),
    ('SUP-004','PART-120','QUALIFIED',300,26.00,6,0.20,'2026-01-01');

CREATE OR REPLACE VIEW ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS AS
SELECT
    sp.part_id,
    p.part_name,
    sp.supplier_id,
    s.supplier_name,
    sp.max_daily_capacity_units,
    sp.unit_cost,
    sp.lead_time_days,
    sp.expedite_cost_pct,
    sp.qualification_status
FROM RAW.SUPPLIER_PARTS sp
JOIN RAW.SUPPLIERS s ON s.supplier_id = sp.supplier_id
JOIN RAW.PARTS p ON p.part_id = sp.part_id
WHERE sp.qualification_status = 'QUALIFIED'
  AND s.status = 'ACTIVE';

CREATE OR REPLACE VIEW ANALYTICS.PART_SOURCE_PROFILE AS
SELECT
    part_id,
    COUNT(DISTINCT supplier_id) AS qualified_supplier_count,
    MIN(lead_time_days) AS fastest_lead_time_days,
    MIN(unit_cost) AS lowest_unit_cost,
    MAX(max_daily_capacity_units) AS max_alternate_capacity_units,
    COUNT_IF(lead_time_days <= 7) AS suppliers_within_7_day_lead_time
FROM ANALYTICS.QUALIFIED_SUPPLIER_OPTIONS
GROUP BY part_id;
