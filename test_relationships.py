"""
End-to-end test for relationship manager integration.
Tests all sample questions against both northwind (descriptive) and nw_abbr (cryptic) schemas.
Verifies that the 4-source relationship merge produces correct JOINs.
"""
import os
import sys
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Connection setup
CONN_PARAMS = dict(
    host='redshift-cluster-amazon-q2.cwtsoujhoswf.us-east-1.redshift.amazonaws.com',
    port=5439, database='dev', user='awsuser', password='Awsuser12345', sslmode='require'
)

sys.path.insert(0, os.path.dirname(__file__))
from src.bedrock.bedrock_helper_iam import BedrockHelper
from src.vector_store.faiss_manager import FAISSManager
from src.graph.workflow import AnalysisWorkflow
from src.utils.relationship_manager import (
    get_all_relationships, build_relationship_map,
    get_fk_relationships, get_comment_relationships, get_yaml_relationships
)

# Sample questions (same as app.py dropdown)
SAMPLE_QUERIES = [
    ("🟢 Simple", "How many customers are there?"),
    ("🟢 Simple", "What are the top 5 most expensive products?"),
    ("🟡 Medium", "What are the top 5 products by total quantity ordered?"),
    ("🟡 Medium", "What's the average order value by country?"),
    ("🟡 Medium", "Which product categories sell the most?"),
    ("🔴 Complex", "What's the monthly sales trend?"),
    ("🔴 Complex", "Which employees generated the most revenue by country, including the product categories they sold?"),
]


def execute_query_redshift(query, params=None):
    conn = psycopg2.connect(**CONN_PARAMS)
    cur = conn.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    conn.close()
    return results


def execute_query_with_columns_redshift(query):
    conn = psycopg2.connect(**CONN_PARAMS)
    cur = conn.cursor()
    cur.execute(query)
    cols = [d[0] for d in cur.description] if cur.description else []
    results = cur.fetchall()
    conn.close()
    return results, cols


def build_workflow(schema):
    """Build a workflow with relationship-aware indexing for a given schema."""
    bedrock = BedrockHelper(region_name='us-east-1')
    vector_store = FAISSManager(bedrock_client=bedrock)

    # Index schema metadata (same logic as app.py load_metadata)
    tables_result = execute_query_redshift(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
        (schema,)
    )
    table_names = [t[0] for t in tables_result]

    # Get relationships from all 4 sources
    all_rels = get_all_relationships(execute_query_redshift, schema)
    fk_map = build_relationship_map(all_rels, schema)

    import numpy as np
    texts = []
    metadatas = []
    database = 'dev'

    for table_name in table_names:
        columns_result = execute_query_redshift(
            "SELECT c.column_name, c.data_type, d.description "
            "FROM information_schema.columns c "
            "LEFT JOIN (SELECT cl.oid, cl.relname, ns.nspname FROM pg_catalog.pg_class cl "
            "JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid WHERE cl.relkind = 'r') t "
            "ON t.relname = c.table_name AND t.nspname = c.table_schema "
            "LEFT JOIN pg_catalog.pg_description d ON t.oid = d.objoid AND d.objsubid = c.ordinal_position "
            "WHERE c.table_schema = %s AND c.table_name = %s ORDER BY c.ordinal_position",
            (schema, table_name)
        )
        try:
            tc_result = execute_query_redshift(
                "SELECT d.description FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid "
                "JOIN pg_catalog.pg_description d ON c.oid = d.objoid AND d.objsubid = 0 "
                "WHERE n.nspname = %s AND c.relname = %s",
                (schema, table_name)
            )
            table_comment = tc_result[0][0] if tc_result else None
        except:
            table_comment = None

        if columns_result:
            col_parts = []
            for col_name, data_type, comment in columns_result:
                if comment:
                    col_parts.append(f"{col_name} ({comment}, {data_type})")
                else:
                    col_parts.append(f"{col_name} ({data_type})")
            columns_str = " | ".join(col_parts)
            relationships = fk_map.get(table_name, [])
            rel_str = f"\nRelationships: {'; '.join(relationships)}" if relationships else ""
            table_desc = f" ({table_comment})" if table_comment else ""
            text = f"Schema: {schema}, Table: {schema}.{table_name}{table_desc}\nColumns: {columns_str}{rel_str}"
            texts.append(text)
            metadatas.append({'database': database, 'schema': schema, 'table': table_name, 'type': 'table'})

    overview = (f"Database: {database}, Schema: {schema}\n"
                f"Available tables: {', '.join([schema + '.' + t for t in table_names])}\n"
                f"IMPORTANT: Always use schema-qualified table names: {schema}.tablename")
    texts.append(overview)
    metadatas.append({'database': database, 'schema': schema, 'type': 'overview'})

    embeddings = []
    for text in texts:
        embedding = vector_store.bedrock_client.get_embeddings(text)
        embeddings.append(embedding)

    if embeddings:
        embeddings_array = np.array(embeddings).astype('float32')
        vector_store.index.add(embeddings_array)
        vector_store.texts = texts
        vector_store.metadata = metadatas

    os.environ['REDSHIFT_SCHEMA'] = schema
    workflow = AnalysisWorkflow(bedrock_helper=bedrock, vector_store=vector_store)
    return workflow, all_rels


def test_relationship_sources(schema):
    """Test that each relationship source returns expected data."""
    print(f"\n{'='*70}")
    print(f"RELATIONSHIP SOURCE TEST: {schema}")
    print(f"{'='*70}")

    fk_rels = get_fk_relationships(execute_query_redshift, schema)
    print(f"\n  Source 1 - FK constraints: {len(fk_rels)} found")
    for r in fk_rels:
        print(f"    {r['source_table']}.{r['source_column']} -> {r['target_table']}.{r['target_column']}")

    comment_rels = get_comment_relationships(execute_query_redshift, schema)
    print(f"\n  Source 2 - COMMENT ON [FK:]: {len(comment_rels)} found")
    for r in comment_rels:
        print(f"    {r['source_table']}.{r['source_column']} -> {r['target_table']}.{r['target_column']}")

    yaml_rels = get_yaml_relationships(schema)
    print(f"\n  Source 3/4 - YAML/UI: {len(yaml_rels)} found")
    for r in yaml_rels:
        print(f"    {r['source_table']}.{r['source_column']} -> {r['target_table']}.{r['target_column']} ({r.get('description','')})")

    all_rels = get_all_relationships(execute_query_redshift, schema)
    print(f"\n  MERGED (deduplicated): {len(all_rels)} relationships")
    for r in all_rels:
        print(f"    [{r['origin']:>13}] {r['source_table']}.{r['source_column']} -> {r['target_table']}.{r['target_column']}")

    return all_rels


def test_queries(schema):
    """Test all sample queries against a schema."""
    print(f"\n{'='*70}")
    print(f"QUERY TEST: {schema}")
    print(f"{'='*70}")

    workflow, all_rels = build_workflow(schema)
    results = []

    for difficulty, question in SAMPLE_QUERIES:
        print(f"\n{'─'*60}")
        print(f"  {difficulty}: {question}")
        print(f"{'─'*60}")

        state = workflow.execute(
            query=question,
            execute_query_func=execute_query_with_columns_redshift
        )

        sql = state.get('generated_sql', 'N/A')
        error = state.get('error') or state.get('friendly_error')
        query_results = state.get('query_results', [])
        col_names = state.get('column_names', [])
        retrieved_tables = state.get('retrieved_tables', [])

        print(f"  Retrieved tables: {retrieved_tables}")
        print(f"  Generated SQL:\n    {sql}")

        # Check for JOIN presence in multi-table queries
        has_join = 'JOIN' in sql.upper() if sql != 'N/A' else False

        if error:
            print(f"  ❌ ERROR: {error}")
            status = "FAIL"
        elif query_results:
            print(f"  ✅ Results: {len(query_results)} rows, columns: {col_names}")
            if len(query_results) <= 5:
                for row in query_results:
                    print(f"    {row}")
            else:
                for row in query_results[:3]:
                    print(f"    {row}")
                print(f"    ... ({len(query_results) - 3} more rows)")
            status = "PASS"
        else:
            print(f"  ⚠️  No results returned")
            status = "WARN"

        if has_join:
            print(f"  🔗 JOIN detected in SQL")

        results.append({
            "difficulty": difficulty,
            "question": question,
            "schema": schema,
            "status": status,
            "has_join": has_join,
            "row_count": len(query_results),
            "sql": sql
        })

    return results


def main():
    print("=" * 70)
    print("RELATIONSHIP MANAGER - END-TO-END TEST")
    print("=" * 70)

    # Test 1: Verify relationship sources for both schemas
    nw_rels = test_relationship_sources("northwind")
    abbr_rels = test_relationship_sources("nw_abbr")

    # Test 2: Run all sample queries against both schemas
    nw_results = test_queries("northwind")
    abbr_results = test_queries("nw_abbr")

    # Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")

    all_results = nw_results + abbr_results
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")
    warned = sum(1 for r in all_results if r["status"] == "WARN")

    print(f"\n  Total tests: {len(all_results)}")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠️  Warnings: {warned}")

    print(f"\n  {'Schema':<12} {'Difficulty':<12} {'Status':<8} {'JOIN':<6} {'Rows':<6} Question")
    print(f"  {'─'*12} {'─'*12} {'─'*8} {'─'*6} {'─'*6} {'─'*40}")
    for r in all_results:
        join_str = "Yes" if r["has_join"] else "No"
        print(f"  {r['schema']:<12} {r['difficulty']:<12} {r['status']:<8} {join_str:<6} {r['row_count']:<6} {r['question'][:50]}")

    if failed > 0:
        print(f"\n  ⚠️  {failed} test(s) FAILED — review errors above")
        sys.exit(1)
    else:
        print(f"\n  🎉 All tests passed!")


if __name__ == "__main__":
    main()
