"""
Redshift connector with IAM role authentication.
"""
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# Connection pool (min 1, max 5 connections)
_pool = None

def _get_pool():
    global _pool
    if _pool is None or _pool.closed:
        host = os.getenv('REDSHIFT_HOST', 'localhost')
        if host == 'localhost':
            host = '127.0.0.1'
        _pool = pool.SimpleConnectionPool(
            1, 5,
            host=host,
            port=os.getenv('REDSHIFT_PORT', '5439'),
            database=os.getenv('REDSHIFT_DATABASE', 'sales_analyst'),
            user=os.getenv('REDSHIFT_USER', 'admin'),
            password=os.getenv('REDSHIFT_PASSWORD'),
            connect_timeout=30,
            sslmode=os.getenv('REDSHIFT_SSL_MODE', 'require')
        )
    return _pool

def get_redshift_connection():
    password = os.getenv('REDSHIFT_PASSWORD')
    if not password:
        raise ValueError("REDSHIFT_PASSWORD must be set in .env file")
    return _get_pool().getconn()

def _return_conn(conn, close=False):
    try:
        if close:
            _get_pool().putconn(conn, close=True)
        else:
            _get_pool().putconn(conn)
    except:
        pass

def _reset_pool():
    global _pool
    try:
        if _pool and not _pool.closed:
            _pool.closeall()
    except:
        pass
    _pool = None

def execute_query(query):
    conn = get_redshift_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except psycopg2.OperationalError:
        # Connection went stale (e.g., tunnel restart) — reset pool and retry once
        _return_conn(conn, close=True)
        _reset_pool()
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        _return_conn(conn)
        return results
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise
    finally:
        try:
            cursor.close()
        except:
            pass
        _return_conn(conn)

def get_available_databases():
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        _return_conn(conn)
        return databases
    except Exception as e:
        print(f"Error getting databases: {str(e)}")
        return []

def get_available_schemas():
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name
        """)
        schemas = [row[0] for row in cursor.fetchall()]
        cursor.close()
        _return_conn(conn)
        return schemas
    except Exception as e:
        print(f"Error getting schemas: {str(e)}")
        return []

def get_available_tables(schema_name=None):
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        if schema_name:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """, (schema_name,))
            tables = [row[0] for row in cursor.fetchall()]
        else:
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('information_schema', 'pg_catalog') 
                AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name
            """)
            results = cursor.fetchall()
            tables = {}
            for schema, table in results:
                tables.setdefault(schema, []).append(table)
        cursor.close()
        _return_conn(conn)
        return tables
    except Exception as e:
        print(f"Error getting tables: {str(e)}")
        return [] if schema_name else {}

def get_table_columns(schema_name, table_name):
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema_name, table_name))
        columns = [{'name': r[0], 'type': r[1], 'nullable': r[2] == 'YES', 'default': r[3]} for r in cursor.fetchall()]
        cursor.close()
        _return_conn(conn)
        return columns
    except Exception as e:
        print(f"Error getting table columns: {str(e)}")
        return []

def test_connection():
    try:
        conn = get_redshift_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        _return_conn(conn)
        return result[0] == 1
    except Exception as e:
        print(f"Connection test failed: {str(e)}")
        return False
