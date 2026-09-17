# NEXUS Evaluation Plan

## Evaluation Dimensions

The prototype should be evaluated against three hackathon-aligned dimensions:

- Real-world relevance
- Technical execution
- Solution completeness

## Golden Question Tests

The following questions form the core regression set:

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

## Adversarial Tests

- Unknown entity
- Ambiguous entity
- Unsupported metric
- Missing duration
- Conflicting scenario parameters
- No alternate supplier
- Insufficient inventory
- Duplicate shipment data
- Scenario outside data horizon
- Zero impacted orders
- Extreme scenario values
- Prompt injection in retrieved documents
- SQL generation failure
- No matching records

## Correctness Principles

- Answers must be grounded in Snowflake data.
- Governed metric definitions must be used consistently.
- Scenario values must be clearly labeled as modeled.
- Unknown values must not be fabricated.
- Evidence must support material business answers.
