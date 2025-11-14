#!/usr/bin/env python3
"""
Migrate application to use IAM role authentication.
"""
import os
import shutil

def backup_original_files():
    """Backup original files."""
    files_to_backup = [
        'src/bedrock/bedrock_helper.py',
        'src/utils/redshift_connector.py',
        '.env'
    ]
    
    print("📦 Backing up original files...")
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            print(f"✅ Backed up {file_path} to {backup_path}")

def migrate_files():
    """Replace files with IAM role versions."""
    
    migrations = [
        ('src/bedrock/bedrock_helper_iam.py', 'src/bedrock/bedrock_helper.py'),
        ('src/utils/redshift_connector_iam.py', 'src/utils/redshift_connector.py'),
        ('.env.iam', '.env')
    ]
    
    print("\n🔄 Migrating to IAM role authentication...")
    for source, target in migrations:
        if os.path.exists(source):
            shutil.copy2(source, target)
            print(f"✅ Updated {target}")
        else:
            print(f"❌ Source file not found: {source}")

def update_cluster_manager():
    """Update redshift_cluster_manager.py to use IAM helper."""
    
    cluster_manager_path = 'src/utils/redshift_cluster_manager.py'
    
    if not os.path.exists(cluster_manager_path):
        print(f"⚠️  {cluster_manager_path} not found - skipping update")
        return
    
    # Read current content
    with open(cluster_manager_path, 'r') as f:
        content = f.read()
    
    # Add import for IAM helper at the top
    if 'from .aws_client_helper_iam import create_aws_client' not in content:
        # Find the imports section and add our import
        lines = content.split('\n')
        import_added = False
        
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                continue
            else:
                # Insert our import before the first non-import line
                lines.insert(i, 'from .aws_client_helper_iam import create_aws_client')
                import_added = True
                break
        
        if import_added:
            content = '\n'.join(lines)
    
    # Replace boto3.client calls with create_aws_client calls
    replacements = [
        ("boto3.client(\n        'redshift'", "create_aws_client('redshift'"),
        ("boto3.client(\n        'ec2'", "create_aws_client('ec2'"),
        ("boto3.client(\n        'iam'", "create_aws_client('iam'"),
        ("boto3.client(\n        'ssm'", "create_aws_client('ssm'"),
        ("region_name=os.getenv('AWS_REGION', 'us-east-1'),\n        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),\n        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')", "")
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write updated content
    with open(cluster_manager_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {cluster_manager_path} for IAM authentication")

def test_iam_authentication():
    """Test IAM role authentication."""
    try:
        import boto3
        
        # Test STS to verify IAM role
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"\n✅ IAM Authentication Test:")
        print(f"Account: {identity['Account']}")
        print(f"User/Role: {identity['Arn']}")
        
        if 'role' in identity['Arn'].lower():
            print("✅ Using IAM role (recommended)")
        else:
            print("⚠️  Not using IAM role - may still be using access keys")
        
        return True
        
    except Exception as e:
        print(f"\n❌ IAM Authentication Test Failed: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 Migrating to IAM Role Authentication\n")
    
    # Step 1: Backup original files
    backup_original_files()
    
    # Step 2: Migrate files
    migrate_files()
    
    # Step 3: Update cluster manager
    update_cluster_manager()
    
    # Step 4: Test authentication
    if test_iam_authentication():
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Ensure your EC2 instance has the IAM role attached")
        print("2. Run: python setup_iam_role.py (if not done already)")
        print("3. Start the application: streamlit run app.py")
        print("\nNote: AWS credentials are no longer needed in .env file")
    else:
        print("\n⚠️  Migration completed but authentication test failed")
        print("Make sure your EC2 instance has the proper IAM role attached")

if __name__ == "__main__":
    main()
