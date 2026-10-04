# NEXUS — Hackathon Submission Brief
## Snowflake CoCo CLI Hackathon — GCC Edition 2026

---

## Elevator Pitch (50 words)

NEXUS is a Snowflake-native supply chain resilience platform that turns a single natural-language question — *"What breaks if our critical supplier fails?"* — into a governed, evidence-backed answer: the full disruption cascade from supplier to customer, three scenario types, and four side-by-side mitigation trade-offs, all computed inside Snowflake in seconds.

---

## Problem Statement

Global manufacturers lose an estimated $184 billion per year to supply chain disruptions. The damage is rarely the disruption itself — it is the **decision lag**: disconnected ERP exports, cross-team email threads, and analyst-built spreadsheets that take days to translate a supplier failure into a customer impact and a response plan.

Three specific problems compound this:

1. **Cross-system blindness** — impact data lives in ERP, WMS, TMS, and supplier portals. No single governed view connects them.
2. **Inconsistent metrics** — different teams compute "orders at risk" or "revenue exposure" differently, leading to conflicting answers from the same data.
3. **No path from problem to action** — operations teams can identify a disruption but cannot quickly model what to do about it with quantified trade-offs.

---

## Solution Description

NEXUS creates a **connected supply-chain ontology** inside Snowflake — Supplier → Part → Plant → Inventory → Product → Order → Customer — and exposes it through three layers:

1. **A native Cortex Semantic View** (`NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN`) with 11 logical tables, 13 governed relationships, 14 business metrics, and 10 verified queries. This is the single source of truth for both the AI agent and the dashboard.

2. **A deterministic scenario engine** (pure SQL views across `NEXUS_DB.SCENARIOS`) that propagates supplier failure, port closure, and freight cost shock through the full dependency chain — no ML, no black box — and compares four mitigation strategies side-by-side.

3. **A Cortex Agent** (`NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT`) that routes plain-English questions to either Cortex Analyst (text-to-SQL against the Semantic View) or one of four SQL UDF tools (deterministic scenario execution), then synthesizes an evidence-backed answer.

The Streamlit-in-Snowflake dashboard surfaces everything visually: KPI strip, animated cascade chain, mitigation comparison, and a governed metric evidence panel — all from live Snowflake queries.

---

## Snowflake Features Used

- **Cortex Agent** (`CREATE AGENT`) — `NEXUS_SUPPLY_CHAIN_AGENT` orchestrates Cortex Analyst + 4 generic SQL UDF tools; handles routing, tool calling, and answer synthesis
- **Native Semantic View** (`CREATE SEMANTIC VIEW`) — 11 tables, 13 relationships, 9 row-level facts, ~50 dimensions, 14 governed metrics, 10 verified queries, AI SQL generation rules, AI question categorization rules
- **Cortex Analyst (text-to-SQL)** — embedded as the `nexus_analyst` tool inside the Agent; resolves natural-language questions to governed SQL
- **Snowpark Python** — key-pair RSA authentication, session management, TTL-cached query execution in `app/services/snowflake.py`
- **Streamlit-in-Snowflake (SiS)** — full 7-section dashboard deployed natively; shareable URL, no external hosting
- **SQL UDFs (generic agent tools)** — 4 parameterless read-only functions: `RUN_ACTIVE_SUPPLIER_FAILURE`, `COMPARE_ACTIVE_MITIGATIONS`, `RUN_ACTIVE_PORT_DISRUPTION`, `GET_ACTIVE_FREIGHT_SHOCK`
- **SQL Views (deterministic engine)** — 15+ views across `SCENARIOS` schema; priority allocation uses `SUM OVER (PARTITION BY ... ORDER BY priority ROWS UNBOUNDED PRECEDING)` window function
- **`OBJECT_CONSTRUCT` / `ARRAY_AGG`** — UDFs return structured JSON objects consumed by the Agent as tool responses
- **AI SQL generation rules** — 15 explicit governance rules preventing revenue double-counting and unauthorized supplier qualification inference
- **AI verified queries** — 10 queries with `VERIFIED_AT` timestamps for grounded, deterministic reference SQL
- **`GREATEST` / `NULLIF` in Semantic View FACTS** — `usable_inventory_units` and `coverage_days` computed inline in the semantic model
- **`CREATE OR REPLACE` idempotent DDL** — all 15 migration scripts safe to re-run

---

## Technical Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│              Streamlit-in-Snowflake (SiS)                        │
│  KPI Cards · Cascade Chain · Mitigation Table · NEXUS Chat       │
└──────────────────────┬───────────────────────────────────────────┘
                       │ Snowpark (RSA key-pair auth)
┌──────────────────────▼───────────────────────────────────────────┐
│                    NEXUS_DB (Snowflake)                          │
│                                                                  │
│  RAW       9 entity tables (suppliers, parts, plants, etc.)      │
│  SEMANTIC  NEXUS_SUPPLY_CHAIN Semantic View                      │
│            11 tables · 13 relationships · 14 metrics             │
│  SCENARIOS Deterministic scenario engine (SQL views)             │
│            Supplier failure · Port disruption · Freight shock    │
│            4 mitigation strategies                               │
│  TOOLS     4 read-only SQL UDFs (Cortex Agent tools)             │
│  ANALYTICS Governed metric catalog + risk summaries              │
│  PUBLIC    NEXUS_SUPPLY_CHAIN_AGENT (Cortex Agent)               │
└──────────────────────────────────────────────────────────────────┘

Question routing:
  Natural-language baseline query  → Cortex Analyst → Semantic View → RAW
  Scenario disruption question     → SQL UDF → SCENARIOS views → JSON response
  Both paths                       → Cortex Agent synthesizes answer with evidence
```

**Ontology:** `Supplier → Part → Plant → Inventory → Product → Order → Customer`

---

## Business Impact / Value Proposition

| Dimension | NEXUS Outcome |
|---|---|
| **Decision speed** | Supplier-to-customer impact computed in seconds, not analyst-days |
| **Revenue protection** | $2.1M at-risk revenue surfaced immediately under the default scenario |
| **Governance** | One Semantic View definition consumed by both dashboard and AI agent — no metric drift |
| **Actionability** | 4 mitigation strategies with quantified cost and protected revenue — operations teams see trade-offs, not just alerts |
| **Explainability** | Every answer traceable to a Snowflake governed view, metric definition, and verified query |
| **Snowflake-native** | Zero external APIs, no external ML, no infrastructure to manage — runs entirely inside the customer's Snowflake account |

---

## Live Demo

**Streamlit-in-Snowflake (no install required):**

> **https://app.snowflake.com/ysyhgbx/cz11690/#/streamlit-apps/NEXUS_DB.STREAMLIT_APP.NEXUS_APP**

Suggested first question to the NEXUS chat: *"What breaks if SUP-001 is unavailable for 14 days?"*

---

## GitHub Repository

> **https://github.com/Harshahg20/nexus**

---

## How to Run Locally

### Prerequisites
- Python 3.11+
- Snowflake account with Cortex Agent + Semantic Views enabled
- Role `ACCOUNTADMIN` (or equivalent)
- Warehouse `COMPUTE_WH`

### Quick start

```bash
# 1. Clone
git clone https://github.com/Harshahg20/nexus.git && cd nexus

# 2. Generate RSA key pair
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out rsa_key.pem
openssl rsa -in rsa_key.pem -pubout -out rsa_key.pub

# 3. Register public key in Snowflake (run in a Snowflake worksheet)
# ALTER USER <your_user> SET RSA_PUBLIC_KEY = '<rsa_key.pub contents>';

# 4. Configure credentials
cp app/.streamlit/secrets.toml.example app/.streamlit/secrets.toml
# Edit secrets.toml — set account, user, private_key_path

# 5. Deploy SQL (run in order in Snowflake)
# See README.md for full ordered list of 15 SQL scripts

# 6. Launch
cd app
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
# Opens at http://localhost:8501
```

Full setup instructions: [`README.md`](../README.md)
Full deployment guide: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

---

## Team

| Field | Value |
|---|---|
| **Team name** | Cortex Forge |
| **Hackathon** | Snowflake CoCo CLI Hackathon — GCC Edition 2026 |
| **Submission date** | October 2026 |
| **Snowflake account** | EB70963 (AWS ap-northeast-1) |
