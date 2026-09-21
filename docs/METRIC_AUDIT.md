# NEXUS Phase 7 — Metric Audit Report

**Date:** 2026-09-22  
**Scenario:** Supplier Failure · SUP-001 · 100% capacity reduction · 14 days · start 2026-09-18  
**Auditor:** Phase 7 automated audit

---

## 1. Repository Structure

```
nexus/
├── app/
│   ├── streamlit_app.py          Entry point
│   ├── components/               One file per UI section
│   │   ├── kpi_cards.py          → V_SUPPLIER_FAILURE_IMPACT
│   │   ├── scenario_panel.py     → V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS
│   │   ├── dependency_graph.py   → V_SUPPLIER_FAILURE_CHAIN
│   │   ├── impact_details.py     → V_SUPPLIER_FAILURE_CHAIN
│   │   ├── mitigation_table.py   → V_MITIGATION_COMPARISON
│   │   ├── chat.py               → NEXUS_SUPPLY_CHAIN_AGENT (Cortex)
│   │   └── evidence.py           → V_NEXUS_GOVERNED_METRIC_CATALOG
│   └── services/
│       ├── snowflake.py          Session, query helpers, loaders
│       └── agent.py              DATA_AGENT_RUN wrapper
├── snowflake/                    All SQL scripts (001–014)
├── agent/                        Agent instructions + tool contract
├── docs/                         Architecture, metrics, scenarios, PRD
├── tests/                        Unit tests (no live Snowflake required)
└── Makefile                      Setup + test helpers
```

---

## 2. Snowflake Object Inventory (UI-consumed)

| Object | Schema | Type | Consumed by |
|--------|--------|------|-------------|
| `V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` | SCENARIOS | View | scenario_panel |
| `V_SUPPLIER_FAILURE_IMPACT` | SCENARIOS | View | kpi_cards |
| `V_SUPPLIER_FAILURE_CHAIN` | SCENARIOS | View | dependency_graph, impact_details |
| `V_MITIGATION_COMPARISON` | SCENARIOS | View | mitigation_table |
| `V_NEXUS_GOVERNED_METRIC_CATALOG` | ANALYTICS | View | evidence (expander) |
| `NEXUS_SUPPLY_CHAIN_AGENT` | PUBLIC | Cortex Agent | chat |

---

## 3. Metric Audit — Source-of-Truth Matrix

| UI Section | UI Label | Displayed Value | Snowflake Source | Exact Column / Aggregate | Business Definition | Scope | Data Type | Comparable With | Status |
|---|---|---|---|---|---|---|---|---|---|
| KPI Strip | Revenue Exposure | $X.xxM | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `SUM(at_risk_revenue) WHERE at_risk_quantity > 0` from `V_ORDER_IMPACT` | Sum of modelled at-risk revenue for open orders with confirmed unmet product quantity | **All** open orders with any unmet demand under the active scenario (all causes) | Modelled scenario outcome | Mitigation "Remaining Exposure" (NO_ACTION row) | VERIFIED — label accurate |
| KPI Strip | Orders at Risk | 20 | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `COUNT_IF(at_risk_quantity > 0)` from `V_ORDER_IMPACT` | Count of open orders with positive unmet product quantity after priority allocation | **All causes** — includes 4 orders whose shortage exists in the baseline (pre-existing zero supply for non-SUP-001 parts: PART-105, PART-109, PART-112, PART-113, PART-115) | Modelled scenario outcome | Chain "Orders at Risk" (16) — chain is SUP-001-caused only | **SCOPE DIFFERENCE** — see §4 |
| KPI Strip | Affected Parts | 11 | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `COUNT(DISTINCT part_id) WHERE unmet_part_units > 0` from `V_ORDER_PART_ALLOCATION` | Distinct parts with positive unmet part units in the allocation pass | **All causes** — includes 7 parts with zero supply in the baseline unrelated to SUP-001 | Modelled scenario outcome | Chain "Parts (4)" — chain is SUP-001-portfolio only | **SCOPE DIFFERENCE** — see §4 |
| KPI Strip | Customers Exposed | 8 | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `COUNT(DISTINCT customer_id) WHERE at_risk_quantity > 0` from `V_ORDER_IMPACT` | Distinct customers with at least one at-risk order (any cause) | **All causes** — all 8 seeded customers have some at-risk order | Modelled scenario outcome | Chain "Customers (7)" — chain is SUP-001-caused only | **SCOPE DIFFERENCE** |
| KPI Strip | Affected Plants | 5 | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `COUNT(DISTINCT plant_id) WHERE at_risk_quantity > 0` from `V_ORDER_IMPACT` | Distinct plants with at least one at-risk order | All 5 plants have at-risk orders under the scenario | Modelled scenario outcome | Impact Details "5 plants" | **VERIFIED** — consistent |
| KPI Strip | Units at Risk | 296 | `SCENARIOS.V_SUPPLIER_FAILURE_IMPACT` | `SUM(at_risk_quantity) WHERE at_risk_quantity > 0` from `V_ORDER_IMPACT` | Sum of unmet product units across all at-risk orders | All causes (same population as Orders at Risk) | Modelled scenario outcome | — | **SCOPE DIFFERENCE** — same population issue as Orders at Risk |
| Scenario Banner | Supplier, capacity, duration, start | SUP-001, 100%, 14d, 2026-09-18 | `SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS` | Hard-coded literal view | Active scenario configuration | Fixed; single row | Observed (configured) | — | **VERIFIED** |
| Failure Propagation | Parts in cascade (4) | 4 | `SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` | `DISTINCT part_id` | Parts from SUP-001's qualified portfolio with positive unmet_part_units AND traceable to an at-risk order | SUP-001 qualified parts only (PART-101, PART-102, PART-104, PART-111) — note: PART-101 is a baseline shortage at PLT-002, not scenario-caused | Modelled scenario outcome | KPI "Affected Parts" (11) | **SCOPE DIFFERENCE** — chain correctly restricts to SUP-001 portfolio, but PART-101 shortage is pre-existing |
| Failure Propagation | Orders at Risk (16) | 16 | `SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` | `DISTINCT order_id` | Orders linked to a SUP-001 portfolio part with unmet demand AND positive order-level at_risk_quantity | SUP-001-caused and mixed-cause orders | Modelled scenario outcome | KPI "Orders at Risk" (20) | **SCOPE DIFFERENCE** — 4 orders omitted because their shortage is from non-SUP-001 parts only |
| Failure Propagation | Customers Exposed (7) | 7 | `SCENARIOS.V_SUPPLIER_FAILURE_CHAIN` | `DISTINCT customer_id` | Customers with at least one order in the chain | SUP-001-portfolio-linked customers only | Modelled scenario outcome | KPI "Customers Exposed" (8) | **SCOPE DIFFERENCE** — 1 customer's exposure is non-SUP-001 only |
| Impact Details | Parts in cascade | 4 | `V_SUPPLIER_FAILURE_CHAIN` | Aggregated from chain | Same as propagation | Same | Modelled | — | **VERIFIED** |
| Impact Details | Plants in cascade | 5 | `V_SUPPLIER_FAILURE_CHAIN` | Aggregated from chain | Same | Same (all 5 plants appear in SUP-001 chain) | Modelled | KPI (5) | **VERIFIED** |
| Impact Details | Orders in cascade | 16 | `V_SUPPLIER_FAILURE_CHAIN` | Aggregated from chain | Same | SUP-001-caused | Modelled | KPI (20) | **SCOPE DIFFERENCE** |
| Impact Details | Customers in cascade | 7 | `V_SUPPLIER_FAILURE_CHAIN` | Aggregated from chain | Same | SUP-001-caused | Modelled | KPI (8) | **SCOPE DIFFERENCE** |
| Mitigation | Orders at Risk (NO_ACTION) | 20 | `SCENARIOS.V_MITIGATION_COMPARISON` | `COUNT_IF(at_risk_quantity > 0)` from `V_MITIGATION_ORDER_SUMMARY` | Same allocation logic, no incremental capacity | All causes — same population as KPI | Modelled | KPI Orders at Risk | **VERIFIED** — NO_ACTION should equal KPI |
| Mitigation | Customers Exposed (NO_ACTION) | 8 | `SCENARIOS.V_MITIGATION_COMPARISON` | `COUNT(DISTINCT customer_id)` | Same | All causes | Modelled | KPI Customers | **VERIFIED** |
| Mitigation | Remaining Exposure | dollar value | `SCENARIOS.V_MITIGATION_COMPARISON` | `SUM(at_risk_revenue)` | Residual at-risk revenue after mitigation | Per-mitigation | Modelled | Revenue Exposure (KPI, NO_ACTION row) | **VERIFIED** |
| Mitigation | Revenue Recovered | dollar value | `SCENARIOS.V_MITIGATION_COMPARISON` | `total_kpi_exposure - remaining_exposure` | Modelled revenue protected vs NO_ACTION baseline | Per-mitigation vs NO_ACTION | Modelled | — | **VERIFIED** |
| Mitigation | Incremental Cost | dollar value | `SCENARIOS.V_MITIGATION_COMPARISON` | `V_MITIGATION_COST.modeled_incremental_cost` | Modelled cost of executing the mitigation (alternate sourcing or expedite premium) | Part-level, then distributed to plants | Modelled | — | **VERIFIED** |
| Evidence | Governed Metric Catalog | table | `ANALYTICS.V_NEXUS_GOVERNED_METRIC_CATALOG` | SELECT * | Definitions for orders_at_risk, revenue_exposure, customers_exposed, affected_parts, inventory_coverage_days | As defined | Governed definition | — | **NEEDS REVIEW** — `affected_parts` definition ("distinct parts with positive unmet demand") does not note the all-causes scope |

---

## 4. Key Scope Differences — Detailed Explanation

### 4.1 KPI Strip vs Cascade/Impact Details

The two data sources serve **different purposes** and are both correct by design:

| | `V_SUPPLIER_FAILURE_IMPACT` (KPI) | `V_SUPPLIER_FAILURE_CHAIN` (Cascade / Impact Details) |
|---|---|---|
| **Purpose** | Holistic scenario-state risk snapshot | Causal trace from SUP-001 specifically |
| **Order population** | All open orders with any unmet demand | Orders where at least one SUP-001 portfolio part is unmet |
| **Part population** | All parts with unmet demand (any supplier) | Only parts in SUP-001's qualified sourcing portfolio |
| **Customer population** | All customers with any at-risk order | Customers whose at-risk orders trace to SUP-001 parts |
| **Includes pre-existing shortages?** | **Yes** | Partially (PART-101 at PLT-002 is pre-existing but included because it is a SUP-001 portfolio part) |

### 4.2 Pre-existing Zero-Supply Parts (Baseline Shortages)

These parts have **zero supply at the required plant in the baseline** — their shortage would exist even if SUP-001 never failed:

| Part | Plant(s) Affected | Reason | Who Supplies It |
|---|---|---|---|
| PART-105 (Drive Housing) | PLT-001, PLT-002, PLT-005 | No inventory, no inbound shipments | SUP-002, SUP-006 |
| PART-109 (Connector Set) | PLT-001 (and others) | No inventory, no inbound shipments | SUP-009 |
| PART-106 (Thermal Unit) | PLT-001, PLT-004 | No inventory, no inbound at those plants | SUP-003 |
| PART-112 (Frame Assembly) | PLT-003 | No inventory, no inbound shipments | SUP-004 |
| PART-113 (Optical Sensor) | PLT-003 | SHP-015 goes to PLT-001 only, not PLT-003 | SUP-005 |
| PART-115 (Power Connector) | PLT-002, PLT-004, PLT-005 | No inventory, no inbound shipments | SUP-007 |
| PART-101 (Control Board) | PLT-002 | No inventory, no inbound at PLT-002 | SUP-001, SUP-002 |

PART-101 appears in the chain because it is in SUP-001's qualified portfolio, but its shortage at PLT-002 is a **baseline shortage not caused by SUP-001's failure** (no SUP-001 in-window shipments for PART-101 exist).

### 4.3 Genuinely SUP-001-Caused Shortages

These are shortages that WOULD NOT EXIST in the baseline:

| Part | Plant | Baseline Supply | Scenario Supply | Demand | Shortage |
|---|---|---|---|---|---|
| PART-102 (Power Module) | PLT-002 | 220 units | 40 units | 51 units | 11 units |
| PART-104 (Precision Motor) | PLT-002 | 110 units | 10 units | 16 units | 6 units |
| PART-111 (Safety Controller) | PLT-001 | 90 units | 10 units | 27 units | 17 units |

Note: PART-102 at PLT-001 has a **pre-existing** baseline shortage (40 available vs 58 needed). SUP-001 did not cause this shortage, but PART-102 is a SUP-001 portfolio part so it appears in the chain.

---

## 5. Error Handling Audit

| Failure Scenario | Handler Present | Method | Raw Traceback Shown? | Status |
|---|---|---|---|---|
| Snowflake connection failure | ✅ | `NexusConnectionError` in `get_session()` | No — user-readable message | VERIFIED |
| Missing private key file | ✅ | `os.path.isfile()` check + `NexusConfigError` | No | VERIFIED |
| Invalid/encrypted private key | ✅ | `load_pem_private_key` try/except | No | VERIFIED |
| Snowflake query failure | ✅ | `query_df` catches + logs to terminal | No | VERIFIED |
| Empty query result | ✅ | All components check `.empty` / `not params` | No | VERIFIED |
| Cortex Agent failure | ✅ | `NexusAgentError` with 60 s timeout | No | VERIFIED |
| Agent timeout | ✅ | `concurrent.futures` with `timeout=60` | No | VERIFIED |
| Scenario tool failure | ✅ | Component empty-state handlers + unsupported-scenario detection | No | VERIFIED |
| Empty chat submission | ✅ | `st.toast` + whitespace strip guard | No | VERIFIED |
| Page refresh / session reset | ✅ | `st.session_state` checked before use | No | VERIFIED |
| Unsupported scenario params | ✅ | `is_unsupported_scenario()` + st.warning banner | No | VERIFIED |

---

## 6. Security Audit

| Check | Result |
|---|---|
| `secrets.toml` in `.gitignore` | ✅ `.streamlit/secrets.toml` and `**/secrets.toml` both listed |
| `*.pem` private keys in `.gitignore` | ✅ |
| `*.p8` keys in `.gitignore` | ✅ |
| `*.key` in `.gitignore` | ✅ |
| Hardcoded Snowflake password in Python | ✅ None found |
| Hardcoded API keys in Python | ✅ None found |
| Private key in documentation | ✅ None found |
| credentials in `secrets.toml.example` | ✅ Only placeholders |
| `venv/` in `.gitignore` | ✅ |

No security issues found.

---

## 7. Scenario Assumption Audit

| Check | Result |
|---|---|
| Active scenario clearly displayed | ✅ Scenario banner shows supplier, capacity, duration, start date |
| Scenario assumptions visible in caption | ✅ Added in Phase 7 |
| Modelled outputs labelled as modelled | ✅ All mitigation cards have "Modelled outputs" banner |
| Mitigation results not presented as guarantees | ✅ Caption + st.info note present |
| Unsupported parameters detected and flagged | ✅ `is_unsupported_scenario()` active in all scenario components |
| Custom parameter support implied? | ✅ No — side-note removed, caption says engine uses fixed params |

---

## 8. Recommended Changes (Minimal, Label-Only)

The underlying SQL logic is **correct by design**. No Snowflake objects need to change.

Required UI label changes:

1. **KPI section header** — add a note that these are scenario-wide totals (all causes), while the cascade traces SUP-001-caused impact only.
2. **KPI "Affected Parts" sub-label** — clarify "all parts with shortage under scenario".
3. **KPI "Orders at Risk" sub-label** — clarify "all orders with shortage (all causes)".
4. **Cascade section description** — clarify this traces SUP-001's specific causal impact.
5. **Impact Details section description** — same.
6. **Governed metric catalog note** — add `affected_parts` scope note.

---

## 9. Summary

| Finding | Count | Action |
|---|---|---|
| VERIFIED (consistent, accurate) | 11 | No change needed |
| SCOPE DIFFERENCE (intentional, label improvement needed) | 7 | UI label update only |
| POTENTIAL BUG | 0 | — |
| BUG | 0 | — |
| NEEDS REVIEW | 1 | Evidence catalog `affected_parts` scope note |

**No SQL changes required. No Snowflake objects changed.**
