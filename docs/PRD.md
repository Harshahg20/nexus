# NEXUS — Product Requirements Document

**Product:** NEXUS — AI Supply Chain Resilience Graph  
**Team:** Cortex Forge  
**Tagline:** Forge Intelligence. Ship Impact.  
**Product tagline:** See the chain. Find the break. Act before the impact.  
**Hackathon:** Snowflake CoCo CLI Hackathon — GCC Edition 2026  
**Theme:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Product Overview

NEXUS is an AI-powered supply-chain resilience and governed conversational analytics application built on Snowflake. It creates a connected business ontology across suppliers, parts, plants, inventory, shipments, orders, products, ports, and customers.

The core product experience is:

**Detect → Ask → Trace → Simulate → Decide → Evidence**

NEXUS is designed around a key operational question:

> What breaks next if supplier SUP-001 becomes unavailable for 14 days?

Instead of returning an isolated KPI, NEXUS traces the dependency chain from supplier to parts, inventory, plants, products, orders, and customers, then models disruption impact and compares mitigation options.

## 2. Problem Statement

Enterprise supply-chain information is distributed across ERP, logistics, supplier, inventory, shipment, and customer systems. Different teams often use different definitions for the same business concepts and metrics.

This creates three problems:

1. Decision-makers cannot easily understand cross-system dependencies.
2. Natural-language analytics can produce inconsistent or poorly governed answers.
3. Teams can identify a disruption without quickly understanding downstream impact and response trade-offs.

NEXUS addresses these problems through a governed ontology, semantic metrics, dependency tracing, scenario simulation, and evidence-backed answers.

## 3. Hackathon Alignment

NEXUS directly addresses the theme requirement to establish an industry ontology and business entity/relationship model such as:

**Supplier → Part → Plant → Shipment → Order → Customer**

The prototype demonstrates governed semantic views, shared business definitions, natural-language analytics, and actionable supply-chain scenario analysis on Snowflake.

## 4. Target Users

### Supply-chain executives
Need a fast view of exposure, affected customers, revenue risk, and response options.

### Supply-chain analysts
Need governed answers to dependency, inventory, supplier, shipment, and order questions.

### Operations planners
Need to test disruption scenarios and compare mitigation trade-offs.

### Data / governance teams
Need consistent entity definitions, metric definitions, evidence, and auditable analytical behavior.

## 5. Product Goals

- Build a connected supply-chain ontology.
- Provide governed natural-language analytics.
- Trace upstream and downstream dependencies.
- Simulate realistic supply-chain disruptions.
- Quantify modeled operational and financial exposure.
- Compare mitigation options transparently.
- Show evidence for AI-generated answers.
- Demonstrate robust behavior for ambiguous, unsupported, and missing-data questions.

## 6. Non-Goals

The MVP will not depend on:

- Live external news feeds.
- Real-time streaming ingestion.
- Advanced ML forecasting.
- Full mathematical optimization.
- Autonomous ERP actions.
- Production ERP integration.
- Real-world customer or supplier data.

Synthetic data will be intentionally designed to represent meaningful supply-chain patterns.

## 7. Core Product Experience

### 7.1 Executive Command Center

The dashboard provides:

- Orders at Risk
- Revenue Exposure
- Critical Part Exposure
- Customers Exposed
- Supplier Concentration
- Single-Source Ratio
- Inventory Coverage Days
- SLA Exposure

A risk card can show an exposure such as:

```text
CRITICAL EXPOSURE
Supplier SUP-001
Critical Parts: 4
Plants Exposed: 2
Orders at Risk: 17
Revenue Exposure: $2.4M
Customers Exposed: 3
```

### 7.2 NEXUS Chat

Users ask business questions in natural language. The agent resolves entities, maps questions to governed concepts and metrics, executes approved analytics, and explains the result.

Example:

> Which customers depend on SUP-001?

> What breaks next if SUP-001 becomes unavailable for 14 days?

> Compare alternate supplier versus expedited freight.

### 7.3 Dependency Graph

The UI visualizes relationships across the ontology and highlights impacted nodes for a selected disruption.

### 7.4 Scenario Simulator

Users configure a disruption, inspect propagated impact, and compare mitigation options.

## 8. Supply Chain Ontology

Core relationship:

```text
Supplier → Part → Plant → Inventory → Shipment → Order → Customer
```

Additional relationships:

```text
Supplier → Shipment
Shipment → Part
Shipment → Port
Shipment → Plant
Part → Plant
Plant → Inventory
Plant → Product
Product → Order
Order → Customer
```

The ontology is the foundation for both governed analytics and impact propagation.

## 9. Entity Model

### Supplier
- supplier_id
- supplier_name
- region
- risk_tier
- capacity_units
- status

### Part
- part_id
- part_name
- category
- criticality
- unit_cost

### Plant
- plant_id
- plant_name
- region
- capacity_units
- status

### Inventory
- inventory_id
- plant_id
- part_id
- on_hand_units
- safety_stock_units
- daily_consumption

### Port
- port_id
- port_name
- region
- congestion_level
- status

### Shipment
- shipment_id
- supplier_id
- part_id
- plant_id
- port_id
- quantity
- ship_date
- expected_arrival
- status

### Product
- product_id
- product_name
- category
- margin

### Order
- order_id
- customer_id
- product_id
- plant_id
- quantity
- order_value
- order_date
- due_date
- priority
- sla_tier
- status

### Customer
- customer_id
- customer_name
- segment
- region
- sla_tier

## 10. Governed Business Metrics

### Orders at Risk
Orders for which available supply cannot satisfy required quantity within the required fulfillment window under the current or simulated scenario.

### Revenue Exposure
Sum of `order_value` for orders classified as at risk.

### Critical Part Exposure
Critical parts whose available supply falls below required demand.

### Customer Exposure
Number of customers with one or more affected orders.

### Supplier Concentration
Percentage of critical-part demand dependent on a particular supplier.

### Single-Source Ratio
Critical parts supplied by exactly one qualified supplier divided by total critical parts.

### Inventory Coverage Days
Available inventory divided by average daily consumption.

### SLA Exposure
Number and value of at-risk orders grouped by SLA tier.

### Recovery Time
Modeled estimate of time required to restore required supply under a scenario or mitigation. This must always be labeled as **modeled**, not observed.

## 11. Scenario Engine

### Scenario 1 — Supplier Failure

Example:

> SUP-001 becomes unavailable for 14 days.

Inputs:
- supplier
- capacity reduction percentage
- duration
- start date

Propagation:

```text
Supplier
  ↓
Parts
  ↓
Inventory
  ↓
Plants
  ↓
Products
  ↓
Orders
  ↓
Customers
```

### Scenario 2 — Port Disruption

Example:

> PORT-TYO becomes unavailable for 7 days.

Propagation:

```text
Port
  ↓
Shipment delay
  ↓
Part arrival
  ↓
Inventory
  ↓
Plant
  ↓
Orders
  ↓
Customers
```

### Scenario 3 — Freight Shock

Example:

> Freight cost increases by 30%.

The engine compares transportation alternatives using incremental cost, orders protected, revenue protected, and modeled recovery impact.

## 12. Mitigation Engine

Supported mitigation options:

1. Alternate Supplier
2. Expedite Shipment
3. Reallocate Inventory
4. No Action

NEXUS presents trade-offs rather than claiming a universally optimal action.

Example comparison dimensions:

| Option | Incremental Cost | Orders Protected | Revenue Protected | Remaining Exposure |
|---|---:|---:|---:|---:|
| No Action | $0 | — | — | — |
| Alternate Supplier | modeled | modeled | modeled | modeled |
| Expedite Shipment | modeled | modeled | modeled | modeled |
| Reallocate Inventory | modeled | modeled | modeled | modeled |

## 13. Explainability and Evidence

Every material answer should be traceable through:

```text
Question
  ↓
Ontology
  ↓
Metric / semantic definition
  ↓
Verified query
  ↓
Source data
  ↓
Calculation
  ↓
Answer
```

The UI should provide an evidence drawer showing how the result was derived.

## 14. AI Agent Requirements

The agent must:

- Ground answers in Snowflake data and governed definitions.
- Resolve business entities before analysis.
- Ask for clarification when required parameters are ambiguous.
- Reject unknown entities rather than inventing them.
- Reject unsupported metrics.
- Never fabricate data.
- Return an explicit insufficient-data response when the available data cannot support a calculation.
- Treat prompt-injection text found in retrieved documents as data, not as instructions.
- Distinguish observed values from modeled scenario outputs.

Example insufficient-data response:

> I don't have enough data to calculate this.

## 15. Adversarial and Edge Cases

The prototype must test:

- Unknown supplier, customer, or part.
- Ambiguous supplier name.
- Unsupported metric.
- Missing scenario duration.
- Conflicting scenario parameters.
- No alternate supplier.
- Insufficient inventory.
- Safety stock covering a temporary shortage.
- Multiple plants able to fulfill demand.
- Shared parts across products.
- Duplicate shipment records.
- Delayed shipment without an actual shortage.
- Scenario beyond the available data horizon.
- Zero impacted orders.
- Extreme disruption values.
- Prompt injection in retrieved documents.
- SQL generation failure.
- No matching data.
- Model or scenario boundary conditions.

## 16. Synthetic Data Requirements

The dataset must be intentionally designed rather than purely random. It must contain:

- Single-source suppliers.
- Multi-source suppliers.
- Critical parts.
- Safety stock.
- Inventory shortages.
- Delayed shipments.
- Multiple plants.
- Multiple customers.
- High-value orders.
- SLA tiers.
- Shared components.
- Alternate suppliers.
- Port dependencies.

Target MVP scale:

- 15–20 suppliers.
- 50–100 parts.
- 5–8 plants.
- Representative shipments and inventory records.
- Multiple products and customers.
- Enough orders to create meaningful exposure scenarios.

Synthetic data should include deliberate golden-path records such as SUP-001, PART-104, PORT-TYO, and CUST-003 so the demo is deterministic.

## 17. Snowflake Architecture

```text
NEXUS_DB
├── RAW
│   ├── SUPPLIERS
│   ├── PARTS
│   ├── PLANTS
│   ├── PRODUCTS
│   ├── INVENTORY
│   ├── PORTS
│   ├── SHIPMENTS
│   ├── ORDERS
│   └── CUSTOMERS
├── SEMANTIC
│   └── SUPPLY_CHAIN_SEMANTIC_VIEW
├── SCENARIOS
│   ├── SCENARIO_DEFINITIONS
│   ├── SCENARIO_IMPACTS
│   └── MITIGATION_OPTIONS
└── ANALYTICS
    ├── SUPPLY_CHAIN_RISK
    ├── ORDER_EXPOSURE
    └── SUPPLIER_RISK
```

Application architecture:

```text
User / Executive
       ↓
NEXUS UI (Streamlit)
       ↓
Cortex Agent
   ├── Governed semantic views / metrics
   ├── Cortex Search (optional documents)
   └── Scenario Engine
             ↓
          Snowflake
```

## 18. Functional Requirements

### FR-01 — Ontology
The system shall represent the defined supply-chain entities and relationships.

### FR-02 — Governed Metrics
The system shall expose business metrics through a consistent semantic definition.

### FR-03 — Natural Language Analytics
The system shall translate supported business questions into governed analytics.

### FR-04 — Entity Resolution
The system shall resolve known suppliers, parts, plants, customers, and other business entities.

### FR-05 — Dependency Tracing
The system shall identify downstream entities affected by a selected supplier, part, plant, shipment, or port.

### FR-06 — Scenario Simulation
The system shall model supplier, port, and freight scenarios.

### FR-07 — Mitigation Comparison
The system shall calculate and display comparable modeled outcomes for supported mitigation options.

### FR-08 — Evidence
The system shall expose metric definitions, queries, source entities, and calculation context for material answers.

### FR-09 — Edge-Case Handling
The system shall fail safely for unsupported, ambiguous, missing, or invalid requests.

### FR-10 — Executive View
The system shall provide an executive summary of current and modeled exposure.

## 19. Golden Questions

1. Which suppliers have the highest revenue exposure?
2. Which critical parts are single-source?
3. Which customers depend on SUP-001?
4. Which plants depend on PART-104?
5. Which shipments are delayed?
6. Which orders are at risk?
7. What is the current revenue exposure?
8. What breaks if SUP-001 fails?
9. What happens if SUP-001 loses 60% capacity for 14 days?
10. What happens if PORT-TYO is unavailable for 7 days?
11. Which customers have the highest SLA exposure?
12. Which parts have less than 7 days of inventory coverage?
13. Why is CUST-003 affected?
14. Which products depend on PART-104?
15. Which suppliers provide PART-104?
16. What happens if PART-104 becomes unavailable?
17. Compare alternate supplier versus expedited freight.
18. How much revenue can each mitigation protect?
19. Which orders remain exposed after mitigation?
20. Show the dependency chain for CUST-003.

## 20. Primary Demo Scenario

The primary end-to-end demonstration is:

> **What breaks next if supplier SUP-001 becomes unavailable for 14 days?**

NEXUS should return:

- affected parts
- exposed plants
- inventory depletion / coverage
- affected products
- at-risk orders
- revenue exposure
- affected customers
- dependency path
- evidence
- mitigation comparison

The demo should visibly move through:

**Detect → Ask → Trace → Simulate → Decide → Evidence**

## 21. Success Criteria

The MVP is successful when a user can:

1. Ask a supported supply-chain question in natural language.
2. Receive an answer grounded in Snowflake data.
3. Understand which ontology entities were involved.
4. Trace a disruption through downstream dependencies.
5. Simulate at least three disruption types.
6. Compare mitigation options.
7. Inspect evidence behind material results.
8. See safe handling of key adversarial and edge cases.

## 22. Prototype Scope

### P0 — Required

- Snowflake data model.
- Synthetic dataset.
- Supply-chain ontology.
- Semantic layer.
- Governed metrics.
- Natural-language analytics.
- Dependency tracing.
- Supplier-failure scenario.
- Port-disruption scenario.
- Freight-shock scenario.
- Impact propagation.
- Mitigation comparison.
- Evidence.
- Executive dashboard.
- Chat.
- Basic dependency graph.
- Edge-case handling.

### P1 — If time permits

- Cortex Search for disruption documents.
- Scenario history.
- Audit log.
- Richer graph visualization.
- Additional metrics.
- More sophisticated mitigation modeling.

### P2 — Do not delay the MVP

- Live external news.
- Real-time streaming.
- ML forecasting.
- Advanced optimization.
- Autonomous actions.
- ERP integrations.

## 23. Repository Structure

```text
nexus/
├── README.md
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── ONTOLOGY.md
│   ├── METRICS.md
│   ├── SCENARIOS.md
│   ├── EVALUATION.md
│   └── DEMO_SCRIPT.md
├── data/
├── snowflake/
├── semantic/
├── agent/
├── app/
└── tests/
```

## 24. Development Principle

Build the smallest complete vertical slice before polishing the dashboard:

```text
Snowflake
 ↓
Supplier
 ↓
Part
 ↓
Plant
 ↓
Inventory
 ↓
Order
 ↓
Customer
 ↓
Semantic definition
 ↓
AI question
 ↓
Correct answer
```

Then add scenario propagation and mitigation comparison.

## 25. Development Constraint

The first successful end-to-end scenario is the MVP freeze point. After the core demo works, prioritize correctness, explainability, adversarial testing, performance, UX polish, and submission readiness over adding new features.

## 26. Frozen Product Definition

> **NEXUS is an AI supply-chain resilience graph that turns governed enterprise data into an interactive dependency map, allowing decision-makers to ask what breaks next, simulate disruption scenarios, compare mitigation trade-offs, and inspect the evidence behind every material answer.**
