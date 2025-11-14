#!/usr/bin/env python3
"""
Quick fix script for Northwind database setup issues.
"""
import sys
sys.path.append('src')

from utils.redshift_connector import get_redshift_connection
import traceback

def fix_northwind_setup():
    """Fix common Northwind setup issues."""
    try:
        print("🔧 Attempting to fix Northwind setup issues...")
        
        conn = get_redshift_connection()
        cursor = conn.cursor()
        
        # Fix 1: Clean up any partial setup
        print("Step 1: Cleaning up partial setup...")
        try:
            cursor.execute("DROP SCHEMA IF EXISTS northwind CASCADE")
            conn.commit()
            print("✅ Cleaned up existing schema")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
        
        # Fix 2: Create schema with explicit permissions
        print("Step 2: Creating schema with proper permissions...")
        cursor.execute("CREATE SCHEMA northwind")
        cursor.execute("GRANT ALL ON SCHEMA northwind TO current_user")
        conn.commit()
        print("✅ Schema created with permissions")
        
        # Fix 3: Test with a simple table
        print("Step 3: Testing table creation...")
        cursor.execute("""
            CREATE TABLE northwind.test_connection (
                id INTEGER,
                created_at TIMESTAMP DEFAULT GETDATE()
            )
        """)
        cursor.execute("INSERT INTO northwind.test_connection (id) VALUES (1)")
        cursor.execute("SELECT COUNT(*) FROM northwind.test_connection")
        count = cursor.fetchone()[0]
        print(f"✅ Test table created and verified ({count} rows)")
        
        # Cleanup test table
        cursor.execute("DROP TABLE northwind.test_connection")
        conn.commit()
        
        conn.close()
        print("🎉 Northwind setup fixed! Try running the app again.")
        return True
        
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_northwind_setup()
