"""
LangGraph workflow for the GenAI Sales Analyst application.
"""
from typing import Dict, Any, List, Tuple
import json
import os
import re
from datetime import datetime


# SQL statements that should never be executed
BLOCKED_SQL_PATTERNS = re.compile(
    r'\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|INSERT|UPDATE|GRANT|REVOKE|MERGE)\b',
    re.IGNORECASE
)


class AnalysisWorkflow:
    def __init__(self, bedrock_helper, vector_store, monitor=None):
        self.bedrock = bedrock_helper
        self.vector_store = vector_store
        self.monitor = monitor
        self.schema = os.getenv('REDSHIFT_SCHEMA', 'northwind')
    
    def retrieve_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant context from vector store."""
        query = state['query']
        
        try:
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
            
            # Extract table names for display
            retrieved_tables = [
                doc['metadata']['table'] for doc in similar_docs 
                if doc['metadata'].get('type') == 'table'
            ]
            
            return {
                **state,
                "relevant_context": similar_docs,
                "retrieved_tables": retrieved_tables,
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in retrieve_context: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["retrieve_context_error"]
            }
    
    def generate_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL based on the query and context."""
        if "error" in state:
            return state
            
        query = state['query']
        context = state.get('relevant_context', [])
        context_str = "\n".join([f"- {doc['text']}" for doc in context])
        schema = self.schema
        
        prompt = f"""Generate a SQL query to answer this question:
            
Question: {query}

Relevant context:
{context_str}

IMPORTANT SQL RULES: 
1. Do NOT use 'USE DATABASE' statements
2. Always use schema.table format from the context provided
3. Use lowercase table and column names
4. Do NOT nest aggregate functions (AVG, SUM, COUNT, etc.)
5. Use subqueries or CTEs for complex calculations
6. Generate valid Redshift SQL syntax
7. Generate ONLY SELECT queries - no INSERT, UPDATE, DELETE, DROP, or DDL

Generate ONLY the SQL query without any explanation.
"""
        
        try:
            sql = self.bedrock.invoke_model(prompt, temperature=0.1)
            
            # Clean up markdown fences
            sql = sql.replace('```sql', '').replace('```', '').strip()
            
            # Remove USE DATABASE statements
            sql_lines = [line for line in sql.split('\n') if not line.strip().upper().startswith('USE DATABASE')]
            sql = '\n'.join(sql_lines).strip()
            
            # Fix #3: Validate SQL is read-only
            if BLOCKED_SQL_PATTERNS.search(sql):
                return {
                    **state,
                    "error": f"SQL validation failed: only SELECT queries are allowed. Generated: {sql[:100]}",
                    "steps_completed": state.get("steps_completed", []) + ["generate_sql_blocked"]
                }
            
            return {
                **state,
                "generated_sql": sql,
                "steps_completed": state.get("steps_completed", []) + ["generate_sql"]
            }
        except Exception as e:
            return {
                **state,
                "error": f"Error in generate_sql: {str(e)}",
                "steps_completed": state.get("steps_completed", []) + ["generate_sql_error"]
            }
    
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
        
        results_str = "\n".join([str(row) for row in results[:10]])
        if len(results) > 10:
            results_str += f"\n... and {len(results) - 10} more rows"
        
        prompt = f"""Analyze these query results to answer the user's question:
        
Question: {query}

SQL Query:
{sql}

Query Results (first 10 rows):
{results_str}

Provide a clear, concise analysis that directly answers the question. Include key insights from the data.
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
        
        # Fix #2: Removed understand_query — it was unused
        # Step 1: Retrieve context
        state = self.retrieve_context(state)
        
        # Step 2: Generate SQL
        if "error" not in state:
            state = self.generate_sql(state)
        
        # Step 3: Execute SQL
        if "generated_sql" in state and "error" not in state and execute_query_func:
            try:
                start_time = datetime.now()
                results = execute_query_func(state["generated_sql"])
                execution_time = (datetime.now() - start_time).total_seconds()
                
                state["query_results"] = results
                state["execution_time"] = execution_time
                
                # Step 4: Analyze results
                state = self.analyze_results(state)
                
            except Exception as e:
                state["error"] = f"Error executing SQL: {str(e)}"
                state = self.handle_error(state)
        elif "error" in state:
            state = self.handle_error(state)
        
        return state
