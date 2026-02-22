"""
Query history manager — saves and retrieves user-saved queries in Redshift.
Table: genai_app_meta.query_history (auto-created on first use)
Uses execute_query for proper connection pool management.
"""
import json
from .redshift_connector_iam import execute_query

META_SCHEMA = "genai_app_meta"
HISTORY_TABLE = f"{META_SCHEMA}.query_history"

_table_ensured = False


def _ensure_table():
    """Create the history schema and table if they don't exist."""
    global _table_ensured
    if _table_ensured:
        return
    try:
        execute_query(f"CREATE SCHEMA IF NOT EXISTS {META_SCHEMA}")
        execute_query(
            f"CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} ("
            f"id INTEGER IDENTITY(1,1), saved_at TIMESTAMP DEFAULT GETDATE(), "
            f"schema_name VARCHAR(100), question VARCHAR(2000), "
            f"generated_sql VARCHAR(10000), row_count INTEGER, "
            f"analysis VARCHAR(30000), results_json VARCHAR(65535))"
        )
        _table_ensured = True
    except Exception as e:
        # Table may already exist (IDENTITY error on re-create) — that's fine
        if 'already exists' in str(e).lower():
            _table_ensured = True
        else:
            print(f"Error ensuring history table: {e}")


def save_query(schema_name: str, question: str, generated_sql: str,
               results: list, column_names: list, analysis: str) -> bool:
    """Save a query and its results to history."""
    _ensure_table()
    try:
        results_data = {"columns": column_names, "rows": [list(map(str, r)) for r in results[:100]]}
        results_json = json.dumps(results_data, default=str)
        if len(results_json) > 65535:
            results_data["rows"] = results_data["rows"][:20]
            results_json = json.dumps(results_data, default=str)

        execute_query(
            f"INSERT INTO {HISTORY_TABLE} (schema_name, question, generated_sql, row_count, analysis, results_json) "
            f"VALUES (%s, %s, %s, %s, %s, %s)",
            (schema_name, question, generated_sql, len(results), analysis[:30000], results_json)
        )
        return True
    except Exception as e:
        print(f"Error saving query: {e}")
        return False


def get_saved_queries(schema_name: str = None, limit: int = 50) -> list:
    """Retrieve saved queries, optionally filtered by schema."""
    _ensure_table()
    try:
        if schema_name:
            rows = execute_query(
                f"SELECT id, saved_at, schema_name, question, generated_sql, row_count, analysis, results_json "
                f"FROM {HISTORY_TABLE} WHERE schema_name = %s ORDER BY saved_at DESC LIMIT %s",
                (schema_name, limit)
            )
        else:
            rows = execute_query(
                f"SELECT id, saved_at, schema_name, question, generated_sql, row_count, analysis, results_json "
                f"FROM {HISTORY_TABLE} ORDER BY saved_at DESC LIMIT %s",
                (limit,)
            )
        return [{"id": r[0], "saved_at": r[1], "schema_name": r[2], "question": r[3],
                 "generated_sql": r[4], "row_count": r[5], "analysis": r[6],
                 "results_json": r[7]} for r in (rows or [])]
    except Exception as e:
        print(f"Error loading history: {e}")
        return []


def delete_saved_query(query_id: int) -> bool:
    """Delete a saved query by ID."""
    try:
        execute_query(f"DELETE FROM {HISTORY_TABLE} WHERE id = %s", (query_id,))
        return True
    except Exception as e:
        print(f"Error deleting query: {e}")
        return False
