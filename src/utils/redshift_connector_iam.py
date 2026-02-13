"""
Redshift connector with IAM role authentication.
"""
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

_pool = None

def _get_pool():
    global _pool
    if _pool is None or _pool.closed:
        host = os.getenv('REDSHIFT_HOST', 'localhost')
        if host == 'localhost':
            host = '127.0.0.1'
        _pool = pool.SimpleConnectionPool(
            1, 10,
            host=host,
            port=os.getenv('REDSHIFT_PORT', '5439'),
            database=os.getenv('REDSHIFT_DATABASE', 'sales_analyst'),
            user=os.getenv('REDSHIFT_USER', 'admin'),
            password=os.getenv('REDSHIFT_PASSWORD'),
            connect_timeout=30,
            sslmode=os.getenv('REDSHIFT_SSL_MODE', 'require')
        )
    return _pool

def _reset_pool():
    global _pool
    try:
        if _pool and not _pool.closed:
            _pool.closeall()
    except:
        pass
    _pool = None

def get_redshift_connection():
    password = os.getenv('REDSHIFT_PASSWORD')
    if not password:
        raise ValueError("REDSHIFT_PASSWORD must be set in .env file")
    return _get_pool().getconn()

def execute_query(query, params=None):
    conn = None
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    except psycopg2.OperationalError:
        # Stale connection — reset pool and retry once
        if conn:
            try:
                _get_pool().putconn(conn, close=True)
            except:
                pass
            conn = None
        _reset_pool()
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        return results
    finally:
        if conn:
            try:
                _get_pool().putconn(conn)
            except:
                try:
                    conn.close()
                except:
                    pass

def get_available_databases():
    try:
        return [r[0] for r in execute_query("SELECT datname FROM pg_database WHERE datistemplate = false")]
    except Exception as e:
        print(f"Error getting databases: {e}")
        return []

def get_available_schemas():
    try:
        return [r[0] for r in execute_query("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
        """)]
    except Exception as e:
        print(f"Error getting schemas: {e}")
        return []

def get_available_tables(schema_name=None):
    try:
        if schema_name:
            return [r[0] for r in execute_query(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                (schema_name,)
            )]
        else:
            results = execute_query("""
                SELECT table_schema, table_name FROM information_schema.tables 
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog') AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name
            """)
            tables = {}
            for schema, table in results:
                tables.setdefault(schema, []).append(table)
            return tables
    except Exception as e:
        print(f"Error getting tables: {e}")
        return [] if schema_name else {}

def get_table_columns(schema_name, table_name):
    try:
        return [{'name': r[0], 'type': r[1], 'nullable': r[2] == 'YES', 'default': r[3]} for r in execute_query(
            "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (schema_name, table_name)
        )]
    except Exception as e:
        print(f"Error getting table columns: {e}")
        return []

def test_connection():
    try:
        result = execute_query("SELECT 1")
        return result[0][0] == 1
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False


def execute_query_with_columns(query):
    """Execute query and return (results, column_names) tuple."""
    conn = None
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        results = cursor.fetchall()
        cursor.close()
        return results, column_names
    except psycopg2.OperationalError:
        if conn:
            try:
                _get_pool().putconn(conn, close=True)
            except:
                pass
            conn = None
        _reset_pool()
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        column_names = [desc[0] for desc in cursor.description] if cursor.description else []
        results = cursor.fetchall()
        cursor.close()
        return results, column_names
    finally:
        if conn:
            try:
                _get_pool().putconn(conn)
            except:
                try:
                    conn.close()
                except:
                    pass
