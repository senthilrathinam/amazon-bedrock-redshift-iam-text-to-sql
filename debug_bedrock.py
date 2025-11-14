#!/usr/bin/env python3
"""
Debug Bedrock authentication and access issues.
"""
import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()

def debug_bedrock_access():
    """Debug Bedrock access issues."""
    
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    print(f"🔍 Debugging Bedrock access in region: {region}")
    
    # Check 1: Basic AWS credentials
    try:
        sts = boto3.client(
            'sts',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials valid")
        print(f"   Account: {identity['Account']}")
        print(f"   User/Role: {identity['Arn']}")
        
    except Exception as e:
        print(f"❌ AWS credentials invalid: {e}")
        return False
    
    # Check 2: Bedrock service availability
    try:
        bedrock = boto3.client(
            'bedrock',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        models = bedrock.list_foundation_models()
        print(f"✅ Bedrock service accessible")
        print(f"   Available models: {len(models['modelSummaries'])}")
        
    except Exception as e:
        print(f"❌ Bedrock service error: {e}")
        if "UnrecognizedClientException" in str(e):
            print("   → Check if Bedrock is available in this region")
        return False
    
    # Check 3: Model access
    try:
        claude_available = False
        titan_available = False
        
        for model in models['modelSummaries']:
            if model['modelId'] == 'anthropic.claude-3-sonnet-20240229-v1:0':
                claude_available = True
            if model['modelId'] == 'amazon.titan-embed-text-v1':
                titan_available = True
        
        if claude_available:
            print("✅ Claude 3 Sonnet available")
        else:
            print("❌ Claude 3 Sonnet not available - request model access")
            
        if titan_available:
            print("✅ Titan Embed available")
        else:
            print("❌ Titan Embed not available - request model access")
            
    except Exception as e:
        print(f"⚠️  Could not check model availability: {e}")
    
    # Check 4: Bedrock Runtime permissions
    try:
        bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Try a simple embedding call
        test_body = json.dumps({"inputText": "test"})
        
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            body=test_body
        )
        print("✅ Bedrock Runtime permissions OK")
        
    except Exception as e:
        print(f"❌ Bedrock Runtime error: {e}")
        if "AccessDeniedException" in str(e):
            print("   → Add bedrock:InvokeModel permission")
        elif "ValidationException" in str(e) and "access" in str(e).lower():
            print("   → Request model access in Bedrock console")
        return False
    
    print("\n🎉 All Bedrock checks passed!")
    return True

if __name__ == "__main__":
    debug_bedrock_access()
