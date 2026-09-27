"""
NEXUS Phase 9 — Snowflake Deployment & E2E Validation Driver

Usage:
    cd /Users/harshahg/Desktop/nexus
    app/venv/bin/python scripts/deploy.py [step]

Steps:
    connect     — test connectivity only
    deploy      — run all SQL files in order (001→014)
    golden      — run 005_golden_queries.sql
    tests       — run 009_scenario_tests.sql + 015_extended_tests.sql
    validate    — run validation views (scenario + metric catalog)
    realloc     — inspect INVENTORY_REALLOCATION detail
    objects     — list all deployed Snowflake objects
    all         — run everything in sequence (default)
"""
from __future__ import annotations
import sys, os, re, time, textwrap
from pathlib import Path

# ── Credential loading ────────────────────────────────────────────────────────
SECRETS_PATH = Path(__file__).parent.parent / "app" / ".streamlit" / "secrets.toml"

def load_secrets() -> dict:
    import re
    cfg = {}
    with open(SECRETS_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg

def get_session():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from snowflake.snowpark import Session
    cfg = load_secrets()
    key_path = cfg.get("private_key_path", "")
    with open(key_path, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None)
    session = Session.builder.configs({
        "account":     cfg["account"],
        "user":        cfg["user"],
        "private_key": private_key,
        "role":        cfg.get("role", "ACCOUNTADMIN"),
        "warehouse":   cfg.get("warehouse", "COMPUTE_WH"),
        "database":    "NEXUS_DB",
    }).create()
    return session

# ── SQL file runner ───────────────────────────────────────────────────────────
SQL_DIR = Path(__file__).parent.parent / "snowflake"

DEPLOY_ORDER = [
    "001_schema.sql",
    "002_seed_data.sql",
    "003_product_bom.sql",
    "007_supplier_part_sources.sql",
    "004_semantic_views.sql",
    "006_scenario_engine.sql",
    "008_mitigation_engine.sql",
    "010_port_disruption_engine.sql",
    "011_freight_shock_engine.sql",
    "012_validation_views.sql",
    "013_nexus_semantic_view.sql",
    "014_nexus_agent.sql",
]

def split_statements(sql: str) -> list[str]:
    """
    Split SQL text into individual statements.
    Respects $$ body blocks (UDFs, agents) and ignores comment-only lines.
    """
    stmts = []
    in_dollar_block = False
    current: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()

        # Track $$ blocks
        dollar_count = stripped.count("$$")
        if dollar_count % 2 == 1:  # odd count toggles
            in_dollar_block = not in_dollar_block

        current.append(line)

        if not in_dollar_block and stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and not all(l.strip().startswith("--") or l.strip() == "" for l in stmt.splitlines()):
                stmts.append(stmt)
            current = []

    # Any remaining content
    remainder = "\n".join(current).strip()
    if remainder and not all(l.strip().startswith("--") or l.strip() == "" for l in remainder.splitlines()):
        stmts.append(remainder)

    return stmts

def run_file(session, filename: str, quiet: bool = False) -> tuple[int, int]:
    """Run a SQL file. Returns (ok_count, error_count)."""
    fpath = SQL_DIR / filename
    sql = fpath.read_text()
    stmts = split_statements(sql)
    ok, errors = 0, 0
    for stmt in stmts:
        first_line = stmt.strip().splitlines()[0][:80] if stmt.strip() else ""
        try:
            session.sql(stmt).collect()
            ok += 1
            if not quiet:
                print(f"    ✓  {first_line}")
        except Exception as e:
            errors += 1
            print(f"    ✗  {first_line}")
            print(f"       ERROR: {e}")
    return ok, errors

def print_table(rows: list[dict], max_col: int = 40) -> None:
    if not rows:
        print("  (no rows)")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(str(c)), max(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    widths = {c: min(w, max_col) for c, w in widths.items()}
    header = "  " + " | ".join(str(c).ljust(widths[c]) for c in cols)
    sep    = "  " + "-+-".join("-" * widths[c] for c in cols)
    print(header)
    print(sep)
    for row in rows:
        line = "  " + " | ".join(str(row.get(c, "")).ljust(widths[c])[:widths[c]] for c in cols)
        print(line)

# ── Steps ─────────────────────────────────────────────────────────────────────

def step_connect():
    print("\n━━━  Step 1: Test Snowflake Connectivity  ━━━")
    try:
        s = get_session()
        row = s.sql("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_VERSION()").collect()[0]
        print(f"  ✓  Connected to Snowflake")
        print(f"     User      : {row[0]}")
        print(f"     Role      : {row[1]}")
        print(f"     Warehouse : {row[2]}")
        print(f"     Database  : {row[3]}")
        print(f"     Version   : {row[4][:30]}")
        return s
    except Exception as e:
        print(f"  ✗  Connection failed: {e}")
        sys.exit(1)

def step_deploy(session):
    print("\n━━━  Step 2: Deploy SQL Files  ━━━")
    total_ok = total_err = 0
    for fname in DEPLOY_ORDER:
        t0 = time.time()
        print(f"\n  ▶  {fname}")
        ok, err = run_file(session, fname)
        elapsed = time.time() - t0
        status = "✓" if err == 0 else "⚠"
        print(f"  {status}  {fname}: {ok} ok, {err} errors  [{elapsed:.1f}s]")
        total_ok += ok
        total_err += err
    print(f"\n  Total: {total_ok} statements ok, {total_err} errors")
    return total_err == 0

def step_golden(session):
    print("\n━━━  Step 3: Golden Queries (005)  ━━━")
    queries = {
        "Q1 — Customers depending on SUP-001": """
            SELECT DISTINCT customer_id, customer_name, product_id, product_name, part_id, part_name
            FROM NEXUS_DB.SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
            WHERE supplier_id = 'SUP-001'
            ORDER BY customer_id""",
        "Q2 — Single-sourced critical parts": """
            SELECT s.part_id, p.part_name, p.criticality
            FROM NEXUS_DB.ANALYTICS.SUPPLIER_CONCENTRATION s
            JOIN NEXUS_DB.RAW.PARTS p ON p.part_id = s.part_id
            WHERE is_single_source = TRUE
            ORDER BY p.part_id""",
        "Q3 — Parts < 7 days inventory": """
            SELECT plant_id, plant_name, part_id, part_name, inventory_coverage_days
            FROM NEXUS_DB.ANALYTICS.PART_PLANT_INVENTORY
            WHERE inventory_coverage_days < 7
            ORDER BY inventory_coverage_days""",
        "Q4 — Delayed shipments": """
            SELECT shipment_id, supplier_name, part_name, plant_name, port_name, quantity, expected_arrival
            FROM NEXUS_DB.ANALYTICS.DELAYED_SHIPMENTS
            ORDER BY expected_arrival""",
        "Q5 — Dependency path for CUST-003": """
            SELECT DISTINCT customer_name, supplier_name, part_name, product_name
            FROM NEXUS_DB.SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
            WHERE customer_id = 'CUST-003'
            ORDER BY supplier_name""",
        "Q6 — Products depending on PART-104": """
            SELECT DISTINCT product_id, product_name
            FROM NEXUS_DB.ANALYTICS.PRODUCT_DEPENDENCY
            WHERE part_id = 'PART-104'""",
        "Q7 — Suppliers of PART-104": """
            SELECT DISTINCT supplier_id, supplier_name
            FROM NEXUS_DB.ANALYTICS.SUPPLIER_PART_DEPENDENCY
            WHERE part_id = 'PART-104'""",
        "Q8 — Supplier exposure": """
            SELECT supplier_id, supplier_name,
                   COUNT(DISTINCT customer_id) AS customers_exposed,
                   COUNT(DISTINCT order_id) AS orders_exposed
            FROM NEXUS_DB.SEMANTIC.V_CUSTOMER_SUPPLIER_DEPENDENCY
            GROUP BY supplier_id, supplier_name
            ORDER BY orders_exposed DESC
            LIMIT 5""",
    }
    for label, sql in queries.items():
        print(f"\n  {label}")
        try:
            rows = [dict(zip([d.name for d in session.sql(sql).schema], r)) for r in session.sql(sql).collect()]
            print_table(rows)
        except Exception as e:
            print(f"  ✗  ERROR: {e}")

def step_scenario_tests(session):
    print("\n━━━  Step 4a: Scenario Tests (009)  ━━━")
    sql = (SQL_DIR / "009_scenario_tests.sql").read_text()
    # Extract each SELECT block
    tests = re.findall(r"(SELECT\s+'[^']+'\s+AS test_name.*?;)", sql, re.DOTALL | re.IGNORECASE)
    for t in tests:
        try:
            rows = session.sql(t.rstrip(";")).collect()
            row = dict(zip([d.name for d in session.sql(t.rstrip(";")).schema], rows[0]))
            result = row.get("RESULT", row.get("result", "?"))
            name   = row.get("TEST_NAME", row.get("test_name", "?"))
            icon   = "✓" if result == "PASS" else "✗"
            print(f"  {icon}  {name}: {result}")
        except Exception as e:
            print(f"  ✗  ERROR: {e}")

def step_extended_tests(session):
    print("\n━━━  Step 4b: Extended Tests (015)  ━━━")
    sql = (SQL_DIR / "015_extended_tests.sql").read_text()
    tests = re.findall(r"(SELECT\s+'[^']+'\s+AS test_name.*?;)", sql, re.DOTALL | re.IGNORECASE)
    pass_count = fail_count = 0
    for t in tests:
        try:
            rows = session.sql(t.rstrip(";")).collect()
            row = dict(zip([d.name for d in session.sql(t.rstrip(";")).schema], rows[0]))
            result = row.get("RESULT", row.get("result", "?"))
            name   = row.get("TEST_NAME", row.get("test_name", "?"))
            icon   = "✓" if result == "PASS" else ("✗" if result == "FAIL" else "ℹ")
            if result == "PASS":
                pass_count += 1
            elif result == "FAIL":
                fail_count += 1
            vcount = row.get("VIOLATION_COUNT", row.get("violation_count", ""))
            print(f"  {icon}  {name}: {result}  [{vcount}]")
        except Exception as e:
            print(f"  ✗  ERROR running test: {e}")
    print(f"\n  Summary: {pass_count} PASS, {fail_count} FAIL")

def step_validate(session):
    print("\n━━━  Step 5: Validation Views  ━━━")
    print("\n  V_SCENARIO_VALIDATION (5 checks):")
    rows = [dict(zip([d.name for d in session.sql("SELECT * FROM NEXUS_DB.ANALYTICS.V_SCENARIO_VALIDATION").schema], r))
            for r in session.sql("SELECT * FROM NEXUS_DB.ANALYTICS.V_SCENARIO_VALIDATION").collect()]
    for r in rows:
        icon = "✓" if r.get("STATUS","") == "PASS" else "✗"
        print(f"  {icon}  {r.get('CHECK_NAME','')} → {r.get('STATUS','')}  (violations: {r.get('VIOLATION_COUNT','')})")

    print("\n  V_SUPPLIER_FAILURE_IMPACT (KPI aggregate):")
    rows = [dict(zip([d.name for d in session.sql("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT").schema], r))
            for r in session.sql("SELECT * FROM NEXUS_DB.SCENARIOS.V_SUPPLIER_FAILURE_IMPACT").collect()]
    print_table(rows, max_col=20)

def step_realloc(session):
    print("\n━━━  Step 6: INVENTORY_REALLOCATION Results  ━━━")

    print("\n  V_MITIGATION_COMPARISON (all 4 strategies):")
    sql = "SELECT mitigation_type, orders_at_risk, customers_exposed, units_at_risk, ROUND(remaining_revenue_exposure,0) AS remaining_exposure, ROUND(modeled_revenue_protected,0) AS revenue_protected, ROUND(modeled_incremental_cost,0) AS incremental_cost FROM NEXUS_DB.SCENARIOS.V_MITIGATION_COMPARISON ORDER BY remaining_revenue_exposure DESC"
    rows = [dict(zip([d.name for d in session.sql(sql).schema], r)) for r in session.sql(sql).collect()]
    print_table(rows, max_col=25)

    print("\n  V_INVENTORY_REALLOCATION_DETAIL (per-plant surplus):")
    sql2 = "SELECT plant_name, part_name, scenario_available_units AS available, local_demand_units AS demand, surplus_units AS surplus, global_shortage_units AS global_shortage, reallocatable_units AS realloc, ROUND(estimated_transfer_cost,0) AS est_cost FROM NEXUS_DB.SCENARIOS.V_INVENTORY_REALLOCATION_DETAIL ORDER BY surplus_units DESC LIMIT 10"
    try:
        rows2 = [dict(zip([d.name for d in session.sql(sql2).schema], r)) for r in session.sql(sql2).collect()]
        print_table(rows2, max_col=22)
    except Exception as e:
        print(f"  ✗  {e}")

def step_objects(session):
    print("\n━━━  Step 7: Snowflake Object Verification  ━━━")

    checks = [
        ("Semantic View",  "SHOW SEMANTIC VIEWS IN SCHEMA NEXUS_DB.SEMANTIC",  "NEXUS_SUPPLY_CHAIN"),
        ("Cortex Agent",   "SHOW AGENTS IN SCHEMA NEXUS_DB.PUBLIC",            "NEXUS_SUPPLY_CHAIN_AGENT"),
        ("Tool UDFs",      "SHOW FUNCTIONS IN SCHEMA NEXUS_DB.TOOLS",          "RUN_ACTIVE_SUPPLIER_FAILURE"),
        ("Mitig View",     "SHOW VIEWS IN SCHEMA NEXUS_DB.SCENARIOS",          "V_MITIGATION_COMPARISON"),
        ("Realloc Detail", "SHOW VIEWS IN SCHEMA NEXUS_DB.SCENARIOS",          "V_INVENTORY_REALLOCATION_DETAIL"),
    ]
    for label, show_sql, expected in checks:
        try:
            rows = session.sql(show_sql).collect()
            names = [str(r[1]).upper() if len(r) > 1 else str(r[0]).upper() for r in rows]
            found = any(expected.upper() in n for n in names)
            icon = "✓" if found else "✗"
            print(f"  {icon}  {label}: {'found' if found else 'NOT FOUND'} ({expected})")
        except Exception as e:
            print(f"  ✗  {label}: ERROR — {e}")

    print("\n  RAW table row counts:")
    for tbl in ["SUPPLIERS","PARTS","PLANTS","INVENTORY","PORTS","SHIPMENTS",
                "PRODUCTS","ORDERS","CUSTOMERS","PRODUCT_PARTS","SUPPLIER_PARTS"]:
        try:
            cnt = session.sql(f"SELECT COUNT(*) FROM NEXUS_DB.RAW.{tbl}").collect()[0][0]
            print(f"    RAW.{tbl}: {cnt} rows")
        except Exception as e:
            print(f"    RAW.{tbl}: ERROR — {e}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    print(f"\n{'='*60}")
    print(f"  NEXUS Phase 9 — Snowflake Deployment & E2E Validation")
    print(f"  Step: {step}")
    print(f"{'='*60}")

    session = step_connect()

    if step in ("connect",):
        return

    if step in ("deploy", "all"):
        ok = step_deploy(session)
        if not ok and step == "deploy":
            print("\n⚠  Deployment had errors. Review above before proceeding.")

    if step in ("golden", "all"):
        step_golden(session)

    if step in ("tests", "all"):
        step_scenario_tests(session)
        step_extended_tests(session)

    if step in ("validate", "all"):
        step_validate(session)

    if step in ("realloc", "all"):
        step_realloc(session)

    if step in ("objects", "all"):
        step_objects(session)

    print(f"\n{'='*60}")
    print("  NEXUS Phase 9 — Complete")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
