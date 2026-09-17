# NEXUS Agent Layer

This directory defines the governed behavior and tool contract for the NEXUS conversational analytics layer.

## Integration sequence

1. Deploy the Snowflake schema and seed data.
2. Deploy scenario and validation SQL files in numeric order.
3. Validate `ANALYTICS.V_SCENARIO_VALIDATION` before enabling conversational access.
4. Register governed views/query templates as agent capabilities.
5. Apply `NEXUS_AGENT_INSTRUCTIONS.md` as the agent's system/developer instruction set.
6. Restrict database access to the approved NEXUS schema objects.
7. Test the golden questions in `snowflake/005_golden_queries.sql` plus the scenario questions in `docs/DEMO_SCRIPT.md`.
8. Capture the generated SQL and evidence source for every demo answer.

## Important

The repository currently contains the logical contract and SQL surfaces. Exact Cortex Agent/semantic-view deployment syntax is account/version dependent and should be configured in the target Snowflake account using the currently supported Cortex tooling. Do not treat the repository markdown as proof that the Snowflake agent is already deployed.
