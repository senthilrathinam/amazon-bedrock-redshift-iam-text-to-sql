"""
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
