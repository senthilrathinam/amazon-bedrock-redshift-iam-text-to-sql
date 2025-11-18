"""
Setup wizard for first-time configuration.
"""
import streamlit as st
from .profile_manager import ProfileManager


def show_setup_wizard():
    """Show the setup wizard for first-time users."""
    st.markdown("""
    <style>
    .wizard-container {
        padding: 2rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 2rem;
    }
    .wizard-option {
        background: white;
        color: #333;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        cursor: pointer;
        border: 2px solid transparent;
    }
    .wizard-option:hover {
        border-color: #667eea;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="wizard-container">', unsafe_allow_html=True)
    st.title("🚀 Welcome to GenAI Sales Analyst!")
    st.markdown("Let's get you set up in just a few clicks.")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### How would you like to get started?")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📚 **Quick Start (Demo)**\n\nTry with sample data\n~10 min setup", use_container_width=True, key="demo_mode"):
            return "demo"
    
    with col2:
        if st.button("🏢 **Use My Cluster**\n\nConnect to existing data\nImmediate access", use_container_width=True, key="existing_mode"):
            return "existing"
    
    with col3:
        if st.button("🔄 **Hybrid Mode**\n\nLoad demo + my data\nBest of both", use_container_width=True, key="hybrid_mode"):
            return "hybrid"
    
    st.markdown("---")
    st.markdown("💡 **Tip:** You can always switch modes later from the sidebar")
    
    return None


def configure_demo_mode(profile_manager):
    """Configure demo mode."""
    st.success("✅ Demo mode selected!")
    st.info("The app will create a new Redshift cluster and load Northwind sample data.")
    
    if st.button("Continue with Demo Mode"):
        profile_manager.set_active_profile("demo")
        profile_manager.mark_setup_complete()
        st.rerun()


def configure_existing_mode(profile_manager):
    """Configure existing cluster mode."""
    st.success("✅ Connecting to your existing cluster")
    
    with st.form("existing_cluster_form"):
        st.markdown("### Enter your Redshift connection details:")
        
        profile_name = st.text_input("Profile Name", value="My Production Cluster")
        host = st.text_input("Cluster Endpoint", placeholder="my-cluster.xxx.us-east-1.redshift.amazonaws.com")
        database = st.text_input("Database", value="dev")
        schema = st.text_input("Schema", value="public")
        user = st.text_input("Username", value="awsuser")
        password = st.text_input("Password", type="password")
        
        submitted = st.form_submit_button("Save and Connect")
        
        if submitted:
            if host and database and schema and user and password:
                # Create profile
                profile_id = "production"
                profile_data = {
                    "name": profile_name,
                    "type": "existing",
                    "host": host,
                    "port": "5439",
                    "database": database,
                    "schema": schema,
                    "user": user,
                    "password": password,
                    "description": "Production cluster"
                }
                
                profile_manager.add_profile(profile_id, profile_data)
                profile_manager.set_active_profile(profile_id)
                profile_manager.mark_setup_complete()
                
                st.success("✅ Profile saved! Connecting...")
                st.rerun()
            else:
                st.error("Please fill in all fields")


def configure_hybrid_mode(profile_manager):
    """Configure hybrid mode."""
    st.success("✅ Hybrid mode selected!")
    st.info("You'll be able to switch between demo data and your own cluster anytime.")
    
    st.markdown("### First, let's connect to your cluster:")
    
    with st.form("hybrid_cluster_form"):
        profile_name = st.text_input("Profile Name", value="My Cluster")
        host = st.text_input("Cluster Endpoint", placeholder="my-cluster.xxx.us-east-1.redshift.amazonaws.com")
        database = st.text_input("Database", value="dev")
        schema = st.text_input("Schema", value="public")
        user = st.text_input("Username", value="awsuser")
        password = st.text_input("Password", type="password")
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted:
            if host and database and schema and user and password:
                # Create profile
                profile_id = "my_cluster"
                profile_data = {
                    "name": profile_name,
                    "type": "existing",
                    "host": host,
                    "port": "5439",
                    "database": database,
                    "schema": schema,
                    "user": user,
                    "password": password,
                    "description": "My cluster"
                }
                
                profile_manager.add_profile(profile_id, profile_data)
                profile_manager.set_active_profile("demo")  # Start with demo
                profile_manager.mark_setup_complete()
                
                st.success("✅ Profiles configured! Starting with demo mode...")
                st.rerun()
            else:
                st.error("Please fill in all fields")
