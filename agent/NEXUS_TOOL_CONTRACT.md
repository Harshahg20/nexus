# NEXUS Agent Tool Contract

The agent should expose a small set of governed capabilities rather than unrestricted database access.

## 1. resolve_entity
Purpose: map a business name to a canonical NEXUS ID.

Inputs:
- entity_type: SUPPLIER | PART | PLANT | PORT | PRODUCT | ORDER | CUSTOMER
- name_or_id: user-provided identifier

Rules:
- Return exact match, candidate matches, or NOT_FOUND.
- Never silently select an ambiguous entity.

## 2. run_governed_metric
Purpose: answer current-state analytics using governed definitions.

Inputs:
- metric_name
- filters
- group_by
- date_scope

Rules:
- Metric must exist in the governed metric catalog.
- Generated SQL must reference an approved view or query template.
- Return result plus source view and metric definition.

## 3. run_scenario
Purpose: calculate modeled disruption impact.

Inputs:
- scenario_type: SUPPLIER_FAILURE | PORT_DISRUPTION | FREIGHT_SHOCK
- target_entity_id
- disruption_pct
- duration_days
- start_date

Rules:
- Validate entity and numeric bounds.
- Return assumptions before results.
- Return impact and evidence identifiers.
- Do not mutate source data.

## 4. trace_dependency
Purpose: explain why an entity/order/customer is exposed.

Inputs:
- source_entity_type
- source_entity_id
- target_entity_type (optional)
- scenario_run_id (optional)

Rules:
- Use ontology relationships.
- Return only trace rows supported by source data.

## 5. compare_mitigations
Purpose: compare modeled mitigation alternatives.

Inputs:
- scenario_run_id
- mitigation options

Rules:
- Return incremental cost, protected orders/units/revenue, residual exposure and assumptions.
- Never output a universal recommendation or hidden ranking.

## Standard response object
The application layer should normalize tool results into:

```json
{
  "answer": "...",
  "scenario": {
    "type": "...",
    "target": "...",
    "duration_days": 0,
    "disruption_pct": 0,
    "start_date": "..."
  },
  "impact": {},
  "dependency_chain": [],
  "mitigations": [],
  "evidence": [
    {
      "source_view": "...",
      "metric_or_calculation": "...",
      "source_entity_ids": []
    }
  ],
  "warnings": []
}
```
