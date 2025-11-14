#!/usr/bin/env python3
"""
Enhanced debugging for Northwind setup failures.
"""
import sys
sys.path.append('src')

from utils.northwind_bootstrapper import create_northwind_schema
from utils.redshift_connector import get_redshift_connection
import traceback

def debug_northwind_creation():
    """Debug the exact failure point in Northwind creation."""
    try:
        print("🔍 Testing Northwind schema creation step by step...")
        
        # Step 1: Test connection
        print("Step 1: Testing connection...")
        conn = get_redshift_connection()
        cursor = conn.cursor()
        print("✅ Connection successful")
        
        # Step 2: Check current permissions
        print("Step 2: Checking permissions...")
        cursor.execute("SELECT has_database_privilege(current_user, current_database(), 'CREATE')")
        can_create = cursor.fetchone()[0]
        print(f"Can create objects: {can_create}")
        
        # Step 3: Try schema creation with detailed error
        print("Step 3: Attempting schema creation...")
        try:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS northwind")
            conn.commit()
            print("✅ Schema creation successful")
        except Exception as schema_error:
            print(f"❌ Schema creation failed: {schema_error}")
            print(f"Error code: {schema_error.pgcode if hasattr(schema_error, 'pgcode') else 'Unknown'}")
            return False
        
        # Step 4: Verify schema exists
        print("Step 4: Verifying schema...")
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'northwind'")
        schema_exists = cursor.fetchone()
        if schema_exists:
            print("✅ Schema verified")
        else:
            print("❌ Schema not found after creation")
            return False
        
        # Step 5: Test table creation
        print("Step 5: Testing table creation...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS northwind.test_table (
                    id INTEGER,
                    name VARCHAR(50)
                )
            """)
            conn.commit()
            print("✅ Table creation successful")
            
            # Cleanup
            cursor.execute("DROP TABLE northwind.test_table")
            conn.commit()
        except Exception as table_error:
            print(f"❌ Table creation failed: {table_error}")
            return False
        
        conn.close()
        print("🎉 All Northwind setup steps successful!")
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_northwind_creation()
