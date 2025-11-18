#!/bin/bash
# Deploy profile-enabled app to EC2

# Configuration
EC2_USER="ec2-user"
EC2_IP="$1"  # Pass as first argument
EC2_PATH="/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql"

if [ -z "$EC2_IP" ]; then
    echo "Usage: ./deploy_to_ec2.sh <EC2_IP_ADDRESS>"
    echo "Example: ./deploy_to_ec2.sh 107.22.128.25"
    exit 1
fi

echo "🚀 Deploying to EC2: $EC2_IP"
echo ""

# Copy files
echo "📦 Copying files..."
scp app_with_profiles.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/ || exit 1
scp src/utils/profile_manager.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/src/utils/ || exit 1
scp src/utils/setup_wizard.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/src/utils/ || exit 1

echo ""
echo "✅ Files copied successfully!"
echo ""
echo "📝 Next steps:"
echo "1. SSH to EC2: ssh ${EC2_USER}@${EC2_IP}"
echo "2. Backup current app: cd ${EC2_PATH} && cp app.py app_backup.py"
echo "3. Replace app: mv app_with_profiles.py app.py"
echo "4. Run: streamlit run app.py"
echo ""
echo "Or run this command:"
echo "ssh ${EC2_USER}@${EC2_IP} 'cd ${EC2_PATH} && cp app.py app_backup.py && mv app_with_profiles.py app.py && streamlit run app.py'"
