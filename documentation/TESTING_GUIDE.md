# Testing Guide - Real & Mock Data

## Overview

Complete guide for testing the Salesforce LangChain system with both real Salesforce data and mock test data.

---

## Quick Start

### Test with Mock Data (No Salesforce Required)
```bash
# 1. Set environment variable
# In .env file:
USE_MOCK_DATA=true
OPENAI_API_KEY=your_openai_key

# 2. Run tests
python tests/test_runner.py

# 3. Run test app
streamlit run tests/app_test.py
```

### Test with Real Data (Salesforce Required)
```bash
# 1. Set environment variables
# In .env file:
USE_MOCK_DATA=false
OPENAI_API_KEY=your_openai_key
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token

# 2. Run production app
streamlit run app_single_agent.py

# 3. Run multi-agent app
streamlit run app_multi_agent.py
```

### Enable LangSmith Monitoring (Optional)

To enable LangSmith tracing for debugging and observability, add the following to your `.env` and restart the app:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=salesforce-agent
```

Traces and execution details will appear in your LangSmith dashboard (https://smith.langchain.com).

---

## Test Suites

### 1. Basic System Tests
**File:** `tests/test_runner.py`

**What it tests:**
- Mock data generation (50 leads, 30 opportunities)
- AI scoring components (LeadPrioritizer, OpportunityScorer)
- LangChain agent initialization
- Streamlit dependencies

**Run:**
```bash
python tests/test_runner.py
```

**Expected output:**
```
[OK] Mock data generation
[OK] Lead prioritization
[OK] Opportunity scoring
[OK] Follow-up generation
[OK] LangChain agent initialization
[OK] Streamlit dependencies

TOTAL: 6/6 tests passed
```

### 2. Multi-Agent System Tests
**File:** `tests/test_multi_agent.py`

**What it tests:**
- Agent initialization (orchestrator + 4 specialists)
- Query routing (single and multi-agent)
- Agent status monitoring
- Async message processing
- Conversation history management

**Run:**
```bash
python tests/test_multi_agent.py
```

**Expected output:**
```
[PASS] Initialization
[PASS] Query Routing
[PASS] Status Monitoring
[PASS] Async Execution
[PASS] History Management

TOTAL: 5/5 tests passed
```

### 3. RAG System Tests
**File:** `tests/test_rag.py`

**What it tests:**
- ChromaDB initialization
- Lead/opportunity indexing
- Semantic search functionality
- Conversation memory
- Collection statistics
- Filtered search

**Run:**
```bash
python tests/test_rag.py
```

**Expected output:**
```
[PASS] Initialization
[PASS] Lead Indexing
[PASS] Opportunity Indexing
[PASS] Semantic Search (Leads)
[PASS] Semantic Search (Opportunities)
[PASS] Conversation Indexing
[PASS] Collection Statistics
[PASS] Filtered Search

TOTAL: 8/8 tests passed
```

---

## Mock Data Details

### Test Data Generator
**File:** `tests/test_data.py`

**Generates:**
- **50 Leads** with realistic data:
  - Names: Random first/last names
  - Companies: Tech companies (Acme Corp, TechStart Inc, etc.)
  - Status: Open, Contacted, Qualified, Unqualified
  - Rating: Hot, Warm, Cold
  - Sources: Web, Referral, Partner, Event
  - Dates: Random within last 90 days

- **30 Opportunities** with realistic data:
  - Names: Company + Product combinations
  - Amounts: $10,000 - $1,000,000
  - Stages: Prospecting, Qualification, Proposal, Negotiation, Closed Won/Lost
  - Probabilities: 10% - 90%
  - Close dates: Next 90 days
  - Types: New Business, Existing Customer

**Usage:**
```python
from tests.test_data import TestSalesforceData

data = TestSalesforceData()
leads = data.generate_leads()  # 50 leads
opps = data.generate_opportunities()  # 30 opportunities

# Export to JSON
data.export_to_json("test_data.json")
```

### Mock Salesforce Agent
**File:** `tests/mock_salesforce_agent.py`

**Purpose:** Drop-in replacement for real SalesforceAgent

**Features:**
- Same interface as real agent
- Returns test data instead of API calls
- Still uses OpenAI for AI scoring
- Prints "[MOCK]" messages to confirm test mode

**Usage:**
```python
from tests.mock_salesforce_agent import MockSalesforceAgent

agent = MockSalesforceAgent()
leads = agent.get_leads()  # Returns 50 test leads
opps = agent.get_opportunities()  # Returns 30 test opportunities
```

### Test Configuration Manager
**File:** `tests/test_config.py`

**Purpose:** Automatically switches between mock and real data

**Usage:**
```python
from tests.test_config import get_test_agent

# Reads USE_MOCK_DATA from .env
agent = get_test_agent()

# Returns MockSalesforceAgent if USE_MOCK_DATA=true
# Returns SalesforceAgent if USE_MOCK_DATA=false
```

---

## Test Applications

### Test-Enabled Streamlit App
**File:** `tests/app_test.py`

**Features:**
- Supports both mock and real data
- Shows test mode banner when using mock data
- Includes test data summary button
- Export test data to JSON
- Identical functionality to production app

**Run:**
```bash
streamlit run tests/app_test.py
```

**UI Indicators:**
- Orange banner: "🧪 TEST MODE - Using Mock Data"
- Test controls in sidebar
- Data export functionality

---

## Testing Scenarios

### Scenario 1: Test Without Salesforce (Mock Data)
**Goal:** Test system functionality without Salesforce API

**Steps:**
1. Set `USE_MOCK_DATA=true` in .env
2. Only need `OPENAI_API_KEY`
3. Run `python tests/test_runner.py`
4. Run `streamlit run tests/app_test.py`

**What works:**
- ✅ All AI scoring (LeadPrioritizer, OpportunityScorer)
- ✅ LangChain ReAct agent with 15 tools
- ✅ Multi-agent system (4 specialists + orchestrator)
- ✅ RAG semantic search
- ✅ All Streamlit UI features

**What doesn't work:**
- ❌ Real Salesforce data (uses test data instead)
- ❌ Salesforce API calls (mocked)

**Cost:** Only OpenAI API usage (~$0.10-0.50/day testing)

### Scenario 2: Test With Salesforce (Real Data)
**Goal:** Test with live Salesforce data

**Steps:**
1. Set `USE_MOCK_DATA=false` in .env
2. Add all Salesforce credentials
3. Run `streamlit run app_single_agent.py`
4. Run `streamlit run app_multi_agent.py`

**What works:**
- ✅ Everything from Scenario 1
- ✅ Real Salesforce data
- ✅ Live API calls
- ✅ Production-ready testing

**Cost:** OpenAI API + Salesforce API calls

### Scenario 3: Test RAG System
**Goal:** Test semantic search and vector database

**Steps:**
1. Install ChromaDB: `pip install chromadb==0.4.22`
2. Run `python tests/test_rag.py`
3. Run `streamlit run app_multi_agent.py`
4. Enable RAG toggle in sidebar

**What it tests:**
- ✅ Vector database initialization
- ✅ Embedding generation
- ✅ Semantic search
- ✅ Conversation memory
- ✅ Collection management

**Cost:** OpenAI embeddings (~$0.01/month)

### Scenario 4: Test Multi-Agent System
**Goal:** Test orchestrated specialist agents

**Steps:**
1. Run `python tests/test_multi_agent.py`
2. Run `streamlit run app_multi_agent.py`
3. Try multi-agent queries

**Example queries:**
- "Show at-risk deals and suggest follow-ups" (2 agents)
- "Complete pipeline analysis" (all 4 agents)
- "High priority leads" (1 agent)

**What it tests:**
- ✅ Agent routing
- ✅ Parallel execution
- ✅ Response synthesis
- ✅ Conversation history

---

## Troubleshooting

### "OpenAI API quota exceeded"
**Cause:** OpenAI rate limit reached  
**Solution:** 
- Check quota at platform.openai.com
- Wait for quota reset
- Upgrade OpenAI plan
- System requires OpenAI for all AI features

### "Salesforce login failed"
**Cause:** Invalid credentials or security token  
**Solution:**
- Verify credentials in .env
- Reset security token in Salesforce
- Use mock data mode: `USE_MOCK_DATA=true`

### "ChromaDB not found"
**Cause:** ChromaDB not installed  
**Solution:**
```bash
pip install chromadb==0.4.22
```

### "Test data not generating"
**Cause:** Import error or missing dependencies  
**Solution:**
```bash
pip install -r requirements.txt
python tests/test_runner.py
```

### "Mock mode not activating"
**Cause:** Environment variable not set  
**Solution:**
- Check .env file exists
- Verify `USE_MOCK_DATA=true`
- Restart application

---

## Test Data Validation

### Verify Mock Data Quality
```python
from tests.test_data import TestSalesforceData

data = TestSalesforceData()
leads = data.generate_leads()
opps = data.generate_opportunities()

# Check lead structure
print(f"Leads: {len(leads)}")
print(f"Sample lead: {leads[0]}")

# Check opportunity structure
print(f"Opportunities: {len(opps)}")
print(f"Sample opp: {opps[0]}")

# Export for inspection
data.export_to_json("validation.json")
```

### Compare Mock vs Real Data
```python
# Mock data
from tests.mock_salesforce_agent import MockSalesforceAgent
mock_agent = MockSalesforceAgent()
mock_leads = mock_agent.get_leads()

# Real data
from services.salesforce_agent import SalesforceAgent
real_agent = SalesforceAgent(username, password, token)
real_leads = real_agent.get_leads()

# Compare structures
print(f"Mock fields: {mock_leads[0].keys()}")
print(f"Real fields: {real_leads[0].keys()}")
```

---

## Performance Testing

### Test Response Times
```python
import time

# Test lead scoring
start = time.time()
scored_leads = lead_prioritizer.prioritize_leads(leads)
print(f"Lead scoring: {time.time() - start:.2f}s")

# Test opportunity scoring
start = time.time()
scored_opps = opportunity_scorer.score_opportunities(opps)
print(f"Opportunity scoring: {time.time() - start:.2f}s")

# Test LangChain agent
start = time.time()
response = agent.chat("Show top leads")
print(f"Agent response: {time.time() - start:.2f}s")
```

**Expected times:**
- Lead scoring (50 leads): 3-5 seconds
- Opportunity scoring (30 opps): 2-4 seconds
- LangChain agent query: 3-8 seconds
- Multi-agent query: 5-15 seconds

---

## Continuous Testing

### Daily Testing Routine
```bash
# Morning: Quick validation
python tests/test_runner.py

# Afternoon: Full system test
python tests/test_multi_agent.py
python tests/test_rag.py

# Evening: UI testing
streamlit run tests/app_test.py
```

### Pre-Deployment Checklist
- [ ] All unit tests pass (`test_runner.py`)
- [ ] Multi-agent tests pass (`test_multi_agent.py`)
- [ ] RAG tests pass (`test_rag.py`)
- [ ] Mock data mode works (`app_test.py`)
- [ ] Real data mode works (`app_single_agent.py`)
- [ ] No OpenAI quota errors
- [ ] No Salesforce API errors

---

## Test Coverage

### What's Tested
✅ Mock data generation  
✅ AI scoring (leads, opportunities)  
✅ LangChain ReAct agent  
✅ Multi-agent orchestration  
✅ RAG semantic search  
✅ Conversation memory  
✅ Streamlit UI  
✅ Agent routing  
✅ Async execution  

### What's Not Tested
❌ Salesforce API edge cases  
❌ Network failures  
❌ Large-scale data (1000+ records)  
❌ Multi-user concurrency  
❌ Long-running sessions  

---

## Best Practices

### 1. Start with Mock Data
- Test functionality without API costs
- Faster iteration
- No Salesforce dependency

### 2. Use Test Runner First
- Validates basic components
- Quick feedback (30 seconds)
- Catches configuration issues

### 3. Test RAG Separately
- RAG has additional dependencies
- Can be disabled if not needed
- Test with small datasets first

### 4. Monitor OpenAI Usage
- Track API calls during testing
- Use mock data to reduce costs
- Set up usage alerts

### 5. Version Control Test Data
- Keep test data consistent
- Document expected results
- Track changes over time

---

## Summary

| Test Type | File | Duration | Cost | Requires |
|-----------|------|----------|------|----------|
| **Basic** | test_runner.py | 30s | $0.01 | OpenAI |
| **Multi-Agent** | test_multi_agent.py | 1min | $0.02 | OpenAI |
| **RAG** | test_rag.py | 2min | $0.01 | OpenAI + ChromaDB |
| **UI (Mock)** | app_test.py | Manual | $0.05 | OpenAI |
| **UI (Real)** | app_single_agent.py | Manual | $0.10 | OpenAI + Salesforce |

**Total testing cost:** ~$0.20/day with mock data, ~$1-2/day with real data

