#!/usr/bin/env python3
"""
Debug session token issues.
"""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def debug_credentials():
    """Debug credential issues."""
    
    # Check environment variables
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY') 
    session_token = os.getenv('AWS_SESSION_TOKEN')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    print("🔍 Credential Check:")
    print(f"Access Key: {'✅ Set' if access_key else '❌ Missing'}")
    print(f"Secret Key: {'✅ Set' if secret_key else '❌ Missing'}")
    print(f"Session Token: {'✅ Set' if session_token else '❌ Missing'}")
    print(f"Region: {region}")
    
    if access_key:
        print(f"Access Key starts with: {access_key[:4]}...")
    if session_token:
        print(f"Token starts with: {session_token[:10]}...")
        print(f"Token length: {len(session_token)} chars")
    
    # Test basic AWS access
    try:
        sts = boto3.client(
            'sts',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token
        )
        
        identity = sts.get_caller_identity()
        print(f"\n✅ AWS Access Valid:")
        print(f"Account: {identity['Account']}")
        print(f"User/Role: {identity['Arn']}")
        
        # Check if token is about to expire
        if 'assumed-role' in identity['Arn']:
            print("ℹ️  Using temporary credentials (will expire)")
        
    except Exception as e:
        print(f"\n❌ AWS Access Failed: {e}")
        
        if "InvalidUserID.NotFound" in str(e):
            print("💡 Solution: Access key is wrong")
        elif "SignatureDoesNotMatch" in str(e):
            print("💡 Solution: Secret key is wrong")  
        elif "UnrecognizedClientException" in str(e) or "security token" in str(e):
            print("💡 Solution: Session token is expired/invalid - get new credentials")
        elif "AccessDenied" in str(e):
            print("💡 Solution: Credentials valid but lack permissions")
        
        return False
    
    return True

if __name__ == "__main__":
    debug_credentials()
