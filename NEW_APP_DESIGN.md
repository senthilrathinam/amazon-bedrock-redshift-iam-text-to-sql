# New App Design - Setup Wizard Approach

## Overview
The app will now have a proper setup flow with 3 options and manual control over each step.

## User Flow

### Home Page (First Time)
```
┌─────────────────────────────────────────────────────────┐
│  Welcome to GenAI Sales Analyst! 🚀                     │
│                                                          │
│  Choose your setup option:                              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Option 1: Create New Redshift Cluster            │  │
│  │ • Creates sales-analyst-cluster                  │  │
│  │ • Loads Northwind sample data                    │  │
│  │ • Uses credentials from .env                     │  │
│  │ [Create New Cluster]                             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Option 2: Load Northwind to Existing Cluster    │  │
│  │ • Connect to your cluster                        │  │
│  │ • Load Northwind sample data                     │  │
│  │ [Configure Cluster]                              │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Option 3: Use Existing Data                      │  │
│  │ • Point to your existing database/schema         │  │
│  │ • No data loading needed                         │  │
│  │ [Configure Connection]                           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### After Setup Choice

#### Option 1 Flow:
```
Step 1: Confirm Creation
  ├─ Show: Cluster will be created with these settings
  ├─ Estimated time: 10 minutes
  └─ [Start Creation] [Cancel]

Step 2: Creating Cluster (Progress Bar)
  ├─ Creating Redshift cluster... ⏳
  ├─ Creating bastion host... ⏳
  └─ Establishing connection... ⏳

Step 3: Load Data
  ├─ Cluster ready! ✅
  ├─ [Load Northwind Data] (manual button)
  └─ Status: Not loaded

Step 4: Index Schema
  ├─ Data loaded! ✅
  ├─ [Index for AI Queries] (manual button)
  └─ Status: Not indexed

Step 5: Ready
  └─ ✅ Ready to query!
```

#### Option 2 Flow:
```
Step 1: Enter Cluster Details
  ├─ Cluster Endpoint: [input]
  ├─ Database: [input]
  ├─ Username: [input]
  ├─ Password: [input]
  └─ [Test Connection]

Step 2: Connection Successful
  ├─ Connected to: cluster-name ✅
  ├─ Check if Northwind exists
  └─ Status: Not found

Step 3: Load Data
  ├─ [Load Northwind Data] (manual button)
  └─ Progress bar when loading

Step 4: Index Schema
  ├─ Data loaded! ✅
  ├─ [Index for AI Queries] (manual button)
  └─ Status: Not indexed

Step 5: Ready
  └─ ✅ Ready to query!
```

#### Option 3 Flow:
```
Step 1: Enter Connection Details
  ├─ Cluster Endpoint: [input]
  ├─ Database: [input]
  ├─ Schema: [input]
  ├─ Username: [input]
  ├─ Password: [input]
  └─ [Test Connection]

Step 2: Connection Successful
  ├─ Connected to: cluster-name ✅
  ├─ Found tables: 15 ✅
  └─ [Continue]

Step 3: Index Schema
  ├─ [Index for AI Queries] (manual button)
  └─ Progress: Indexing 15 tables...

Step 4: Ready
  └─ ✅ Ready to query!
```

## State Management

Store setup state in `~/.genai_sales_analyst/setup_state.json`:

```json
{
  "setup_complete": false,
  "setup_option": null,  // 1, 2, or 3
  "cluster_created": false,
  "data_loaded": false,
  "schema_indexed": false,
  "connection": {
    "host": "",
    "database": "",
    "schema": "",
    "user": ""
  }
}
```

## Prevent Re-execution

- **Cluster creation**: Check if `cluster_created: true` → Show "Already created" message
- **Data loading**: Check if `data_loaded: true` → Show "Already loaded" message
- **Schema indexing**: Check if `schema_indexed: true` → Show "Already indexed" message

## UI Components

### Setup Status Card (Always Visible)
```
┌─────────────────────────────────┐
│ 📊 Setup Status                 │
├─────────────────────────────────┤
│ ✅ Cluster: Connected           │
│ ✅ Data: Loaded (Northwind)     │
│ ✅ AI: Indexed (92 columns)     │
│                                 │
│ [Reset Setup]                   │
└─────────────────────────────────┘
```

### Manual Control Buttons
- Each step has explicit button
- No automatic execution
- Clear progress indicators
- Can skip steps if already done

## Key Improvements

1. **No Auto-execution**: Nothing happens on page load
2. **Manual Control**: User clicks buttons for each step
3. **State Persistence**: Remembers what's done
4. **Prevent Duplicates**: Won't recreate/reload if already done
5. **Clear Progress**: Visual feedback for each step
6. **Fast Refresh**: Page loads instantly, no waiting

## Implementation Files

1. `app_wizard.py` - New main app with wizard
2. `src/utils/setup_state.py` - State management
3. `src/utils/setup_wizard_v2.py` - Enhanced wizard UI
4. `src/utils/cluster_creator.py` - Cluster creation logic
5. `src/utils/data_loader.py` - Northwind data loading
6. `src/utils/schema_indexer.py` - AI indexing logic

Ready to implement?
