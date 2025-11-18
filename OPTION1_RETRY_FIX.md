# Option 1 Retry Logic - Fixes Applied

## Issues Fixed

### 1. Schema Creation Failure ✅
**Problem:** "❌ Failed to create Northwind schema"

**Root Cause:** 
- Connection not properly closed
- No check if schema already exists

**Solution:**
- Added check for existing schema before creation
- Proper connection cleanup in try/finally
- Better error handling

**Code:** `src/utils/northwind_bootstrapper.py` - `create_northwind_schema()`

---

### 2. No Retry Logic ✅
**Problem:** Retrying Option 1 recreates everything from scratch

**Solution:** Smart detection at each step

#### Step 1: Cluster Detection
```
Check if sales-analyst-cluster exists
  ↓
If exists and available:
  ├─ Show: "ℹ️ Cluster already exists"
  ├─ Button: [Use Existing Cluster]
  └─ Skip creation
  
If doesn't exist:
  └─ Show: [🚀 Create Cluster]
```

#### Step 2: Data Detection
```
Check if northwind schema exists
  ↓
If exists:
  ├─ Show: "ℹ️ Northwind database already exists"
  ├─ Button: [Skip to Indexing]
  └─ Skip data loading
  
If doesn't exist:
  └─ Show: [📦 Load Northwind Data]
```

#### Step 3: Always Run
```
Index Schema
  └─ Always runs (fast, ~30 seconds)
```

---

## User Experience

### First Run:
```
Step 1: [🚀 Create Cluster] → Creates cluster (~10 min)
Step 2: [📦 Load Northwind Data] → Loads data (~2 min)
Step 3: [🤖 Index Schema] → Indexes (~30 sec)
```

### Second Run (Retry):
```
Step 1: ℹ️ Cluster already exists
        [Use Existing Cluster] → Instant

Step 2: ℹ️ Northwind database already exists
        [Skip to Indexing] → Instant

Step 3: [🤖 Index Schema] → Indexes (~30 sec)
```

**Total retry time: ~30 seconds** (vs 12+ minutes)

---

## What Gets Checked

### Cluster Check:
```python
redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
  ↓
If found and status='available':
  └─ Use existing
```

### Data Check:
```python
check_northwind_exists()
  ↓
Queries: SELECT * FROM information_schema.schemata WHERE schema_name='northwind'
  ↓
If found:
  └─ Skip loading
```

---

## Files Modified

1. **`app_wizard_v3.py`** - Added detection logic in `show_option1_workflow()`
2. **`src/utils/northwind_bootstrapper.py`** - Fixed `create_northwind_schema()`

---

## Deploy

```bash
# Copy both files
scp app_wizard_v3.py ec2-user@107.22.128.25:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/
scp src/utils/northwind_bootstrapper.py ec2-user@107.22.128.25:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/src/utils/

# SSH and deploy
ssh ec2-user@107.22.128.25
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql
cp app_wizard_v3.py app.py
pkill -f streamlit
streamlit run app.py
```

---

## Testing

### Test 1: Fresh Install
1. Select Option 1
2. Click "Create Cluster" → Wait ~10 min
3. Click "Load Northwind Data" → Wait ~2 min
4. Click "Index Schema" → Wait ~30 sec
5. ✅ Complete

### Test 2: Retry After Success
1. Reset setup (sidebar button)
2. Select Option 1 again
3. See "Cluster already exists" → Click "Use Existing"
4. See "Northwind already exists" → Click "Skip to Indexing"
5. Click "Index Schema" → Wait ~30 sec
6. ✅ Complete in 30 seconds!

### Test 3: Retry After Partial Failure
1. If cluster created but data failed
2. Select Option 1
3. See "Cluster already exists" → Click "Use Existing"
4. See "Load Northwind Data" button (no skip)
5. Click to load data
6. ✅ Resumes from where it failed

---

## Error Messages Improved

### Before:
```
❌ Failed to create Northwind schema.
```

### After:
```
❌ Failed to load data. Check connection and permissions.
Error: permission denied for schema northwind
```

More actionable error messages with actual error details.

---

## Summary

✅ Schema creation fixed with proper cleanup  
✅ Detects existing cluster  
✅ Detects existing data  
✅ Smart skip buttons  
✅ Fast retry (~30 sec vs 12+ min)  
✅ Better error messages  

Ready to deploy! 🚀
