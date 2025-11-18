# Deploy Profile-Enabled App

## Files Created

✅ **`app_with_profiles.py`** - Complete app with profile switching
✅ **`src/utils/profile_manager.py`** - Profile management backend
✅ **`src/utils/setup_wizard.py`** - Setup wizard components

## Quick Deploy to EC2

### Step 1: Copy Files

```bash
# From your local machine
cd /home/skamalar/tests/genai-quickstart-pocs/genai-quickstart-pocs-python/amazon-bedrock-redshift-iam-text-to-sql

# Copy to EC2
scp app_with_profiles.py ec2-user@<EC2_IP>:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/
scp src/utils/profile_manager.py ec2-user@<EC2_IP>:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/src/utils/
scp src/utils/setup_wizard.py ec2-user@<EC2_IP>:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/src/utils/
```

### Step 2: Backup and Replace

```bash
# SSH to EC2
ssh ec2-user@<EC2_IP>
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql

# Backup current app
cp app.py app_backup_$(date +%Y%m%d).py

# Replace with new version
mv app_with_profiles.py app.py
```

### Step 3: Run the App

```bash
streamlit run app.py
```

## What You Get

### 1. Profile Switcher in Sidebar
```
🔄 Data Source
Active Profile: [Demo (Northwind) ▼]
📚 Demo Mode
Northwind sample data

➕ Add New Profile
```

### 2. Mode Banner at Top
```
ℹ️  Demo Mode Active - Using Northwind sample data. 
   Switch profiles in the sidebar to use your own data.
```

### 3. Easy Profile Management
- **Add profiles** via sidebar form
- **Switch instantly** with dropdown
- **Auto-reload** metadata when switching
- **Persistent** - saved in ~/.genai_sales_analyst/

## How to Use

### First Time:
1. App starts with "Demo (Northwind)" profile
2. Click "➕ Add New Profile" in sidebar
3. Enter your cluster details:
   - Profile Name: "My Production"
   - Cluster Endpoint: redshift-cluster-amazon-q2...
   - Database: dev
   - Schema: demo
   - Username: awsuser
   - Password: ****
4. Click "Save Profile"

### Switching:
1. Click dropdown: "Active Profile"
2. Select "My Production"
3. App reloads with your data
4. Banner shows: "🏢 Production Mode"

### Adding More Profiles:
- Staging environment
- Different schemas
- Test clusters
- Unlimited profiles!

## Profile Storage

Profiles are saved in:
```
~/.genai_sales_analyst/
├── profiles.json    # All your profiles
└── config.json      # Active profile setting
```

## Features

✅ **Zero .env editing** - All in UI
✅ **Instant switching** - One click
✅ **Visual indicators** - Always know your mode
✅ **Persistent** - Survives restarts
✅ **Secure** - Passwords stored locally
✅ **Multi-environment** - Dev/Staging/Prod

## Troubleshooting

**Profile not switching?**
- Check sidebar shows new profile name
- Refresh browser if needed

**Can't connect to cluster?**
- Verify endpoint is correct
- Check security group allows EC2 IP
- Test credentials manually

**Want to reset?**
```bash
rm -rf ~/.genai_sales_analyst/
# Restart app - will recreate defaults
```

## Next Steps

Want to add:
- Connection testing before saving
- Profile import/export
- Shared team profiles
- First-time setup wizard

Let me know!
