# NEXUS Governed Metrics

All metrics below must have one canonical definition and should be exposed through the semantic layer.

## Orders at Risk

Orders for which available supply cannot satisfy required quantity within the required fulfillment window under the selected baseline or scenario.

## Revenue Exposure

Sum of `order_value` for orders classified as at risk.

## Critical Part Exposure

Critical parts for which available supply falls below required demand.

## Customer Exposure

Count of customers with one or more affected orders.

## Supplier Concentration

Percentage of critical-part demand dependent on a specified supplier.

## Single-Source Ratio

```text
critical parts supplied by exactly one qualified supplier
---------------------------------------------------------
total critical parts
```

## Inventory Coverage Days

```text
available inventory / average daily consumption
```

## SLA Exposure

Count and value of at-risk orders grouped by SLA tier.

## Recovery Time

Modeled estimate of time needed to restore required supply under a scenario or mitigation. It must be labeled as modeled and must not be presented as an observed operational measurement.

## Metric Governance Requirements

- Use consistent filters and joins.
- Avoid duplicate shipment contribution.
- Preserve entity grain when aggregating.
- Clearly distinguish baseline from scenario values.
- Return an insufficient-data response when required inputs are unavailable.
- Expose metric definitions in the evidence view.
