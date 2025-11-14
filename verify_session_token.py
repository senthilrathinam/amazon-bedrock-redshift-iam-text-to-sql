#!/usr/bin/env python3
"""
Verify session token support in all files.
"""

def check_bedrock_helper():
    """Check if bedrock_helper.py has session token support."""
    try:
        with open('src/bedrock/bedrock_helper.py', 'r') as f:
            content = f.read()
        
        if 'AWS_SESSION_TOKEN' in content:
            print("✅ bedrock_helper.py has session token support")
            return True
        else:
            print("❌ bedrock_helper.py missing session token support")
            return False
    except Exception as e:
        print(f"❌ Error checking bedrock_helper.py: {e}")
        return False

def check_env_file():
    """Check if .env has session token."""
    try:
        with open('.env', 'r') as f:
            content = f.read()
        
        if 'AWS_SESSION_TOKEN=' in content and 'AWS_SESSION_TOKEN=your_session_token_here' not in content:
            print("✅ .env has session token configured")
            return True
        else:
            print("❌ .env missing or has placeholder session token")
            return False
    except Exception as e:
        print(f"❌ Error checking .env: {e}")
        return False

def test_bedrock_directly():
    """Test Bedrock access directly."""
    try:
        import sys
        sys.path.append('src')
        from bedrock.bedrock_helper import BedrockHelper
        
        bedrock = BedrockHelper()
        # Try to get embeddings (this calls Bedrock)
        embedding = bedrock.get_embeddings("test")
        print("✅ Bedrock access working")
        return True
    except Exception as e:
        print(f"❌ Bedrock access failed: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying session token setup...\n")
    
    checks = [
        ("Bedrock Helper", check_bedrock_helper),
        ("Environment File", check_env_file),
        ("Bedrock Access", test_bedrock_directly)
    ]
    
    all_passed = True
    for name, check_func in checks:
        result = check_func()
        if not result:
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 All checks passed!")
    else:
        print("⚠️  Some checks failed - fix the issues above")
