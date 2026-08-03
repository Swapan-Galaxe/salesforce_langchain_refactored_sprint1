#!/usr/bin/env python
"""
Diagnostic script to identify startup issues
"""
import sys

print("=" * 60)
print("STARTUP DIAGNOSTICS")
print("=" * 60)

# Test 1: Check Python version
print(f"\n✓ Python: {sys.version}")

# Test 2: Check imports
modules_to_check = [
    'streamlit',
    'openai',
    'dotenv',
    'simple_salesforce',
    'chromadb',
    'langchain',
    'asyncio',
    'pydantic'
]

print("\nChecking imports:")
failed = []
for module in modules_to_check:
    try:
        __import__(module)
        print(f"  ✓ {module}")
    except ImportError as e:
        print(f"  ✗ {module} - MISSING")
        failed.append(module)

# Test 3: Check .env file
print("\nChecking environment:")
try:
    from dotenv import load_dotenv
    load_dotenv()
    import os
    
    openai_key = os.getenv('OPENAI_API_KEY')
    sf_user = os.getenv('SF_USERNAME') or os.getenv('SALESFORCE_USERNAME')
    
    if openai_key:
        print(f"  ✓ OPENAI_API_KEY: Found ({len(openai_key)} chars)")
    else:
        print(f"  ✗ OPENAI_API_KEY: Not found")
        
    if sf_user:
        print(f"  ✓ Salesforce credentials: Found")
    else:
        print(f"  ⚠ Salesforce credentials: Not found (will use mock mode)")
except Exception as e:
    print(f"  ✗ Error loading .env: {e}")

# Test 4: Check agent imports
print("\nChecking local modules:")
try:
    from services.salesforce_agent import SalesforceAgent
    print("  ✓ salesforce_agent.py")
except Exception as e:
    print(f"  ✗ salesforce_agent.py - {e}")
    failed.append('salesforce_agent')

try:
    from services.rag_manager import SalesforceRAGManager
    print("  ✓ rag_manager.py")
except Exception as e:
    print(f"  ✗ rag_manager.py - {e}")
    failed.append('rag_manager')

try:
    from agents import OrchestratorAgent
    print("  ✓ agents/OrchestratorAgent")
except Exception as e:
    print(f"  ✗ agents/OrchestratorAgent - {e}")
    failed.append('agents')

# Summary
print("\n" + "=" * 60)
if failed:
    print(f"❌ {len(failed)} ISSUES FOUND:")
    print("\nTo fix, run:")
    print("  python -m pip install --upgrade pip")
    print("  python -m pip install -r requirements.txt")
    print("\nThen restart Streamlit:")
    print("  streamlit run app_multi_agent.py")
else:
    print("✅ ALL CHECKS PASSED!")
    print("\nYou can now run:")
    print("  streamlit run app_multi_agent.py")

print("=" * 60)
