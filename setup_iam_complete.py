#!/usr/bin/env python3
"""
Complete setup script for IAM role authentication.
"""
import subprocess
import sys

def run_setup():
    """Run the complete IAM setup process."""
    
    print("🚀 Complete IAM Role Setup for Bedrock Redshift Analyst\n")
    
    steps = [
        ("1. Setup IAM Role and Attach to EC2", "python setup_iam_role.py"),
        ("2. Migrate Application Files", "python migrate_to_iam.py"),
        ("3. Install Dependencies", "pip install -r requirements.txt"),
    ]
    
    for step_name, command in steps:
        print(f"\n📋 {step_name}")
        print(f"Running: {command}")
        
        try:
            result = subprocess.run(command.split(), capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Success")
                if result.stdout:
                    print(result.stdout)
            else:
                print("❌ Failed")
                if result.stderr:
                    print(result.stderr)
                return False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    print("\n🎉 Setup Complete!")
    print("\nYour application is now configured to use IAM role authentication.")
    print("\nTo start the application:")
    print("streamlit run app.py")
    
    return True

if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)
