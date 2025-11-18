"""
GenAI Sales Analyst - With Profile Management
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


def apply_profile_to_env(profile_data):
    """Apply profile settings to environment variables."""
    os.environ['REDSHIFT_HOST'] = profile_data.get('host', 'localhost')
    os.environ['REDSHIFT_PORT'] = profile_data.get('port', '5439')
    os.environ['REDSHIFT_DATABASE'] = profile_data.get('database', 'sales_analyst')
    os.environ['REDSHIFT_SCHEMA'] = profile_data.get('schema', 'northwind')
    os.environ['REDSHIFT_USER'] = profile_data.get('user', 'admin')
    os.environ['REDSHIFT_PASSWORD'] = profile_data.get('password', '')


def show_profile_switcher():
    """Show profile switcher in sidebar."""
    if 'profile_manager' not in st.session_state:
        st.session_state.profile_manager = ProfileManager()
    
    pm = st.session_state.profile_manager
    profiles = pm.get_profiles()
    active_profile_id = pm.get_active_profile()
    
    st.sidebar.markdown("### 🔄 Data Source")
    
    # Profile selector
    profile_names = {pid: pdata['name'] for pid, pdata in profiles.items()}
    selected = st.sidebar.selectbox(
        "Active Profile:",
        options=list(profile_names.keys()),
        format_func=lambda x: profile_names[x],
        index=list(profile_names.keys()).index(active_profile_id) if active_profile_id in profile_names else 0,
        key="profile_selector"
    )
    
    # If profile changed, update and reload
    if selected != active_profile_id:
        pm.set_active_profile(selected)
        # Clear cached data
        for key in ['metadata_loaded', 'cluster_tables', 'database_tested', 'cluster_info_displayed']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Apply current profile
    current_profile = profiles[active_profile_id]
    apply_profile_to_env(current_profile)
    
    # Show mode indicator
    profile_type = current_profile.get('type', 'demo')
    if profile_type == 'demo':
        st.sidebar.info("📚 **Demo Mode**\nNorthwind sample data")
    else:
        schema = current_profile.get('schema', 'unknown')
        st.sidebar.success(f"🏢 **Your Data**\nSchema: {schema}")
    
    # Add new profile form
    with st.sidebar.expander("➕ Add New Profile"):
        with st.form("new_profile_form"):
            name = st.text_input("Profile Name", placeholder="My Production Cluster")
            host = st.text_input("Cluster Endpoint", placeholder="cluster.xxx.redshift.amazonaws.com")
            database = st.text_input("Database", value="dev")
            schema = st.text_input("Schema", value="public")
            user = st.text_input("Username", value="awsuser")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Save Profile"):
                if name and host and database and schema and user and password:
                    profile_id = name.lower().replace(" ", "_")
                    new_profile = {
                        "name": name,
                        "type": "existing",
                        "host": host,
                        "port": "5439",
                        "database": database,
                        "schema": schema,
                        "user": user,
                        "password": password,
                        "description": f"Custom profile: {name}"
                    }
                    pm.add_profile(profile_id, new_profile)
                    st.success(f"✅ Profile '{name}' added!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please fill in all fields")
    
    st.sidebar.markdown("---")
    
    return current_profile


def initialize_components():
    """Initialize application components."""
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    bedrock = BedrockHelper(region_name=aws_region)
    vector_store = FAISSManager(bedrock_client=bedrock)
    monitor = None
    workflow = AnalysisWorkflow(
        bedrock_helper=bedrock,
        vector_store=vector_store,
        monitor=monitor
    )
    return {
        'bedrock': bedrock,
        'vector_store': vector_store,
        'monitor': monitor,
        'workflow': workflow
    }


def load_all_metadata(vector_store, show_progress=False):
    """Dynamically load metadata from configured schema."""
    database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
    schema = os.getenv('REDSHIFT_SCHEMA', 'northwind')
    
    try:
        tables_query = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        tables_result = execute_query(tables_query)
        
        if not tables_result:
            if show_progress:
                st.sidebar.warning(f"⚠️ No tables found in schema '{schema}'")
            return None
        
        schema_parts = [f"Database: {database}, Schema: {schema}\n"]
        
        for (table_name,) in tables_result:
            columns_query = f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = '{schema}' 
                AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """
            columns_result = execute_query(columns_query)
            
            if columns_result:
                columns_list = []
                for col_name, data_type, nullable in columns_result:
                    col_desc = f"{col_name} ({data_type})"
                    columns_list.append(col_desc)
                
                columns_str = ", ".join(columns_list)
                schema_parts.append(f"Table: {table_name}\nColumns: {columns_str}\n")
        
        schema_text = "\n".join(schema_parts)
        texts = [schema_text]
        metadatas = [{'database': database, 'schema': schema, 'type': 'schema'}]
        
        embeddings = []
        for text in texts:
            embedding = vector_store.bedrock_client.get_embeddings(text)
            embeddings.append(embedding)
        
        if embeddings:
            embeddings_array = np.array(embeddings).astype('float32')
            if embeddings_array.ndim == 1:
                embeddings_array = embeddings_array.reshape(1, -1)
            
            vector_store.texts = texts
            vector_store.metadata = metadatas
            vector_store.index.add(embeddings_array)
            
            if show_progress:
                st.sidebar.success(f"✅ Loaded schema '{schema}' metadata")
            
            return pd.DataFrame({'schema': [schema], 'tables': [len(tables_result)]})
        
        return None
    except Exception as e:
        if show_progress:
            st.sidebar.error(f"❌ Error loading metadata: {str(e)}")
        return None


def main():
    """Main application function."""
    st.set_page_config(
        page_title="Sales Data Analyst",
        page_icon="📊",
        layout="wide"
    )
    
    # Profile switcher (must be first)
    current_profile = show_profile_switcher()
    
    # Hide Streamlit branding
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Custom CSS
    st.markdown("""
    <style>
    .subheader {
        font-size: 1.8rem;
        font-weight: 600;
        color: #444;
        margin-bottom: 1rem;
    }
    .info-text {
        font-size: 1.1rem;
        color: #666;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 style="font-size: 50px; font-weight: 900; color: #0066cc;">Sales Data Analyst</h1>', unsafe_allow_html=True)
    st.markdown('<p style="font-size: 14px; color: #0066cc;">(Powered by Amazon Bedrock and Amazon Redshift)</p>', unsafe_allow_html=True)
    st.markdown('<div style="border-bottom: 4px double #0066cc; margin-bottom: 30px;"></div>', unsafe_allow_html=True)
    
    # Show mode banner
    profile_type = current_profile.get('type', 'demo')
    if profile_type == 'demo':
        st.info("ℹ️  **Demo Mode Active** - Using Northwind sample data. Switch profiles in the sidebar to use your own data.")
    else:
        schema = current_profile.get('schema', 'unknown')
        st.success(f"🏢 **Production Mode** - Connected to your cluster (schema: {schema}). Switch to 'Demo (Northwind)' to try sample data.")
    
    # Initialize components
    components = initialize_components()
    
    # Auto-create Redshift cluster and test connection
    try:
        from src.utils.redshift_cluster_manager import create_redshift_cluster
        
        # Test connection first
        try:
            conn = get_redshift_connection()
            conn.close()
        except:
            with st.spinner("🚀 Setting up environment..."):
                endpoint = create_redshift_cluster()
                if endpoint:
                    os.environ['REDSHIFT_HOST'] = endpoint if endpoint != 'localhost' else 'localhost'
                
                for i in range(180):
                    try:
                        conn = get_redshift_connection()
                        conn.close()
                        break
                    except:
                        time.sleep(2)
                else:
                    st.sidebar.error("❌ Connection timeout - please refresh")
                    st.stop()
        
        # Auto-create Northwind database if in demo mode
        if profile_type == 'demo' and not check_northwind_exists():
            with st.spinner("Setting up sample database..."):
                success = bootstrap_northwind(show_progress=False)
                if not success:
                    st.sidebar.error("❌ Database setup failed")
                    return
                st.session_state.metadata_loaded = False
        
        # Display cluster connection info
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔗 Connection Status")
        
        try:
            redshift_host = os.getenv('REDSHIFT_HOST', 'localhost')
            cluster_id = redshift_host.split('.')[0] if redshift_host != 'localhost' else 'localhost'
            database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
            schema = os.getenv('REDSHIFT_SCHEMA', 'northwind')
            
            if 'cluster_tables' not in st.session_state:
                tables_result = execute_query(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = '{schema}' 
                    ORDER BY table_name
                """)
                st.session_state.cluster_tables = [row[0] for row in tables_result] if tables_result else []
            
            tables = st.session_state.cluster_tables
            
            st.sidebar.success("✅ **Connected**")
            st.sidebar.markdown(f"""
            **Cluster:** `{cluster_id}`  
            **Database:** `{database}`  
            **Schema:** `{schema}`  
            **Tables:** {len(tables)} available
            """)
            
            if tables:
                with st.sidebar.expander("📋 View All Tables"):
                    for table in tables:
                        st.write(f"• {table}")
        except Exception as e:
            st.sidebar.error(f"❌ Connection error")
        
        # Test database connection (silent)
        if 'database_tested' not in st.session_state:
            try:
                test_table = st.session_state.cluster_tables[0] if st.session_state.cluster_tables else None
                if test_table:
                    result = execute_query(f"SELECT COUNT(*) FROM {schema}.{test_table}")
                    if result:
                        st.session_state.database_tested = True
            except Exception as e:
                st.sidebar.error(f"❌ Data validation failed")
                return
            
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {str(e)}")
        return
    
    # Load metadata
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 AI Query Engine")
    
    if 'metadata_loaded' not in st.session_state or not st.session_state.metadata_loaded:
        with st.spinner("Indexing schema for AI..."):
            try:
                metadata_df = load_all_metadata(components['vector_store'], show_progress=False)
                if metadata_df is not None and len(metadata_df) > 0:
                    st.session_state.metadata_df = metadata_df
                    st.session_state.metadata_loaded = True
                    tables = st.session_state.cluster_tables
                    total_cols = 0
                    schema = os.getenv('REDSHIFT_SCHEMA', 'northwind')
                    for table in tables:
                        cols = execute_query(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='{schema}' AND table_name='{table}'")
                        if cols:
                            total_cols += cols[0][0]
                    st.session_state.metadata_count = total_cols
                else:
                    st.sidebar.warning("⚠️ Schema indexing incomplete")
                    st.session_state.metadata_loaded = False
            except Exception as e:
                st.sidebar.error(f"❌ Indexing failed: {str(e)}")
                st.session_state.metadata_loaded = False
    
    if st.session_state.get('metadata_loaded', False):
        col_count = st.session_state.get('metadata_count', 0)
        st.sidebar.success(f"✅ **Ready to Query**")
        st.sidebar.markdown(f"Indexed **{col_count} columns** across all tables")
    else:
        st.sidebar.warning("⚠️ Not ready - refresh page")
    
    st.sidebar.markdown("---")
    
    # Sidebar settings
    with st.sidebar:
        st.header("Settings")
        
        if components['workflow']:
            st.success("✅ Analysis workflow enabled")
        
        st.header("📋 Available Data")
        st.markdown("""
        **🏢 Business Data:**
        - 👥 **Customers** - Company details, contacts, locations
        - 📦 **Orders** - Order dates, shipping info, freight costs
        - 🛒 **Order Details** - Products, quantities, prices, discounts
        
        **🏭 Product Catalog:**
        - 🎯 **Products** - Names, prices, stock levels
        - 📂 **Categories** - Product groupings and descriptions
        - 🚚 **Suppliers** - Vendor information and contacts
        
        **👨💼 Operations:**
        - 👔 **Employees** - Staff details and hierarchy
        - 🚛 **Shippers** - Delivery companies and contacts
        """)
    
    # Main content
    col1 = st.container()
    
    with col1:
        st.markdown('<p class="subheader">Ask questions about your sales data</p>', unsafe_allow_html=True)
        st.markdown('<p class="info-text">You can ask about customer orders, product sales, and more.</p>', unsafe_allow_html=True)
        
        with st.expander("💡 Example questions", expanded=False):
            st.markdown("""
            **✅ Try these working questions:**
            
            1. **What are the top 10 customers by total order value?**
            2. **Which products generate the most revenue?**
            3. **What's the average order value by country?**
            4. **Which product categories sell the most?**
            5. **What are the top 5 most expensive products?**
            6. **How many orders come from each country?**
            7. **Which countries have the highest average order values?**
            8. **Who are our most frequent customers?**
            9. **Which suppliers provide the most products?**
            10. **Which employees process the most orders?**
            """)
        
        question = st.text_input(
            "💬 Ask your question:",
            placeholder="e.g., What are the top 10 customers by total revenue?"
        )
    
    # Process question
    if question:
        if 'metadata_df' not in st.session_state or not st.session_state.get('metadata_loaded', False):
            st.error("Metadata not loaded. Please refresh the page.")
            return
        
        try:
            with st.spinner("Processing your question..."):
                result = components['workflow'].execute(question, execute_query)
            
            with st.expander("Workflow Steps", expanded=False):
                steps = result.get("steps_completed", [])
                for step in steps:
                    if "error" in step:
                        st.markdown(f'<div class="workflow-step workflow-step-error">{step}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="workflow-step workflow-step-completed">{step}</div>', unsafe_allow_html=True)
            
            if "error" in result:
                st.error(f"❌ Error: {result['error']}")
            else:
                if "generated_sql" in result:
                    st.subheader("📝 Generated SQL Query")
                    st.code(result["generated_sql"], language="sql")
                
                if "query_results" in result and result["query_results"]:
                    st.subheader("📊 Query Results")
                    
                    results = result["query_results"]
                    if isinstance(results, list) and len(results) > 0:
                        if isinstance(results[0], tuple):
                            df = pd.DataFrame(results)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.write(results)
                    else:
                        st.info("No results returned")
                
                if "analysis" in result:
                    st.subheader("💡 Analysis")
                    st.markdown(result["analysis"])
        
        except Exception as e:
            st.error(f"❌ Error processing question: {str(e)}")


if __name__ == "__main__":
    main()
