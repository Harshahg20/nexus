# NEXUS Architecture

## Overview

NEXUS is a Snowflake-native AI supply-chain resilience application.

```text
User / Executive
       ↓
NEXUS UI (Streamlit)
       ↓
Cortex Agent
   ├── Governed semantic views / metrics
   ├── Cortex Search (optional)
   └── Scenario Engine
             ↓
          Snowflake
```

## Data Domains

```text
RAW
├── SUPPLIERS
├── PARTS
├── PLANTS
├── PRODUCTS
├── INVENTORY
├── PORTS
├── SHIPMENTS
├── ORDERS
└── CUSTOMERS
```

Scenario and analytics layers:

```text
SCENARIOS
├── SCENARIO_DEFINITIONS
├── SCENARIO_IMPACTS
└── MITIGATION_OPTIONS

ANALYTICS
├── SUPPLY_CHAIN_RISK
├── ORDER_EXPOSURE
└── SUPPLIER_RISK
```

## Semantic Layer

The semantic layer provides governed definitions for entities, relationships, dimensions, measures, and business metrics. Natural-language questions should resolve to these definitions rather than inventing metric logic.

Core ontology:

```text
Supplier → Part → Plant → Inventory → Shipment → Order → Customer
```

Supporting relationships include supplier-to-shipment, shipment-to-port, shipment-to-plant, part-to-plant, plant-to-product, and product-to-order.

## Scenario Flow

```text
Scenario Input
     ↓
Entity Resolution
     ↓
Dependency Traversal
     ↓
Supply / Inventory Recalculation
     ↓
Order Exposure
     ↓
Customer / Revenue Exposure
     ↓
Mitigation Modeling
     ↓
Evidence
```

## Governance

The application must distinguish:

- observed data from modeled results
- governed metrics from ad-hoc calculations
- known entities from unknown entities
- supported questions from unsupported questions

Unknown or insufficient data should produce an explicit safe response instead of fabricated results.
