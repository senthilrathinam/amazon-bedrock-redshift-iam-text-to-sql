
"""
GenAI Sales Analyst - Wizard-Based Setup v2.2
"""
import streamlit as st
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()

from src.bedrock.bedrock_helper_iam import BedrockHelper
from src.vector_store.faiss_manager import FAISSManager
from src.graph.workflow import AnalysisWorkflow
from src.utils.redshift_connector_iam import execute_query, execute_query_with_columns
from src.utils.northwind_bootstrapper import bootstrap_northwind, check_northwind_exists
from src.utils.setup_state import SetupState
from src.utils.redshift_cluster_manager import create_redshift_cluster
from src.utils.relationship_manager import (
    get_all_relationships, build_relationship_map,
    save_yaml_relationship, delete_yaml_relationship, get_yaml_relationships
)
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
        
        # Show selected option workflow
        if state['setup_option'] == 1:
            show_option1_workflow(setup_state)
        elif state['setup_option'] == 2:
            show_option2_workflow(setup_state)
        elif state['setup_option'] == 3:
            show_option3_workflow(setup_state)
        elif state['setup_option'] == 4:
            show_option4_workflow(setup_state)
        return
    
    # Landing page - show option choices
    st.markdown("Choose how you want to get started:")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### Option 1")
        st.markdown("**Create New Cluster**")
        st.write(f"• Creates {os.getenv('OPTION1_CLUSTER_ID', 'sales-analyst-cluster')}")
        st.write("• Loads Northwind sample data")
        st.write("• Uses .env credentials")
        st.write("⏱️ ~10 minutes")
        
        # Check if cluster exists
        cluster_id = os.getenv('OPTION1_CLUSTER_ID', 'sales-analyst-cluster')
        cluster_exists = False
        try:
            import boto3
            redshift = boto3.client('redshift', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            cluster_info = redshift.describe_clusters(ClusterIdentifier=cluster_id)
            if cluster_info['Clusters'][0]['ClusterStatus'] == 'available':
                cluster_exists = True
                st.info("✅ Cluster exists")
        except:
            pass
        
        if st.button("Select Option 1", key="opt1", width="stretch"):
            setup_state.reset_state()  # Clear any cached connection
            setup_state.update_state(setup_option=1)
            st.rerun()
        
        # Show cleanup if cluster exists
        if cluster_exists:
            st.markdown("---")
            if st.button("🗑️ Delete Cluster", key="delete_landing", width="stretch"):
                st.session_state.confirm_delete_landing = True
            if st.session_state.get('confirm_delete_landing', False):
                if st.button("⚠️ Confirm", key="confirm_landing", width="stretch"):
                    with st.spinner("Deleting..."):
                        cleanup_option1_resources()
                        setup_state.reset_state()
                        st.session_state.confirm_delete_landing = False
                        time.sleep(2)
                        st.rerun()
    
    with col2:
        st.markdown("### Option 2")
        st.markdown("**Load to Existing Cluster**")
        st.write("• Connect to your cluster")
        st.write("• Load Northwind sample data")
        st.write("• Keep your existing data")
        st.write("⏱️ ~5 minutes")
        if st.button("Select Option 2", key="opt2", width="stretch"):
            setup_state.reset_state()  # Clear any cached connection
            setup_state.update_state(setup_option=2)
            st.rerun()
    
    with col3:
        st.markdown("### Option 3")
        st.markdown("**Use Existing Data**")
        st.write("• Point to your database")
        st.write("• No data loading needed")
        st.write("• Query your own data")
        st.write("⏱️ ~2 minutes")
        if st.button("Select Option 3", key="opt3", width="stretch"):
            setup_state.reset_state()  # Clear any cached connection
            setup_state.update_state(setup_option=3)
            st.rerun()
    
    with col4:
        st.markdown("### Option 4")
        st.markdown("**Import from Excel**")
        st.write("• Upload schema Excel workbook")
        st.write("• Auto-creates tables + metadata")
        st.write("• Loads golden queries")
        st.write("⏱️ ~3 minutes")
        if st.button("Select Option 4", key="opt4", width="stretch"):
            setup_state.reset_state()
            setup_state.update_state(setup_option=4)
            st.rerun()
    
    # Reset button for clearing stale state
    st.markdown("---")
    if st.button("🔄 Reset All Setup", key="reset_all_setup_landing", width="stretch"):
        setup_state.reset_state()
        st.success("Setup state reset successfully!")
        time.sleep(1)
        st.rerun()


def cleanup_option1_resources():
    """Delete Option 1 cluster and all related resources."""
    import boto3
    region = os.getenv('AWS_REGION', 'us-east-1')
    cluster_id = os.getenv('OPTION1_CLUSTER_ID', 'sales-analyst-cluster')
    
    try:
        # Delete Redshift cluster
        redshift = boto3.client('redshift', region_name=region)
        try:
            redshift.delete_cluster(
                ClusterIdentifier=cluster_id,
                SkipFinalClusterSnapshot=True
            )
            st.info("🗑️ Deleting Redshift cluster...")
        except:
            pass
        
        # Terminate bastion host
        ec2 = boto3.client('ec2', region_name=region)
        try:
            instances = ec2.describe_instances(
                Filters=[
                    {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                    {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                ]
            )
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    ec2.terminate_instances(InstanceIds=[instance['InstanceId']])
                    st.info(f"🗑️ Terminating bastion host {instance['InstanceId']}...")
        except:
            pass
        
        st.success("✅ Cleanup initiated. Resources will be deleted in a few minutes.")
    except Exception as e:
        st.error(f"❌ Cleanup error: {str(e)}")


def show_option1_workflow(setup_state):
    """Option 1: Create new cluster."""
    st.markdown("## Option 1: Create New Cluster")
    
    # Validate required environment variables
    password = os.getenv('OPTION1_PASSWORD')
    if not password:
        st.error("❌ Missing required environment variable: OPTION1_PASSWORD")
        st.info("💡 Please set OPTION1_PASSWORD in your .env file and restart the application")
        st.code("OPTION1_PASSWORD=YourSecurePassword123!", language="bash")
        return
    
    state = setup_state.get_state()
    
    # Start SSM tunnel if using localhost and cluster is created
    if state['cluster_created'] and state['connection']['host'] == 'localhost':
        import subprocess
        try:
            result = subprocess.run(['pgrep', '-f', 'session-manager-plugin'], 
                                  capture_output=True, text=True)
            if not result.stdout.strip():
                # Tunnel not running, start it
                import boto3
                ec2 = boto3.client('ec2', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                redshift = boto3.client('redshift', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                
                instances = ec2.describe_instances(
                    Filters=[
                        {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                        {'Name': 'instance-state-name', 'Values': ['running']}
                    ]
                )
                
                if instances['Reservations']:
                    bastion_id = instances['Reservations'][0]['Instances'][0]['InstanceId']
                    cluster_info = redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
                    endpoint = cluster_info['Clusters'][0]['Endpoint']['Address']
                    
                    subprocess.Popen([
                        'aws', 'ssm', 'start-session',
                        '--target', bastion_id,
                        '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
                        '--parameters', f'{{"host":["{endpoint}"],"portNumber":["5439"],"localPortNumber":["5439"]}}',
                        '--region', os.getenv('AWS_REGION', 'us-east-1')
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    st.info("🔄 Starting SSM tunnel... Please wait.")
                    time.sleep(5)
                    st.rerun()
        except:
            pass
    
    # Step 1: Create Cluster (with check for existing)
    st.markdown("### Step 1: Create Redshift Cluster")
    if state['cluster_created']:
        st.success(f"✅ Cluster created: {state['cluster_id']}")
    else:
        # Check if cluster already exists in AWS
        cluster_exists = False
        endpoint = None
        is_public = False
        
        try:
            import boto3
            redshift = boto3.client('redshift', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            cluster_info = redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
            if cluster_info['Clusters'][0]['ClusterStatus'] == 'available':
                cluster_exists = True
                endpoint = cluster_info['Clusters'][0]['Endpoint']['Address']
                is_public = cluster_info['Clusters'][0].get('PubliclyAccessible', False)
        except:
            pass
        
        if cluster_exists:
            st.info("ℹ️ Cluster 'sales-analyst-cluster' already exists")
            if st.button("✅ Use Existing Cluster", key="use_existing"):
                host = endpoint if is_public else 'localhost'
                setup_state.update_state(cluster_created=True, cluster_id='sales-analyst-cluster')
                setup_state.update_connection(
                    host=host, 
                    database=os.getenv('OPTION1_DATABASE', 'sales_analyst'), 
                    schema=os.getenv('OPTION1_SCHEMA', 'northwind'), 
                    user=os.getenv('OPTION1_USER', 'admin'), 
                    password=os.getenv('OPTION1_PASSWORD')
                )
                st.rerun()
            return
        
        # Cluster doesn't exist, show create button
        st.info("Cluster will be created with credentials from .env file")
        if st.button("🚀 Create Cluster", key="create_cluster"):
            with st.spinner("Creating cluster... This takes ~10 minutes"):
                try:
                    endpoint = create_redshift_cluster()
                    if endpoint:
                        cluster_id = endpoint.split('.')[0] if endpoint != 'localhost' else os.getenv('OPTION1_CLUSTER_ID', 'sales-analyst-cluster')
                        setup_state.update_state(cluster_created=True, cluster_id=cluster_id)
                        setup_state.update_connection(
                            host=endpoint, 
                            database=os.getenv('OPTION1_DATABASE', 'sales_analyst'), 
                            schema=os.getenv('OPTION1_SCHEMA', 'northwind'), 
                            user=os.getenv('OPTION1_USER', 'admin'), 
                            password=os.getenv('OPTION1_PASSWORD')
                        )
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        return
    
    # Step 2: Load Data (with check for existing)
    st.markdown("### Step 2: Load Northwind Data")
    if state['data_loaded']:
        st.success("✅ Northwind data loaded")
    else:
        # Check if Northwind already exists with retry
        northwind_exists = False
        check_error = None
        
        with st.spinner("Checking for existing Northwind data..."):
            for attempt in range(3):
                try:
                    conn_info = state['connection']
                    os.environ['REDSHIFT_HOST'] = conn_info['host']
                    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                    os.environ['REDSHIFT_SCHEMA'] = 'northwind'
                    os.environ['REDSHIFT_USER'] = conn_info['user']
                    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                    
                    northwind_exists = check_northwind_exists()
                    check_error = None
                    break
                except Exception as e:
                    check_error = str(e)
                    if attempt < 2:
                        time.sleep(2)
                    continue
        
        if check_error:
            st.error(f"❌ Cannot connect to database: {check_error}")
            st.info("💡 Make sure SSM tunnel is running. Wait a moment and refresh the page.")
            return
        
        if northwind_exists:
            st.info("ℹ️ Northwind database already exists")
            if st.button("✅ Skip to Indexing", key="skip_to_index"):
                setup_state.update_state(data_loaded=True)
                st.rerun()
            return
        
        # Northwind doesn't exist, show load button
        st.info("Northwind data not found. Click below to load sample data.")
        if st.button("📦 Load Northwind Data", key="load_data_opt1"):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            try:
                conn_info = state['connection']
                os.environ['REDSHIFT_HOST'] = conn_info['host']
                os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
                os.environ['REDSHIFT_USER'] = conn_info['user']
                os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                
                progress_placeholder.info("📥 Downloading Northwind database...")
                
                # Show loading progress
                tables = ['customers', 'orders', 'order_details', 'products', 'categories', 
                         'suppliers', 'employees', 'shippers', 'regions', 'territories']
                
                progress_bar = st.progress(0)
                for i, table in enumerate(tables):
                    status_placeholder.info(f"Loading table: {table}...")
                    progress_bar.progress((i + 1) / len(tables))
                    time.sleep(0.1)
                
                success = bootstrap_northwind(show_progress=True)
                
                if success:
                    setup_state.update_state(data_loaded=True)
                    progress_placeholder.success("✅ All tables loaded!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to load data. Check connection and permissions.")
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
                    
                    bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    vector_store = FAISSManager(bedrock_client=bedrock)
                    load_metadata(vector_store, conn_info['schema'])
                    
                    setup_state.update_state(schema_indexed=True)
                    st.success("✅ Schema indexed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    return
        else:
            return  # Only return if button not clicked yet
    
    st.success("🎉 Setup complete!")
    if st.button("Start Using App", type="primary"):
        setup_state.mark_setup_complete()
        st.rerun()


def show_option2_workflow(setup_state):
    """Option 2: Load to existing cluster."""
    st.markdown("## Option 2: Load to Existing Cluster")
    
    state = setup_state.get_state()
    
    # Step 1: Configure Connection
    if not state['connection'].get('host'):
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
                        
                        from src.utils.redshift_connector_iam import _reset_pool
                        _reset_pool()
                        execute_query("SELECT 1")
                        
                        setup_state.update_connection(host=host, database=database, schema='northwind', user=user, password=password)
                        st.success("✅ Connection successful!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
        return
    
    st.success(f"✅ Connected to: {state['connection']['host']}")
    
    # Step 2: Load Data (with check if already loaded)
    st.markdown("### Step 2: Load Northwind Data")
    if state['data_loaded']:
        st.success("✅ Northwind data already loaded")
    else:
        # Check if Northwind already exists
        northwind_exists = False
        try:
            conn_info = state['connection']
            os.environ['REDSHIFT_HOST'] = conn_info['host']
            os.environ['REDSHIFT_DATABASE'] = conn_info['database']
            os.environ['REDSHIFT_SCHEMA'] = 'northwind'
            os.environ['REDSHIFT_USER'] = conn_info['user']
            os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
            
            northwind_exists = check_northwind_exists()
        except:
            pass
        
        if northwind_exists:
            st.info("ℹ️ Northwind database already exists in this cluster")
            if st.button("Skip to Indexing", key="skip_load"):
                setup_state.update_state(data_loaded=True)
                st.rerun()
            return  # Don't show load button if Northwind exists
        
        # Only show load button if Northwind doesn't exist
        if st.button("📦 Load Northwind Data", key="load_data_opt2"):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            
            try:
                conn_info = state['connection']
                os.environ['REDSHIFT_HOST'] = conn_info['host']
                os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                os.environ['REDSHIFT_SCHEMA'] = 'northwind'
                os.environ['REDSHIFT_USER'] = conn_info['user']
                os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                
                # Check if cluster is private
                status_placeholder.info("🔍 Checking cluster accessibility...")
                try:
                    from src.utils.redshift_connector_iam import _reset_pool
                    _reset_pool()
                    execute_query("SELECT 1")
                    status_placeholder.success("✅ Direct connection successful")
                except:
                    status_placeholder.warning("⚠️ Setting up secure connection...")
                    
                    import boto3
                    redshift = boto3.client('redshift', 
                        region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    
                    cluster_id = conn_info['host'].split('.')[0]
                    
                    try:
                        cluster_info = redshift.describe_clusters(ClusterIdentifier=cluster_id)
                        is_public = cluster_info['Clusters'][0].get('PubliclyAccessible', False)
                        
                        if not is_public:
                            status_placeholder.info("🔧 Creating bastion host...")
                            from src.utils.redshift_cluster_manager import create_bastion_host, create_ssm_tunnel
                            bastion_id = create_bastion_host()
                            if bastion_id:
                                status_placeholder.info(f"✅ Bastion created: {bastion_id}")
                                status_placeholder.info("🔗 Establishing SSM tunnel...")
                                tunnel_success = create_ssm_tunnel(bastion_id, conn_info['host'])
                                if tunnel_success:
                                    status_placeholder.success("✅ Tunnel established")
                                    os.environ['REDSHIFT_HOST'] = 'localhost'
                                    setup_state.update_connection(host='localhost')
                    except Exception as e:
                        status_placeholder.warning(f"Proceeding with connection: {str(e)}")
                
                # Load data
                progress_placeholder.info("📥 Downloading Northwind database...")
                
                # Show loading progress
                tables = ['customers', 'orders', 'order_details', 'products', 'categories', 
                         'suppliers', 'employees', 'shippers', 'regions', 'territories']
                
                progress_bar = st.progress(0)
                for i, table in enumerate(tables):
                    status_placeholder.info(f"Loading table: {table}...")
                    progress_bar.progress((i + 1) / len(tables))
                    time.sleep(0.1)
                
                success = bootstrap_northwind(show_progress=True)
                
                if success:
                    setup_state.update_state(data_loaded=True)
                    progress_placeholder.success("✅ Data loaded successfully!")
                    time.sleep(1)
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
    if not state['connection'].get('host'):
        st.markdown("### Step 1: Enter Connection Details")
        with st.form("existing_config"):
            host = st.text_input("Cluster Endpoint", value=os.getenv('OPTION3_HOST', ''), placeholder="cluster.xxx.redshift.amazonaws.com")
            database = st.text_input("Database", value=os.getenv('OPTION3_DATABASE', 'dev'))
            schema = st.text_input("Schema", value=os.getenv('OPTION3_SCHEMA', 'public'))
            user = st.text_input("Username", value=os.getenv('OPTION3_USER', 'awsuser'))
            password = st.text_input("Password", type="password", value=os.getenv('OPTION3_PASSWORD', ''))
            
            if st.form_submit_button("Test Connection"):
                if host and database and schema and user and password:
                    try:
                        os.environ['REDSHIFT_HOST'] = host
                        os.environ['REDSHIFT_DATABASE'] = database
                        os.environ['REDSHIFT_SCHEMA'] = schema
                        os.environ['REDSHIFT_USER'] = user
                        os.environ['REDSHIFT_PASSWORD'] = password
                        
                        from src.utils.redshift_connector_iam import _reset_pool
                        _reset_pool()
                        
                        result = execute_query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s", (schema,))
                        table_count = result[0][0]
                        
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


def show_option4_workflow(setup_state):
    """Option 4: Import from Excel workbook."""
    st.markdown("## Option 4: Import from Excel")

    state = setup_state.get_state()

    # Step 1: Connect to cluster
    if not state['connection'].get('host'):
        st.markdown("### Step 1: Enter Cluster Connection")
        with st.form("excel_cluster_config"):
            host = st.text_input("Cluster Endpoint", value=os.getenv('OPTION3_HOST', ''), placeholder="cluster.xxx.redshift.amazonaws.com")
            database = st.text_input("Database", value=os.getenv('OPTION3_DATABASE', 'dev'))
            user = st.text_input("Username", value=os.getenv('OPTION3_USER', 'awsuser'))
            password = st.text_input("Password", type="password", value=os.getenv('OPTION3_PASSWORD', ''))

            if st.form_submit_button("Test Connection"):
                if host and database and user and password:
                    try:
                        os.environ['REDSHIFT_HOST'] = host
                        os.environ['REDSHIFT_DATABASE'] = database
                        os.environ['REDSHIFT_USER'] = user
                        os.environ['REDSHIFT_PASSWORD'] = password
                        from src.utils.redshift_connector_iam import _reset_pool
                        _reset_pool()
                        execute_query("SELECT 1")
                        setup_state.update_connection(host=host, database=database, schema='', user=user, password=password)
                        st.success("✅ Connection successful!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection failed: {str(e)}")
        return

    st.success(f"✅ Connected to: {state['connection']['host']}")

    # Step 2: Upload Excel and specify schema
    st.markdown("### Step 2: Upload Excel & Create Schema")

    if state.get('schema_indexed'):
        st.success(f"✅ Schema `{state['connection']['schema']}` created and indexed")
    else:
        schema_name = st.text_input("Schema name to create", value="genai_poc", key="excel_schema_name")
        uploaded_file = st.file_uploader("Upload Excel workbook (3 tabs: Tables, Columns, Queries)", type=["xlsx"])
        load_data = st.checkbox("📦 Load sample data for testing", value=True, key="excel_load_data")

        if uploaded_file and schema_name:
            if st.button("🚀 Import & Create Schema", key="import_excel"):
                with st.spinner("Processing Excel and creating schema..."):
                    try:
                        from src.utils.excel_knowledge_loader import parse_excel, provision_schema
                        import io

                        # Parse Excel
                        st.info("📖 Parsing Excel workbook...")
                        parsed = parse_excel(io.BytesIO(uploaded_file.read()))
                        st.info(f"Found {len(parsed['tables'])} tables, {len(parsed['columns'])} columns, {len(parsed['queries'])} queries")

                        # Set connection env vars
                        conn_info = state['connection']
                        os.environ['REDSHIFT_HOST'] = conn_info['host']
                        os.environ['REDSHIFT_DATABASE'] = conn_info['database']
                        os.environ['REDSHIFT_USER'] = conn_info['user']
                        os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
                        os.environ['REDSHIFT_SCHEMA'] = schema_name

                        from src.utils.redshift_connector_iam import _reset_pool
                        _reset_pool()

                        # Provision schema
                        st.info("🔧 Creating schema, tables, and metadata...")
                        success, message = provision_schema(schema_name, parsed, execute_query, load_sample_data=load_data)

                        if success:
                            st.success(f"✅ {message}")
                            setup_state.update_connection(schema=schema_name)

                            # Index schema
                            st.info("🤖 Indexing schema for AI queries...")
                            bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
                            vector_store = FAISSManager(bedrock_client=bedrock)
                            load_metadata(vector_store, schema_name)

                            setup_state.update_state(schema_indexed=True, data_loaded=True)
                            st.success("✅ Schema indexed!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        return

    st.success("🎉 Setup complete!")
    if st.button("Start Using App", key="start_opt4"):
        setup_state.mark_setup_complete()
        st.rerun()


def load_metadata(vector_store, schema):
    """Load and index schema metadata as per-table documents for selective retrieval.
    Enriches with COMMENT ON metadata (business glossary) when available."""
    database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
    
    tables_result = execute_query(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
        (schema,)
    )
    
    if not tables_result:
        raise Exception(f"No tables found in schema '{schema}'")
    
    texts = []
    metadatas = []
    table_names = [t[0] for t in tables_result]
    
    # Get relationships from all 4 sources (FK constraints, COMMENT ON [FK:], YAML, UI)
    all_rels = get_all_relationships(execute_query, schema)
    fk_map = build_relationship_map(all_rels, schema)
    
    for table_name in table_names:
        columns_result = execute_query(
            "SELECT c.column_name, c.data_type, d.description "
            "FROM information_schema.columns c "
            "LEFT JOIN (SELECT cl.oid, cl.relname, ns.nspname FROM pg_catalog.pg_class cl "
            "JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid WHERE cl.relkind = 'r') t "
            "ON t.relname = c.table_name AND t.nspname = c.table_schema "
            "LEFT JOIN pg_catalog.pg_description d ON t.oid = d.objoid AND d.objsubid = c.ordinal_position "
            "WHERE c.table_schema = %s AND c.table_name = %s ORDER BY c.ordinal_position",
            (schema, table_name)
        )
        
        try:
            tc_result = execute_query(
                "SELECT d.description FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid "
                "JOIN pg_catalog.pg_description d ON c.oid = d.objoid AND d.objsubid = 0 "
                "WHERE n.nspname = %s AND c.relname = %s",
                (schema, table_name)
            )
            table_comment = tc_result[0][0] if tc_result else None
        except:
            table_comment = None
        
        if columns_result:
            # Build column descriptions: include business glossary if available
            col_parts = []
            for col_name, data_type, comment in columns_result:
                if comment:
                    col_parts.append(f"{col_name} ({comment}, {data_type})")
                else:
                    col_parts.append(f"{col_name} ({data_type})")
            columns_str = " | ".join(col_parts)
            
            relationships = fk_map.get(table_name, [])
            rel_str = f"\nRelationships: {'; '.join(relationships)}" if relationships else ""
            
            # Include table comment as business description
            table_desc = f" ({table_comment})" if table_comment else ""
            
            text = (f"Schema: {schema}, Table: {schema}.{table_name}{table_desc}\n"
                    f"Columns: {columns_str}{rel_str}")
            texts.append(text)
            metadatas.append({'database': database, 'schema': schema, 
                            'table': table_name, 'type': 'table'})
    
    # Add overview document for broad questions
    overview = (f"Database: {database}, Schema: {schema}\n"
                f"Available tables: {', '.join([schema + '.' + t for t in table_names])}\n"
                f"IMPORTANT: Always use schema-qualified table names: {schema}.tablename")
    texts.append(overview)
    metadatas.append({'database': database, 'schema': schema, 'type': 'overview'})
    
    embeddings = []
    for text in texts:
        embedding = vector_store.bedrock_client.get_embeddings(text)
        embeddings.append(embedding)
    
    if embeddings:
        embeddings_array = np.array(embeddings).astype('float32')
        if embeddings_array.ndim == 1:
            embeddings_array = embeddings_array.reshape(1, -1)
        
        # Reset index before adding (prevents stale entries from previous schema)
        vector_store.index.reset()
        vector_store.texts = texts
        vector_store.metadata = metadatas
        vector_store.index.add(embeddings_array)
    
    return _detect_glossary_status(schema)


def _detect_glossary_status(schema):
    """Detect if schema uses descriptive names or cryptic names with/without glossary."""
    try:
        col_comments = execute_query(
            "SELECT COUNT(*) FROM pg_catalog.pg_description d "
            "JOIN pg_catalog.pg_class c ON d.objoid = c.oid "
            "JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid "
            "WHERE n.nspname = %s AND d.objsubid > 0", (schema,)
        )[0][0]
        total_cols = execute_query(
            "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = %s", (schema,)
        )[0][0]
    except:
        return {'status': 'unknown', 'message': '', 'type': 'info'}
    
    comment_pct = (col_comments / total_cols * 100) if total_cols > 0 else 0
    
    try:
        tables = [r[0] for r in execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE'",
            (schema,)
        )]
    except:
        tables = []
    
    # Heuristic: cryptic names tend to be short segments joined by underscores
    # e.g., t_cust_mst, t_ord_dtl vs customers, order_details
    cryptic_count = 0
    for name in tables:
        parts = name.replace('_', ' ').split()
        avg_part_len = sum(len(p) for p in parts) / len(parts) if parts else 0
        if avg_part_len <= 4 and len(parts) >= 2:
            cryptic_count += 1
    
    cryptic_pct = (cryptic_count / len(tables) * 100) if tables else 0
    
    if comment_pct >= 50:
        return {
            'status': 'glossary',
            'message': f"✅ Business glossary detected — {int(comment_pct)}% of columns have descriptions. Using metadata for AI queries.",
            'type': 'success'
        }
    elif cryptic_pct >= 50 and comment_pct < 10:
        return {
            'status': 'cryptic_no_glossary',
            'message': f"⚠️ Cryptic object names detected ({int(cryptic_pct)}% abbreviated) with minimal glossary ({int(comment_pct)}% commented). "
                       f"For best results, add COMMENT ON to your tables and columns.",
            'type': 'warning'
        }
    else:
        return {
            'status': 'descriptive',
            'message': f"✅ Descriptive object names detected — using table/column names directly for AI queries.",
            'type': 'success'
        }


def _get_sample_queries(schema: str) -> dict:
    """Build sample queries dict for the dropdown based on connected schema.
    Loads from examples.yaml if available, falls back to built-in defaults.
    For genai_poc* schemas, also loads demo questions from genai_poc_demo section."""
    import yaml

    # Try loading schema-specific examples from examples.yaml
    examples_path = os.path.join(os.path.dirname(__file__), "examples.yaml")
    if os.path.exists(examples_path):
        try:
            with open(examples_path, 'r') as f:
                data = yaml.safe_load(f) or {}

            # For genai_poc* schemas, fall back to genai_poc examples if no exact match
            lookup_schema = schema
            if schema not in data and schema.startswith('genai_poc') and 'genai_poc' in data:
                lookup_schema = 'genai_poc'

            if lookup_schema in data and data[lookup_schema]:
                queries = {}
                for ex in data[lookup_schema]:
                    q = ex['question']
                    sql = ex.get('sql', '').strip()
                    join_count = sql.lower().count(' join ')
                    if join_count >= 2:
                        label = f"🔴 Complex: {q}"
                    elif join_count == 1 or 'group by' in sql.lower():
                        label = f"🟡 Medium: {q}"
                    else:
                        label = f"🟢 Simple: {q}"
                    queries[label] = q

                # Add demo questions for genai_poc* schemas
                if schema.startswith('genai_poc') and 'genai_poc_demo' in data:
                    queries["─── Additional Demo Questions ───"] = ""
                    for ex in data['genai_poc_demo']:
                        q = ex['question']
                        queries[f"🆕 {q}"] = q

                return queries
        except Exception:
            pass

    # Default queries for northwind / nw_abbr / unknown schemas
    queries = {
        "🟢 Simple: How many customers are there?": "How many customers are there?",
        "🟡 Medium: What are the top 5 products by total quantity ordered?": "What are the top 5 products by total quantity ordered?",
        "🔴 Complex: Which employees generated the most revenue by country, including the product categories they sold?": "Which employees generated the most revenue by country, including the product categories they sold?",
    }
    if schema in ('northwind', 'nw_abbr'):
        queries.update({
            "🟢 Simple: What are the top 5 most expensive products?": "What are the top 5 most expensive products?",
            "🟡 Medium: What's the average order value by country?": "What's the average order value by country?",
            "🟡 Medium: Which product categories sell the most?": "Which product categories sell the most?",
            "🔴 Complex: What's the monthly sales trend?": "What's the monthly sales trend?",
        })
    return queries


def show_main_app():
    """Show main application after setup."""
    setup_state = SetupState()
    state = setup_state.get_state()
    conn_info = state['connection']
    
    # Start SSM tunnel if using localhost (private cluster)
    if conn_info['host'] == 'localhost':
        import subprocess
        # Check if tunnel is already running
        try:
            result = subprocess.run(['pgrep', '-f', 'session-manager-plugin'], 
                                  capture_output=True, text=True)
            if not result.stdout.strip():
                # Tunnel not running, start it
                import boto3
                ec2 = boto3.client('ec2', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                redshift = boto3.client('redshift', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                
                # Get bastion instance
                instances = ec2.describe_instances(
                    Filters=[
                        {'Name': 'tag:Name', 'Values': ['sales-analyst-bastion']},
                        {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                    ]
                )
                
                if instances['Reservations']:
                    instance = instances['Reservations'][0]['Instances'][0]
                    bastion_id = instance['InstanceId']
                    
                    # Start bastion if stopped
                    if instance['State']['Name'] == 'stopped':
                        st.info("🔄 Starting bastion host (was stopped)...")
                        ec2.start_instances(InstanceIds=[bastion_id])
                        ec2.get_waiter('instance_running').wait(InstanceIds=[bastion_id])
                        time.sleep(30)  # Wait for SSM agent
                    
                    # Get cluster endpoint
                    cluster_info = redshift.describe_clusters(ClusterIdentifier='sales-analyst-cluster')
                    endpoint = cluster_info['Clusters'][0]['Endpoint']['Address']
                    
                    # Start tunnel in background
                    subprocess.Popen([
                        'aws', 'ssm', 'start-session',
                        '--target', bastion_id,
                        '--document-name', 'AWS-StartPortForwardingSessionToRemoteHost',
                        '--parameters', f'{{"host":["{endpoint}"],"portNumber":["5439"],"localPortNumber":["5439"]}}',
                        '--region', os.getenv('AWS_REGION', 'us-east-1')
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    st.info("🔄 Starting SSM tunnel... Please wait 5 seconds and refresh.")
                    time.sleep(5)
                    st.rerun()
        except:
            pass
    
    os.environ['REDSHIFT_HOST'] = conn_info['host']
    os.environ['REDSHIFT_DATABASE'] = conn_info['database']
    os.environ['REDSHIFT_SCHEMA'] = conn_info['schema']
    os.environ['REDSHIFT_USER'] = conn_info['user']
    os.environ['REDSHIFT_PASSWORD'] = conn_info['password']
    
    # Initialize components (cached in session state to avoid re-indexing on reruns)
    cache_key = f"indexed_{conn_info['schema']}_{conn_info['host']}"
    if cache_key not in st.session_state:
        bedrock = BedrockHelper(region_name=os.getenv('AWS_REGION', 'us-east-1'))
        vector_store = FAISSManager(bedrock_client=bedrock)
        with st.spinner("Indexing schema..."):
            glossary_status = load_metadata(vector_store, conn_info['schema'])
        workflow = AnalysisWorkflow(bedrock_helper=bedrock, vector_store=vector_store, monitor=None)
        st.session_state[cache_key] = {
            'bedrock': bedrock, 'vector_store': vector_store,
            'workflow': workflow, 'glossary_status': glossary_status
        }
    
    cached = st.session_state[cache_key]
    bedrock = cached['bedrock']
    vector_store = cached['vector_store']
    workflow = cached['workflow']
    glossary_status = cached['glossary_status']
    
    # Header
    st.title("📊 Sales Data Analyst")
    st.markdown("*Powered by Amazon Bedrock and Amazon Redshift*")
    
    # Show glossary detection status
    if glossary_status and glossary_status.get('message'):
        if glossary_status['type'] == 'warning':
            st.warning(glossary_status['message'])
        else:
            st.info(glossary_status['message'])
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📊 Connection Status")
        st.success("✅ Connected")
        st.markdown(f"**Cluster:** `{conn_info['host'].split('.')[0]}`")
        st.markdown(f"**Database:** `{conn_info['database']}`")
        st.markdown(f"**Schema:** `{conn_info['schema']}`")
        
        # Show available tables with expandable column details
        st.markdown("---")
        st.markdown("### 📋 Available Tables")
        try:
            schema_name = conn_info['schema']
            tables_result = execute_query(
                "SELECT c.relname, d.description FROM pg_catalog.pg_class c "
                "JOIN pg_catalog.pg_namespace n ON c.relnamespace = n.oid "
                "LEFT JOIN pg_catalog.pg_description d ON c.oid = d.objoid AND d.objsubid = 0 "
                "WHERE n.nspname = %s AND c.relkind = 'r' ORDER BY c.relname",
                (schema_name,)
            )
            if tables_result:
                for table_name, table_comment in tables_result:
                    label = f"📄 {table_name}"
                    if table_comment:
                        label += f" — _{table_comment.split(' - ')[0]}_"
                    with st.expander(label):
                        cols = execute_query(
                            "SELECT c.column_name, c.data_type, d.description "
                            "FROM information_schema.columns c "
                            "LEFT JOIN (SELECT cl.oid, cl.relname, ns.nspname FROM pg_catalog.pg_class cl "
                            "JOIN pg_catalog.pg_namespace ns ON cl.relnamespace = ns.oid WHERE cl.relkind = 'r') t "
                            "ON t.relname = c.table_name AND t.nspname = c.table_schema "
                            "LEFT JOIN pg_catalog.pg_description d ON t.oid = d.objoid AND d.objsubid = c.ordinal_position "
                            "WHERE c.table_schema = %s AND c.table_name = %s ORDER BY c.ordinal_position",
                            (schema_name, table_name)
                        )
                        for col_name, data_type, comment in cols:
                            if comment:
                                st.markdown(f"**`{col_name}`** ({data_type}) — {comment}")
                            else:
                                st.markdown(f"**`{col_name}`** ({data_type})")
        except Exception as e:
            st.error(f"Error loading tables: {str(e)}")
        
        # Create Abbreviated Schema button (only when connected to northwind)
        if conn_info['schema'] == 'northwind':
            st.markdown("---")
            st.markdown("### 🧪 Demo: Cryptic Schema")
            from src.utils.nw_abbr_bootstrapper import check_nw_abbr_exists, bootstrap_nw_abbr
            if check_nw_abbr_exists():
                st.success("✅ `nw_abbr` schema exists. Use Option 3 to connect to it.")
            else:
                st.caption("Create an abbreviated copy of Northwind with cryptic table/column names and business glossary metadata. Use it to demo the Relationship Manager on non-obvious schemas.")
                if st.button("🧪 Create nw_abbr Schema", key="create_nw_abbr"):
                    result = bootstrap_nw_abbr(northwind_schema='northwind', show_progress=True)
                    if result:
                        st.success("✅ Created! Go to **⬅️ Back to Setup** → **Option 3** → schema `nw_abbr` to try it.")
        
        # Relationship Management Panel
        st.markdown("---")
        st.markdown("### 🔗 Manage Relationships")
        
        schema_name = conn_info['schema']
        all_rels = get_all_relationships(execute_query, schema_name)
        
        if all_rels:
            for rel in all_rels:
                origin_icon = {"fk_constraint": "✅", "comment_fk": "📝", "yaml": "🔧"}.get(rel["origin"], "❓")
                desc = f" — {rel['description']}" if rel.get("description") else ""
                st.markdown(f"{origin_icon} `{rel['source_table']}.{rel['source_column']}` → `{rel['target_table']}.{rel['target_column']}`{desc}")
            st.caption("✅ FK constraint | 📝 COMMENT ON | 🔧 YAML/UI")
        else:
            st.info("No relationships found. Add some below.")
        
        with st.expander("➕ Add Relationship"):
            try:
                all_tables = [t[0] for t in execute_query(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name",
                    (schema_name,)
                )]
                all_cols_cache = {}
                for tbl in all_tables:
                    cols = execute_query(
                        "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
                        (schema_name, tbl)
                    )
                    all_cols_cache[tbl] = [c[0] for c in cols]
                
                src_table = st.selectbox("Source table", all_tables, key="rel_src_tbl")
                src_col = st.selectbox("Source column", all_cols_cache.get(src_table, []), key="rel_src_col")
                tgt_table = st.selectbox("Target table", all_tables, key="rel_tgt_tbl")
                tgt_col = st.selectbox("Target column", all_cols_cache.get(tgt_table, []), key="rel_tgt_col")
                rel_desc = st.text_input("Description (optional)", key="rel_desc")
                
                if st.button("Add Relationship", key="add_rel"):
                    save_yaml_relationship(schema_name, src_table, src_col, tgt_table, tgt_col, rel_desc)
                    # Clear cached index to force re-indexing
                    for key in list(st.session_state.keys()):
                        if key.startswith('indexed_'):
                            del st.session_state[key]
                    st.success("Relationship added! Re-indexing...")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Delete relationship
        yaml_rels = get_yaml_relationships(schema_name)
        if yaml_rels:
            with st.expander("🗑️ Remove YAML Relationship"):
                del_options = [f"{r['source_table']}.{r['source_column']} → {r['target_table']}.{r['target_column']}"
                               for r in yaml_rels]
                del_sel = st.selectbox("Select to remove", del_options, key="del_rel_sel")
                if st.button("Delete", key="del_rel"):
                    idx = del_options.index(del_sel)
                    r = yaml_rels[idx]
                    delete_yaml_relationship(schema_name,
                                             f"{r['source_table']}.{r['source_column']}",
                                             f"{r['target_table']}.{r['target_column']}")
                    for key in list(st.session_state.keys()):
                        if key.startswith('indexed_'):
                            del st.session_state[key]
                    st.success("Deleted! Re-indexing...")
                    st.rerun()
        
        if st.button("🔄 Re-index Schema", key="reindex"):
            for key in list(st.session_state.keys()):
                if key.startswith('indexed_'):
                    del st.session_state[key]
            st.rerun()
        
        # Back to setup button
        st.markdown("---")
        if st.button("⬅️ Back to Setup", key="back_to_setup"):
            # Clear cached index so re-indexing happens on next setup
            for key in list(st.session_state.keys()):
                if key.startswith('indexed_'):
                    del st.session_state[key]
            setup_state.update_state(setup_complete=False)
            st.rerun()
    
    # Query mode selection
    st.markdown("### Ask questions about your data")
    query_mode = st.radio("Choose input mode:", ["📋 Sample Questions", "✏️ Custom Question"], horizontal=True)
    
    question = ""
    
    if query_mode == "📋 Sample Questions":
        SAMPLE_QUERIES = _get_sample_queries(conn_info['schema'])
        
        selected = st.selectbox("💡 Select a question:", ["-- Select a question --"] + list(SAMPLE_QUERIES.keys()), index=0)
        question = SAMPLE_QUERIES.get(selected, '')
    else:
        question = st.text_input("💬 Enter your question:", placeholder="e.g., What are the top 10 customers by revenue?")
    
    if question:
        with st.spinner("Processing..."):
            try:
                result = workflow.execute(question, execute_query_with_columns)
                
                if "generated_sql" in result:
                    sql = result["generated_sql"]
                    
                    # Collapsible: Semantic search details
                    with st.expander("🔍 Semantic Search Details", expanded=False):
                        if result.get("retrieved_tables"):
                            st.markdown("**Tables identified:**")
                            for t in result["retrieved_tables"]:
                                st.markdown(f"- `{conn_info['schema']}.{t}`")
                        
                        # Show columns from filtered context (genuinely filtered by semantic search)
                        if result.get("relevant_context"):
                            st.markdown("**Columns identified:**")
                            for doc in result["relevant_context"]:
                                if doc.get('metadata', {}).get('type') == 'table':
                                    tbl = doc['metadata']['table']
                                    text = doc['text']
                                    if 'Columns:' in text:
                                        cols_part = text.split('Columns:')[1].split('\n')[0].strip()
                                        st.markdown(f"**`{tbl}`**: {cols_part}")
                    
                    # Plain-English SQL explanation
                    with st.expander("📖 Query Explanation", expanded=False):
                        with st.spinner("Generating explanation..."):
                            explanation = bedrock.invoke_model(
                                f"Explain this SQL query in plain English so a business user can understand what it does. "
                                f"Be concise (3-5 bullet points).\n\nSQL:\n{result['generated_sql']}",
                                temperature=0.3
                            )
                            st.markdown(explanation)
                    
                    st.subheader("📝 Generated SQL")
                    st.code(result["generated_sql"], language="sql")
                
                if "query_results" in result and result["query_results"]:
                    st.subheader("📊 Results")
                    results = result["query_results"]
                    
                    if isinstance(results, list) and len(results) > 0:
                        # Use column names captured during execution (no re-query needed)
                        column_names = result.get("column_names", [])
                        if column_names:
                            df = pd.DataFrame(results, columns=column_names)
                        else:
                            df = pd.DataFrame(results)
                        
                        st.dataframe(df, width="stretch")
                        
                        # Download button
                        csv = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv",
                            key="download_csv"
                        )
                
                if "analysis" in result:
                    st.subheader("💡 Analysis")
                    st.markdown(result["analysis"])
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")


def main():
    """Main application entry point."""
    st.set_page_config(page_title="Sales Data Analyst", page_icon="📊", layout="wide")
    
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Better form input styling */
    .stTextInput > div > div > input {
        border: 2px solid #e0e0e0;
        border-radius: 5px;
        padding: 10px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #0066cc;
        box-shadow: 0 0 0 1px #0066cc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    setup_state = SetupState()
    state = setup_state.get_state()
    
    # Validate state
    if state.get('setup_complete') and not state.get('schema_indexed'):
        st.warning("⚠️ Setup state is incomplete. Resetting...")
        setup_state.reset_state()
        time.sleep(1)
        st.rerun()
    
    if not setup_state.is_setup_complete():
        show_setup_wizard(setup_state)
    else:
        show_main_app()


if __name__ == "__main__":
    main()
