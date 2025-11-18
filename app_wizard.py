"""
GenAI Sales Analyst - Wizard-Based Setup
"""
import streamlit as st
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()

from src.bedrock.bedrock_helper import BedrockHelper
from src.vector_store.faiss_manager import FAISSManager
from src.graph.workflow import AnalysisWorkflow
from src.utils.redshift_connector import get_redshift_connection, execute_query
from src.utils.northwind_bootstrapper import bootstrap_northwind, check_northwind_exists
from src.utils.setup_state import SetupState
from src.utils.redshift_cluster_manager import create_redshift_cluster
import numpy as np


def show_setup_wizard(setup_state):
    """Show setup wizard for first-time configuration."""
    st.title("🚀 GenAI Sales Analyst Setup")
    
    state = setup_state.get_state()
    
    # Show back button if option is selected
    if state['setup_option']:
        if st.button("⬅️ Back to Options", key="back_to_options"):
            setup_state.update_state(setup_option=None)
            st.rerun()
        st.markdown("---")
    
    st.markdown("Choose how you want to get started:")
    
    # If no option selected, show choices
    if not state['setup_option']:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### Option 1")
            st.markdown("**Create New Cluster**")
            st.write("• Creates sales-analyst-cluster")
            st.write("• Loads Northwind sample data")
            st.write("• Uses .env credentials")
            st.write("⏱️ ~10 minutes")
            if st.button("Select Option 1", key="opt1", use_container_width=True):
                setup_state.update_state(setup_option=1)
                st.rerun()
        
        with col2:
            st.markdown("### Option 2")
            st.markdown("**Load to Existing Cluster**")
            st.write("• Connect to your cluster")
            st.write("• Load Northwind sample data")
            st.write("• Keep your existing data")
            st.write("⏱️ ~5 minutes")
            if st.button("Select Option 2", key="opt2", use_container_width=True):
                setup_state.update_state(setup_option=2)
                st.rerun()
        
        with col3:
            st.markdown("### Option 3")
            st.markdown("**Use Existing Data**")
            st.write("• Point to your database")
            st.write("• No data loading needed")
            st.write("• Query your own data")
            st.write("⏱️ ~2 minutes")
            if st.button("Select Option 3", key="opt3", use_container_width=True):
                setup_state.update_state(setup_option=3)
                st.rerun()
        
        return
    
    # Show selected option workflow
    if state['setup_option'] == 1:
        show_option1_workflow(setup_state)
    elif state['setup_option'] == 2:
        show_option2_workflow(setup_state)
    elif state['setup_option'] == 3:
        show_option3_workflow(setup_state)


def show_option1_workflow(setup_state):
    """Option 1: Create new cluster."""
    st.markdown("## Option 1: Create New Cluster")
    
    state = setup_state.get_state()
    
    # Step 1: Create Cluster
    st.markdown("### Step 1: Create Redshift Cluster")
    if state['cluster_created']:
        st.success(f"✅ Cluster created: {state['cluster_id']}")
    else:
        st.info("Cluster will be created with credentials from .env file")
        if st.button("🚀 Create Cluster", key="create_cluster"):
            with st.spinner("Creating cluster... This takes ~10 minutes"):
                try:
                    endpoint = create_redshift_cluster()
                    if endpoint:
                        cluster_id = endpoint.split('.')[0] if endpoint != 'localhost' else 'sales-analyst-cluster'
                        setup_state.update_state(cluster_created=True, cluster_id=cluster_id)
                        setup_state.update_connection(host=endpoint, database='sales_analyst', schema='northwind', user='admin', password=os.getenv('REDSHIFT_PASSWORD', 'Awsuser123$'))
                        st.success("✅ Cluster created!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    # Step 2: Load Data
    st.markdown("### Step 2: Load Northwind Data")
    if state['data_loaded']:
        st.success("✅ Northwind data loaded")
    else:
        if st.button("📦 Load Northwind Data", key="load_data_opt1"):
            with st.spinner("Loading Northwind database..."):
                try:
                    # Set environment from state
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
                    success = bootstrap_northwind(show_progress=True)
                    if success:
                        setup_state.update_state(data_loaded=True)
                        st.success("✅ Data loaded!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    # Step 3: Index Schema
    st.markdown("### Step 3: Index for AI Queries")
    if state['schema_indexed']:
        st.success("✅ Schema indexed and ready")
    else:
        if st.button("🤖 Index Schema", key="index_opt1"):
            with st.spinner("Indexing schema..."):
                try:
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
                    # Index schema
                    bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    vector_store = FAISSManager(bedrock_client=bedrock)
                    load_metadata(vector_store, conn_info['schema'])
                    
                    setup_state.update_state(schema_indexed=True)
                    st.success("✅ Schema indexed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    # All done
    st.success("🎉 Setup complete!")
    if st.button("Start Using App"):
        setup_state.mark_setup_complete()
        st.rerun()


def show_option2_workflow(setup_state):
    """Option 2: Load to existing cluster."""
    st.markdown("## Option 2: Load to Existing Cluster")
    
    state = setup_state.get_state()
    
    # Step 1: Configure Connection
    if not state['connection']['host']:
        st.markdown("### Step 1: Enter Cluster Details")
        with st.form("cluster_config"):
            host = st.text_input("Cluster Endpoint", placeholder="cluster.xxx.redshift.amazonaws.com")
            database = st.text_input("Database", value="dev")
            user = st.text_input("Username", value="awsuser")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Test Connection"):
                if host and database and user and password:
                    try:
                        os.environ['REDSHIFT_HOST'] = host
                        os.environ['REDSHIFT_DATABASE'] = database
                        os.environ['REDSHIFT_USER'] = user
                        os.environ['REDSHIFT_PASSWORD'] = password
                        
                        conn = get_redshift_connection()
                        conn.close()
                        
                        setup_state.update_connection(host=host, database=database, schema='northwind', user=user, password=password)
                        st.success("✅ Connection successful!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
        return
    
    st.success(f"✅ Connected to: {state['connection']['host']}")
    
    # Step 2: Load Data
    st.markdown("### Step 2: Load Northwind Data")
    if state['data_loaded']:
        st.success("✅ Northwind data loaded")
    else:
        if st.button("📦 Load Northwind Data", key="load_data_opt2"):
            with st.spinner("Setting up connection and loading data..."):
                try:
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = 'northwind'
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
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
                        redshift = boto3.client('redshift', 
                            region_name=os.getenv('AWS_REGION', 'us-east-1'),
                            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))
                        
                        # Extract cluster ID from host
                        cluster_id = conn_info['host'].split('.')[0]
                        
                        try:
                            cluster_info = redshift.describe_clusters(ClusterIdentifier=cluster_id)
                            is_public = cluster_info['Clusters'][0].get('PubliclyAccessible', False)
                            
                            if not is_public:
                                st.info("🔧 Cluster is private. Setting up bastion host and tunnel...")
                                # Create bastion and tunnel
                                from src.utils.redshift_cluster_manager import create_bastion_host, create_ssm_tunnel
                                bastion_id = create_bastion_host()
                                if bastion_id:
                                    st.info(f"✅ Bastion host created: {bastion_id}")
                                    # Create tunnel
                                    tunnel_success = create_ssm_tunnel(bastion_id, conn_info['host'])
                                    if tunnel_success:
                                        st.info("✅ SSM tunnel established")
                                        os.environ['REDSHIFT_HOST'] = 'localhost'
                                        setup_state.update_connection(host='localhost')
                                    else:
                                        raise Exception("Failed to create SSM tunnel")
                                else:
                                    raise Exception("Failed to create bastion host")
                        except Exception as e:
                            st.warning(f"Could not check cluster accessibility: {str(e)}")
                            st.info("Attempting to load data anyway...")
                    
                    # Now load the data
                    success = bootstrap_northwind(show_progress=True)
                    if success:
                        setup_state.update_state(data_loaded=True)
                        st.success("✅ Data loaded!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to load data")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    # Step 3: Index Schema
    st.markdown("### Step 3: Index for AI Queries")
    if state['schema_indexed']:
        st.success("✅ Schema indexed and ready")
    else:
        if st.button("🤖 Index Schema", key="index_opt2"):
            with st.spinner("Indexing schema..."):
                try:
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = 'northwind'
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
                    bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    vector_store = FAISSManager(bedrock_client=bedrock)
                    load_metadata(vector_store, 'northwind')
                    
                    setup_state.update_state(schema_indexed=True)
                    st.success("✅ Schema indexed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    st.success("🎉 Setup complete!")
    if st.button("Start Using App"):
        setup_state.mark_setup_complete()
        st.rerun()


def show_option3_workflow(setup_state):
    """Option 3: Use existing data."""
    st.markdown("## Option 3: Use Existing Data")
    
    state = setup_state.get_state()
    
    # Step 1: Configure Connection
    if not state['connection']['host']:
        st.markdown("### Step 1: Enter Connection Details")
        with st.form("existing_config"):
            host = st.text_input("Cluster Endpoint", placeholder="cluster.xxx.redshift.amazonaws.com")
            database = st.text_input("Database", value="dev")
            schema = st.text_input("Schema", value="public")
            user = st.text_input("Username", value="awsuser")
            password = st.text_input("Password", type="password")
            
            if st.form_submit_button("Test Connection"):
                if host and database and schema and user and password:
                    try:
                        os.environ['REDSHIFT_HOST'] = host
                        os.environ['REDSHIFT_DATABASE'] = database
                        os.environ['REDSHIFT_SCHEMA'] = schema
                        os.environ['REDSHIFT_USER'] = user
                        os.environ['REDSHIFT_PASSWORD'] = password
                        
                        conn = get_redshift_connection()
                        cursor = conn.cursor()
                        cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{schema}'")
                        table_count = cursor.fetchone()[0]
                        conn.close()
                        
                        setup_state.update_connection(host=host, database=database, schema=schema, user=user, password=password)
                        st.success(f"✅ Connection successful! Found {table_count} tables")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
        return
    
    st.success(f"✅ Connected to: {state['connection']['host']}")
    st.info(f"Schema: {state['connection']['schema']}")
    
    # Step 2: Index Schema
    st.markdown("### Step 2: Index for AI Queries")
    if state['schema_indexed']:
        st.success("✅ Schema indexed and ready")
    else:
        if st.button("🤖 Index Schema", key="index_opt3"):
            with st.spinner("Indexing schema..."):
                try:
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
                    bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    vector_store = FAISSManager(bedrock_client=bedrock)
                    load_metadata(vector_store, conn_info['schema'])
                    
                    setup_state.update_state(schema_indexed=True, data_loaded=True)
                    st.success("✅ Schema indexed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    st.success("🎉 Setup complete!")
    if st.button("Start Using App"):
        setup_state.mark_setup_complete()
        st.rerun()


def load_metadata(vector_store, schema):
    """Load and index schema metadata."""
    database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
    
    tables_query = f"""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{schema}' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    tables_result = execute_query(tables_query)
    
    if not tables_result:
        raise Exception(f"No tables found in schema '{schema}'")
    
    schema_parts = [f"Database: {database}, Schema: {schema}\n"]
    
    for (table_name,) in tables_result:
        columns_query = f"""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_schema = '{schema}' 
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        columns_result = execute_query(columns_query)
        
        if columns_result:
            columns_list = [f"{col_name} ({data_type})" for col_name, data_type in columns_result]
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


def show_main_app():
    """Show main application after setup."""
    # Apply connection from state
    setup_state = SetupState()
    state = setup_state.get_state()
    conn_info = state['connection']
    
    os.environ['REDSHIFT_HOST'] = conn_info['host']
    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
    os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
    os.environ['REDSHIFT_USER'] = conn_info['user']
    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
    
    # Initialize components
    bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
    vector_store = FAISSManager(bedrock_client=bedrock)
    workflow = AnalysisWorkflow(bedrock_helper=bedrock, vector_store=vector_store, monitor=None)
    
    # Load metadata
    load_metadata(vector_store, conn_info['schema'])
    
    # Header
    st.title("📊 Sales Data Analyst")
    st.markdown("*Powered by Amazon Bedrock and Amazon Redshift*")
    
    # Sidebar status
    with st.sidebar:
        st.markdown("### 📊 Connection Status")
        st.success("✅ Connected")
        st.markdown(f"**Cluster:** `{conn_info['host'].split('.')[0]}`")
        st.markdown(f"**Database:** `{conn_info['database']}`")
        st.markdown(f"**Schema:** `{conn_info['schema']}`")
        
        if st.button("🔄 Reset Setup"):
            setup_state.reset_state()
            st.rerun()
    
    # Query interface
    st.markdown("### Ask questions about your data")
    question = st.text_input("💬 Your question:", placeholder="e.g., What are the top 10 customers by revenue?")
    
    if question:
        with st.spinner("Processing..."):
            try:
                result = workflow.execute(question, execute_query)
                
                if "generated_sql" in result:
                    st.subheader("📝 Generated SQL")
                    st.code(result["generated_sql"], language="sql")
                
                if "query_results" in result and result["query_results"]:
                    st.subheader("📊 Results")
                    results = result["query_results"]
                    if isinstance(results, list) and len(results) > 0:
                        df = pd.DataFrame(results)
                        st.dataframe(df, use_container_width=True)
                
                if "analysis" in result:
                    st.subheader("💡 Analysis")
                    st.markdown(result["analysis"])
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


def main():
    """Main application entry point."""
    st.set_page_config(page_title="Sales Data Analyst", page_icon="📊", layout="wide")
    
    # Hide Streamlit branding
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """, unsafe_allow_html=True)
    
    # Check setup state
    setup_state = SetupState()
    state = setup_state.get_state()
    
    # Validate state - if setup is marked complete but missing critical data, reset
    if state.get('setup_complete') and not state.get('schema_indexed'):
        st.warning("⚠️ Setup state is incomplete. Resetting...")
        setup_state.reset_state()
        time.sleep(1)
        st.rerun()
    
    # Add reset button in sidebar for debugging
    with st.sidebar:
        if st.button("🔄 Reset All Setup", key="reset_all"):
            setup_state.reset_state()
            st.success("Setup reset! Reloading...")
            time.sleep(1)
            st.rerun()
    
    if not setup_state.is_setup_complete():
        show_setup_wizard(setup_state)
    else:
        show_main_app()


if __name__ == "__main__":
    main()
