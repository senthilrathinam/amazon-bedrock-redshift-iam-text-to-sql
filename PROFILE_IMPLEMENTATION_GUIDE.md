# Profile Switcher Implementation Guide

## Quick Implementation (30 minutes)

Instead of a full rewrite, here's a **minimal implementation** that adds profile switching to your existing app:

### Step 1: Add Profile Switcher to Sidebar

Add this code at the **beginning of your main() function**, right after `st.set_page_config()`:

```python
# Add at top of app.py imports
from src.utils.profile_manager import ProfileManager

# Add in main() function after st.set_page_config()
def main():
    st.set_page_config(...)
    
    # === NEW CODE START ===
    # Initialize profile manager
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = ProfileManager()
    
    pm = st.session_state.profile_manager
    
    # Get profiles
    profiles = pm.get_profiles()
    active_profile_id = pm.get_active_profile()
    
    # Sidebar profile switcher
    st.sidebar.markdown("### 🔄 Data Source")
    profile_names = {pid: pdata['name'] for pid, pdata in profiles.items()}
    
    selected = st.sidebar.selectbox(
        "Active Profile:",
        options=list(profile_names.keys()),
        format_func=lambda x: profile_names[x],
        index=list(profile_names.keys()).index(active_profile_id),
        key="profile_select"
    )
    
    # Apply profile if changed
    if selected != active_profile_id:
        pm.set_active_profile(selected)
        profile_data = profiles[selected]
        os.environ['REDSHIFT_HOST'] = profile_data['host']
        os.environ['REDSHIFT_DATABASE'] = profile_data['database']
        os.environ['REDSHIFT_SCHEMA'] = profile_data['schema']
        os.environ['REDSHIFT_USER'] = profile_data['user']
        os.environ['REDSHIFT_PASSWORD'] = profile_data['password']
        st.session_state.metadata_loaded = False
        st.rerun()
    
    # Apply current profile
    profile_data = profiles[active_profile_id]
    os.environ['REDSHIFT_HOST'] = profile_data['host']
    os.environ['REDSHIFT_DATABASE'] = profile_data['database']
    os.environ['REDSHIFT_SCHEMA'] = profile_data['schema']
    os.environ['REDSHIFT_USER'] = profile_data['user']
    os.environ['REDSHIFT_PASSWORD'] = profile_data['password']
    
    # Show mode banner
    if profile_data.get('type') == 'demo':
        st.info("📚 **Demo Mode** - Using Northwind sample data")
    else:
        st.success(f"🏢 **Your Data** - Schema: {profile_data['schema']}")
    
    st.sidebar.markdown("---")
    # === NEW CODE END ===
    
    # Rest of your existing code continues...
```

### Step 2: Add "Add Profile" Form

Add this in the sidebar section (around line 350):

```python
# In sidebar section
with st.sidebar:
    st.header("Settings")
    
    # === NEW CODE START ===
    with st.expander("➕ Add New Profile"):
        with st.form("add_profile"):
            name = st.text_input("Profile Name")
            host = st.text_input("Cluster Endpoint")
            db = st.text_input("Database", "dev")
            schema = st.text_input("Schema", "public")
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            
            if st.form_submit_button("Save Profile"):
                if name and host and user and pwd:
                    pid = name.lower().replace(" ", "_")
                    pm.add_profile(pid, {
                        "name": name,
                        "type": "existing",
                        "host": host,
                        "port": "5439",
                        "database": db,
                        "schema": schema,
                        "user": user,
                        "password": pwd
                    })
                    st.success(f"✅ Added '{name}'")
                    time.sleep(1)
                    st.rerun()
    # === NEW CODE END ===
```

### Step 3: Files to Copy to EC2

Copy these 2 new files:
1. `src/utils/profile_manager.py` (already created)
2. `src/utils/setup_wizard.py` (already created)

And modify:
3. `app.py` (add the code snippets above)

### Step 4: Test It

1. Restart the app
2. You'll see "Demo (Northwind)" in the dropdown
3. Click "Add New Profile" to add your cluster
4. Switch between profiles using the dropdown

---

## Full Implementation (2 hours)

If you want the complete wizard experience, I can create a fully rewritten app.py with:
- Setup wizard on first launch
- Profile management UI
- Context banners
- Profile import/export

**Which approach do you prefer?**
1. **Quick (30 min)** - Add profile switcher to existing app (minimal changes)
2. **Full (2 hours)** - Complete rewrite with wizard and all features

Let me know and I'll provide the exact files!
