#!/bin/bash
# Deploy fix and clear state

EC2_IP="107.22.128.25"
EC2_USER="ec2-user"
EC2_PATH="/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql"

echo "🚀 Deploying fix..."

# Copy file
scp app_wizard.py ${EC2_USER}@${EC2_IP}:${EC2_PATH}/ || exit 1

# Deploy and clear state
ssh ${EC2_USER}@${EC2_IP} << 'ENDSSH'
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql

# Clear old state
rm -rf ~/.genai_sales_analyst/

# Deploy new app
cp app_wizard.py app.py

# Kill and restart
pkill -f streamlit
nohup streamlit run app.py > /dev/null 2>&1 &

echo "✅ Deployed and restarted!"
ENDSSH

echo ""
echo "✅ Done! App should now start fresh with 3 options."
echo "Access at: http://${EC2_IP}:8501"
