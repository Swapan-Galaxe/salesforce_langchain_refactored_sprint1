# System Architecture & Flow

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  Streamlit Web App (app_single_agent.py / app_multi_agent.py)          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    GUARDRAILS LAYER                         │
│  Input Validation | Rate Limiting | Output Sanitization    │
│  security.guardrails                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AGENT LAYER                              │
│  ┌──────────────────┐      ┌──────────────────────────┐   │
│  │ Single Agent     │      │ Multi-Agent System       │   │
│  │ (LangChain)      │      │ (Orchestrator + 4)       │   │
│  │ agents.conversational_agent_enhanced │ agents.orchestrator_agent │   │
│  └──────────────────┘      └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    RAG LAYER (Optional)                     │
│  services.rag_manager     | ChromaDB Vector Store           │
│  Semantic Search | Embeddings                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                               │
│  ┌──────────────────┐      ┌──────────────────────────┐   │
│  │ Salesforce API   │      │ AI Scoring               │   │
│  │ services.salesforce_agent │ skills.prioritization_simple │   │
│  └──────────────────┘      └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    LLM LAYER                                │
│  OpenAI GPT-4 | Reasoning | Generation | Embeddings        │
└─────────────────────────────────────────────────────────────┘
```

---

## Single Agent Flow (app_single_agent.py)

```
User Query
    ↓
[Guardrails] Input Validation
    ↓
[Guardrails] Rate Limit Check
    ↓
LangChain ReAct Agent
    ↓
Agent Reasoning (GPT-4)
    ↓
Tool Selection (1 of 15 tools)
    ↓
┌─────────────────────────────────────┐
│ Tool Execution                      │
│ ├─ get_leads() → Salesforce API    │
│ ├─ prioritize_leads() → AI Scoring │
│ └─ Return scored data               │
└─────────────────────────────────────┘
    ↓
Agent Synthesis (GPT-4)
    ↓
[Guardrails] Output Validation
    ↓
[Guardrails] PII Redaction
    ↓
Response to User
```

---

## Multi-Agent Flow (app_multi_agent.py)

```
User Query
    ↓
[Guardrails] Input Validation
    ↓
Orchestrator Agent
    ↓
Query Analysis & Routing
    ↓
┌─────────────────────────────────────────────────────────┐
│         Parallel Agent Execution (asyncio.gather)       │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Sales        │  │ Deal Risk    │  │ Pricing      │ │
│  │ Strategy     │  │ Agent        │  │ Agent        │ │
│  │ Agent        │  │              │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         ↓                  ↓                  ↓         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Lead         │  │ At-Risk      │  │ Discount     │ │
│  │ Analysis     │  │ Detection    │  │ Analysis     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
    ↓
Response Synthesis (Orchestrator)
    ↓
[Guardrails] Output Validation
    ↓
Combined Response to User
```

---

## RAG Flow (Semantic Search)

```
User Query: "deals about to close"
    ↓
Agent determines need for data
    ↓
┌─────────────────────────────────────┐
│ RAG Manager                         │
│                                     │
│ 1. Fetch Salesforce Data            │
│    ├─ get_opportunities()           │
│    └─ 30 opportunities returned     │
│                                     │
│ 2. Index Data (if not cached)       │
│    ├─ Convert to text               │
│    ├─ Generate embeddings (OpenAI)  │
│    └─ Store in ChromaDB             │
│                                     │
│ 3. Semantic Search                  │
│    ├─ Embed query                   │
│    ├─ Cosine similarity search      │
│    └─ Return top 5 matches          │
└─────────────────────────────────────┘
    ↓
Relevant opportunities returned
    ↓
Agent + LLM generates response
    ↓
Response to User
```

---

## Data Flow: Lead Scoring

```
Salesforce API
    ↓
get_leads() → 50 leads
    ↓
[Cache Check] 5-min TTL
    ↓
LeadPrioritizer.prioritize_leads()
    ↓
For each lead:
    ↓
┌─────────────────────────────────────┐
│ GPT-4 Scoring                       │
│                                     │
│ Input:                              │
│ - Name, Company, Status             │
│ - Email, Phone, Rating              │
│ - Created Date, Source              │
│                                     │
│ Analysis:                           │
│ - Engagement level                  │
│ - Timing/urgency                    │
│ - Company fit                       │
│ - Conversion likelihood             │
│                                     │
│ Output:                             │
│ - Priority Score (0-100)            │
│ - Reasoning                         │
└─────────────────────────────────────┘
    ↓
Scored leads sorted by priority
    ↓
Return to agent/UI
```

---

## Caching Strategy

```
Request for leads
    ↓
Check cache timestamp
    ↓
┌─────────────────────────────────────┐
│ Cache Hit (< 5 min old)             │
│ └─ Return cached data               │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Cache Miss (> 5 min old)            │
│ ├─ Fetch from Salesforce API       │
│ ├─ Update cache                     │
│ ├─ Update timestamp                 │
│ └─ Return fresh data                │
└─────────────────────────────────────┘
    ↓
Subsequent requests use cache
```

---

## Guardrails Flow

```
User Input
    ↓
┌─────────────────────────────────────┐
│ Input Validation                    │
│ ├─ Length check (1-2000 chars)     │
│ ├─ PII detection                    │
│ ├─ SQL injection check              │
│ ├─ Prompt injection check           │
│ └─ Profanity filter                 │
└─────────────────────────────────────┘
    ↓
[PASS] → Continue
[FAIL] → Return error + log violation
    ↓
┌─────────────────────────────────────┐
│ Rate Limit Check                    │
│ ├─ Get user request history         │
│ ├─ Count requests in last minute    │
│ ├─ Count requests in last hour      │
│ └─ Compare to limits                │
└─────────────────────────────────────┘
    ↓
[ALLOWED] → Process request
[BLOCKED] → Return rate limit error
    ↓
Agent Processing
    ↓
Agent Response
    ↓
┌─────────────────────────────────────┐
│ Output Validation                   │
│ ├─ Length truncation                │
│ ├─ PII redaction                    │
│ ├─ HTML sanitization                │
│ └─ SQL command removal              │
└─────────────────────────────────────┘
    ↓
Safe Response to User
```

---

## Async Multi-Agent Execution

```
User: "Show at-risk deals and suggest follow-ups"
    ↓
Orchestrator analyzes query
    ↓
Keywords detected: ["risk", "at-risk", "follow-up"]
    ↓
Route to: Deal Risk Agent + Follow-up Agent
    ↓
┌─────────────────────────────────────────────────────┐
│ Parallel Execution (asyncio.gather)                 │
│                                                     │
│  async def execute():                               │
│      task1 = deal_risk.chat_async(message)         │
│      task2 = followup.chat_async(message)          │
│      results = await asyncio.gather(task1, task2)  │
│      return results                                 │
└─────────────────────────────────────────────────────┘
    ↓
Both agents execute simultaneously
    ↓
┌──────────────────────┐  ┌──────────────────────┐
│ Deal Risk Agent      │  │ Follow-up Agent      │
│ ├─ Fetch opps        │  │ ├─ Fetch leads/opps  │
│ ├─ Score risks       │  │ ├─ Generate actions  │
│ └─ Return analysis   │  │ └─ Return plan       │
└──────────────────────┘  └──────────────────────┘
    ↓                          ↓
Response 1                 Response 2
    ↓                          ↓
┌─────────────────────────────────────┐
│ Orchestrator Synthesis              │
│ ├─ Combine responses                │
│ ├─ Remove duplicates                │
│ ├─ Generate unified answer (GPT-4)  │
│ └─ Add source attribution           │
└─────────────────────────────────────┘
    ↓
Synthesized Response to User
```

---

## Component Interactions

```
┌──────────────────────────────────────────────────────┐
│                  Streamlit UI                        │
│  ├─ User input                                       │
│  ├─ Display results                                  │
│  └─ Session state management                         │
└──────────────────────────────────────────────────────┘
         ↓                           ↑
         ↓                           ↑
┌──────────────────────────────────────────────────────┐
│              Guardrails Manager                      │
│  ├─ validate_input()                                 │
│  ├─ check_rate_limit()                               │
│  └─ validate_output()                                │
└──────────────────────────────────────────────────────┘
         ↓                           ↑
         ↓                           ↑
┌──────────────────────────────────────────────────────┐
│         Agent Layer (Single or Multi)                │
│  ├─ ConversationalSalesAgentEnhanced                 │
│  └─ OrchestratorAgent + 4 Specialists                │
└──────────────────────────────────────────────────────┘
         ↓                           ↑
         ↓                           ↑
┌──────────────────────────────────────────────────────┐
│              RAG Manager (Optional)                  │
│  ├─ index_leads()                                    │
│  ├─ index_opportunities()                            │
│  └─ semantic_search()                                │
└──────────────────────────────────────────────────────┘
         ↓                           ↑
         ↓                           ↑
┌──────────────────────────────────────────────────────┐
│           Data & Scoring Layer                       │
│  ├─ SalesforceAgent (API calls)                      │
│  ├─ LeadPrioritizer (AI scoring)                     │
│  ├─ OpportunityScorer (AI scoring)                   │
│  └─ FollowUpGenerator (AI actions)                   │
└──────────────────────────────────────────────────────┘
         ↓                           ↑
         ↓                           ↑
┌──────────────────────────────────────────────────────┐
│              External Services                       │
│  ├─ OpenAI API (GPT-4, embeddings)                   │
│  ├─ Salesforce API (SOQL queries)                    │
│  └─ ChromaDB (local vector store)                    │
└──────────────────────────────────────────────────────┘
```

---

## Technology Stack

**Frontend:**
- Streamlit (Web UI)
- Plotly (Charts)
- Pandas (Data manipulation)

**Backend:**
- Python 3.8+
- asyncio (Async execution)
- LangChain/LangGraph (Agent framework)

**AI/ML:**
- OpenAI GPT-4 (Reasoning, generation)
- OpenAI text-embedding-3-small (Embeddings)
- ChromaDB (Vector database)

**Data:**
- simple-salesforce (Salesforce API)
- Caching (in-memory, TTL-based)

**Security:**
- Custom guardrails system
- Rate limiting
- Input/output validation

---

## Deployment Architecture

**Current (Local):**
```
Developer Machine
├─ Python process (Streamlit)
├─ ChromaDB (local files)
└─ .env (credentials)
```

**Production (Cloud):**
```
┌─────────────────────────────────────┐
│ Load Balancer                       │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Application Servers (3x)            │
│ ├─ Streamlit app                    │
│ ├─ Agent system                     │
│ └─ Guardrails                       │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Redis (Caching + Rate Limiting)     │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Pinecone (Vector DB - Cloud)        │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ External APIs                       │
│ ├─ OpenAI                           │
│ └─ Salesforce                       │
└─────────────────────────────────────┘
```

---

## Performance Characteristics

**Latency:**
- Single agent query: 3-8 seconds
- Multi-agent query: 5-15 seconds
- RAG semantic search: 0.5-1 second
- Lead scoring (50): 3-5 seconds

**Throughput:**
- Current: 10-20 concurrent users
- With Celery: 100-1000 users
- With K8s: 100,000+ users

**Bottlenecks:**
1. OpenAI API rate limits (3,500 RPM)
2. Salesforce API limits (varies by license)
3. Single Python process (GIL)
4. Network latency

---

## Security Architecture

```
┌─────────────────────────────────────┐
│ User Input                          │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 1: Input Validation           │
│ ├─ Length check                     │
│ ├─ PII detection                    │
│ ├─ Injection detection              │
│ └─ Profanity filter                 │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 2: Rate Limiting              │
│ ├─ Per-user tracking                │
│ ├─ Per-minute limits                │
│ └─ Per-hour limits                  │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 3: SOQL Validation            │
│ ├─ Only SELECT allowed              │
│ ├─ LIMIT enforcement                │
│ └─ Block DELETE/UPDATE              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 4: Agent Execution            │
│ (Protected by guardrails)           │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 5: Output Sanitization        │
│ ├─ PII redaction                    │
│ ├─ HTML sanitization                │
│ └─ Length truncation                │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│ Layer 6: Audit Logging              │
│ ├─ Violation tracking               │
│ ├─ User identification              │
│ └─ Severity classification          │
└─────────────────────────────────────┘
```

---

## Summary

**Architecture Type:** Microservices-inspired modular design

**Key Patterns:**
- ReAct (Reasoning + Acting)
- Orchestration (Multi-agent coordination)
- RAG (Retrieval-Augmented Generation)
- Caching (TTL-based)
- Guardrails (Defense in depth)

**Scalability:** Horizontal (add more workers/servers)

**Reliability:** Caching, error handling, fallbacks

**Security:** Multi-layer validation and sanitization


---

## Guardrails Architecture

```
User Input
    ↓
┌─────────────────────────────────────┐
│ Layer 1: Input Validation           │
│ ├─ Length check (1-1000 chars)     │
│ ├─ PII detection                    │
│ ├─ SQL injection check              │
│ ├─ Prompt injection check           │
│ └─ Profanity filter                 │
└─────────────────────────────────────┘
    ↓
[PASS] → Continue | [FAIL] → Return error + log
    ↓
┌─────────────────────────────────────┐
│ Layer 2: Rate Limit Check           │
│ ├─ Get user request history         │
│ ├─ Count last minute (max 20)       │
│ ├─ Count last hour (max 200)        │
│ └─ Update request log               │
└─────────────────────────────────────┘
    ↓
[ALLOWED] → Process | [BLOCKED] → Return error
    ↓
Agent Processing
    ↓
AI Response
    ↓
┌─────────────────────────────────────┐
│ Layer 3: Output Validation          │
│ ├─ Length truncation                │
│ ├─ PII redaction                    │
│ ├─ HTML sanitization                │
│ └─ SQL command removal              │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Layer 4: Audit Logging              │
│ ├─ Log violations                   │
│ ├─ Assign severity                  │
│ └─ Store for 30 days                │
└─────────────────────────────────────┘
    ↓
Safe Response to User
```

---

## Evaluation Architecture

```
AI Response Generated
    ↓
┌─────────────────────────────────────────────────┐
│ Hallucination Detection                         │
│                                                 │
│ 1. Extract Claims                               │
│    ├─ Numerical facts ($100K, 85%, etc)        │
│    ├─ Named entities (John Doe, Acme Corp)     │
│    └─ Specific statements                      │
│                                                 │
│ 2. Verify Against Source Data                  │
│    ├─ Search in Salesforce data                │
│    ├─ Match claims to facts                    │
│    └─ Count verified vs unverified             │
│                                                 │
│ 3. Calculate Scores                            │
│    ├─ Hallucination Score = unverified/total   │
│    ├─ Confidence = verified/total              │
│    └─ Has Hallucination = score > 0.3          │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ RAG Quality Metrics (if RAG used)               │
│                                                 │
│ 1. Relevance Scoring                           │
│    ├─ Extract query terms                      │
│    ├─ Extract document terms                   │
│    └─ Calculate term overlap                   │
│                                                 │
│ 2. Diversity Scoring                           │
│    ├─ Count unique types                       │
│    ├─ Count unique stages                      │
│    └─ Calculate variety ratio                  │
│                                                 │
│ 3. Coverage Scoring                            │
│    ├─ Identify query terms                     │
│    ├─ Find covered terms in docs               │
│    └─ Calculate coverage ratio                 │
│                                                 │
│ 4. Precision/Recall (if expected docs)         │
│    ├─ True positives                           │
│    ├─ Precision = TP / retrieved               │
│    ├─ Recall = TP / expected                   │
│    └─ F1 = 2 * (P * R) / (P + R)              │
└─────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│ Quality Determination                           │
│                                                 │
│ IF hallucination detected:                     │
│    → "Poor - Hallucinations Detected"          │
│                                                 │
│ ELSE IF confidence ≥ 0.8 AND relevance ≥ 0.7:  │
│    → "Excellent"                                │
│                                                 │
│ ELSE IF confidence ≥ 0.6 AND relevance ≥ 0.5:  │
│    → "Good"                                     │
│                                                 │
│ ELSE IF confidence ≥ 0.4:                       │
│    → "Fair"                                     │
│                                                 │
│ ELSE:                                           │
│    → "Poor"                                     │
└─────────────────────────────────────────────────┘
    ↓
Display Quality Indicator in UI
```

---

## Complete System Flow with Guardrails & Evaluation

```
User Input
    ↓
Guardrails: Input Validation
    ↓
Guardrails: Rate Limit Check
    ↓
Agent Processing (Single or Multi-Agent)
    ↓
RAG Retrieval (if enabled)
    ↓
Salesforce Data Fetch
    ↓
AI Scoring & LLM Generation
    ↓
AI Response Generated
    ↓
Evaluation: Hallucination Detection
    ↓
Evaluation: RAG Quality Metrics
    ↓
Evaluation: Quality Determination
    ↓
Guardrails: Output Validation
    ↓
Guardrails: PII Redaction
    ↓
Display Response + Quality Indicator
    ↓
Guardrails: Audit Logging
    ↓
Evaluation: Metrics Storage
```

---

## Security & Quality Layers

```
┌─────────────────────────────────────────────────┐
│ Application Layer (Streamlit)                   │
│ ├─ User interface                               │
│ └─ Session management                           │
└─────────────────────────────────────────────────┘
         ↓                           ↑
┌─────────────────────────────────────────────────┐
│ Guardrails Layer                                │
│ ├─ Input validation                             │
│ ├─ Rate limiting                                │
│ ├─ Output sanitization                          │
│ └─ Audit logging                                │
└─────────────────────────────────────────────────┘
         ↓                           ↑
┌─────────────────────────────────────────────────┐
│ Agent Layer                                     │
│ ├─ Single agent (15 tools)                      │
│ └─ Multi-agent (orchestrator + 4 specialists)   │
└─────────────────────────────────────────────────┘
         ↓                           ↑
┌─────────────────────────────────────────────────┐
│ Evaluation Layer                                │
│ ├─ Hallucination detection                      │
│ ├─ RAG quality metrics                          │
│ └─ Quality grading                              │
└─────────────────────────────────────────────────┘
         ↓                           ↑
┌─────────────────────────────────────────────────┐
│ Data Layer                                      │
│ ├─ Salesforce API                               │
│ ├─ RAG (ChromaDB)                               │
│ └─ AI Scoring                                   │
└─────────────────────────────────────────────────┘
         ↓                           ↑
┌─────────────────────────────────────────────────┐
│ LLM Layer (OpenAI GPT-4)                        │
└─────────────────────────────────────────────────┘
```

---

## Summary

**Complete Protection:**
- 4 layers of guardrails (input, rate limit, output, audit)
- 2 evaluation systems (hallucination, RAG quality)
- Real-time quality indicators
- Comprehensive audit trail

**Performance Impact:**
- Guardrails: +50-100ms per request
- Evaluation: +100-200ms per request
- Total overhead: ~150-300ms (acceptable)

**Production Ready:**
- Full security coverage
- Quality assurance on every response
- Audit logging for compliance
- Real-time monitoring

