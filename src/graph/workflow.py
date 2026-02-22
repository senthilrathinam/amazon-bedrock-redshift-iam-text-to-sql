"""
LangGraph workflow for the GenAI Sales Analyst application.
"""
from typing import Dict, Any, List, Tuple
import json
import os
import re
import yaml
import numpy as np
from datetime import datetime


# SQL statements that should never be executed
BLOCKED_SQL_PATTERNS = re.compile(
    r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|GRANT|REVOKE|MERGE)\b',
    re.IGNORECASE
)

EXAMPLES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "examples.yaml")


def _load_examples(schema: str) -> List[dict]:
    """Load golden query examples for a schema from examples.yaml."""
    if not os.path.exists(EXAMPLES_PATH):
        return []
    try:
        with open(EXAMPLES_PATH, 'r') as f:
            data = yaml.safe_load(f) or {}
        return data.get(schema, [])
    except:
        return []


def _find_best_examples(query: str, examples: List[dict], bedrock_client, top_k: int = 3) -> List[dict]:
    """Find the most semantically similar golden examples to the user's query."""
    if not examples:
        return []
    query_emb = np.array(bedrock_client.get_embeddings(query), dtype='float32')
    scored = []
    for ex in examples:
        ex_emb = np.array(bedrock_client.get_embeddings(ex['question']), dtype='float32')
        dist = float(np.sum((query_emb - ex_emb) ** 2))
        scored.append((ex, dist))
    scored.sort(key=lambda x: x[1])
    return [s[0] for s in scored[:top_k]]


def _extract_sql_identifiers(sql: str) -> Tuple[set, dict]:
    """Extract table aliases and column references from SQL for validation.
    Returns (table_refs, column_refs_by_alias)."""
    # Simple regex-based extraction — not a full parser but catches common patterns
    sql_clean = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql_clean = re.sub(r"'[^']*'", "''", sql_clean)  # Remove string literals

    # Find schema.table references and aliases
    table_pattern = re.compile(
        r'(?:from|join)\s+(\w+\.\w+)(?:\s+(?:as\s+)?(\w+))?',
        re.IGNORECASE
    )
    tables = {}  # alias -> schema.table
    for match in table_pattern.finditer(sql_clean):
        full_table = match.group(1).lower()
        alias = (match.group(2) or full_table.split('.')[-1]).lower()
        tables[alias] = full_table

    # Find column references (alias.column or bare column)
    col_pattern = re.compile(r'(?<!\w)(\w+)\.(\w+)(?!\s*\()', re.IGNORECASE)
    col_refs = {}  # alias -> set of columns
    for match in col_pattern.finditer(sql_clean):
        alias = match.group(1).lower()
        col = match.group(2).lower()
        # Skip schema.table references (already captured above)
        if alias in tables or any(alias == t.split('.')[0] for t in tables.values()):
            continue
        col_refs.setdefault(alias, set()).add(col)

    return tables, col_refs


class AnalysisWorkflow:
    def __init__(self, bedrock_helper, vector_store, monitor=None):
        self.bedrock = bedrock_helper
        self.vector_store = vector_store
        self.monitor = monitor
        self.schema = os.getenv('REDSHIFT_SCHEMA', 'northwind')
        self._examples = _load_examples(self.schema)
        # Cache valid columns per table (populated during retrieve_context)
        self._valid_columns = {}

    def _get_example_columns(self) -> set:
        """Extract all column names referenced in golden query examples."""
        cols = set()
        for ex in self._examples:
            sql = ex.get('sql', '')
            # Find alias.column patterns
            for match in re.finditer(r'(?:\w+)\.(\w+)', sql):
                cols.add(match.group(1).lower())
        return cols

    def _select_tables_via_llm(self, query: str) -> List[str]:
        """First pass: ask LLM which tables are needed based on table names + descriptions."""
        # Build a compact table summary from vector store
        table_summaries = []
        for i, meta in enumerate(self.vector_store.metadata):
            if meta.get('type') == 'table':
                text = self.vector_store.texts[i]
                # Extract just table name and first line (description)
                header = text.split('\nColumns:')[0].strip() if '\nColumns:' in text else text.split('\n')[0]
                table_summaries.append(f"- {header}")

        if not table_summaries:
            return []

        prompt = f"""Given this user question and the available tables, return ONLY the table names needed to answer the question.

Question: {query}

Available tables:
{chr(10).join(table_summaries)}

Return ONLY a comma-separated list of table names (without schema prefix). If all tables are needed, list all of them.
Example response: customers, orders, order_details"""

        try:
            response = self.bedrock.invoke_model(prompt, temperature=0.0, max_tokens=200)
            # Parse table names from response
            names = [t.strip().lower().split('.')[-1] for t in response.strip().split(',')]
            return [n for n in names if n]
        except:
            return []  # On failure, fall back to all tables

    def retrieve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context with two-pass table selection for small schemas."""
        query = state['query']

        try:
            table_doc_count = sum(1 for m in self.vector_store.metadata if m.get('type') == 'table')

            similar_docs = self.vector_store.similarity_search(query, k=8)

            if not similar_docs:
                return {
                    **state,
                    "relevant_context": [{
                        "text": f"Use {self.schema} schema. Query information_schema to discover available tables and columns."
                    }],
                    "retrieved_tables": [],
                    "steps_completed": state.get("steps_completed", []) + ["retrieve_context"]
                }

            # Two-pass filtering for small schemas: ask LLM which tables are needed
            if table_doc_count <= 5:
                needed_tables = self._select_tables_via_llm(query)
                if needed_tables:
                    filtered_docs = [doc for doc in similar_docs
                                     if doc.get('metadata', {}).get('type') != 'table'
                                     or doc['metadata'].get('table', '').lower() in needed_tables]
                else:
                    filtered_docs = similar_docs  # Fallback: keep all
            else:
                best_dist = similar_docs[0]['distance']
                threshold = best_dist * 1.15
                filtered_docs = [doc for doc in similar_docs if doc['distance'] <= threshold]

            # Always include overview docs
            overview_docs = [doc for doc in similar_docs if doc['metadata'].get('type') == 'overview']
            for od in overview_docs:
                if od not in filtered_docs:
                    filtered_docs.append(od)

            # Column-level filtering
            query_emb = np.array(self.vector_store.bedrock_client.get_embeddings(query), dtype='float32')
            example_cols = self._get_example_columns()

            column_filtered_docs = []
            self._valid_columns = {}

            for doc in filtered_docs:
                if doc.get('metadata', {}).get('type') != 'table':
                    column_filtered_docs.append(doc)
                    continue

                text = doc['text']
                table_name = doc['metadata'].get('table', '')

                if 'Columns:' not in text:
                    column_filtered_docs.append(doc)
                    continue

                header = text.split('Columns:')[0]
                cols_str = text.split('Columns:')[1].split('\n')[0].strip()
                rel_str = ""
                if '\nRelationships:' in text:
                    rel_str = '\n' + text.split('\nRelationships:')[1]

                col_entries = [c.strip() for c in cols_str.split(' | ') if c.strip()]

                # Cache ALL valid column names for this table (for SQL validation)
                for col_entry in col_entries:
                    col_name = col_entry.split(' (')[0].strip().lower()
                    self._valid_columns.setdefault(table_name, set()).add(col_name)

                # Skip column filtering for small tables
                if len(col_entries) <= 8:
                    column_filtered_docs.append(doc)
                    continue

                scored = []
                for col_entry in col_entries:
                    col_emb = np.array(
                        self.vector_store.bedrock_client.get_embeddings(col_entry), dtype='float32'
                    )
                    dist = float(np.sum((query_emb - col_emb) ** 2))
                    scored.append((col_entry, dist))

                scored.sort(key=lambda x: x[1])
                # Keep top 10 by semantic similarity (capped, not 50%)
                keep_n = min(10, max(5, len(scored) // 4))
                kept = scored[:keep_n]
                kept_set = {s[0] for s in kept}

                # Always keep ID/key/number columns and columns from golden examples
                for col_entry, dist in scored[keep_n:]:
                    col_name = col_entry.split(' (')[0].strip().lower()
                    if col_entry in kept_set:
                        continue
                    if 'id' in col_name or 'key' in col_name or 'number' in col_name:
                        kept.append((col_entry, dist))
                    elif col_name in example_cols:
                        kept.append((col_entry, dist))

                new_text = f"{header}Columns: {' | '.join(s[0] for s in kept)}{rel_str}"
                new_doc = {**doc, 'text': new_text}
                column_filtered_docs.append(new_doc)

            retrieved_tables = [
                doc['metadata']['table'] for doc in column_filtered_docs
                if doc['metadata'].get('type') == 'table'
            ]

            return {
                **state,
                "relevant_context": column_filtered_docs,
                "retrieved_tables": retrieved_tables,
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in retrieve_context: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context_error"]
            }

    def _build_few_shot_section(self, query: str) -> str:
        """Build few-shot examples section for the prompt."""
        if not self._examples:
            return ""
        best = _find_best_examples(query, self._examples, self.bedrock, top_k=3)
        if not best:
            return ""
        lines = ["\nREFERENCE EXAMPLES (use these as patterns for correct column/table usage):"]
        for i, ex in enumerate(best, 1):
            lines.append(f"\nExample {i}:")
            lines.append(f"Question: {ex['question']}")
            lines.append(f"SQL:\n{ex['sql'].strip()}")
        return "\n".join(lines)

    def _validate_sql_columns(self, sql: str, context: List[dict]) -> List[str]:
        """Validate that all column references in SQL exist in the schema.
        Returns list of error messages (empty = valid)."""
        if not self._valid_columns:
            return []

        errors = []
        tables, col_refs = _extract_sql_identifiers(sql)

        # Build alias -> table_name mapping
        alias_to_table = {}
        for alias, full_ref in tables.items():
            table_name = full_ref.split('.')[-1]
            alias_to_table[alias] = table_name

        # Check each column reference
        for alias, cols in col_refs.items():
            table_name = alias_to_table.get(alias)
            if not table_name or table_name not in self._valid_columns:
                continue
            valid = self._valid_columns[table_name]
            for col in cols:
                if col not in valid:
                    errors.append(f"Column '{col}' does not exist in table '{table_name}'. Valid columns: {', '.join(sorted(valid))}")
        return errors

    def generate_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL based on the query and context, with validation and retry."""
        if "error" in state:
            return state

        query = state['query']
        context = state.get('relevant_context', [])
        context_str = "\n".join([f"- {doc['text']}" for doc in context])
        schema = self.schema
        few_shot = self._build_few_shot_section(query)

        prompt = f"""Generate a SQL query to answer this question:

Question: {query}

Available schema context (ONLY use tables and columns listed here):
{context_str}
{few_shot}

STRICT SQL RULES:
1. ONLY use table names and column names that appear in the schema context above. Do NOT invent or assume any column names.
2. Always use {schema}.table_name format for all table references.
3. Use lowercase table and column names.
4. Do NOT use 'USE DATABASE' statements.
5. Do NOT nest aggregate functions (AVG, SUM, COUNT, etc.) — use subqueries or CTEs instead.
6. Generate valid Amazon Redshift SQL syntax.
7. Generate ONLY SELECT queries — no INSERT, UPDATE, DELETE, DROP, or DDL.
8. When joining tables, use the relationships specified in the context.
9. If the question asks about a concept, match it to the correct column using the business descriptions in parentheses.

Generate ONLY the SQL query without any explanation.
"""

        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                sql = self.bedrock.invoke_model(prompt, temperature=0.1)
                sql = sql.replace('```sql', '').replace('```', '').strip()
                sql_lines = [line for line in sql.split('\n') if not line.strip().upper().startswith('USE DATABASE')]
                sql = '\n'.join(sql_lines).strip()

                if BLOCKED_SQL_PATTERNS.search(sql):
                    return {
                        **state,
                        "error": f"SQL validation failed: only SELECT queries are allowed. Generated: {sql[:100]}",
                        "steps_completed": state.get("steps_completed", []) + ["generate_sql_blocked"]
                    }

                # Validate column references
                col_errors = self._validate_sql_columns(sql, context)
                if col_errors and attempt < max_attempts - 1:
                    # Retry with correction feedback
                    error_feedback = "\n".join(col_errors)
                    prompt = f"""The previous SQL query had invalid column references:

{error_feedback}

Original question: {query}

Available schema context (ONLY use tables and columns listed here):
{context_str}
{few_shot}

STRICT RULES: ONLY use column names from the schema context above. Fix the query.

Generate ONLY the corrected SQL query without any explanation.
"""
                    continue

                return {
                    **state,
                    "generated_sql": sql,
                    "sql_validation_errors": col_errors,
                    "steps_completed": state.get("steps_completed", []) + ["generate_sql"]
                }
            except Exception as e:
                return {
                    **state,
                    "error": f"Error in generate_sql: {str(e)}",
                    "steps_completed": state.get("steps_completed", []) + ["generate_sql_error"]
                }

        return {**state, "error": "SQL generation failed after retries", "steps_completed": state.get("steps_completed", []) + ["generate_sql_failed"]}

    def analyze_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query results and provide an answer."""
        if "error" in state:
            return state

        query = state['query']
        sql = state.get('generated_sql', '')
        results = state.get('query_results', [])

        if not results:
            return {
                **state,
                "analysis": "No results found for this query.",
                "steps_completed": state.get("steps_completed", []) + ["analyze_results"]
            }

        results_str = "\n".join([str(row) for row in results[:20]])
        if len(results) > 20:
            results_str += f"\n... and {len(results) - 20} more rows"

        column_names = state.get('column_names', [])
        col_header = f"Columns: {', '.join(column_names)}\n" if column_names else ""

        prompt = f"""You are a data analyst. Analyze these query results to answer the user's question.

Question: {query}

SQL Query:
{sql}

{col_header}Query Results ({len(results)} total rows, showing first 20):
{results_str}

Provide your analysis in this structure:
1. **Direct Answer**: A one-sentence answer to the question
2. **Key Findings**: 3-5 bullet points highlighting the most important patterns, rankings, or numbers from the data
3. **Notable Observations**: Any interesting trends, outliers, or business implications an analyst should be aware of

Use specific numbers from the results. Format currency values with $ and commas. Keep it concise and actionable.
"""

        try:
            analysis = self.bedrock.invoke_model(prompt)
            return {
                **state,
                "analysis": analysis.strip(),
                "steps_completed": state.get("steps_completed", []) + ["analyze_results"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in analyze_results: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["analyze_results_error"]
            }

    def handle_error(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors in the workflow."""
        error = state.get('error', 'Unknown error')

        return {
            **state,
            "error_handled": True,
            "friendly_error": f"Sorry, an error occurred: {error}. Please try rephrasing your question.",
            "steps_completed": state.get("steps_completed", []) + ["handle_error"]
        }

    def execute(self, query: str, execute_query_func=None) -> Dict[str, Any]:
        """Execute the analysis workflow."""
        state = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "steps_completed": []
        }

        # Step 1: Retrieve context
        state = self.retrieve_context(state)

        # Step 2: Generate SQL
        if "error" not in state:
            state = self.generate_sql(state)

        # Step 3: Execute SQL
        if "generated_sql" in state and "error" not in state and execute_query_func:
            try:
                start_time = datetime.now()
                results, column_names = execute_query_func(state["generated_sql"])
                execution_time = (datetime.now() - start_time).total_seconds()

                state["query_results"] = results
                state["column_names"] = column_names
                state["execution_time"] = execution_time

                # Step 4: Analyze results
                state = self.analyze_results(state)

            except Exception as e:
                state["error"] = f"Error executing SQL: {str(e)}"
                state = self.handle_error(state)
        elif "error" in state:
            state = self.handle_error(state)

        return state
