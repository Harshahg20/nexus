# NEXUS Demo Script

## Demo Story

NEXUS is introduced as a supply-chain resilience graph that connects governed enterprise data to operational decisions.

## Step 1 — Detect

Open the Executive Command Center and show current supply-chain exposure:

- Orders at Risk
- Revenue Exposure
- Critical Part Exposure
- Customers Exposed
- Supplier Concentration

## Step 2 — Ask

Ask:

> What breaks next if SUP-001 becomes unavailable for 14 days?

## Step 3 — Trace

Show the dependency chain:

```text
SUP-001
  ↓
Critical Parts
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

Highlight affected nodes and summarize the modeled exposure.

## Step 4 — Simulate

Open the scenario simulator and run the supplier-failure scenario.

Show:

- impacted parts
- exposed plants
- inventory depletion
- at-risk orders
- revenue exposure
- affected customers

## Step 5 — Decide

Compare:

- No Action
- Alternate Supplier
- Expedite Shipment
- Reallocate Inventory

Show incremental cost, orders protected, revenue protected, and remaining exposure.

Do not present a mitigation as universally optimal; show the trade-offs.

## Step 6 — Evidence

Open the evidence drawer and show:

```text
Question
  ↓
Ontology
  ↓
Metric Definition
  ↓
Verified Query
  ↓
Source Data
  ↓
Calculation
  ↓
Answer
```

## Closing Message

> NEXUS doesn't just answer what happened. It traces what breaks next, lets you test what to do about it, and shows the evidence behind the answer.
