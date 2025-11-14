"""
Redshift connector for the GenAI Sales Analyst application.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_redshift_connection():
    """
    Get a connection to Redshift.
    
    Returns:
        Redshift connection object
    """
    # Get credentials from environment variables
    host = os.getenv('REDSHIFT_HOST')
    if not host or host == 'NOT_SET':
        raise Exception("Redshift host not configured yet. Please wait for setup to complete.")
        
    port = os.getenv('REDSHIFT_PORT', '5439')
    database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
    user = os.getenv('REDSHIFT_USER', 'admin')
    password = os.getenv('REDSHIFT_PASSWORD', 'Awsuser123$')
    
    # For localhost connections (SSM tunnel), force IPv4
    if host == 'localhost':
        host = '127.0.0.1'
    
    # Connect to Redshift with timeout
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=30  # Increased timeout for tunnel connections
    )
    
    return conn

def execute_query(query):
    """
    Execute a SQL query on Redshift.
    
    Args:
        query: SQL query to execute
        
    Returns:
        Query results
    """
    conn = get_redshift_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()
