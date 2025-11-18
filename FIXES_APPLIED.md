# Fixes Applied to app_wizard.py

## Issue 1: No Back Button ✅ FIXED

**Problem:** Once user selects an option, they can't go back to explore other options.

**Solution:** Added "⬅️ Back to Options" button at the top of setup screens.

**Location:** Line ~25 in `show_setup_wizard()` function

**Code Added:**
```python
# Show back button if option is selected
if state['setup_option']:
    if st.button("⬅️ Back to Options", key="back_to_options"):
        setup_state.update_state(setup_option=None)
        st.rerun()
    st.markdown("---")
```

**User Experience:**
- Button appears on all option screens (1, 2, 3)
- Clicking it returns to the 3-option landing page
- Can explore different options without resetting entire setup

---

## Issue 2: Option 2 Bootstrap Error ✅ FIXED

**Problem:** 
```
❌ Error bootstrapping Northwind database: [Errno 5] Input/output error
```

**Root Cause:** 
- Option 2 tried to load data to existing cluster
- If cluster is private (not publicly accessible), needs bastion host + SSM tunnel
- App didn't set up the tunnel, causing I/O error

**Solution:** Enhanced Option 2 to:
1. Try direct connection first
2. If fails, check if cluster is private
3. If private, automatically create bastion host
4. Establish SSM tunnel
5. Then load data through tunnel

**Location:** Line ~200 in `show_option2_workflow()` function

**Code Added:**
```python
# Check if cluster is private and needs bastion
try:
    # Try direct connection first
    conn = get_redshift_connection()
    conn.close()
    st.info("✅ Direct connection successful")
except:
    # If direct connection fails, might need bastion/tunnel
    st.warning("⚠️ Direct connection failed. Checking if bastion host is needed...")
    
    # Check if cluster is publicly accessible
    import boto3
    redshift = boto3.client('redshift', ...)
    
    cluster_id = conn_info['host'].split('.')[0]
    cluster_info = redshift.describe_clusters(ClusterIdentifier=cluster_id)
    is_public = cluster_info['Clusters'][0].get('PubliclyAccessible', False)
    
    if not is_public:
        st.info("🔧 Cluster is private. Setting up bastion host and tunnel...")
        # Create bastion and tunnel
        bastion_id = create_bastion_host()
        tunnel_success = create_ssm_tunnel(bastion_id, conn_info['host'])
        if tunnel_success:
            os.environ['REDSHIFT_HOST'] = 'localhost'
```

**User Experience:**
- If cluster is public → Direct connection, fast loading
- If cluster is private → Automatic bastion setup, then loading
- Progress messages show what's happening
- No manual intervention needed

---

## Deploy Updated App

```bash
# Copy fixed file to EC2
scp app_wizard.py ec2-user@107.22.128.25:/usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql/

# SSH and restart
ssh ec2-user@107.22.128.25
cd /usr/bin/senthil/amazon-bedrock-redshift-iam-text-to-sql
cp app_wizard.py app.py
streamlit run app.py
```

---

## Testing

### Test Issue 1 Fix:
1. Open app → Select Option 1
2. See "⬅️ Back to Options" button at top
3. Click it → Returns to 3-option screen
4. Select Option 2 → Back button still there
5. Can switch between options freely

### Test Issue 2 Fix:
1. Select Option 2
2. Enter your existing cluster details (redshift-cluster-amazon-q2)
3. Click "Test Connection" → ✅ Success
4. Click "Load Northwind Data"
5. Should see:
   - "⚠️ Direct connection failed..." (if private)
   - "🔧 Cluster is private. Setting up bastion..."
   - "✅ Bastion host created: i-xxxxx"
   - "✅ SSM tunnel established"
   - "✅ Data loaded!"

---

## Files Modified

- `app_wizard.py` - Both fixes applied

## Ready to Deploy!

The app now handles:
✅ Back navigation between options
✅ Private cluster detection
✅ Automatic bastion host creation
✅ SSM tunnel establishment
✅ Data loading through tunnel
