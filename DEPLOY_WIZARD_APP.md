# Deploy New Wizard-Based App

## ✅ What's Ready

1. **app_wizard.py** - Complete new app with wizard
2. **src/utils/setup_state.py** - State management
3. **Clean AWS environment** - Cluster and bastion deleted

## 🚀 Quick Deploy

### Step 1: Copy Files to EC2

```bash
cd /home/skamalar/tests/genai-quickstart-pocs/genai-quickstart-pocs-python/amazon-bedrock-redshift-iam-text-to-sql

# Copy new files
scp app_wizard.py ec2-user@107.22.128.25:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/
scp src/utils/setup_state.py ec2-user@107.22.128.25:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/src/utils/
```

### Step 2: Deploy on EC2

```bash
# SSH to EC2
ssh ec2-user@107.22.128.25

# Navigate to app directory
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql

# Backup old app
cp app.py app_old_backup.py

# Use new wizard app
cp app_wizard.py app.py

# Run the app
streamlit run app.py
```

## 🎯 What You'll See

### First Launch - Home Page
```
┌─────────────────────────────────────────────┐
│  🚀 GenAI Sales Analyst Setup               │
│  Choose how you want to get started:        │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Option 1 │  │ Option 2 │  │ Option 3 │ │
│  │ Create   │  │ Load to  │  │ Use      │ │
│  │ New      │  │ Existing │  │ Existing │ │
│  │ Cluster  │  │ Cluster  │  │ Data     │ │
│  │          │  │          │  │          │ │
│  │ [Select] │  │ [Select] │  │ [Select] │ │
│  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────┘
```

### Option 1 Flow
```
Step 1: Create Redshift Cluster
  [🚀 Create Cluster] ← Click to start
  
  (After clicking)
  ✅ Cluster created: sales-analyst-cluster

Step 2: Load Northwind Data
  [📦 Load Northwind Data] ← Click to load
  
  (After clicking)
  ✅ Northwind data loaded

Step 3: Index for AI Queries
  [🤖 Index Schema] ← Click to index
  
  (After clicking)
  ✅ Schema indexed and ready

🎉 Setup complete!
[Start Using App]
```

### Option 2 Flow
```
Step 1: Enter Cluster Details
  Cluster Endpoint: [input]
  Database: [input]
  Username: [input]
  Password: [input]
  [Test Connection]
  
  ✅ Connection successful!

Step 2: Load Northwind Data
  [📦 Load Northwind Data]
  
  ✅ Northwind data loaded

Step 3: Index for AI Queries
  [🤖 Index Schema]
  
  ✅ Schema indexed and ready

🎉 Setup complete!
[Start Using App]
```

### Option 3 Flow
```
Step 1: Enter Connection Details
  Cluster Endpoint: [input]
  Database: [input]
  Schema: [input]
  Username: [input]
  Password: [input]
  [Test Connection]
  
  ✅ Connection successful! Found 15 tables

Step 2: Index for AI Queries
  [🤖 Index Schema]
  
  ✅ Schema indexed and ready

🎉 Setup complete!
[Start Using App]
```

## ✨ Key Features

1. **No Auto-Execution**
   - Page loads instantly
   - Nothing happens until you click buttons
   - Full manual control

2. **Prevents Re-Execution**
   - If cluster already created → Shows "✅ Cluster created"
   - If data already loaded → Shows "✅ Data loaded"
   - If schema already indexed → Shows "✅ Schema indexed"
   - Won't recreate/reload unnecessarily

3. **State Persistence**
   - Stored in `~/.genai_sales_analyst/setup_state.json`
   - Survives page refreshes
   - Can reset with "Reset Setup" button

4. **Fast Page Loads**
   - No waiting on refresh
   - Instant UI response
   - Progress only when you click

## 🧪 Testing Scenarios

### Test 1: Fresh Install (Option 1)
1. Open app → See 3 options
2. Click "Select Option 1"
3. Click "Create Cluster" → Wait ~10 min
4. Click "Load Northwind Data" → Wait ~2 min
5. Click "Index Schema" → Wait ~30 sec
6. Click "Start Using App" → Query interface

### Test 2: Existing Cluster (Option 2)
1. Open app → See 3 options
2. Click "Select Option 2"
3. Enter cluster details → Click "Test Connection"
4. Click "Load Northwind Data"
5. Click "Index Schema"
6. Click "Start Using App"

### Test 3: Your Own Data (Option 3)
1. Open app → See 3 options
2. Click "Select Option 3"
3. Enter connection + schema → Click "Test Connection"
4. Click "Index Schema"
5. Click "Start Using App"

### Test 4: Refresh Behavior
1. Complete any option above
2. Refresh browser
3. Should show main app immediately (no re-setup)

### Test 5: Reset and Retry
1. In main app, click "Reset Setup" in sidebar
2. Returns to option selection
3. Can choose different option

## 📁 Files Modified

```
New Files:
├── app_wizard.py (new main app)
└── src/utils/setup_state.py (state management)

Backup:
└── app_old_backup.py (your old app)
```

## 🔄 Rollback

If you want to go back to the old app:
```bash
cp app_old_backup.py app.py
streamlit run app.py
```

## 🎉 Ready to Test!

The app is now ready with:
✅ 3 setup options
✅ Manual control for each step
✅ No auto-execution
✅ Prevents re-execution
✅ Fast page loads
✅ Clean wizard interface

Deploy and test!
