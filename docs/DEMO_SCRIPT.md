# NEXUS — 5-Minute Demo Script
## Snowflake CoCo CLI Hackathon — GCC Edition 2026

**Theme:** Supply Chain Ontology and Governed Conversational Analytics
**Total time:** 5 minutes 00 seconds
**Central scenario:** SUP-001 (Apex Components, Japan, CRITICAL) — 100% capacity failure, 14 days
**Demo URL:** https://app.snowflake.com/ysyhgbx/cz11690/#/streamlit-apps/NEXUS_DB.STREAMLIT_APP.NEXUS_APP

---

## THE STORY IN ONE SENTENCE

> A critical Japanese supplier just went dark. Every operations team faces the same three questions: *What's broken? What do we do about it? And can we trust the numbers?* NEXUS answers all three — in under five minutes, from governed Snowflake data.

---

## SEGMENT 1 — THE PROBLEM (0:00–0:30)

**[Don't open the app yet. Look at the judges.]**

"Gartner estimates supply chain disruptions cost manufacturers $184 billion per year. But the real cost isn't the disruption itself — it's the *decision lag*. An analyst pulls an ERP export. A planner emails four teams. Someone builds a spreadsheet. By the time you understand what's broken, you've already missed your PLATINUM customers' SLA window.

NEXUS eliminates that lag. Watch."

**[Open the app.]**

---

## SEGMENT 2 — DASHBOARD WALKTHROUGH (0:30–2:00)

**[The KPI strip loads at the top of the screen.]**

"These six numbers are live from Snowflake — no cached CSV, no pre-computed slide. Right now, with SUP-001 modeled as 100% unavailable for 14 days:

- **$2.1 million** in revenue is at risk
- **17 open orders** cannot be fulfilled
- **3 critical parts** are in shortage
- **3 customers** — including two PLATINUM-tier accounts — are exposed

That's the business impact, computed in seconds from a single deterministic SQL engine."

**[Point to the scenario banner below the KPI strip.]**

"The active scenario: Apex Components, our CRITICAL-tier Japanese supplier, SUP-001, 100% capacity reduction starting September 18. Changing this parameter in Snowflake re-propagates the entire chain automatically."

**[Scroll down to the Failure Propagation section.]**

"Now here's what makes NEXUS different from a dashboard. This isn't a KPI. This is the *causal chain.*"

---

## SEGMENT 3 — CASCADE CHAIN (2:00–3:00)

**[Point to the animated cascade.]**

"Watch the dependency trace:

```
SUP-001 (Apex Components)
  ↓  qualified supplier → PART-104 (Precision Motor, CRITICAL)
                       → PART-111 (Safety Controller, CRITICAL)
  ↓  parts required by product BOM
PROD-001 (Nexus Drive)  →  PROD-005 (Nexus Safety Unit)
  ↓  products fulfil orders at plants
PLT-001 (Tokyo Assembly)  ·  PLT-002 (Osaka Systems)
  ↓  plants fulfil open customer orders
ORD-002  ·  ORD-004  ·  ORD-011  ·  ORD-017 …
  ↓  orders belong to customers
CUST-001 Kanto Robotics  [PLATINUM]
CUST-003 Pacific Automation  [PLATINUM]
```

Every node here is a governed entity from `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` — our native Snowflake Semantic View. The dependency path uses `SUPPLIER_PARTS`, the *authoritative* qualification table, not shipment history. That governance decision is encoded in the semantic view's AI SQL generation rules."

**[Open the 'Customers in SUP-001 Cascade' expander.]**

"PLATINUM customers first — because that's how a real prioritization engine works."

---

## SEGMENT 4 — NEXUS CHAT — AI AGENT (3:00–4:30)

**[Scroll to the NEXUS chat panel.]**

**TYPE OR CLICK:** `What breaks if SUP-001 is unavailable for 14 days?`

**[While the agent responds, narrate:]**

"NEXUS routes this to `RUN_ACTIVE_SUPPLIER_FAILURE` — a deterministic SQL UDF, not a language model guess. The Cortex Agent calls it, gets a structured JSON response, and synthesizes an evidence-backed answer. Every metric in the response is traceable to a governed Snowflake view."

**[Read 2-3 lines from the agent answer aloud. Then ask a second question.]**

**TYPE:** `Which customers are exposed to a PART-104 shortage?`

"Now it routes to Cortex Analyst — text-to-SQL against our Semantic View. The verified query traces: `supplier_parts → parts → product_parts → orders → customers`. Kanto Robotics and Pacific Automation come back because that's what the data says — no hallucination, no approximation."

---

## SEGMENT 5 — MITIGATION (4:30–5:00)

**[Scroll to 'Compare Mitigations'.]**

"NEXUS doesn't just show the problem — it shows the response options.

| Strategy | Cost | Revenue Protected |
|---|---|---|
| No Action | $0 | $0 — full $2.1M exposed |
| Expedite Shipment | 25% freight premium | Partial — recovers in-transit goods |
| **Reallocate Inventory** | **15% logistics** | **Highest value, lowest cost** — surplus at PLT-005 Munich covers PLT-001 and PLT-002 deficits |
| Alternate Supplier | Sourcing premium | Full recovery — SUP-002 and SUP-005 are pre-qualified for PART-104 |

Operations leadership chooses based on cost, customer SLA, and risk appetite. NEXUS surfaces the trade-offs — it doesn't make the call for you."

---

## CLOSING (4:55–5:00)

**[Look up from the screen.]**

"NEXUS is three things in one Snowflake account:
- A **governed semantic layer** — one definition, used by both the dashboard and the AI agent
- A **deterministic scenario engine** — pure SQL views, reproducible results, no black box
- A **Cortex Agent** — natural language over the same governed data, with evidence

Everything you saw ran inside Snowflake. No external APIs. No hidden models. No spreadsheets.

Thank you."

---

## OPTIONAL QUESTIONS (if time allows)

| Question | What it demonstrates |
|---|---|
| `Which parts are single-sourced?` | Supplier concentration via Semantic View `qualified_source_count` metric |
| `What happens if PORT-TYO is disrupted?` | Port disruption engine — different propagation path (port → shipments → plants → orders) |
| `Compare alternate supplier versus expedited freight` | `COMPARE_ACTIVE_MITIGATIONS` UDF — all 4 strategies with modeled cost |
| `Show me the dependency chain for CUST-003` | Full ontology traversal Q10 verified query |
| `Which plants have the lowest inventory coverage?` | Q3 verified query — `on_hand_units / daily_consumption` sorted ascending |

---

## KEY TALKING POINTS FOR JUDGES

| Point | Detail |
|---|---|
| All business logic lives in Snowflake | Streamlit is a pure presentation layer — zero business logic in Python |
| `SUPPLIER_PARTS` is authoritative | Not `SHIPMENTS` — this governance decision is enforced in the Semantic View AI SQL rules |
| 4 mitigation strategies modeled | Including Inventory Reallocation — no new procurement, only logistics cost |
| Scenario outputs are labeled "modeled" | Agent and dashboard distinguish observed data from scenario estimates throughout |
| One semantic view, two consumers | Both the dashboard and the Cortex Agent use `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` |
| 33 regression tests | `009_scenario_tests.sql` + `015_extended_tests.sql` — all invariants verified |

---

## TECHNICAL HIGHLIGHTS TABLE

| Snowflake Feature | Usage in NEXUS |
|---|---|
| `CREATE SEMANTIC VIEW` | `NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN` — 11 tables, 13 relationships, 14 metrics, 10 verified queries |
| `CREATE AGENT` | `NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT` — orchestrates Cortex Analyst + 4 generic SQL UDF tools |
| Cortex Analyst (text-to-SQL) | Embedded as `nexus_analyst` tool in the Agent; backed by the Semantic View |
| Deterministic Scenario Engine | Pure SQL views — no procedural code, reproducible results |
| Priority Allocation Window Function | `SUM OVER (PARTITION BY plant_id, part_id ORDER BY priority ROWS UNBOUNDED PRECEDING)` |
| Snowpark Python (key-pair auth) | RSA key-pair authentication, session management, TTL-cached query execution |
| Streamlit-in-Snowflake | Native SiS deployment — shareable URL, no external hosting |
| `OBJECT_CONSTRUCT` / `ARRAY_AGG` | UDFs return structured JSON consumed by the Cortex Agent as tool responses |
| AI SQL generation rules | 15 governance rules preventing revenue double-counting and hallucinated qualifications |
| AI verified queries | 10 verified queries with `VERIFIED_AT` timestamps — grounded, deterministic reference SQL |
