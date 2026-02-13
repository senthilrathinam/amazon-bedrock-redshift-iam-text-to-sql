"""
Configuration settings for the GenAI Sales Analyst application.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# AWS Bedrock settings
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
