-- =============================================================================
-- 014_nexus_agent.sql
-- NEXUS Supply Chain Resilience Agent — MVP deployment
--
-- Creates:
--   NEXUS_DB.TOOLS schema
--   4 parameterless read-only SQL UDFs (active scenario tools)
--   1 Cortex Agent with Cortex Analyst + 4 generic tools
--
-- All scenario tools execute the currently configured deterministic scenario
-- with fixed MVP parameters. They do not accept arbitrary parameters.
--   Supplier failure: SUP-001, 100% capacity reduction, 14 days
--   Port disruption:  PORT-TYO, 100% disruption, 7 days
--   Freight shock:    30% freight increase, 14 days
--
-- Prerequisite scripts: 001 through 013
-- =============================================================================

USE DATABASE NEXUS_DB;

-- ---------------------------------------------------------------------------
-- 1. Schema
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS NEXUS_DB.TOOLS;

-- ---------------------------------------------------------------------------
-- 2. RUN_ACTIVE_SUPPLIER_FAILURE
--    Read-only. Returns active supplier failure impact + dependency chain.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION NEXUS_DB.TOOLS.RUN_ACTIVE_SUPPLIER_FAILURE()
RETURNS OBJECT
LANGUAGE SQL
AS
$$
  SELECT OBJECT_CONSTRUCT(
    'scenario_type', 'SUPPLIER_FAILURE',
    'parameters', (
      SELECT OBJECT_CONSTRUCT(
        'supplier_id', failed_supplier_id,
        'capacity_reduction_pct', capacity_reduction_pct,
        'duration_days', duration_days,
        'start_date', start_date
      ) FROM NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS
    ),
    'impact', (
      SELECT OBJECT_CONSTRUCT(
        'orders_at_risk', orders_at_risk,
        'customers_exposed', customers_exposed,
        'affected_plants', affected_plants,
        'affected_parts', affected_parts,
        'revenue_exposure', revenue_exposure,
        'units_at_risk', units_at_risk
      ) FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT
    ),
    'dependency_chain', (
      SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
        'supplier_name', supplier_name,
        'part_id', part_id,
        'part_name', part_name,
        'criticality', criticality,
        'product_name', product_name,
        'order_id', order_id,
        'customer_name', customer_name,
        'plant_name', plant_name,
        'at_risk_quantity', at_risk_quantity,
        'at_risk_revenue', at_risk_revenue,
        'sla_tier', sla_tier,
        'priority', priority
      )) FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_CHAIN
    ),
    'note', 'Deterministic modeled outcome using explicit part capacity and priority-based order allocation; not an operational execution guarantee.'
  )
$$;

-- ---------------------------------------------------------------------------
-- 3. COMPARE_ACTIVE_MITIGATIONS
--    Read-only. Returns all mitigation strategies for the active scenario.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION NEXUS_DB.TOOLS.COMPARE_ACTIVE_MITIGATIONS()
RETURNS OBJECT
LANGUAGE SQL
AS
$$
  SELECT OBJECT_CONSTRUCT(
    'scenario_type', 'MITIGATION_COMPARISON',
    'parameters', (
      SELECT OBJECT_CONSTRUCT(
        'supplier_id', failed_supplier_id,
        'capacity_reduction_pct', capacity_reduction_pct,
        'duration_days', duration_days,
        'start_date', start_date
      ) FROM NEXUS_DB.SCENARIOS.V_ACTIVE_SUPPLIER_FAILURE_PARAMETERS
    ),
    'strategies', (
      SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
        'mitigation_type', mitigation_type,
        'orders_at_risk', orders_at_risk,
        'customers_exposed', customers_exposed,
        'units_at_risk', units_at_risk,
        'remaining_revenue_exposure', remaining_revenue_exposure,
        'modeled_revenue_protected', modeled_revenue_protected,
        'modeled_incremental_cost', modeled_incremental_cost,
        'note', calculation_note
      )) FROM NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON
    )
  )
$$;

-- ---------------------------------------------------------------------------
-- 4. RUN_ACTIVE_PORT_DISRUPTION
--    Read-only. Returns active port disruption impact + disruption chain.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION NEXUS_DB.TOOLS.RUN_ACTIVE_PORT_DISRUPTION()
RETURNS OBJECT
LANGUAGE SQL
AS
$$
  SELECT OBJECT_CONSTRUCT(
    'scenario_type', 'PORT_DISRUPTION',
    'parameters', (
      SELECT OBJECT_CONSTRUCT(
        'port_id', disrupted_port_id,
        'disruption_pct', disruption_pct,
        'duration_days', duration_days,
        'start_date', start_date
      ) FROM NEXUS_DB.SCENARIOS.V_ACTIVE_PORT_DISRUPTION_PARAMETERS
    ),
    'impact', (
      SELECT OBJECT_CONSTRUCT(
        'orders_at_risk', orders_at_risk,
        'customers_exposed', customers_exposed,
        'affected_plants', affected_plants,
        'revenue_exposure', revenue_exposure,
        'units_at_risk', units_at_risk
      ) FROM NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_IMPACT
    ),
    'disruption_chain', (
      SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
        'port_name', port_name,
        'shipment_id', shipment_id,
        'supplier_name', supplier_name,
        'part_id', part_id,
        'part_name', part_name,
        'plant_name', plant_name,
        'shipment_quantity', shipment_quantity,
        'expected_arrival', expected_arrival,
        'order_id', order_id,
        'customer_name', customer_name,
        'product_name', product_name,
        'at_risk_quantity', at_risk_quantity,
        'at_risk_revenue', at_risk_revenue,
        'sla_tier', sla_tier
      )) FROM NEXUS_DB.SCENARIOS.V_PORT_DISRUPTION_CHAIN
    ),
    'note', 'Deterministic modeled outcome using explicit part capacity and priority-based order allocation; not an operational execution guarantee.'
  )
$$;

-- ---------------------------------------------------------------------------
-- 5. GET_ACTIVE_FREIGHT_SHOCK
--    Read-only. Returns active freight shock summary + sourcing options.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION NEXUS_DB.TOOLS.GET_ACTIVE_FREIGHT_SHOCK()
RETURNS OBJECT
LANGUAGE SQL
AS
$$
  SELECT OBJECT_CONSTRUCT(
    'scenario_type', 'FREIGHT_SHOCK',
    'parameters', (
      SELECT OBJECT_CONSTRUCT(
        'freight_increase_pct', freight_increase_pct,
        'duration_days', duration_days,
        'start_date', start_date
      ) FROM NEXUS_DB.SCENARIOS.V_ACTIVE_FREIGHT_SHOCK_PARAMETERS
    ),
    'summary', (
      SELECT OBJECT_CONSTRUCT(
        'parts_analyzed', parts_analyzed,
        'modeled_protected_units', modeled_protected_units,
        'modeled_uncovered_units', modeled_uncovered_units,
        'modeled_minimum_source_cost', modeled_minimum_source_cost
      ) FROM NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_SUMMARY
    ),
    'source_options', (
      SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
        'part_id', part_id,
        'supplier_id', supplier_id,
        'supplier_name', supplier_name,
        'required_units', required_units,
        'protected_units', protected_units,
        'uncovered_units', uncovered_units,
        'modeled_freight_cost', modeled_freight_cost,
        'lead_time_days', lead_time_days,
        'note', calculation_note
      )) FROM NEXUS_DB.SCENARIOS.V_FREIGHT_SHOCK_CHAIN
    )
  )
$$;

-- ---------------------------------------------------------------------------
-- 6. NEXUS_SUPPLY_CHAIN_AGENT
-- ---------------------------------------------------------------------------
CREATE OR REPLACE AGENT NEXUS_DB.PUBLIC.NEXUS_SUPPLY_CHAIN_AGENT
  COMMENT = 'NEXUS Supply Chain Resilience Agent — governed baseline analytics and deterministic scenario modeling.'
  PROFILE = '{"display_name": "NEXUS Supply Chain", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  instructions:
    response: |
      You are the NEXUS Supply Chain Resilience Agent. You answer questions about a
      global manufacturing supply chain covering suppliers, parts, plants, inventory,
      products, orders, shipments, ports, and customers.

      BASELINE ANALYTICS: Use the nexus_analyst tool for current-state questions about
      suppliers, parts, inventory, orders, dependencies, shipments, and customers.
      The semantic view governs all entity resolution and metric definitions.

      SCENARIO MODELING: Use the scenario tools for disruption impact analysis.
      These tools execute the currently configured deterministic scenario with fixed
      MVP parameters. They do not accept arbitrary scenario parameters.
      - Supplier failure: SUP-001, 100% capacity reduction, 14 days
      - Port disruption: PORT-TYO, 100% disruption, 7 days
      - Freight shock: 30% freight increase, 14 days
      - Mitigation strategies (4): NO_ACTION, EXPEDITE_SHIPMENT, INVENTORY_REALLOCATION, ALTERNATE_SUPPLIER

      CRITICAL RULES:
      1. Every scenario result is a DETERMINISTIC MODELED OUTCOME, not an operational
         guarantee. Always state this clearly.
      2. Never fabricate supplier IDs, part IDs, order IDs, or metric values.
      3. Never execute or suggest autonomous procurement or operational actions.
      4. Resolve entity names to canonical IDs via the semantic view before answering.
      5. When tracing dependencies, follow the governed ontology path:
         supplier_parts → parts → product_parts → orders → customers.
      6. Mitigation strategies are modeled comparisons. Present all available strategies
         with their modeled cost and protected revenue.

    orchestration: |
      ROUTING RULES:
      - Baseline current-state questions (suppliers, parts, inventory, orders,
        dependencies, BOM, shipments, customers) → nexus_analyst
      - "What breaks if supplier fails" or supplier failure impact → run_active_supplier_failure
      - "What can we do" or mitigation comparison → compare_active_mitigations
      - Port disruption impact → run_active_port_disruption
      - Freight cost shock or freight increase → get_active_freight_shock
      - For the canonical journey "What breaks next if SUP-001 becomes unavailable":
        1. Call run_active_supplier_failure to get impact and dependency chain
        2. Call compare_active_mitigations to get mitigation options
        3. Synthesize both results into an evidence-backed answer

    sample_questions:
      - question: "Which suppliers provide critical parts?"
      - question: "What breaks if supplier SUP-001 is unavailable for 14 days?"
      - question: "What products depend on PART-104?"
      - question: "What can we do to reduce the impact of a supplier failure?"

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "nexus_analyst"
        description: "Governed baseline analytics for the NEXUS supply chain. Answers current-state questions about suppliers, parts, inventory, orders, products, shipments, ports, and customers using the semantic view."
    - tool_spec:
        type: "generic"
        name: "run_active_supplier_failure"
        description: "Executes the currently configured supplier failure scenario (SUP-001, 100% capacity reduction, 14 days). Returns modeled impact including orders at risk, customers exposed, affected parts and plants, revenue exposure, units at risk, and the full dependency chain. This is a deterministic modeled outcome, not an operational guarantee."
    - tool_spec:
        type: "generic"
        name: "compare_active_mitigations"
        description: "Compares four mitigation strategies for the currently active supplier failure scenario: no action (baseline), expedite shipment (rush in-transit goods via alternate freight, 25% cost premium), inventory reallocation (transfer surplus stock from non-deficit plants, 15% logistics cost), and alternate supplier (source from other qualified suppliers). Returns modeled outcomes for each strategy including orders at risk, customers exposed, remaining and protected revenue exposure, and incremental modeled cost. All results are deterministic modeled outcomes."
    - tool_spec:
        type: "generic"
        name: "run_active_port_disruption"
        description: "Executes the currently configured port disruption scenario (PORT-TYO, 100% disruption, 7 days). Returns modeled impact including orders at risk, customers exposed, affected plants, revenue exposure, and the disruption chain tracing port to shipments to orders to customers. This is a deterministic modeled outcome."
    - tool_spec:
        type: "generic"
        name: "get_active_freight_shock"
        description: "Executes the currently configured freight cost shock scenario (30% freight increase, 14 days). Returns modeled summary including parts analyzed, protected and uncovered units, minimum source cost, and per-part supplier sourcing options. This is a deterministic modeled outcome."

  tool_resources:
    nexus_analyst:
      semantic_view: "NEXUS_DB.SEMANTIC.NEXUS_SUPPLY_CHAIN"
      execution_environment:
        type: warehouse
        warehouse: "COMPUTE_WH"
    run_active_supplier_failure:
      type: function
      identifier: "NEXUS_DB.TOOLS.RUN_ACTIVE_SUPPLIER_FAILURE"
      execution_environment:
        type: warehouse
        warehouse: "COMPUTE_WH"
    compare_active_mitigations:
      type: function
      identifier: "NEXUS_DB.TOOLS.COMPARE_ACTIVE_MITIGATIONS"
      execution_environment:
        type: warehouse
        warehouse: "COMPUTE_WH"
    run_active_port_disruption:
      type: function
      identifier: "NEXUS_DB.TOOLS.RUN_ACTIVE_PORT_DISRUPTION"
      execution_environment:
        type: warehouse
        warehouse: "COMPUTE_WH"
    get_active_freight_shock:
      type: function
      identifier: "NEXUS_DB.TOOLS.GET_ACTIVE_FREIGHT_SHOCK"
      execution_environment:
        type: warehouse
        warehouse: "COMPUTE_WH"
  $$;
