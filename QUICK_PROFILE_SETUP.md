# Quick Profile Switcher - Ready to Use!

## Files Created

I've created these 2 new files for you:

1. **`src/utils/profile_manager.py`** - Manages connection profiles
2. **`src/utils/setup_wizard.py`** - Setup wizard (optional)

## How to Add Profile Switching (5-Minute Setup)

### Option 1: Manual .env Profiles (Simplest)

Just create multiple `.env` files:

```bash
# .env.demo
REDSHIFT_SCHEMA=northwind
REDSHIFT_HOST=localhost
REDSHIFT_DATABASE=sales_analyst

# .env.production  
REDSHIFT_SCHEMA=demo
REDSHIFT_HOST=redshift-cluster-amazon-q2.cwtsoujhoswf.us-east-1.redshift.amazonaws.com
REDSHIFT_DATABASE=dev
```

**To switch:**
```bash
# Use demo
cp .env.demo .env
streamlit run app.py

# Use production
cp .env.production .env
streamlit run app.py
```

### Option 2: Add Profile Dropdown (10 Minutes)

Add this code to `app.py` at line 170 (after `st.set_page_config()`):

```python
# Add to imports at top
from src.utils.profile_manager import ProfileManager

# Add after st.set_page_config() in main()
@st.cache_resource
def get_profile_manager():
    return ProfileManager()

pm = get_profile_manager()

# Sidebar profile switcher
st.sidebar.markdown("### 🔄 Data Source")
profiles = pm.get_profiles()
active = pm.get_active_profile()

# Add your production profile if not exists
if 'production' not in profiles:
    pm.add_profile('production', {
        "name": "My Cluster (demo schema)",
        "type": "existing",
        "host": "redshift-cluster-amazon-q2.cwtsoujhoswf.us-east-1.redshift.amazonaws.com",
        "port": "5439",
        "database": "dev",
        "schema": "demo",
        "user": "awsuser",
        "password": "Awsuser12345"
    })
    profiles = pm.get_profiles()

# Profile selector
profile_names = {pid: pdata['name'] for pid, pdata in profiles.items()}
selected = st.sidebar.selectbox(
    "Select Profile:",
    options=list(profile_names.keys()),
    format_func=lambda x: profile_names[x],
    index=list(profile_names.keys()).index(active)
)

# Apply profile
if selected != active:
    pm.set_active_profile(selected)
    st.rerun()

# Set environment from profile
profile = profiles[active]
os.environ['REDSHIFT_HOST'] = profile['host']
os.environ['REDSHIFT_DATABASE'] = profile['database']
os.environ['REDSHIFT_SCHEMA'] = profile['schema']
os.environ['REDSHIFT_USER'] = profile['user']
os.environ['REDSHIFT_PASSWORD'] = profile['password']

# Show banner
if profile.get('type') == 'demo':
    st.info("📚 Demo Mode - Northwind sample data")
else:
    st.success(f"🏢 Your Data - Schema: {profile['schema']}")

st.sidebar.markdown("---")
```

## Files to Copy to EC2

```bash
# Copy new files
scp src/utils/profile_manager.py ec2-user@<EC2_IP>:/path/to/app/src/utils/
scp src/utils/setup_wizard.py ec2-user@<EC2_IP>:/path/to/app/src/utils/

# If you modified app.py
scp app.py ec2-user@<EC2_IP>:/path/to/app/
```

## How It Works

1. **First run**: Uses demo profile (Northwind)
2. **Add profiles**: Stores in `~/.genai_sales_analyst/profiles.json`
3. **Switch**: Dropdown in sidebar
4. **Automatic**: Reloads metadata when switching

## Testing

```bash
# Start app
streamlit run app.py

# You'll see dropdown with:
# - Demo (Northwind)
# - My Cluster (demo schema)  ← Your production data

# Switch between them - app reloads automatically!
```

## What You Get

✅ Easy switching between demo and production
✅ No .env editing needed
✅ Profiles saved permanently
✅ Visual indicator of current mode
✅ Can add unlimited profiles

## Next Steps

Want the full wizard experience? Let me know and I'll create:
- First-time setup wizard
- Profile management UI
- Import/export profiles
- Connection testing

For now, this gives you instant profile switching!
