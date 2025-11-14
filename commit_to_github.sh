#!/bin/bash
# Script to rename project and commit to new GitHub repo

set -e

# Configuration
OLD_DIR="amazon-bedrock-amazon-redshift-text-to-sql-poc"
NEW_DIR="amazon-bedrock-redshift-iam-text-to-sql"
GITHUB_USER="senthilrathinam"
REPO_NAME="amazon-bedrock-redshift-iam-text-to-sql"

echo "🚀 Setting up new GitHub repository..."

# Step 1: Navigate to parent directory
cd ..

# Step 2: Copy to new directory with new name
echo "📁 Creating new directory: $NEW_DIR"
cp -r "$OLD_DIR" "$NEW_DIR"
cd "$NEW_DIR"

# Step 3: Clean up any existing git history
echo "🧹 Cleaning up old git history..."
rm -rf .git

# Step 4: Initialize new git repository
echo "📦 Initializing new git repository..."
git init
git branch -M main

# Step 5: Create .gitignore if not exists
echo "📝 Creating .gitignore..."
cat > .gitignore << 'EOF'
# Python
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
EOF

# Step 6: Update README with IAM authentication info
echo "📄 Updating README..."
cat > README_IAM.md << 'EOF'
# Amazon Bedrock & Amazon Redshift Sales Analyst POC (IAM Role Authentication)

**Enhanced version with IAM role-based authentication for EC2 deployment**

## Key Differences from Original

This version is optimized for **EC2 deployment** with **IAM role authentication**:

- ✅ **No AWS credentials needed** - Uses EC2 IAM role
- ✅ **More secure** - No access keys or tokens in configuration
- ✅ **Simpler setup** - Automatic credential management
- ✅ **Production-ready** - Follows AWS security best practices

## Quick Start

### Prerequisites
1. EC2 instance (t3.medium or larger, 30GB storage)
2. IAM permissions to create roles and attach to EC2

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

### Configuration

Only Redshift connection details needed in `.env`:
```bash
AWS_REGION=us-east-1
REDSHIFT_HOST=localhost
REDSHIFT_PORT=5439
REDSHIFT_DATABASE=sales_analyst
REDSHIFT_USER=admin
REDSHIFT_PASSWORD=Awsuser123$
```

No AWS credentials required!

## Architecture

This version uses:
- **IAM Role** for AWS service authentication
- **EC2 Instance Profile** for automatic credential management
- **Session Manager** for secure Redshift access
- **Amazon Bedrock** for AI/ML capabilities

## Original Documentation

For detailed information about the application functionality, see the original README.md

## License

This project is licensed under the MIT-0 License.
EOF

# Step 7: Add all files
echo "➕ Adding files to git..."
git add .

# Step 8: Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: IAM role-based authentication version

- Removed explicit AWS credential requirements
- Added IAM role authentication support
- Optimized for EC2 deployment
- Enhanced security with instance profiles
- Automated setup scripts for IAM configuration"

# Step 9: Create GitHub repository and push
echo "🌐 Creating GitHub repository..."
echo ""
echo "Please run these commands to create and push to GitHub:"
echo ""
echo "# Create the repository on GitHub (requires GitHub CLI)"
echo "gh repo create $GITHUB_USER/$REPO_NAME --public --source=. --remote=origin"
echo ""
echo "# Or manually create at: https://github.com/new"
echo "# Then run:"
echo "git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
echo "git push -u origin main"
echo ""
echo "✅ Repository prepared at: $(pwd)"
echo "📁 New directory name: $NEW_DIR"

# Step 10: Show next steps
cat << 'EOF'

🎉 Setup Complete!

Next Steps:
1. Create repository on GitHub:
   - Go to: https://github.com/new
   - Repository name: amazon-bedrock-redshift-iam-text-to-sql
   - Description: Amazon Bedrock & Redshift Text-to-SQL with IAM Role Authentication
   - Make it Public
   - Click "Create repository"

2. Push your code:
   git remote add origin https://github.com/senthilrathinam/amazon-bedrock-redshift-iam-text-to-sql.git
   git push -u origin main

3. Update repository settings:
   - Add topics: aws, bedrock, redshift, iam, text-to-sql, generative-ai
   - Add description
   - Enable Issues and Discussions

EOF
