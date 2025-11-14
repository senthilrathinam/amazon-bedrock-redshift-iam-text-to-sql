#!/usr/bin/env python3
"""
Fix the tuple indexing error in app.py
"""

def fix_app_py():
    """Fix the tuple indexing issue in app.py"""
    
    # Read the current app.py
    with open('app.py', 'r') as f:
        content = f.read()
    
    # Replace the problematic lines
    old_code = '''                if customer_result and order_result:
                    customers = customer_result[0]['count']
                    orders = order_result[0]['count']'''
    
    new_code = '''                if customer_result and order_result:
                    customers = customer_result[0][0]  # First row, first column
                    orders = order_result[0][0]        # First row, first column'''
    
    # Replace in content
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Write back to file
        with open('app.py', 'w') as f:
            f.write(content)
        
        print("✅ Fixed tuple indexing error in app.py")
        print("Changed customer_result[0]['count'] to customer_result[0][0]")
        print("Changed order_result[0]['count'] to order_result[0][0]")
    else:
        print("❌ Could not find the problematic code to fix")

if __name__ == "__main__":
    fix_app_py()
