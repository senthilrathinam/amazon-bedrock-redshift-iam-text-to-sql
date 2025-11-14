#!/usr/bin/env python3
"""
Setup new GitHub repository with IAM authentication version.
"""
import os
import shutil
import subprocess

def setup_new_repo():
    """Setup new repository with renamed directory."""
    
    OLD_DIR = "amazon-bedrock-amazon-redshift-text-to-sql-poc"
    NEW_DIR = "amazon-bedrock-redshift-iam-text-to-sql"
    GITHUB_USER = "senthilrathinam"
    REPO_NAME = "amazon-bedrock-redshift-iam-text-to-sql"
    
    print("🚀 Setting up new GitHub repository...\n")
    
    # Get current directory
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    new_repo_path = os.path.join(parent_dir, NEW_DIR)
    
    # Step 1: Copy to new directory
    print(f"📁 Creating new directory: {NEW_DIR}")
    if os.path.exists(new_repo_path):
        print(f"⚠️  Directory {NEW_DIR} already exists. Remove it? (y/n)")
        response = input().strip().lower()
        if response == 'y':
            shutil.rmtree(new_repo_path)
        else:
            print("❌ Aborted")
            return False
    
    shutil.copytree(current_dir, new_repo_path)
    os.chdir(new_repo_path)
    print(f"✅ Created: {new_repo_path}\n")
    
    # Step 2: Clean up old git history
    print("🧹 Cleaning up old git history...")
    if os.path.exists('.git'):
        shutil.rmtree('.git')
    
    # Step 3: Initialize new git repository
    print("📦 Initializing new git repository...")
    subprocess.run(['git', 'init'], check=True)
    subprocess.run(['git', 'branch', '-M', 'main'], check=True)
    
    # Step 4: Create enhanced .gitignore
    print("📝 Creating .gitignore...")
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
.venv/
venv/
ENV/
env/

# Environment variables
.env
.env.backup
*.backup

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Application specific
*.db
*.sqlite
*.sqlite3
faiss_index/
generated-diagrams/

# Logs
*.log
"""
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    
    # Step 5: Create IAM-focused README
    print("📄 Creating README_IAM.md...")
    readme_content = """# Amazon Bedrock & Amazon Redshift Sales Analyst (IAM Authentication)

**Enhanced version with IAM role-based authentication for secure EC2 deployment**

## 🎯 Key Features

- ✅ **IAM Role Authentication** - No AWS credentials needed
- ✅ **EC2 Optimized** - Designed for production EC2 deployment
- ✅ **Enhanced Security** - No access keys or tokens in configuration
- ✅ **Auto Setup** - One-command IAM role creation and attachment
- ✅ **Production Ready** - Follows AWS security best practices

## 🚀 Quick Start

### Prerequisites
- EC2 instance (t3.medium or larger, 30GB storage)
- IAM permissions to create roles and attach to EC2
- Python 3.11+

### Installation

```bash
# Clone the repository
git clone https://github.com/senthilrathinam/amazon-bedrock-redshift-iam-text-to-sql.git
cd amazon-bedrock-redshift-iam-text-to-sql

# Run complete setup (creates IAM role, attaches to EC2, migrates files)
python setup_iam_complete.py

# Start the application
streamlit run app.py
```

## 🔧 Configuration

Only Redshift connection details needed in `.env`:

```bash
AWS_REGION=us-east-1
REDSHIFT_HOST=localhost
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=sales_analyst
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=Awsuser123$
```

**No AWS credentials required!** The application uses the EC2 instance's IAM role.

## 🏗️ Architecture

```
EC2 Instance (with IAM Role)
    ↓
IAM Role → Bedrock API (Claude 3 Sonnet, Titan Embed)
    ↓
SSM Tunnel → Bastion Host → Private Redshift Cluster
```

## 📋 What's Different from Original?

| Feature | Original | IAM Version |
|---------|----------|-------------|
| Authentication | Access Keys + Secret + Token | IAM Role |
| Credential Management | Manual .env file | Automatic |
| Security | Credentials in files | Instance Profile |
| Token Expiration | Yes (1-12 hours) | No expiration |
| Setup Complexity | Manual credential rotation | One-time setup |

## 🔐 IAM Permissions

The setup script creates a role with these permissions:
- `bedrock:InvokeModel` - For AI/ML operations
- `redshift:*` - For cluster management
- `ec2:*` - For bastion host creation
- `ssm:*` - For secure tunneling

## 📚 Documentation

For detailed application functionality, see [README.md](README.md)

## 🤝 Contributing

Contributions welcome! Please open an issue or submit a PR.

## 📄 License

MIT-0 License - See LICENSE file for details.

## 🙏 Credits

Based on the original [Amazon Bedrock Redshift Text-to-SQL POC](https://github.com/aws-samples/genai-quickstart-pocs)

Enhanced with IAM role authentication by Senthil Kamala Rathinam
"""
    with open('README_IAM.md', 'w') as f:
        f.write(readme_content)
    
    # Step 6: Add all files
    print("➕ Adding files to git...")
    subprocess.run(['git', 'add', '.'], check=True)
    
    # Step 7: Create initial commit
    print("💾 Creating initial commit...")
    commit_message = """Initial commit: IAM role-based authentication version

- Removed explicit AWS credential requirements
- Added IAM role authentication support
- Optimized for EC2 deployment
- Enhanced security with instance profiles
- Automated setup scripts for IAM configuration
- Added comprehensive documentation for IAM setup"""
    
    subprocess.run(['git', 'commit', '-m', commit_message], check=True)
    
    # Step 8: Show next steps
    print("\n" + "="*60)
    print("🎉 Repository prepared successfully!")
    print("="*60)
    print(f"\n📁 New repository location: {new_repo_path}")
    print(f"📝 Repository name: {REPO_NAME}\n")
    
    print("Next Steps:\n")
    print("1️⃣  Create repository on GitHub:")
    print(f"   https://github.com/new")
    print(f"   Repository name: {REPO_NAME}")
    print(f"   Description: Amazon Bedrock & Redshift Text-to-SQL with IAM Role Authentication")
    print(f"   Make it Public\n")
    
    print("2️⃣  Push your code:")
    print(f"   cd {new_repo_path}")
    print(f"   git remote add origin https://github.com/{GITHUB_USER}/{REPO_NAME}.git")
    print(f"   git push -u origin main\n")
    
    print("3️⃣  Or use GitHub CLI (if installed):")
    print(f"   cd {new_repo_path}")
    print(f"   gh repo create {GITHUB_USER}/{REPO_NAME} --public --source=. --remote=origin --push\n")
    
    print("4️⃣  Add repository topics:")
    print("   aws, bedrock, redshift, iam, text-to-sql, generative-ai, claude, python\n")
    
    return True

if __name__ == "__main__":
    try:
        success = setup_new_repo()
        if success:
            print("✅ Setup completed successfully!")
        else:
            print("❌ Setup failed")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
