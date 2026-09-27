# NEXUS Deployment Guide

## Prerequisites

| Requirement | Notes |
|---|---|
| Snowflake account | With Cortex AI features enabled (Agents, Semantic Views). Contact your account team if `CREATE SEMANTIC VIEW` or `CREATE AGENT` are not available. |
| Role | `ACCOUNTADMIN` or a role with `CREATE DATABASE`, `CREATE SCHEMA`, `CREATE TABLE`, `CREATE VIEW`, `CREATE FUNCTION`, `CREATE AGENT` privileges |
| Warehouse | `COMPUTE_WH` (or update the warehouse name throughout the SQL scripts and `secrets.toml`) |
| Python 3.11+ | For the Streamlit app. Python 3.9 works but is EOL. |

---

## Step 1 — Snowflake Deployment

Open a Snowflake worksheet. Run the scripts below **in order**. Every script uses `CREATE OR REPLACE` and is idempotent — safe to re-run.

### Required execution order

```
snowflake/001_schema.sql
snowflake/002_seed_data.sql
snowflake/003_product_bom.sql
snowflake/007_supplier_part_sources.sql
snowflake/004_semantic_views.sql
snowflake/006_scenario_engine.sql
snowflake/008_mitigation_engine.sql
snowflake/010_port_disruption_engine.sql
snowflake/011_freight_shock_engine.sql
snowflake/012_validation_views.sql
snowflake/013_nexus_semantic_view.sql
snowflake/014_nexus_agent.sql        (requires Cortex Agent preview)
```

### Validation scripts (run to verify, no DDL)

```
snowflake/005_golden_queries.sql     — 8 demo golden queries
snowflake/009_scenario_tests.sql     — 8 regression invariants
snowflake/015_extended_tests.sql     — 22 Phase 8 extended tests
```

### Why this order?

| Dependency | Reason |
|---|---|
| `001` before all | Creates the database and schemas |
| `002` before `003/007` | RAW tables must exist before inserts |
| `007` before `004/006` | `SUPPLIER_PARTS` is used by analytics and scenario views |
| `006` before `008` | Mitigation engine references scenario views (`V_ORDER_PART_ALLOCATION`, etc.) |
| `013` last among views | Semantic view references all RAW tables and analytics views |
| `014` last | Agent requires the semantic view and all tool UDF targets to exist |

---

## Step 2 — Verify Deployment

Run these three validation queries in Snowflake after the scripts complete:

```sql
-- 1. Scenario validation (expect all PASS)
SELECT check_name, status, violation_count
FROM NEXUS_DB.ANALYTICS.V_SCENARIO_VALIDATION;

-- 2. Supplier failure impact (expect 1 row with non-zero values)
SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT;

-- 3. Mitigation comparison (expect 4 rows)
SELECT mitigation_type, orders_at_risk, remaining_revenue_exposure, modeled_incremental_cost
FROM NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON
ORDER BY remaining_revenue_exposure DESC;
```

Expected results:

| mitigation_type | orders_at_risk | Remaining Exposure | Incremental Cost |
|---|---|---|---|
| NO_ACTION | highest | highest | $0 |
| EXPEDITE_SHIPMENT | lower | lower | moderate |
| INVENTORY_REALLOCATION | lower | lower | lowest |
| ALTERNATE_SUPPLIER | lowest | lowest | highest |

---

## Step 3 — Key-Pair Authentication Setup

NEXUS uses RSA key-pair authentication for the Snowpark session.

### Generate the key pair

```bash
# Unencrypted PKCS#8 private key (required by snowflake-snowpark-python)
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out rsa_key.pem

# Extract public key
openssl rsa -in rsa_key.pem -pubout -out rsa_key.pub
```

### Register in Snowflake

```sql
-- Run as ACCOUNTADMIN or SECURITYADMIN
ALTER USER <your_user>
  SET RSA_PUBLIC_KEY = '<paste content of rsa_key.pub — omit header/footer lines>';
```

### Configure secrets.toml

```bash
cp app/.streamlit/secrets.toml.example app/.streamlit/secrets.toml
# Edit the file with your values
```

```toml
[connections.snowflake]
account          = "your-account.snowflakecomputing.com"
user             = "your-snowflake-user"
private_key_path = "/absolute/path/to/rsa_key.pem"
role             = "ACCOUNTADMIN"
warehouse        = "COMPUTE_WH"
database         = "NEXUS_DB"
```

**Never commit `secrets.toml` — it is in `.gitignore`.**

---

## Step 4 — Local Streamlit Setup

```bash
# From the repo root
cd app

# Create and activate a virtual environment (Python 3.11+ recommended)
python3.11 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

---

## Step 5 — Run Tests

```bash
# From the repo root
cd app
./venv/bin/python -m pytest ../tests/ -v
```

Expected: **64 tests pass**, 2 warnings (EOL Python version, LibreSSL).

All tests run without a live Snowflake connection.

---

## Snowflake Objects Summary

After a complete deployment, the following objects exist in `NEXUS_DB`:

### RAW schema — 10 observed entity tables

| Table | Contents |
|---|---|
| `SUPPLIERS` | 10 suppliers (CRITICAL to LOW risk tier) |
| `PARTS` | 20 parts (CRITICAL to LOW criticality) |
| `PLANTS` | 5 manufacturing plants across Asia/Europe |
| `INVENTORY` | 20 inventory records |
| `PORTS` | 5 logistics ports |
| `SHIPMENTS` | 15 shipments (DELIVERED, IN_TRANSIT, DELAYED) |
| `PRODUCTS` | 6 finished products |
| `ORDERS` | 20 open customer orders |
| `CUSTOMERS` | 8 customers (PLATINUM, GOLD, SILVER SLA) |
| `PRODUCT_PARTS` | 33 BOM entries |
| `SUPPLIER_PARTS` | 28 qualified sourcing relationships |

### SCENARIOS schema — scenario engine views

| View | Purpose |
|---|---|
| `V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` | SUP-001, 100%, 14 days |
| `V_ACTIVE_PORT_DISRUPTION_PARAMETERS` | PORT-TYO, 100%, 7 days |
| `V_ACTIVE_FREIGHT_SHOCK_PARAMETERS` | 30% freight increase, 14 days |
| `V_ORDER_PART_DEMAND` | Part requirements per open order |
| `V_BASELINE_PART_SUPPLY` | Supply before disruption |
| `V_SCENARIO_PART_SUPPLY` | Supply after supplier failure |
| `V_ORDER_PART_ALLOCATION` | Priority-based allocation |
| `V_ORDER_IMPACT` | Order-level at-risk analysis |
| `V_SUPPLIER_FAILURE_IMPACT` | Aggregate KPIs (1 row) |
| `V_SUPPLIER_FAILURE_CHAIN` | Full cascade (multi-row) |
| `V_MITIGATION_PART_CAPACITY` | 4 strategies × affected parts |
| `V_MITIGATION_PLANT_CAPACITY` | Proportional plant distribution |
| `V_MITIGATION_ORDER_IMPACT` | Per-order mitigation analysis |
| `V_MITIGATION_ORDER_SUMMARY` | Per-order mitigation summary |
| `V_MITIGATION_COST` | Aggregate cost per strategy |
| `V_MITIGATION_COMPARISON` | **4-strategy comparison** (key demo view) |
| `V_INVENTORY_REALLOCATION_DETAIL` | Per-plant surplus detail |
| `V_PORT_DISRUPTION_*` | Port scenario chain (5 views) |
| `V_FREIGHT_SHOCK_*` | Freight scenario chain (3 views) |
| `SCENARIO_RUNS` | Scenario run log table |

### ANALYTICS schema — governed views and catalog

| View | Purpose |
|---|---|
| `SUPPLY_CHAIN_RISK` | Order-level risk summary |
| `SUPPLIER_PART_DEPENDENCY` | Qualified sourcing relationships |
| `PART_PLANT_INVENTORY` | Inventory coverage days |
| `PRODUCT_DEPENDENCY` | BOM dependency view |
| `ORDER_PART_REQUIREMENTS` | Part requirements per order |
| `SUPPLIER_CONCENTRATION` | Single-source detection |
| `DELAYED_SHIPMENTS` | Active delayed shipments |
| `QUALIFIED_SUPPLIER_OPTIONS` | Qualified sourcing options |
| `PART_SOURCE_PROFILE` | Per-part sourcing profile |
| `EXECUTIVE_RISK_SUMMARY` | Top-level aggregate |
| `V_SCENARIO_VALIDATION` | 5 validation checks (all PASS) |
| `V_NEXUS_EVIDENCE_SUPPLIER_FAILURE` | Evidence for supplier failure |
| `V_NEXUS_EVIDENCE_PORT_DISRUPTION` | Evidence for port disruption |
| `V_NEXUS_GOVERNED_METRIC_CATALOG` | 5 metric definitions |

### SEMANTIC schema

| Object | Purpose |
|---|---|
| `NEXUS_SUPPLY_CHAIN` | Cortex Semantic View — 11 tables, 13 relationships, 14 metrics, 10 verified queries |
| `V_CUSTOMER_SUPPLIER_DEPENDENCY` | Customer→Supplier dependency helper |
| `V_SHIPMENT_EXPOSURE` | Shipment exposure view |

### TOOLS schema

| Object | Purpose |
|---|---|
| `RUN_ACTIVE_SUPPLIER_FAILURE()` | SQL UDF — supplier failure tool |
| `COMPARE_ACTIVE_MITIGATIONS()` | SQL UDF — mitigation comparison tool |
| `RUN_ACTIVE_PORT_DISRUPTION()` | SQL UDF — port disruption tool |
| `GET_ACTIVE_FREIGHT_SHOCK()` | SQL UDF — freight shock tool |

### PUBLIC schema

| Object | Purpose |
|---|---|
| `NEXUS_SUPPLY_CHAIN_AGENT` | Cortex Agent backed by semantic view + 4 tools |

---

## Changing Scenario Parameters

Scenario parameters are hard-coded in three views. To change them, update the view in Snowflake:

```sql
-- Supplier failure: change SUP-001 to another supplier or adjust severity
CREATE OR REPLACE VIEW NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS AS
SELECT
    'SUP-002'::VARCHAR   AS failed_supplier_id,     -- change supplier
    60::NUMBER(8,4)      AS capacity_reduction_pct,  -- 60% reduction
    14::NUMBER(10,0)     AS duration_days,
    '2026-09-18'::DATE   AS start_date;
```

All downstream views (`V_SCENARIO_PART_SUPPLY`, `V_ORDER_IMPACT`, `V_MITIGATION_COMPARISON`, etc.) re-compute automatically — no other changes needed.

**Note:** The UI's `is_unsupported_scenario()` check in `services/snowflake.py` compares the active parameters to the hard-coded seed values. If you change the parameters to a non-seed scenario, the UI will show a warning banner. This is by design — the warning tells users exactly which scenario IS supported.

---

## Known Limitations

| Area | Limitation |
|---|---|
| Scenario parameters | Hard-coded in `V_ACTIVE_*_PARAMETERS` views. UI shows a warning if parameters differ from seed values. |
| Scenario coverage | One supplier failure, one port, one freight scenario. Multi-supplier failure requires extending the engine. |
| Cortex Agent | Requires the Cortex Agent feature to be enabled on your Snowflake account. Not available in all regions. |
| Python runtime | Venv uses Python 3.9 (EOL). Recreate with 3.11+ using `make setup PYTHON=python3.11` for production. |
| Data scale | Demo dataset: ~10 suppliers, 20 parts, 20 orders, 8 customers. Not stress-tested at production scale. |
| Inventory reallocation | The reallocation model distributes surplus proportionally. A production system would use network optimization. |

---

## Troubleshooting

### Streamlit shows "Data source unavailable"

- Verify `secrets.toml` is populated with valid credentials
- Confirm `private_key_path` points to an existing unencrypted PKCS#8 `.pem` file
- Test the connection: `SELECT CURRENT_USER()` in Snowflake with the same credentials

### V_SUPPLIER_FAILURE_IMPACT returns 0 orders at risk

- Confirm `002_seed_data.sql` was re-run (truncates and reinserts with correct dates)
- Verify the disruption window: `SELECT * FROM SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS`
- Check that SUP-001 shipments are IN_TRANSIT/DELAYED after the start date:
  ```sql
  SELECT * FROM RAW.SHIPMENTS WHERE supplier_id = 'SUP-001' AND status IN ('IN_TRANSIT','DELAYED');
  ```

### V_MITIGATION_COMPARISON returns only 3 rows (missing INVENTORY_REALLOCATION)

- Confirm `008_mitigation_engine.sql` (Phase 8 version) was executed after `006_scenario_engine.sql`
- Re-run `008_mitigation_engine.sql` using the latest version from the repo

### Cortex Agent chat returns "not deployed" error

- Confirm `014_nexus_agent.sql` ran successfully
- Verify `NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT` exists: `SHOW AGENTS IN SCHEMA NEXUS_DB.PUBLIC`
- Confirm Cortex Agents are enabled: contact your Snowflake account team
