#!/bin/bash
# Deploy wizard-based app to EC2

EC2_IP="107.22.128.25"
EC2_USER="ec2-user"
EC2_PATH="/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql"

echo "🚀 Deploying Wizard App to EC2..."
echo ""

# Copy files
echo "📦 Copying files..."
scp app_wizard.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/ || exit 1
scp src/utils/setup_state.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/src/utils/ || exit 1

echo ""
echo "✅ Files copied!"
echo ""
echo "📝 Next steps:"
echo "1. SSH: ssh ${EC2_USER}@${EC2_IP}"
echo "2. Backup: cd ${EC2_PATH} && cp app.py app_old_backup.py"
echo "3. Deploy: cp app_wizard.py app.py"
echo "4. Run: streamlit run app.py"
echo ""
echo "Or run this one-liner:"
echo "ssh ${EC2_USER}@${EC2_IP} 'cd ${EC2_PATH} && cp app.py app_old_backup.py && cp app_wizard.py app.py && streamlit run app.py'"
