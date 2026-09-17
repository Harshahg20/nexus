# NEXUS Supply Chain Ontology

## Core Business Entities

| Entity | Purpose | Key Identifier |
|---|---|---|
| Supplier | Provides parts and shipments | supplier_id |
| Part | Component consumed by plants | part_id |
| Plant | Manufacturing / fulfillment location | plant_id |
| Inventory | Part availability at a plant | inventory_id |
| Port | Logistics gateway | port_id |
| Shipment | Movement of parts | shipment_id |
| Product | Finished product | product_id |
| Order | Customer demand | order_id |
| Customer | End customer / account | customer_id |

## Relationships

```text
Supplier
   │
   ├──── provides ────> Part
   │
   └──── sends ───────> Shipment
                         │
                         ├── carries ──> Part
                         ├── passes ────> Port
                         └── delivers ──> Plant

Part ───── consumed by ─────> Plant
Plant ──── holds ────────────> Inventory
Plant ──── produces ─────────> Product
Product ── fulfills ────────> Order
Order ──── belongs to ──────> Customer
```

## Dependency Path

The canonical downstream impact path is:

```text
Supplier → Part → Inventory → Plant → Product → Order → Customer
```

A logistics disruption can enter through:

```text
Port → Shipment → Part → Inventory → Plant → Product → Order → Customer
```

## Ontology Rules

1. Every entity must have a stable business identifier.
2. Relationships must be explicit enough to support dependency traversal.
3. A part can be shared across multiple products.
4. A part can have one or multiple qualified suppliers.
5. A plant can hold inventory for multiple parts.
6. An order is associated with a customer, product, and fulfillment plant.
7. Scenario calculations must preserve the same entity relationships as baseline analytics.

## Demo Entities

The synthetic dataset should deliberately include deterministic entities used in the demo:

- `SUP-001` — disruption target supplier
- `PART-104` — critical shared component
- `PORT-TYO` — port disruption target
- `CUST-003` — customer used for dependency explanation
