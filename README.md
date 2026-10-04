# NEXUS — Supply Chain Resilience Intelligence

> **When a critical supplier goes dark, every minute of confusion is revenue bleeding away.**
> Global manufacturers lose an estimated **$184 billion per year** to supply chain disruptions — yet most operations teams still piece together impact from disconnected ERP exports, spreadsheets, and gut feel. NEXUS changes that: ask a plain-English question, get a governed, evidence-backed answer in seconds, straight from Snowflake.

---

## 🚀 Try the Live Demo

**Streamlit-in-Snowflake (no install required):**

> **[https://app.snowflake.com/ysyhgbx/cz11690/#/streamlit-apps/NEXUS_DB.STREAMLIT_APP.NEXUS_APP](https://app.snowflake.com/ysyhgbx/cz11690/#/streamlit-apps/NEXUS_DB.STREAMLIT_APP.NEXUS_APP)**

> **GitHub:** [https://github.com/Harshahg20/nexus](https://github.com/Harshahg20/nexus)

Click the link, pick a scenario, and ask NEXUS: *"What breaks if SUP-001 is unavailable for 14 days?"*

---

## Built With Snowflake CoCo CLI

NEXUS was built end-to-end using [Snowflake CoCo CLI](https://docs.snowflake.com/en/developer-guide/coco/overview) — Snowflake's terminal-native AI coding agent that understands your schema, RBAC, and data catalog to generate production-ready SQL, pipelines, and agents from natural language.

### How CoCo CLI Accelerated NEXUS Development

| Component | CoCo CLI Prompt | What It Generated |
|---|---|---|
| Supply Chain Ontology | *"Design a supply chain entity model: Supplier → Part → Plant → Shipment → Order → Customer with FK constraints"* | `001_schema.sql` — full normalized schema with 7 entities |
| Semantic View | *"Create a governed Snowflake Semantic View over the supply chain schema with At-Risk Revenue, Cascade Depth, and Parts Shortage metrics"* | `013_nexus_semantic_view.sql` — NEXUS_SUPPLY_CHAIN with 12 governed metrics |
| Cortex Agent | *"Scaffold a Snowflake Cortex Agent that uses the NEXUS_SUPPLY_CHAIN semantic view to answer supply chain questions"* | `014_nexus_agent.sql` — DATA_AGENT_RUN with semantic view binding |
| Scenario Engine | *"Write SQL views that model a supplier failure and propagate its impact through the full supply chain BOM"* | `006_scenario_engine.sql` — deterministic cascade allocation logic |
| Mitigation Engine | *"Generate inventory reallocation and alternative supplier routing logic as SQL views"* | `008_mitigation_engine.sql` — 4 mitigation strategies |
| Test Suite | *"Write SQL assertions to validate the scenario engine outputs against baseline allocations"* | `009_scenario_tests.sql` + `015_extended_tests.sql` — 33 passing tests |

### Run CoCo CLI Against NEXUS Today

```bash
# Connect CoCo CLI to the NEXUS account
snow connection add --connection-name nexus \
  --account EB70963.ap-northeast-1.aws \
  --user HGHARSHA20 \
  --database NEXUS_DB --warehouse COMPUTE_WH

# Ask CoCo about the supply chain
snow cortex complete \
  --query "What is the revenue impact if SUP-001 is unavailable for 14 days?" \
  --model snowflake-arctic

# Generate a new scenario with CoCo
snow coco "Add a tariff shock scenario that increases part costs by 25% and recalculates at-risk revenue"
```

The `snowflake.yml` project definition (in repo root) connects CoCo CLI to the NEXUS deployment.

---

## What NEXUS Does

- **Traces the full disruption chain** — one supplier failure propagates through parts, inventory, plants, products, orders, and customers in a single governed query, not a week of cross-team emails.
- **Runs deterministic what-if scenarios** — supplier failure, port closure, and freight cost shock are modeled as pure SQL views; changing a parameter in Snowflake re-propagates the entire chain in seconds.
- **Compares mitigation trade-offs side-by-side** — No Action vs. Expedite Shipment vs. Inventory Reallocation vs. Alternate Supplier, with modeled cost and protected revenue for each.
- **Answers natural-language questions over governed data** — a Cortex Agent backed by a native Semantic View means every answer is traceable to a Snowflake-defined metric, not a language-model guess.

---

## Hackathon Submission

| Field | Value |
|---|---|
| **Hackathon** | Snowflake CoCo CLI Hackathon — GCC Edition 2026 |
| **Theme** | Supply Chain Ontology and Governed Conversational Analytics |
| **Account** | EB70963 (AWS ap-northeast-1) |
| **Submission date** | October 2026 |
| **Team** | Cortex Forge |
| **Tagline** | *See the chain. Find the break. Act before the impact.* |

---

## Snowflake Features Used

Every feature below is actively used in NEXUS — not listed for padding.

| Feature | How NEXUS uses it |
|---|---|
| **CoCo CLI** | Terminal-native AI coding agent; used to scaffold all 15 SQL files, the semantic view, Cortex Agent, and Streamlit components from natural language prompts |
| **Cortex Agent** (`CREATE AGENT`) | `NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT` — orchestrates 4 tool UDFs + Cortex Analyst for natural-language Q&A |
| **Native Semantic View** (`CREATE SEMANTIC VIEW`) | `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` — 11 logical tables, 13 relationships, 9 row-level facts, ~50 dimensions, 14 governed metrics, 10 verified queries, AI SQL generation rules |
| **Cortex Analyst (text-to-SQL)** | Embedded as the `nexus_analyst` tool inside the Agent; resolves plain-English questions to governed SQL against the Semantic View |
| **Snowpark Python** | Session management, key-pair RSA authentication, query execution, and data loading in `app/services/snowflake.py` |
| **Streamlit-in-Snowflake (SiS)** | Full 7-section dashboard deployed as a native SiS app — shareable via URL, zero external hosting |
| **SQL UDF (generic agent tool)** | 4 parameterless read-only UDFs in `NEXUS_DB.TOOLS`: `RUN_ACTIVE_SUPPLIER_FAILURE`, `COMPARE_ACTIVE_MITIGATIONS`, `RUN_ACTIVE_PORT_DISRUPTION`, `GET_ACTIVE_FREIGHT_SHOCK` |
| **SQL Views (deterministic scenario engine)** | 15+ views across `NEXUS_DB.SCENARIOS`: supplier failure, port disruption, freight shock, order allocation, and mitigation comparison — pure SQL, no procedural code |
| **Window functions (priority allocation)** | `SUM(...) OVER (PARTITION BY plant_id, part_id ORDER BY priority ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` reproduces order-priority fulfillment logic inside the scenario engine |
| **`OBJECT_CONSTRUCT` / `ARRAY_AGG`** | UDFs return structured JSON objects consumed by the Cortex Agent as tool responses |
| **`CREATE OR REPLACE` idempotent DDL** | All 15 migration scripts are safe to re-run; `002_seed_data.sql` uses `TRUNCATE` + `INSERT` for clean re-execution |
| **Snowflake Stages** | Private key and app assets referenced via Snowflake internal stages for SiS deployment |
| **Query result cache** | TTL-based caching (`st.cache_data`) on all Snowpark queries to minimize warehouse compute |
| **`GREATEST` / `NULLIF` in metrics** | `GREATEST(on_hand_units - safety_stock_units, 0)` and `on_hand_units / NULLIF(daily_consumption, 0)` baked into Semantic View FACTS and METRICS |
| **AI SQL generation rules** | 15 explicit governance rules in `AI_SQL_GENERATION` block — prevent revenue double-counting, enforce `SUPPLIER_PARTS` over `SHIPMENTS` for qualification, and mandate modeled-vs-observed labeling |
| **AI verified queries** | 10 `AI_VERIFIED_QUERIES` with `VERIFIED_AT` timestamps covering the full ontology traversal path |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Streamlit-in-Snowflake (SiS)                   │
│  KPI Cards · Scenario Banner · Cascade Chain · Impact Details    │
│  Mitigation Table · NEXUS Chat · Evidence & Metric Catalog       │
└────────────────────────────┬─────────────────────────────────────┘
                             │ Snowpark (RSA key-pair auth)
┌────────────────────────────▼─────────────────────────────────────┐
│                      NEXUS_DB (Snowflake)                        │
│                                                                  │
│  RAW schema            9 entity tables — suppliers, parts,       │
│                        plants, inventory, ports, shipments,      │
│                        products, orders, customers               │
│                                                                  │
│  SEMANTIC schema       NEXUS_SUPPLY_CHAIN (Semantic View)        │
│                        11 tables · 13 relationships              │
│                        14 metrics · 10 verified queries          │
│                                                                  │
│  SCENARIOS schema      Deterministic scenario engine (SQL views) │
│                        Supplier failure · Port disruption        │
│                        Freight shock · 4 mitigation strategies   │
│                                                                  │
│  TOOLS schema          4 read-only SQL UDFs (agent tools)        │
│                                                                  │
│  ANALYTICS schema      Governed metric catalog + risk summaries  │
│                                                                  │
│  PUBLIC schema         NEXUS_SUPPLY_CHAIN_AGENT (Cortex Agent)   │
└──────────────────────────────────────────────────────────────────┘

Data flow for a natural-language question:

  User question
       ↓
  Cortex Agent (orchestration layer)
       ├─ Baseline analytics → Cortex Analyst → Semantic View → RAW tables
       └─ Scenario modeling  → SQL UDF → SCENARIOS views → OBJECT_CONSTRUCT response
       ↓
  Structured JSON answer
       ↓
  Streamlit chat component (renders evidence + citations)
```

### Supply-Chain Ontology

```
Supplier ──qualified──▶ Part ──BOM──▶ Product ──ordered──▶ Customer
    │                    │                                      │
    │              consumed by                             places order
    │                    │
    ▼                    ▼
Shipment ──via──▶ Port   Plant ──holds──▶ Inventory
    │                       │
    └──────arrives at────────┘
```

---

## Key Metrics (from deployed seed data)

| Metric | Value |
|---|---|
| Suppliers | 10 (1 CRITICAL-tier, 3 HIGH, 4 MEDIUM, 2 LOW) |
| Parts | 20 (5 CRITICAL, 4 HIGH, 6 MEDIUM, 5 LOW) |
| Plants | 5 (Japan × 2, India, Singapore, Germany) |
| Ports | 5 (Tokyo, Osaka, Singapore, Busan, Hamburg) |
| Orders | 50+ open orders across all customer tiers |
| Customers | 8 (PLATINUM, GOLD, and SILVER SLA tiers) |
| Revenue at risk (SUP-001 failure, 14 days) | **$2.1M** |
| Scenario types | 3 (supplier failure, port disruption, freight shock) |
| Mitigation strategies modeled | 4 (No Action, Expedite, Reallocate, Alternate Supplier) |
| Semantic View metrics | 14 governed aggregates |
| Semantic View verified queries | 10 |
| SQL migration files | 15 |
| Regression / validation tests | 33 |

---

## Setup — 5 Steps

### Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.11+** | 3.9 works but is EOL; 3.11+ strongly recommended |
| Snowflake account | Cortex Agent + Semantic Views features enabled |
| Role `ACCOUNTADMIN` (or equivalent) | Required to create database, schemas, agent |
| Warehouse `COMPUTE_WH` | Or update `secrets.toml` to match yours |

### Step 1 — Clone

```bash
git clone https://github.com/Harshahg20/nexus.git
cd nexus
```

### Step 2 — Generate RSA key pair (no password required)

```bash
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out rsa_key.pem
openssl rsa -in rsa_key.pem -pubout -out rsa_key.pub
```

Register the public key in Snowflake:

```sql
ALTER USER <your_user>
  SET RSA_PUBLIC_KEY = '<contents of rsa_key.pub — no header/footer lines>';
```

### Step 3 — Configure secrets

```bash
cp app/.streamlit/secrets.toml.example app/.streamlit/secrets.toml
# Edit secrets.toml — set account, user, private_key_path
```

```toml
[connections.snowflake]
account          = "your-account-identifier"
user             = "your-snowflake-user"
private_key_path = "/absolute/path/to/rsa_key.pem"
role             = "ACCOUNTADMIN"
warehouse        = "COMPUTE_WH"
database         = "NEXUS_DB"
```

### Step 4 — Deploy SQL to Snowflake

Run the following scripts **in order** in a Snowflake worksheet:

```
001_schema.sql            Database, schemas, 9 raw entity tables
002_seed_data.sql         10 suppliers, 20 parts, 5 plants, 50+ orders (idempotent)
003_product_bom.sql       Product-to-part bill of materials
007_supplier_part_sources.sql  Supplier qualification (SUPPLIER_PARTS)
004_semantic_views.sql    Analytics views: SUPPLY_CHAIN_RISK, ORDER_EXPOSURE, etc.
006_scenario_engine.sql   Supplier failure engine (V_SUPPLIER_FAILURE_IMPACT, chain, allocation)
008_mitigation_engine.sql 4 mitigation strategies (NO_ACTION, EXPEDITE, REALLOCATE, ALTERNATE)
010_port_disruption_engine.sql  PORT-TYO disruption scenario
011_freight_shock_engine.sql    30% freight shock scenario
012_validation_views.sql  Evidence views + governed metric catalog
009_scenario_tests.sql    Run to validate — all 9 invariant tests should PASS
013_nexus_semantic_view.sql     Cortex Semantic View (NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN)
014_nexus_agent.sql       Cortex Agent + 4 SQL tool UDFs (requires Cortex Agent preview)
015_extended_tests.sql    Run to validate — 33 extended regression tests should PASS
005_golden_queries.sql    Validation-only golden queries (SELECT statements)
```

> All DDL uses `CREATE OR REPLACE` — scripts are idempotent and safe to re-run.

### Step 5 — Launch the app

```bash
cd app
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
# Opens at http://localhost:8501
```

For Streamlit-in-Snowflake deployment, see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Demo Flow

| Step | What you see | Time |
|---|---|---|
| 1 · KPI Strip | 6 live metrics: Revenue Exposure · Orders at Risk · Parts with Shortage · Customers Exposed · Affected Plants · Units at Risk | 0:30 |
| 2 · Scenario Banner | SUP-001 (Apex Components, Japan, CRITICAL) · 100% capacity · 14 days | 0:15 |
| 3 · Cascade Chain | Animated propagation: SUP-001 → PART-104/111/102 → PLT-001/002 → PROD-001/005 → ORD-002/004/011… → CUST-001/003 | 1:00 |
| 4 · Mitigation Table | Side-by-side: No Action $2.1M exposed · Expedite · Reallocate Inventory (lowest cost) · Alternate Supplier (highest recovery) | 0:45 |
| 5 · NEXUS Chat | Ask: *"What breaks if SUP-001 is unavailable for 14 days?"* — Cortex Agent answers with evidence | 1:30 |
| 6 · Evidence Panel | Governed metric definitions, source tables, verified query SQL | 0:30 |

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the full rehearsable 5-minute script.

---

## Project Structure

```
nexus/
├── README.md
├── SUBMISSION.md                     ← Hackathon submission brief
├── app/
│   ├── streamlit_app.py              Entry point (7 UI sections)
│   ├── requirements.txt
│   ├── .streamlit/
│   │   ├── config.toml               Theme + Snowflake connection config
│   │   └── secrets.toml.example      Credential template (safe to commit)
│   ├── components/                   One file per dashboard section
│   │   ├── kpi_cards.py              6-metric KPI strip
│   │   ├── scenario_panel.py         Active scenario banner
│   │   ├── dependency_graph.py       Animated cascade chain
│   │   ├── impact_details.py         Expandable parts / plants / orders / customers
│   │   ├── mitigation_table.py       4-strategy comparison panel
│   │   ├── chat.py                   Cortex Agent chat interface
│   │   └── evidence.py               Governed metric catalog + source evidence
│   ├── services/
│   │   ├── snowflake.py              Snowpark session + query loaders
│   │   └── agent.py                  Cortex Agent API wrapper (60 s timeout)
│   └── ui/
│       ├── theme.py                  Design tokens, global CSS
│       └── html.py                   HTML render helpers
├── agent/
│   ├── NEXUS_AGENT_INSTRUCTIONS.md   Agent system prompt
│   ├── NEXUS_TOOL_CONTRACT.md        Tool routing + governance rules
│   └── README.md
├── snowflake/                        15 ordered SQL migration files
│   ├── 001_schema.sql … 015_extended_tests.sql
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md
│   ├── PRD.md
│   ├── SCENARIOS.md
│   ├── ONTOLOGY.md
│   ├── METRICS.md
│   ├── DEPLOYMENT.md
│   └── EVALUATION.md
└── tests/
    └── test_utils.py                 Unit tests (no Snowflake connection required)
```

---

## Known MVP Limitations

| Area | Limitation |
|---|---|
| Scenario parameters | Hard-coded in `V_ACTIVE_*_PARAMETERS` views. Changing them requires editing the Snowflake view directly — UI does not expose parameter controls. |
| Cortex Agent timeout | Defaults to 60 s wall-clock. Adjust `AGENT_TIMEOUT` in `services/agent.py` for cold-start warehouses. |
| Multi-turn threads | Thread IDs are not persisted across browser sessions. Each chat session starts fresh. |
| Scale | Demo dataset: 10 suppliers, 20 parts, 5 plants, 50+ orders. Not load-tested at production scale. |

---

## Security

- `secrets.toml` is `.gitignore`d — never committed. Use `secrets.toml.example` as a template.
- RSA private key must be stored outside the repository (absolute path in `secrets.toml`).
- All SQL executed by the app is visible in Snowflake Query History under the authenticated user.
- No raw tracebacks are shown to end users — all service errors are caught and converted to friendly messages.

---

## Running the Tests

```bash
cd app
python -m pytest ../tests/ -v
# No live Snowflake connection required
```

For scenario regression tests, run `snowflake/009_scenario_tests.sql` and `snowflake/015_extended_tests.sql` in a deployed NEXUS_DB environment. All 33 tests should return `result = 'PASS'`.
