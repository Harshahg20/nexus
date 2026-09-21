# NEXUS — Supply Chain Resilience Command Center

> **Snowflake CoCo CLI Hackathon submission.**
> Built on Snowflake Cortex AI, Snowpark, a native Semantic View, and a deterministic scenario engine — entirely within Snowflake.

---

## Project Overview

NEXUS is a real-time supply-chain resilience dashboard.  
It lets operations teams instantly answer three questions:

| Question | NEXUS Answer |
|---|---|
| **See the chain** | Full cascade map: which suppliers → parts → plants → products → orders → customers are connected |
| **Find the break** | Scenario engine: what breaks if a supplier fails, a port closes, or freight costs spike |
| **Act before the impact** | Three modeled mitigation strategies with cost/recovery trade-offs |

All business logic lives in Snowflake.  The Streamlit front-end is a pure presentation layer.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Streamlit UI                         │
│  kpi_cards  ·  scenario_panel  ·  dependency_graph          │
│  impact_details  ·  mitigation_table  ·  chat  ·  evidence  │
└───────────────────┬─────────────────────────────────────────┘
                    │  Snowpark (key-pair auth)
┌───────────────────▼─────────────────────────────────────────┐
│                     Snowflake (NEXUS_DB)                     │
│                                                             │
│  RAW schema         — 9 observed entity tables              │
│  SEMANTIC schema    — Cortex Semantic View (11 entities)     │
│  SCENARIOS schema   — Deterministic scenario engine (views) │
│  ANALYTICS schema   — Governed metric catalog + summaries   │
└─────────────────────────────────────────────────────────────┘
                    │
         Cortex Agents (DATA_AGENT_RUN)
         ↳ NEXUS_SUPPLY_CHAIN_AGENT
           backed by NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN
```

### Key Snowflake objects

| Object | Purpose |
|---|---|
| `NEXUS_DB.RAW.*` | 9 observed entity tables (suppliers, parts, plants, inventory, ports, shipments, products, orders, customers) |
| `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` | Cortex Semantic View — 11 logical tables, 14 metrics, 10 verified queries |
| `NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` | Active scenario configuration |
| `NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | Shortage-allocation KPIs (1 aggregate row) |
| `NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` | Full cascade chain (multi-row) |
| `NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON` | Three modeled mitigation strategies |
| `NEXUS_DB.ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG` | Governed metric definitions |
| `NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT` | Cortex Agent (natural-language Q&A) |

### Metric scope note

Two Snowflake views serve related but distinct counts:

- **`V_SUPPLIER_FAILURE_IMPACT`** (KPI strip) — counts orders / customers / parts where the priority-allocation engine produced a confirmed supply deficit.
- **`V_SUPPLIER_FAILURE_CHAIN`** (cascade drill-down) — traces every entity in the full disruption path, including those only partially impacted.

These differences are intentional.  Both scopes are displayed with explanatory labels in the UI.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.11+** | 3.9 works but is EOL — Snowflake has deprecated that runtime. The app shows a warning banner on 3.9. Install 3.11+ and recreate the venv before production use (see below). |
| Snowflake account | With Cortex features enabled (Agents, Semantic Views) |
| Role `ACCOUNTADMIN` (or equivalent) | To query NEXUS_DB |
| Warehouse `COMPUTE_WH` | Or update `secrets.toml` to match yours |
| `NEXUS_DB` deployed | Run all SQL scripts in `sql/` (see Deployment below) |

### Python dependencies

```
snowflake-snowpark-python
streamlit>=1.35
pandas
cryptography
```

Install with:

```bash
cd app
pip install -r requirements.txt
```

### Upgrading to Python 3.11+

```bash
# macOS — install via Homebrew (recommended)
brew install python@3.11

# Then recreate the venv with the new interpreter
make setup PYTHON=python3.11

# Or manually:
python3.11 -m venv app/venv
app/venv/bin/pip install -r app/requirements.txt
```

---

## Key-Pair Authentication Setup

NEXUS uses RSA key-pair authentication (no password, no browser pop-up — required for automated/server deployments).

### 1. Generate the key pair

```bash
# Generate unencrypted private key (PKCS#8 PEM)
openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out rsa_key.pem

# Extract the public key
openssl rsa -in rsa_key.pem -pubout -out rsa_key.pub
```

### 2. Register the public key in Snowflake

```sql
-- Run in Snowflake as ACCOUNTADMIN or SECURITYADMIN
ALTER USER <your_user>
  SET RSA_PUBLIC_KEY = '<paste contents of rsa_key.pub — header/footer lines excluded>';
```

### 3. Store the private key path in secrets.toml

```toml
# app/.streamlit/secrets.toml  (NEVER commit this file)
[connections.snowflake]
account          = "your-account-identifier"
user             = "your-snowflake-user"
private_key_path = "/absolute/path/to/rsa_key.pem"
role             = "ACCOUNTADMIN"
warehouse        = "COMPUTE_WH"
database         = "NEXUS_DB"
```

> See `app/.streamlit/secrets.toml.example` for a ready-to-copy template.

---

## Local Streamlit Startup

```bash
# From the repo root
cd app

# (First time) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and fill in credentials
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml — set account, user, private_key_path

# Launch
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

---

## Demo Flow

The recommended live demo path (all data is live from Snowflake):

| Step | What to show | Journey |
|---|---|---|
| 1 | Open the dashboard | KPI strip loads — 6 live metrics |
| 2 | Read the scenario banner | SUP-001 · 100% capacity · 14 days |
| 3 | Scroll to **Failure Propagation** | Animated cascade: supplier → parts → plants → products → orders → customers |
| 4 | Open **Parts in Cascade** expander | PART-104 in the chain |
| 5 | Open **Customers in Cascade** expander | Customers exposed to PART-104 |
| 6 | Scroll to **Compare Mitigations** | Side-by-side: No Action vs Expedite vs Alternate Supplier |
| 7 | Ask **NEXUS** (chat): `What happens if PORT-TYO is disrupted?` | Cortex Agent answers using the semantic view |
| 8 | Ask: `Which customers are exposed to PART-104?` | Natural-language query over governed data |
| 9 | Scroll to **Evidence & Modeling** | Expand "Governed Metric Definitions" — shows full metric catalog |
| 10 | Refresh the page | All data reloads from Snowflake (TTL cache = 5 min) |

---

## Known MVP Limitations

| Area | Limitation | Mitigation |
|---|---|---|
| Scenario parameters | Hard-coded in `V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS`. UI cannot change the active scenario — editing parameters requires updating the Snowflake view. | The UI detects unsupported parameters and shows a clear guidance banner instead of silently returning blank data. |
| Scenario coverage | Only the seeded scenario (SUP-001 · 100% · 14 days) is supported by the supplier-failure engine. The UI shows a warning if different parameters are detected. | Port disruption (PORT-TYO) and freight shock are available via the Cortex Agent chat. |
| Cortex Agent timeout | Long or complex agent queries default to a 60 s wall-clock timeout. | Timeout raises a user-friendly message with a retry suggestion. Adjust `AGENT_TIMEOUT` in `services/agent.py` if your warehouse needs more warm-up time. |
| Multi-turn threads | Thread IDs are not yet persisted between sessions. Each chat session is independent. | Acceptable for a demo; add `st.session_state` thread management for production. |
| Auth method | Key-pair only. `externalbrowser` (OAuth) is not currently configured. | See secrets.toml.example for key-pair setup. |
| Data refresh | Snowflake query cache TTL is 5 minutes. Failed queries are never cached — they retry on every render. | Set `ttl=` in `_query_df_cached` to control freshness. |
| Scale | Demo dataset: ~10 suppliers, 20 parts, 5 plants, 6 products, 20 orders, 8 customers. Not tested at production scale. | — |

---

## Security Guidance

- **Never commit `secrets.toml`** — it is listed in `.gitignore`. The example file (`secrets.toml.example`) contains only placeholders.
- **Keep the RSA private key outside the repository** — use an absolute path in `secrets.toml`.
- **Use the principle of least privilege** — consider creating a dedicated Snowflake role for the app rather than using `ACCOUNTADMIN`.
- **Rotate keys periodically** — `ALTER USER <user> SET RSA_PUBLIC_KEY = '<new_key>'`.
- **No raw tracebacks are shown to end users** — all service errors are caught and converted to friendly messages. Internal details are logged to the Streamlit server console only.
- **Audit queries** — all SQL executed by the app is visible in Snowflake's Query History under the authenticated user.

---

## Running the Tests

The test suite covers pure utility functions and does **not** require a live Snowflake connection.

```bash
cd app
python -m pytest ../tests/ -v
```

Expected output: all tests pass with no Snowflake credentials required.

---

## Project Structure

```
nexus/
├── README.md
├── app/
│   ├── streamlit_app.py          # Entry point
│   ├── requirements.txt
│   ├── .streamlit/
│   │   ├── config.toml           # Streamlit theme config
│   │   ├── secrets.toml          # NOT committed — your credentials
│   │   └── secrets.toml.example  # Template (safe to commit)
│   ├── components/               # UI sections (one file per section)
│   │   ├── kpi_cards.py
│   │   ├── scenario_panel.py
│   │   ├── dependency_graph.py
│   │   ├── impact_details.py
│   │   ├── mitigation_table.py
│   │   ├── chat.py
│   │   └── evidence.py
│   ├── services/                 # Data access layer
│   │   ├── snowflake.py          # Snowpark session + loaders
│   │   └── agent.py              # Cortex Agent wrapper
│   └── ui/
│       ├── theme.py              # Design tokens, global CSS
│       └── html.py               # HTML helpers
├── agent/                        # Agent documentation
│   ├── NEXUS_AGENT_INSTRUCTIONS.md
│   ├── NEXUS_TOOL_CONTRACT.md
│   └── README.md
└── tests/
    └── test_utils.py             # Unit tests (no Snowflake required)
```

---

## Snowflake Deployment

SQL scripts are in the `sql/` directory (see `.cortex/plans/` for the full execution order).  
Run in this order: `001_schema → 002_seed_data → 003_product_bom → 007_supplier_part_sources → 004_semantic_views → 006_scenario_engine → 008_mitigation_engine → 010_port_disruption_engine → 011_freight_shock_engine → 012_validation_views → 009_scenario_tests → 013_nexus_semantic_view`

All scripts are idempotent (`CREATE OR REPLACE`).
