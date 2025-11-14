#!/usr/bin/env python3
"""
Apply session token fix to all AWS client files.
"""
import os

def fix_bedrock_helper():
    """Fix bedrock_helper.py"""
    content = '''"""
Amazon Bedrock helper for the GenAI Sales Analyst application.
"""
import boto3
import json
import os
from typing import List, Dict, Any, Optional


class BedrockHelper:
    """
    Helper class for Amazon Bedrock operations.
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize the Bedrock helper.
        
        Args:
            region_name: AWS region name
        """
        # Support both permanent and temporary credentials
        session_token = os.getenv('AWS_SESSION_TOKEN')
        
        if session_token:
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=session_token
            )
        else:
            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
    
    def invoke_model(self, 
                    prompt: str, 
                    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
                    max_tokens: int = 4096,
                    temperature: float = 0.7) -> str:
        """
        Invoke a Bedrock model with a prompt.
        
        Args:
            prompt: Input prompt text
            model_id: Bedrock model ID
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            
        Returns:
            Model response text
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
        
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=body
            )
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
        except Exception as e:
            print(f"Error invoking Bedrock: {str(e)}")
            raise
    
    def get_embeddings(self, text: str) -> List[float]:
        """
        Get embeddings for a text using Bedrock.
        
        Args:
            text: Input text
            
        Returns:
            List of embedding values
        """
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v1",
                body=json.dumps({"inputText": text})
            )
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
        except Exception as e:
            print(f"Error getting embeddings: {str(e)}")
            raise
'''
    
    with open('src/bedrock/bedrock_helper.py', 'w') as f:
        f.write(content)
    print("✅ Fixed src/bedrock/bedrock_helper.py")

def fix_redshift_connector():
    """Fix redshift_connector.py"""
    content = '''"""
Redshift connector for the GenAI Sales Analyst application.
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_redshift_connection():
    """
    Get a connection to Redshift.
    
    Returns:
        Redshift connection object
    """
    # Get credentials from environment variables
    host = os.getenv('REDSHIFT_HOST')
    if not host or host == 'NOT_SET':
        raise Exception("Redshift host not configured yet. Please wait for setup to complete.")
        
    port = os.getenv('REDSHIFT_PORT', '5439')
    database = os.getenv('REDSHIFT_DATABASE', 'sales_analyst')
    user = os.getenv('REDSHIFT_USER', 'admin')
    password = os.getenv('REDSHIFT_PASSWORD', 'Awsuser123$')
    
    # For localhost connections (SSM tunnel), force IPv4
    if host == 'localhost':
        host = '127.0.0.1'
    
    # Connect to Redshift with timeout
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connect_timeout=30  # Increased timeout for tunnel connections
    )
    
    return conn

def execute_query(query):
    """
    Execute a SQL query on Redshift.
    
    Args:
        query: SQL query to execute
        
    Returns:
        Query results
    """
    conn = get_redshift_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error executing query: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()
'''
    
    with open('src/utils/redshift_connector.py', 'w') as f:
        f.write(content)
    print("✅ Fixed src/utils/redshift_connector.py")

def create_aws_client_helper():
    """Create helper function for AWS clients with session token support"""
    content = '''"""
AWS client helper with session token support.
"""
import boto3
import os

def create_aws_client(service_name, region_name=None):
    """
    Create AWS client with automatic session token support.
    
    Args:
        service_name: AWS service name (e.g., 'ec2', 'redshift', 'iam')
        region_name: AWS region name
        
    Returns:
        Configured boto3 client
    """
    if not region_name:
        region_name = os.getenv('AWS_REGION', 'us-east-1')
    
    session_token = os.getenv('AWS_SESSION_TOKEN')
    
    if session_token:
        # Temporary credentials
        return boto3.client(
            service_name,
            region_name=region_name,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=session_token
        )
    else:
        # Permanent credentials
        return boto3.client(
            service_name,
            region_name=region_name,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
'''
    
    with open('src/utils/aws_client_helper.py', 'w') as f:
        f.write(content)
    print("✅ Created src/utils/aws_client_helper.py")

if __name__ == "__main__":
    print("🔧 Applying session token fixes...")
    fix_bedrock_helper()
    fix_redshift_connector()
    create_aws_client_helper()
    print("\n🎉 All fixes applied!")
    print("\nNow add to .env file:")
    print("AWS_SESSION_TOKEN=your_session_token_here")
