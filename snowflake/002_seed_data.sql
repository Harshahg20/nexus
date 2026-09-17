-- Deterministic synthetic data for the NEXUS MVP.
-- Deliberately contains single-source parts, alternate suppliers,
-- safety stock, delayed shipments, shared components and high-value orders.

USE DATABASE NEXUS_DB;

INSERT INTO RAW.SUPPLIERS VALUES
('SUP-001','Apex Components','Japan','CRITICAL',12000,'ACTIVE'),
('SUP-002','Nova Industrial','South Korea','MEDIUM',10000,'ACTIVE'),
('SUP-003','Pacific Precision','Japan','HIGH',8500,'ACTIVE'),
('SUP-004','Orion Materials','Taiwan','MEDIUM',9000,'ACTIVE'),
('SUP-005','Delta Electronics','Singapore','LOW',11000,'ACTIVE'),
('SUP-006','Vertex Metals','India','MEDIUM',7000,'ACTIVE'),
('SUP-007','Zenith Plastics','Vietnam','LOW',9500,'ACTIVE'),
('SUP-008','Atlas Power','China','HIGH',6000,'ACTIVE'),
('SUP-009','Meridian Glass','Japan','LOW',5000,'ACTIVE'),
('SUP-010','Helix Systems','Germany','HIGH',4500,'ACTIVE');

INSERT INTO RAW.PARTS VALUES
('PART-101','Control Board','Electronics','HIGH',85.00),
('PART-102','Power Module','Electronics','CRITICAL',140.00),
('PART-103','Sensor Array','IoT','HIGH',65.00),
('PART-104','Precision Motor','Mechanical','CRITICAL',210.00),
('PART-105','Drive Housing','Mechanical','MEDIUM',95.00),
('PART-106','Thermal Unit','Mechanical','HIGH',120.00),
('PART-107','Display Panel','Electronics','MEDIUM',175.00),
('PART-108','Battery Cell','Energy','CRITICAL',155.00),
('PART-109','Connector Set','Electronics','LOW',18.00),
('PART-110','Cooling Fan','Mechanical','MEDIUM',32.00),
('PART-111','Safety Controller','Electronics','CRITICAL',190.00),
('PART-112','Frame Assembly','Mechanical','MEDIUM',110.00),
('PART-113','Optical Sensor','IoT','HIGH',72.00),
('PART-114','Cable Harness','Electrical','LOW',28.00),
('PART-115','Power Connector','Electrical','MEDIUM',22.00),
('PART-116','Actuator','Mechanical','HIGH',135.00),
('PART-117','Seal Kit','Mechanical','LOW',14.00),
('PART-118','Processor Unit','Electronics','CRITICAL',260.00),
('PART-119','Memory Module','Electronics','MEDIUM',90.00),
('PART-120','Mounting Kit','Mechanical','LOW',25.00);

INSERT INTO RAW.PLANTS VALUES
('PLT-001','Tokyo Assembly','Japan',10000,'ACTIVE'),
('PLT-002','Osaka Systems','Japan',8500,'ACTIVE'),
('PLT-003','Bangalore Manufacturing','India',9000,'ACTIVE'),
('PLT-004','Singapore Integration','Singapore',7000,'ACTIVE'),
('PLT-005','Munich Precision','Germany',6000,'ACTIVE');

INSERT INTO RAW.INVENTORY VALUES
('INV-001','PLT-001','PART-101',900,300,45),
('INV-002','PLT-001','PART-102',220,180,22),
('INV-003','PLT-001','PART-104',90,70,12),
('INV-004','PLT-001','PART-107',180,80,15),
('INV-005','PLT-001','PART-111',70,60,10),
('INV-006','PLT-002','PART-102',160,120,18),
('INV-007','PLT-002','PART-104',60,50,11),
('INV-008','PLT-002','PART-108',250,150,20),
('INV-009','PLT-002','PART-118',90,70,8),
('INV-010','PLT-003','PART-103',500,200,35),
('INV-011','PLT-003','PART-104',40,35,10),
('INV-012','PLT-003','PART-106',130,80,12),
('INV-013','PLT-003','PART-108',180,100,16),
('INV-014','PLT-003','PART-116',95,60,9),
('INV-015','PLT-004','PART-107',140,60,13),
('INV-016','PLT-004','PART-108',120,80,14),
('INV-017','PLT-004','PART-111',55,45,8),
('INV-018','PLT-005','PART-104',110,70,13),
('INV-019','PLT-005','PART-118',75,60,7),
('INV-020','PLT-005','PART-119',200,90,15);

INSERT INTO RAW.PORTS VALUES
('PORT-TYO','Tokyo Port','Japan','HIGH','ACTIVE'),
('PORT-OSA','Osaka Port','Japan','MEDIUM','ACTIVE'),
('PORT-SIN','Singapore Port','Singapore','LOW','ACTIVE'),
('PORT-BUS','Busan Port','South Korea','MEDIUM','ACTIVE'),
('PORT-HAM','Hamburg Port','Germany','LOW','ACTIVE');

INSERT INTO RAW.SHIPMENTS VALUES
('SHP-001','SUP-001','PART-104','PLT-001','PORT-TYO',120,'2026-09-10','2026-09-13','DELIVERED'),
('SHP-002','SUP-001','PART-104','PLT-002','PORT-TYO',100,'2026-09-11','2026-09-14','IN_TRANSIT'),
('SHP-003','SUP-001','PART-111','PLT-001','PORT-TYO',80,'2026-09-12','2026-09-15','IN_TRANSIT'),
('SHP-004','SUP-001','PART-102','PLT-002','PORT-TYO',180,'2026-09-12','2026-09-15','DELAYED'),
('SHP-005','SUP-002','PART-104','PLT-003','PORT-BUS',90,'2026-09-09','2026-09-13','DELIVERED'),
('SHP-006','SUP-003','PART-102','PLT-001','PORT-TYO',120,'2026-09-08','2026-09-12','DELIVERED'),
('SHP-007','SUP-003','PART-103','PLT-003','PORT-TYO',300,'2026-09-12','2026-09-16','IN_TRANSIT'),
('SHP-008','SUP-004','PART-108','PLT-002','PORT-BUS',220,'2026-09-08','2026-09-13','DELIVERED'),
('SHP-009','SUP-005','PART-107','PLT-004','PORT-SIN',180,'2026-09-10','2026-09-14','IN_TRANSIT'),
('SHP-010','SUP-006','PART-116','PLT-003','PORT-SIN',100,'2026-09-11','2026-09-15','IN_TRANSIT'),
('SHP-011','SUP-008','PART-118','PLT-005','PORT-HAM',100,'2026-09-07','2026-09-12','DELIVERED'),
('SHP-012','SUP-010','PART-119','PLT-005','PORT-HAM',180,'2026-09-10','2026-09-15','IN_TRANSIT'),
('SHP-013','SUP-001','PART-104','PLT-005','PORT-TYO',90,'2026-09-13','2026-09-17','IN_TRANSIT'),
('SHP-014','SUP-007','PART-110','PLT-004','PORT-SIN',200,'2026-09-12','2026-09-16','IN_TRANSIT'),
('SHP-015','SUP-009','PART-113','PLT-001','PORT-TYO',160,'2026-09-12','2026-09-16','IN_TRANSIT');

INSERT INTO RAW.PRODUCTS VALUES
('PROD-001','Nexus Drive','Industrial Automation',0.34),
('PROD-002','Nexus Controller','Industrial Automation',0.38),
('PROD-003','Nexus Power Hub','Energy Systems',0.29),
('PROD-004','Nexus Sensor Pro','IoT',0.42),
('PROD-005','Nexus Safety Unit','Industrial Safety',0.36),
('PROD-006','Nexus Mobility Core','Mobility',0.31);

INSERT INTO RAW.CUSTOMERS VALUES
('CUST-001','Kanto Robotics','Enterprise','Japan','PLATINUM'),
('CUST-002','Sakura Mobility','Enterprise','Japan','GOLD'),
('CUST-003','Pacific Automation','Enterprise','Singapore','PLATINUM'),
('CUST-004','Bharat Industrial','Enterprise','India','GOLD'),
('CUST-005','Alpine Systems','Enterprise','Germany','GOLD'),
('CUST-006','Metro Controls','Mid-Market','Japan','SILVER'),
('CUST-007','Orchid Energy','Enterprise','Singapore','PLATINUM'),
('CUST-008','Vertex Logistics','Mid-Market','India','SILVER');

INSERT INTO RAW.ORDERS VALUES
('ORD-001','CUST-001','PROD-001','PLT-001',20,420000,'2026-09-12','2026-09-20','URGENT','PLATINUM','OPEN'),
('ORD-002','CUST-002','PROD-001','PLT-002',16,336000,'2026-09-12','2026-09-21','HIGH','GOLD','OPEN'),
('ORD-003','CUST-003','PROD-001','PLT-001',28,588000,'2026-09-13','2026-09-22','URGENT','PLATINUM','OPEN'),
('ORD-004','CUST-003','PROD-005','PLT-001',12,312000,'2026-09-13','2026-09-21','HIGH','PLATINUM','OPEN'),
('ORD-005','CUST-004','PROD-004','PLT-003',30,360000,'2026-09-12','2026-09-23','HIGH','GOLD','OPEN'),
('ORD-006','CUST-004','PROD-006','PLT-003',18,270000,'2026-09-13','2026-09-24','NORMAL','GOLD','OPEN'),
('ORD-007','CUST-005','PROD-001','PLT-005',14,294000,'2026-09-12','2026-09-22','HIGH','GOLD','OPEN'),
('ORD-008','CUST-006','PROD-002','PLT-002',20,250000,'2026-09-13','2026-09-25','NORMAL','SILVER','OPEN'),
('ORD-009','CUST-007','PROD-003','PLT-004',22,396000,'2026-09-13','2026-09-24','HIGH','PLATINUM','OPEN'),
('ORD-010','CUST-008','PROD-006','PLT-003',10,150000,'2026-09-14','2026-09-26','NORMAL','SILVER','OPEN'),
('ORD-011','CUST-001','PROD-005','PLT-001',8,208000,'2026-09-14','2026-09-25','NORMAL','PLATINUM','OPEN'),
('ORD-012','CUST-002','PROD-002','PLT-002',15,187500,'2026-09-14','2026-09-26','NORMAL','GOLD','OPEN'),
('ORD-013','CUST-003','PROD-001','PLT-001',10,210000,'2026-09-14','2026-09-23','HIGH','PLATINUM','OPEN'),
('ORD-014','CUST-007','PROD-005','PLT-004',9,234000,'2026-09-14','2026-09-26','HIGH','PLATINUM','OPEN'),
('ORD-015','CUST-005','PROD-002','PLT-005',11,137500,'2026-09-14','2026-09-27','NORMAL','GOLD','OPEN'),
('ORD-016','CUST-006','PROD-004','PLT-003',15,180000,'2026-09-15','2026-09-27','NORMAL','SILVER','OPEN'),
('ORD-017','CUST-003','PROD-005','PLT-001',7,182000,'2026-09-15','2026-09-24','HIGH','PLATINUM','OPEN'),
('ORD-018','CUST-004','PROD-006','PLT-003',12,180000,'2026-09-15','2026-09-28','NORMAL','GOLD','OPEN'),
('ORD-019','CUST-007','PROD-003','PLT-004',13,234000,'2026-09-15','2026-09-28','NORMAL','PLATINUM','OPEN'),
('ORD-020','CUST-001','PROD-001','PLT-001',6,126000,'2026-09-15','2026-09-29','NORMAL','PLATINUM','OPEN');
