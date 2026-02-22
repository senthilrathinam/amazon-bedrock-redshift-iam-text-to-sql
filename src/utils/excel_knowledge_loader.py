"""
Excel Knowledge Loader — parses a customer Excel workbook (3 tabs: Tables, Columns, Queries)
and provisions the schema in Redshift with COMMENT ON metadata, relationships, and golden queries.

Expected Excel format:
  Tab 1 "Tables":  columns = [Tables, Description]
  Tab 2 "Columns": columns = [table_name, column_name, data_type, comment]
  Tab 3 "Queries": columns = [User Question, Expected Query]
"""
import os
import yaml
import openpyxl
from typing import Dict, List, Tuple, Optional

EXAMPLES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "examples.yaml")
RELATIONSHIPS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "relationships.yaml")

# Redshift data type mapping from common pg types
DTYPE_MAP = {
    "character varying": "VARCHAR(500)",
    "integer": "INTEGER",
    "bigint": "BIGINT",
    "numeric": "NUMERIC(15,4)",
    "boolean": "BOOLEAN",
    "timestamp without time zone": "TIMESTAMP",
    "date": "DATE",
    "text": "TEXT",
    "double precision": "FLOAT",
    "real": "FLOAT",
    "smallint": "SMALLINT",
}


def parse_excel(file_path_or_bytes) -> dict:
    """Parse the 3-tab Excel workbook. Accepts file path (str) or BytesIO object.
    Returns dict with keys: tables, columns, queries."""
    if isinstance(file_path_or_bytes, str):
        wb = openpyxl.load_workbook(file_path_or_bytes)
    else:
        wb = openpyxl.load_workbook(file_path_or_bytes)

    result = {"tables": [], "columns": [], "queries": []}

    # Tab 1: Tables
    ws = wb.worksheets[0]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            # Clean table name: strip " table" suffix, lowercase, strip whitespace
            name = str(row[0]).strip().lower()
            if name.endswith(" table"):
                name = name[:-6].strip()
            result["tables"].append({
                "table_name": name,
                "description": str(row[1]).strip() if row[1] else ""
            })

    # Tab 2: Columns
    ws = wb.worksheets[1]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            result["columns"].append({
                "table_name": str(row[0]).strip().lower(),
                "column_name": str(row[1]).strip().lower(),
                "data_type": str(row[2]).strip().lower() if row[2] else "character varying",
                "comment": str(row[3]).strip() if row[3] else None
            })

    # Tab 3: Queries
    ws = wb.worksheets[2]
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            result["queries"].append({
                "question": str(row[0]).strip(),
                "sql": str(row[1]).strip()
            })

    return result


def _build_ddl(schema: str, parsed: dict) -> List[str]:
    """Build CREATE TABLE DDL statements from parsed Excel data."""
    # Group columns by table
    table_cols: Dict[str, List[dict]] = {}
    for col in parsed["columns"]:
        table_cols.setdefault(col["table_name"], []).append(col)

    ddl_list = [f"CREATE SCHEMA IF NOT EXISTS {schema}"]

    for table_info in parsed["tables"]:
        tbl = table_info["table_name"]
        cols = table_cols.get(tbl, [])
        if not cols:
            continue
        col_defs = []
        for c in cols:
            rs_type = DTYPE_MAP.get(c["data_type"], "VARCHAR(500)")
            col_defs.append(f"    {c['column_name']} {rs_type}")
        ddl = f"CREATE TABLE IF NOT EXISTS {schema}.{tbl} (\n"
        ddl += ",\n".join(col_defs)
        ddl += "\n)"
        ddl_list.append(ddl)

    return ddl_list


def _detect_join_columns(parsed: dict) -> List[Tuple[str, str, str, str]]:
    """Auto-detect JOIN relationships by finding columns with the same name across tables.
    Filters to likely join keys (columns containing 'id', 'number', 'key', 'code')."""
    col_to_tables: Dict[str, List[str]] = {}
    for col in parsed["columns"]:
        col_to_tables.setdefault(col["column_name"], []).append(col["table_name"])

    # Only consider columns that look like join keys
    join_indicators = ('id', 'number', 'key', 'code')

    relationships = []
    for col_name, tables in col_to_tables.items():
        unique_tables = list(set(tables))
        if len(unique_tables) < 2:
            continue
        if not any(ind in col_name.lower() for ind in join_indicators):
            continue
        primary = unique_tables[0]
        for other in unique_tables[1:]:
            relationships.append((other, col_name, primary, col_name))

    return relationships


def save_examples(schema: str, queries: List[dict]):
    """Save golden queries to examples.yaml."""
    data = {}
    if os.path.exists(EXAMPLES_PATH):
        with open(EXAMPLES_PATH, 'r') as f:
            data = yaml.safe_load(f) or {}

    data[schema] = [{"question": q["question"], "sql": q["sql"]} for q in queries]

    with open(EXAMPLES_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_relationships(schema: str, rels: List[Tuple[str, str, str, str]]):
    """Save detected relationships to relationships.yaml."""
    data = {}
    if os.path.exists(RELATIONSHIPS_PATH):
        with open(RELATIONSHIPS_PATH, 'r') as f:
            data = yaml.safe_load(f) or {}

    entries = []
    for src_tbl, src_col, tgt_tbl, tgt_col in rels:
        entries.append({
            "source": f"{src_tbl}.{src_col}",
            "target": f"{tgt_tbl}.{tgt_col}",
            "description": f"{src_tbl} references {tgt_tbl} via {src_col}"
        })
    data[schema] = entries

    with open(RELATIONSHIPS_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def provision_schema(schema: str, parsed: dict, execute_query_func):
    """Create schema, tables, and apply COMMENT ON metadata in Redshift.
    Returns (success: bool, message: str)."""
    try:
        from .redshift_connector_iam import get_redshift_connection
        conn = get_redshift_connection()
        cur = conn.cursor()

        # Drop and recreate
        cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        conn.commit()

        # Create tables
        for ddl in _build_ddl(schema, parsed):
            cur.execute(ddl)
            conn.commit()

        # Apply table comments
        for t in parsed["tables"]:
            if t["description"]:
                cur.execute(f"COMMENT ON TABLE {schema}.{t['table_name']} IS %s", (t["description"],))
        conn.commit()

        # Apply column comments
        commented = 0
        for c in parsed["columns"]:
            if c["comment"]:
                try:
                    cur.execute(f"COMMENT ON COLUMN {schema}.{c['table_name']}.{c['column_name']} IS %s", (c["comment"],))
                    commented += 1
                except Exception:
                    conn.rollback()
        conn.commit()

        # Save relationships and examples
        rels = _detect_join_columns(parsed)
        save_relationships(schema, rels)
        save_examples(schema, parsed["queries"])

        conn.close()

        table_count = len(parsed["tables"])
        query_count = len(parsed["queries"])
        return True, f"Created {table_count} tables, {commented} column comments, {len(rels)} relationships, {query_count} golden queries."

    except Exception as e:
        return False, f"Error: {str(e)}"
