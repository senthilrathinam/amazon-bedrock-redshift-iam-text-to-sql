"""
GenAI Sales Analyst - Enhanced with Profile Management
"""
import streamlit as st
import pandas as pd
import time
import os
import pickle
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import components
from src.bedrock.bedrock_helper import BedrockHelper
from src.vector_store.faiss_manager import FAISSManager
from src.graph.workflow import AnalysisWorkflow
from src.utils.redshift_connector import (
    get_redshift_connection, 
    execute_query,
    get_available_databases,
    get_available_schemas,
    get_available_tables,
    get_table_columns
)
from src.utils.northwind_bootstrapper import bootstrap_northwind, check_northwind_exists
from src.utils.profile_manager import ProfileManager
from src.utils.setup_wizard import show_setup_wizard, configure_demo_mode, configure_existing_mode, configure_hybrid_mode


def apply_profile(profile_data):
    """Apply profile settings to environment variables."""
    os.environ['REDSHIFT_HOST'] = profile_data.get('host', 'localhost')
    os.environ['REDSHIFT_PORT'] = profile_data.get('port', '5439')
    os.environ['REDSHIFT_DATABASE'] = profile_data.get('database', 'sales_analyst')
    os.environ['REDSHIFT_SCHEMA'] = profile_data.get('schema', 'northwind')
    os.environ['REDSHIFT_USER'] = profile_data.get('user', 'admin')
    os.environ['REDSHIFT_PASSWORD'] = profile_data.get('password', '')


def show_profile_switcher(profile_manager):
    """Show profile switcher in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔄 Active Profile")
    
    profiles = profile_manager.get_profiles()
    active_profile = profile_manager.get_active_profile()
    
    # Create profile options
    profile_options = {pid: pdata['name'] for pid, pdata in profiles.items()}
    
    # Profile selector
    selected_profile = st.sidebar.selectbox(
        "Switch Profile:",
        options=list(profile_options.keys()),
        format_func=lambda x: profile_options[x],
        index=list(profile_options.keys()).index(active_profile) if active_profile in profile_options else 0,
        key="profile_selector"
    )
    
    # If profile changed, update and reload
    if selected_profile != active_profile:
        profile_manager.set_active_profile(selected_profile)
        # Clear cached metadata
        if 'metadata_loaded' in st.session_state:
            st.session_state.metadata_loaded = False
        if 'cluster_tables' in st.session_state:
            del st.session_state.cluster_tables
        st.rerun()
    
    # Show profile info
    current_profile = profiles[active_profile]
    profile_type = current_profile.get('type', 'demo')
    
    if profile_type == 'demo':
        st.sidebar.info("📚 **Demo Mode**\nUsing Northwind sample data")
    else:
        st.sidebar.success("🏢 **Production Mode**\nUsing your cluster data")
    
    # Add new profile button
    with st.sidebar.expander("➕ Add New Profile"):
        with st.form("new_profile_form"):
            profile_name = st.text_input("Profile Name")
            host = st.text_input("Cluster Endpoint")
            database = st.text_input("Database", value="dev")
            schema = st.text_input("Schema", value="public")
            user = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Add Profile"):
                if profile_name and host and database and schema and user:
                    profile_id = profile_name.lower().replace(" ", "_")
                    new_profile = {
                        "name": profile_name,
                        "type": "existing",
                        "host": host,
                        "port": "5439",
                        "database": database,
                        "schema": schema,
                        "user": user,
                        "password": password,
                        "description": f"Custom profile: {profile_name}"
                    }
                    profile_manager.add_profile(profile_id, new_profile)
                    st.success(f"✅ Profile '{profile_name}' added!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")


def show_context_banner(profile_manager):
    """Show context banner indicating current mode."""
    profiles = profile_manager.get_profiles()
    active_profile = profile_manager.get_active_profile()
    current_profile = profiles.get(active_profile, {})
    profile_type = current_profile.get('type', 'demo')
    
    if profile_type == 'demo':
        st.info("ℹ️  **Demo Mode Active** - You're using sample Northwind data. Switch to your data using the profile selector in the sidebar.")
    else:
        schema = current_profile.get('schema', 'unknown')
        st.success(f"🏢 **Production Mode** - Connected to your cluster (schema: {schema}). Try demo data by switching to 'Demo (Northwind)' profile.")


# Copy the rest of the functions from original app.py
# (initialize_components, load_all_metadata, etc.)
