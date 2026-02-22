"""
Amazon Bedrock helper with IAM role authentication.
"""
import boto3
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class BedrockHelper:
    """
    Helper class for Amazon Bedrock operations using IAM role.
    """
    
    def __init__(self, region_name: str = None):
        if not region_name:
            region_name = os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or 'us-east-1'
        
        self.bedrock_runtime = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name
        )
    
    def invoke_model(self, 
                    prompt: str, 
                    model_id: str = None,
                    max_tokens: int = 4096,
                    temperature: float = 0.7) -> str:
        if not model_id:
            model_id = os.getenv('BEDROCK_MODEL_ID')
        
        try:
            response = self.bedrock_runtime.converse(
                modelId=model_id,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": max_tokens, "temperature": temperature}
            )
            return response['output']['message']['content'][0]['text']
        except Exception as e:
            print(f"Error invoking Bedrock: {str(e)}")
            raise
    
    def get_embeddings(self, text: str) -> List[float]:
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=json.dumps({"inputText": text})
            )
            response_body = json.loads(response['body'].read())
            return response_body['embedding']
        except Exception as e:
            print(f"Error getting embeddings: {str(e)}")
            raise
