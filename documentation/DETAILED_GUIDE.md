# Detailed System Guide

## 1. LangChain ReAct Agent

**What it is:** AI agent that reasons about which tools to use and acts by executing them.

**15 Tools:**
- get_top_leads, get_top_opportunities - Fetch and score data
- search_lead_by_name, get_opportunity_summary - Detailed analysis
- generate_followup_for_lead - Action recommendations
- compare_leads, compare_opportunities - Side-by-side comparison
- get_pipeline_summary, get_all_opportunities_summary - Overview metrics
- identify_stale_leads - Find inactive leads (30+ days)
- find_high_value_at_risk - High-value deals with low scores
- analyze_deal_velocity - Time in each stage
- suggest_discount_strategy - Pricing recommendations
- get_critical_actions_today - Urgent tasks

**How it works:**
1. User asks question
2. Agent analyzes query
3. Selects appropriate tool(s)
4. Executes tools
5. Synthesizes response
6. Returns natural language answer

**Memory:** MemorySaver maintains conversation context across queries.

**Caching:** 5-minute TTL reduces Salesforce API calls.

---

## 2. Multi-Agent System

**Architecture:** 1 Orchestrator + 4 Specialists

**Orchestrator Agent:**
- Routes queries to appropriate specialists
- Keyword-based matching
- Parallel execution for multi-agent queries
- Response synthesis

**Sales Strategy Agent:**
- Lead analysis and prioritization
- Opportunity scoring
- Revenue forecasting
- Pipeline optimization

**Deal Risk Agent:**
- At-risk deal identification
- Stalled deal detection (30+ days)
- Pipeline health assessment
- Risk categorization

**Pricing Agent:**
- Discount analysis
- Margin calculation
- Pricing recommendations
- Profitability optimization

**Follow-up Agent:**
- Action recommendations
- Email drafting
- Task prioritization
- Urgency-based sorting

**Async Execution:** Uses asyncio.gather() for parallel agent processing (3-5x faster).

---

## 3. RAG System (ChromaDB)

**What it does:** Semantic search across Salesforce data using vector embeddings.

**Collections:**
- leads - Indexed lead data
- opportunities - Indexed opportunity data
- conversations - Past chat history

**How it works:**
1. Data fetched from Salesforce
2. Converted to text representations
3. Embedded using OpenAI text-embedding-3-small
4. Stored in ChromaDB with metadata
5. Semantic search finds relevant items
6. Results returned to agent

**Benefits:**
- Natural language queries ("deals about to close")
- Pattern recognition (similar deals)
- Unstructured data search (descriptions, notes)
- Conversation memory

**Cost:** ~$0.01/month (embeddings only)

---

## 4. AI Scoring Components

**LeadPrioritizer:**
- Scores leads 0-100
- Factors: engagement, timing, fit, urgency
- Uses GPT-4 for intelligent scoring
- Fast batch processing

**OpportunityScorer:**
- Calculates win probability 0-100%
- Factors: stage, amount, age, activity
- Identifies at-risk deals
- Conversion likelihood prediction

**FollowUpGenerator:**
- Creates personalized action plans
- Context-aware recommendations
- Timing suggestions
- Next-best-actions

---

## 5. Salesforce Integration

**SalesforceAgent:**
- SOQL query execution
- Lead/opportunity fetching
- Real-time data sync
- Intelligent caching

**Mock Mode:**
- Test without Salesforce API
- 50 leads + 30 opportunities generated
- Same interface as real agent
- Perfect for development

---

## 6. Guardrails System

**Input Protection:**
- PII detection (email, phone, SSN, credit cards)
- SQL injection blocking
- Prompt injection detection
- Profanity filtering
- Length validation

**Rate Limiting:**
- 20 requests/minute (default)
- 200 requests/hour (default)
- Per-user tracking
- Automatic cleanup

**Output Protection:**
- PII redaction in responses
- HTML/script sanitization
- Length truncation
- Safe output guarantee

**SOQL Validation:**
- Only SELECT allowed
- LIMIT enforcement
- Max 100 records
- Block DELETE/UPDATE

**Audit Logging:**
- Violation tracking
- Severity levels
- User identification
- 30-day retention

---

## 7. Testing Infrastructure

**Mock Data:**
- 50 realistic leads
- 30 realistic opportunities
- Proper Salesforce structure
- Random but consistent

**Test Suites:**
- test_runner.py - Basic validation (6 tests)
- test_multi_agent.py - Multi-agent orchestration (5 tests)
- test_rag.py - RAG functionality (8 tests)
- test_guardrails.py - Security validation (8 test suites)

**Test Applications:**
- app_test.py - Mock/real data toggle
- Test mode banner
- Data export functionality

---

## 8. Performance & Scaling

**Current Performance:**
- Single query: 3-8 seconds
- Multi-agent: 5-15 seconds (parallel)
- Lead scoring: 3-5 seconds (50 leads)
- RAG search: 0.5-1 second

**Current Scale:**
- 10-20 concurrent users (asyncio)
- Single process, GIL-bound

**Scaling Options:**
- Celery + Redis: 100-1000 users
- FastAPI + Uvicorn: 50-500 users
- Kubernetes: 100,000+ users
- AWS Lambda: Unlimited (serverless)

---

## 9. Cost Analysis

**Monthly Costs:**
- OpenAI API: $70-150 (GPT-4 + embeddings)
- Salesforce: $0 (included in license)
- ChromaDB: $0 (local)
- Infrastructure: $0 (local)
- **Total: $70-150/month**

**vs Salesforce Agentforce:**
- Agentforce: $77+/user/month
- This system: $70-150/month total
- **Savings: 80%+ for 3+ users**

---

## 10. Key Advantages

**vs Direct OpenAI:**
- Autonomous tool selection
- Multi-step reasoning
- Conversation memory
- Structured outputs

**vs Salesforce Agentforce:**
- 10x more tools (15 vs 1-2)
- Unlimited customization
- 80% cost savings
- Advanced AI (GPT-4)
- Multi-agent orchestration

**vs Traditional CRM:**
- AI-powered insights
- Natural language interface
- Proactive recommendations
- Pattern recognition

---

## 11. File Structure

```
salesforce_langchain/
├── app_single_agent.py                          # Single agent web app
├── app_multi_agent.py                           # Multi-agent web app
├── agent_security.py                            # Security helpers
├── audit_log.json                               # Guardrails audit log
├── services/                                    # Core backend services
│   ├── evaluation.py                            # Evaluation framework
│   ├── evaluation_integration.py                # Evaluation examples
│   ├── rag_manager.py                           # ChromaDB RAG manager
│   ├── salesforce_agent.py                       # Salesforce API connector
│   ├── salesforce_service.py                     # Salesforce helper utilities
│   ├── __init__.py                              # Package exports
├── security/                                    # Guardrails package
│   ├── guardrails.py                            # Guardrails manager
│   ├── guardrails_integration.py                # Guardrails integration examples
│   ├── runtime.py                               # Runtime guardrails helpers
│   ├── README.md                                # Guardrails docs
│   ├── __init__.py                              # Package exports
├── skills/                                      # AI scoring and skills
│   ├── prioritization_simple.py                 # Lead/opportunity scoring
│   ├── skill_executor.py                        # Skill execution utilities
│   ├── __init__.py                              # Package exports
├── agents/                                      # Multi-agent system
│   ├── base_agent.py                            # Abstract base class
│   ├── orchestrator_agent.py                     # Query routing orchestrator
│   ├── sales_strategy_agent.py                   # Sales strategy agent
│   ├── deal_risk_agent.py                        # Risk analysis agent
│   ├── pricing_agent.py                          # Pricing optimization agent
│   ├── followup_agent.py                         # Follow-up recommendations
│   ├── README.md                                # Agent docs
│   ├── __init__.py                              # Package exports
├── tests/                                       # Test infrastructure
│   ├── test_data.py                             # Mock data generator
│   ├── mock_salesforce_agent.py                 # Mock Salesforce API
│   ├── test_config.py                           # Mock/real data switcher
│   ├── test_runner.py                           # Basic tests
│   ├── test_multi_agent.py                      # Multi-agent tests
│   ├── test_rag.py                              # RAG tests
│   ├── test_guardrails.py                       # Guardrails tests
│   ├── test_evaluation.py                       # Evaluation tests
│   ├── app_test.py                              # Test-enabled UI
└── documentation/                               # Docs files
    ├── ARCHITECTURE.md
    ├── DETAILED_GUIDE.md
    ├── SUMMARY.md
    ├── TESTING_GUIDE.md
```

---

## 12. Configuration

**.env file:**
```
OPENAI_API_KEY=your_key
SALESFORCE_USERNAME=your_username
SALESFORCE_PASSWORD=your_password
SALESFORCE_SECURITY_TOKEN=your_token
USE_MOCK_DATA=false
```

### LangSmith Observability (Optional)

LangSmith provides observability and tracing for LangChain-based agents. To enable tracing, add the following to your `.env` (optional):

```bash
# Enable LangChain / LangSmith tracing
LANGCHAIN_TRACING_V2=true
# LangSmith API key (get from https://smith.langchain.com)
LANGCHAIN_API_KEY=your_langsmith_api_key
# Optional project name for grouping traces
LANGCHAIN_PROJECT=salesforce-agent
```

Set `LANGCHAIN_TRACING_V2` to `true` and provide `LANGCHAIN_API_KEY` to start sending traces. Traces will appear in your LangSmith dashboard.

**Guardrails Config:**
- Strict: Production (tight limits)
- Lenient: Development (loose limits)
- Enterprise: Corporate (balanced)

---

## 13. Common Use Cases

**Lead Management:**
- "Show me top priority leads"
- "Find stale leads not contacted in 30 days"
- "Generate follow-up plan for John Doe"

**Opportunity Analysis:**
- "Which high-value deals are at risk?"
- "Complete pipeline analysis"
- "Compare top 2 opportunities"

**Risk Assessment:**
- "Show at-risk deals and suggest follow-ups"
- "Analyze pipeline health"
- "Find deals with pricing concerns"

**Strategic Planning:**
- "What should I focus on this week?"
- "Revenue forecast for this quarter"
- "Deal velocity analysis"

---

## 14. Troubleshooting

**OpenAI quota exceeded:**
- Check platform.openai.com
- Upgrade plan or wait for reset

**Salesforce connection failed:**
- Verify credentials in .env
- Reset security token
- Use mock data mode

**ChromaDB errors:**
- Install: pip install chromadb==0.4.22
- Check write permissions
- Delete ./chroma_db and reinitialize

**Slow performance:**
- Clear cache
- Reduce record limits
- Check network latency

---

## 15. Best Practices

**Development:**
- Use mock data mode
- Test with small datasets
- Monitor OpenAI usage

**Production:**
- Enable guardrails
- Set rate limits
- Monitor audit logs
- Regular cache refresh

**Security:**
- Never commit .env file
- Use strict guardrails config
- Review audit logs weekly
- Redact PII in outputs

**Performance:**
- Use caching (5-min TTL)
- Limit records per query
- Enable RAG for semantic search
- Consider async multi-agent for complex queries


---

## 16. Guardrails System

**Input Protection:**
- PII detection (email, phone, SSN, credit cards)
- SQL injection blocking
- Prompt injection detection
- Profanity filtering
- Length validation (1-1000 chars)

**Rate Limiting:**
- 20 requests/minute per user
- 200 requests/hour per user
- Automatic request tracking
- Violation logging

**Output Protection:**
- PII redaction in responses
- HTML/script sanitization
- SQL command removal
- Length truncation (max 10,000 chars)

**SOQL Validation:**
- Only SELECT queries allowed
- LIMIT clause required
- Max 100 records per query
- DELETE/UPDATE operations blocked

**Audit Logging:**
- All violations logged with timestamps
- Severity levels (HIGH/MEDIUM/LOW)
- User identification
- 30-day retention period

**Integration:**
- Active in app_single_agent.py (single agent)
- Active in app_multi_agent.py (multi-agent)
- Automatic validation on every request
- Real-time violation alerts

---

## 17. Evaluation Framework

**Hallucination Detection:**
- Extracts factual claims from AI responses
- Verifies claims against source Salesforce data
- Calculates hallucination score (0-1)
- Computes confidence level (0-1)
- Tracks verified vs unverified facts
- Logs all detected hallucinations

**RAG Quality Metrics:**
- Relevance: Query-document term overlap
- Diversity: Variety in retrieved results
- Coverage: How well query terms are covered
- Precision: Correct retrievals / total retrievals
- Recall: Correct retrievals / expected retrievals
- F1 Score: Harmonic mean of precision and recall

**Quality Grading:**
- Excellent: Confidence ≥80%, Relevance ≥70%
- Good: Confidence ≥60%, Relevance ≥50%
- Fair: Confidence ≥40%
- Poor: Confidence <40% or hallucinations detected

**Real-time Display:**
- Quality indicator shown after each response
- Color-coded badges (green/blue/orange/red)
- Confidence percentage displayed
- Hallucination warnings when detected
- RAG metrics shown when available

**Integration:**
- Active in app_single_agent.py (single agent)
- Active in app_multi_agent.py (multi-agent)
- Evaluates every AI response
- Stores metrics in session state
- Comprehensive reports available

---

## 18. Testing Infrastructure

**Test Suites:**
1. test_runner.py - Basic system (6 tests)
2. test_multi_agent.py - Multi-agent (5 tests)
3. test_rag.py - RAG system (8 tests)
4. test_guardrails.py - Security (8 test suites, 40+ tests)
5. test_evaluation.py - Quality metrics (5 test suites, 15+ tests)

**Total Test Coverage:**
- 32 test suites
- 70+ individual test cases
- Mock data testing
- Real data testing
- Security validation
- Quality assurance

**Run All Tests:**
```bash
python tests/test_runner.py
python tests/test_multi_agent.py
python tests/test_rag.py
python tests/test_guardrails.py
python tests/test_evaluation.py
```

