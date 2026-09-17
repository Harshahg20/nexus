# NEXUS Disruption Scenarios

## 1. Supplier Failure

Example:

`SUP-001` unavailable for 14 days.

Inputs:
- supplier
- capacity reduction percentage
- duration
- start date

Impact propagation:

```text
Supplier → Parts → Inventory → Plants → Products → Orders → Customers
```

## 2. Port Disruption

Example:

`PORT-TYO` unavailable for 7 days.

Impact propagation:

```text
Port → Shipment Delay → Part Arrival → Inventory → Plant → Orders → Customers
```

## 3. Freight Shock

Example:

Freight cost increases by 30%.

The scenario should model incremental transportation cost and compare alternatives that protect customer demand.

## Mitigations

- Alternate Supplier
- Expedite Shipment
- Reallocate Inventory
- No Action

## Scenario Rules

1. Scenario inputs must be explicit.
2. Unknown entities must be rejected.
3. Missing required parameters must trigger clarification.
4. Results must distinguish modeled impact from observed baseline data.
5. Mitigation outputs must show trade-offs rather than an opaque recommendation.
6. Scenario calculations should preserve the ontology and metric definitions used by baseline analytics.
7. Extreme inputs should be bounded and surfaced to the user.

## Scenario Output

Every scenario should provide:

- impacted entities
- dependency path
- orders at risk
- revenue exposure
- customer exposure
- critical parts exposed
- inventory impact
- mitigation comparison
- evidence / calculation context
