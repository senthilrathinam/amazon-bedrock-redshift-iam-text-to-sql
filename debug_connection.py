#!/usr/bin/env python3
"""
Debug script for Redshift connection and Northwind setup issues.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')
from utils.redshift_connector import get_redshift_connection

def test_connection():
    """Test basic Redshift connection."""
    try:
        print("🔍 Testing Redshift connection...")
        conn = get_redshift_connection()
        cursor = conn.cursor()
        
        # Basic connection test
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Connected to: {version}")
        
        # Check current user and database
        cursor.execute("SELECT current_user, current_database()")
        user_info = cursor.fetchone()
        print(f"✅ User: {user_info[0]}, Database: {user_info[1]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_permissions():
    """Test database permissions."""
    try:
        print("\n🔍 Testing database permissions...")
        conn = get_redshift_connection()
        cursor = conn.cursor()
        
        # Test schema creation
        test_schema = "test_debug_schema"
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {test_schema}")
        print("✅ Can create schemas")
        
        # Test table creation
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {test_schema}.test_table (
                id INTEGER,
                name VARCHAR(50)
            )
        """)
        print("✅ Can create tables")
        
        # Test data insertion
        cursor.execute(f"INSERT INTO {test_schema}.test_table VALUES (1, 'test')")
        print("✅ Can insert data")
        
        # Cleanup
        cursor.execute(f"DROP TABLE {test_schema}.test_table")
        cursor.execute(f"DROP SCHEMA {test_schema}")
        print("✅ Can drop objects")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Permission error: {e}")
        return False

def check_existing_northwind():
    """Check if Northwind already exists."""
    try:
        print("\n🔍 Checking existing Northwind data...")
        conn = get_redshift_connection()
        cursor = conn.cursor()
        
        # Check for existing schema
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'northwind'")
        schema_exists = cursor.fetchone()
        
        if schema_exists:
            print("⚠️  Northwind schema already exists")
            
            # Check tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'northwind'
            """)
            tables = cursor.fetchall()
            print(f"📋 Existing tables: {[t[0] for t in tables]}")
            
            # Check data count
            if tables:
                cursor.execute("SELECT COUNT(*) FROM northwind.orders")
                count = cursor.fetchone()[0]
                print(f"📊 Orders count: {count}")
        else:
            print("✅ No existing Northwind schema found")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error checking existing data: {e}")
        return False

def main():
    """Run all debug tests."""
    print("🚀 Starting Redshift connection debug...\n")
    
    # Load environment
    load_dotenv()
    
    # Check environment variables
    print("🔍 Environment variables:")
    print(f"REDSHIFT_HOST: {os.getenv('REDSHIFT_HOST', 'NOT_SET')}")
    print(f"REDSHIFT_PORT: {os.getenv('REDSHIFT_PORT', 'NOT_SET')}")
    print(f"REDSHIFT_DATABASE: {os.getenv('REDSHIFT_DATABASE', 'NOT_SET')}")
    print(f"REDSHIFT_USER: {os.getenv('REDSHIFT_USER', 'NOT_SET')}")
    print(f"REDSHIFT_PASSWORD: {'SET' if os.getenv('REDSHIFT_PASSWORD') else 'NOT_SET'}")
    
    # Run tests
    tests = [
        ("Connection Test", test_connection),
        ("Permission Test", test_permissions),
        ("Existing Data Check", check_existing_northwind)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n📋 Debug Summary:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! The issue might be in the data loading process.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above for troubleshooting.")

if __name__ == "__main__":
    main()
