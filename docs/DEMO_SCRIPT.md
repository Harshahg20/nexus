# NEXUS Demo Script
## Snowflake CoCo CLI Hackathon — GCC Edition

**Theme:** Supply-Chain Ontology and Governed Conversational Analytics  
**Total time:** 5 minutes  
**Central scenario:** SUP-001 (Apex Components, Japan, CRITICAL risk tier) — 100% capacity failure, 14 days

---

## Demo Story

> "Every supply chain team faces the same three questions when a disruption hits: *What's broken? What do we do? What does the data say?* NEXUS answers all three — instantly, from governed Snowflake data."

**Journey: Detect → Ask → Trace → Simulate → Decide → Evidence**

---

## Step 1 — Detect (30 seconds)

Open the NEXUS Executive Command Center (Streamlit app).

**Show the KPI strip (6 live metrics):**

| Metric | What it means |
|---|---|
| Revenue Exposure | Total at-risk revenue under the active scenario |
| Orders at Risk | Count of open orders with a confirmed supply deficit |
| Parts With Shortage | Distinct components with unmet demand |
| Customers Exposed | Buyers with at least one at-risk order |
| Affected Plants | Manufacturing sites with shortage-affected production |
| Units at Risk | Total unmet units across all at-risk orders |

**Say:** "This is live Snowflake data. SUP-001 — Apex Components, our CRITICAL-tier Japanese supplier — is modeled as 100% unavailable for 14 days. NEXUS has already computed the downstream exposure."

---

## Step 2 — Ask (45 seconds)

**Scroll to the NEXUS chat panel. Ask:**

> "What breaks if SUP-001 is unavailable for 14 days?"

**Or click:** `→ SUP-001 failure impact?`

**While the agent responds, narrate:**

"NEXUS routes this to its deterministic scenario engine — not a language model guess. It traces the qualified sourcing relationship: SUP-001 is approved to supply PART-104 (Precision Motor), PART-111 (Safety Controller), and PART-102 (Power Module). It then finds which in-transit shipments are lost, recalculates supply, re-runs priority allocation, and surfaces the orders that can't be fulfilled."

**The agent answer will include:**
- Supplier ID and risk tier
- Affected parts with criticality
- Orders at risk with revenue exposure
- Customers exposed with SLA tier
- Modeled mitigation options

---

## Step 3 — Trace (45 seconds)

**Scroll to "Failure Propagation — SUP-001 Causal Impact"**

**Show the animated cascade:**

```
SUP-001 (Apex Components)
  ↓  qualified supplier → parts
PART-104 · CRITICAL  /  PART-111 · CRITICAL
  ↓  parts consumed by products in BOM
PROD-001 (Nexus Drive)  /  PROD-005 (Nexus Safety Unit)
  ↓  products ordered by customers
PLT-001 Tokyo  /  PLT-002 Osaka
  ↓  plants fulfil orders
ORD-002 · ORD-004 · ORD-011 · ORD-017 ...
  ↓  orders placed by customers
CUST-001 Kanto Robotics (PLATINUM)
CUST-002 Sakura Mobility (GOLD)
CUST-003 Pacific Automation (PLATINUM)
```

**Open the "Parts in SUP-001 Cascade" expander** — shows PART-104 and PART-111 with at-risk revenue.

**Open the "Customers in SUP-001 Cascade" expander** — shows PLATINUM and GOLD SLA customers.

**Say:** "Every node here is a governed entity from our semantic layer. The dependency path uses `SUPPLIER_PARTS` — the authoritative qualification table — not just shipment history."

---

## Step 4 — Simulate (30 seconds)

**Point to the scenario banner:**

> SUP-001 · 100% capacity reduction · 14 days · starting 2026-09-18

**Say:** "The scenario parameters are deterministic. Changing them in Snowflake re-propagates the entire chain — every order, every customer, every part — in seconds."

**Show the Impact Details section** (scroll below the cascade):
- Parts in cascade: confirmed shortage parts from SUP-001's portfolio
- Plants in cascade: manufacturing sites affected
- Orders in cascade: individual at-risk orders with revenue
- Customers in cascade: buyers sorted by at-risk exposure

---

## Step 5 — Decide (75 seconds)

**Scroll to "Compare Mitigations"**

**Show the four-strategy comparison panel:**

| Strategy | What it models |
|---|---|
| **No Action** | Absorb the full disruption — baseline |
| **Expedite Shipment** | Rush in-transit goods via alternate freight (25% cost premium) |
| **Reallocate Inventory** | Transfer surplus stock from non-deficit plants (15% logistics cost) |
| **Alternate Supplier** | Source from other qualified suppliers for the 14-day window |

**Walk through each card:**

- **No Action:** full revenue exposure, no cost
- **Expedite:** partial recovery, modest cost — gets goods already in-transit
- **Reallocate Inventory:** PART-104 has surplus at PLT-005 (Munich/Singapore) that can cover the deficit at PLT-001 and PLT-002 — lowest cost per unit recovered
- **Alternate Supplier:** highest recovery — SUP-002 and SUP-005 are pre-qualified for PART-104 with 450 and 300 unit/day capacity respectively; highest incremental cost

**Say:** "NEXUS doesn't recommend a single answer — it shows the trade-offs. Operations leadership can choose based on cost, customer SLA, and risk appetite. The PLATINUM customers — Kanto Robotics and Pacific Automation — will drive the decision."

---

## Step 6 — Evidence (30 seconds)

**Scroll to "Evidence & Modeling"**

**Show the two panels:**
- **Observed/Governed Data** — 7 RAW source tables in NEXUS_DB
- **Modeled Scenario Outputs** — 6 SCENARIOS views including V_SUPPLIER_FAILURE_IMPACT and V_MITIGATION_COMPARISON

**Open "Governed Metric Definitions"** expander — shows metric name, definition, and source view for every KPI.

**Say:** "Every number on this screen is traceable to a Snowflake governed source. The agent uses the same semantic definitions as the dashboard. There's no silent column rename or ambiguous calculation."

---

## Closing Message (15 seconds)

> "NEXUS doesn't just answer what happened.  
> It traces what breaks next, lets you test what to do about it,  
> and shows the evidence behind every answer —  
> all from a native Snowflake semantic view, a deterministic scenario engine,  
> and a Cortex Agent that speaks the language of your supply chain."

---

## Optional Chat Questions (if time allows)

| Question | What it demonstrates |
|---|---|
| `Which customers are exposed to PART-104?` | BOM dependency tracing via semantic view |
| `What happens if PORT-TYO is disrupted?` | Port disruption engine (different from supplier failure) |
| `Which parts are single-sourced?` | Supplier concentration analytics |
| `Compare alternate supplier versus expedited freight` | Mitigation comparison via Cortex tools |
| `Show me the dependency chain for CUST-003` | Full ontology traversal |

---

## Key Talking Points

- **All business logic lives in Snowflake** — the Streamlit UI is a pure presentation layer
- **SUPPLIER_PARTS is the authoritative qualification table** — not SHIPMENTS history; this is a governance decision that prevents wrong dependency traces
- **Four mitigation strategies are modeled** — including Inventory Reallocation which requires no new procurement, only logistics cost
- **Scenario outputs are labeled "modeled"** — the agent and UI distinguish observed data from scenario estimates throughout
- **The semantic view drives both the dashboard and the agent** — one governed definition, two consumption paths

---

## Technical Highlights for Judges

| Snowflake Feature | Usage in NEXUS |
|---|---|
| Native Semantic View (`CREATE SEMANTIC VIEW`) | `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` — 11 tables, 14 metrics, 10 verified queries |
| Cortex Agent | `NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT` with 4 tool UDFs |
| Cortex Analyst (text-to-SQL) | Backed by the semantic view for baseline analytics |
| Deterministic Scenario Engine | Pure SQL views — no procedural code, no external ML |
| Priority Allocation | Window function (`SUM OVER ... ROWS PRECEDING`) — reproduces order fulfillment logic |
| Governed Metrics | 14 defined metrics in the semantic view + 5 metrics in the governed catalog |
| Snowpark (key-pair auth) | Python Snowpark session with RSA key authentication |
| Streamlit | 7-section dashboard rendered from live Snowflake queries |
