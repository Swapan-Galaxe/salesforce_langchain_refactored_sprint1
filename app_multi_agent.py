"""
Multi-Agent Streamlit Application
Async orchestrated multi-agent system with guardrails protection
"""

import streamlit as st
import asyncio
import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Import existing components
from services.salesforce_agent import SalesforceAgent
from skills.prioritization_simple import LeadPrioritizer, OpportunityScorer, FollowUpGenerator
from services.rag_manager import SalesforceRAGManager
from security.guardrails import GuardrailsManager
from services.evaluation import EvaluationManager

# Import multi-agent system
from agents import OrchestratorAgent
from security import ExecutionBudget, UserContext, SkillExecutor

# Load environment variables
load_dotenv()

use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"

# LangSmith / tracing configuration for multi-agent (env-driven)
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "salesforce-agent")

# Page configuration
st.set_page_config(
    page_title="Multi-Agent Sales Intelligence",
    page_icon="📈",
    layout="wide"
)

# UI styling for a polished experience
st.markdown("""
<style>
    .hero-banner {
        position: relative;
        background: linear-gradient(135deg, #0f172a 0%, #283046 100%);
        color: #ffffff;
        border-radius: 24px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
        text-align: left;
    }
    .mode-badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.14);
        color: #f8fafc;
        font-weight: 700;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.22);
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
        font-size: 0.88rem;
        margin: 0.75rem 0 1rem 0;
    }
    .sidebar-logo {
        width: 140px;
        display: block;
        margin: 0 auto 0.85rem auto;
    }
    .hero-banner h1 {
        margin: 0;
        font-size: 2.4rem;
        letter-spacing: -0.04em;
    }
    .hero-banner p {
        color: #cbd5e1;
        font-size: 1rem;
        margin-top: 0.6rem;
        line-height: 1.6;
        max-width: 760px;
        text-align: left;
    }
    body .stApp h1 {
        font-size: 2.2rem !important;
        text-align: left !important;
    }
    body .stApp h2 {
        font-size: 1.45rem !important;
        text-align: left !important;
    }
    body .stApp h3 {
        font-size: 1.05rem !important;
        text-align: left !important;
    }
    body .stApp h4 {
        font-size: 0.98rem !important;
        text-align: left !important;
    }
    body .stApp p {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        text-align: left !important;
    }
    .info-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 1.35rem;
        box-shadow: 0 16px 50px rgba(15, 23, 42, 0.08);
        transition: transform 0.2s ease;
    }
    .info-card:hover {
        transform: translateY(-2px);
    }
    .stButton>button {
        border-radius: 12px;
        height: 3rem;
        font-weight: 700;
    }
    .sidebar .stButton>button {
        border-radius: 12px;
    }
    .agent-card {
        background: #f8fafc;
        border-radius: 18px;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    .chat-header {
        color: #0f172a;
        font-size: 1.4rem;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-banner"><h1>Multi-Agent Sales Intelligence</h1><p>Orchestrated specialist agents for faster, safer, and more actionable Salesforce insights.</p></div>', unsafe_allow_html=True)

hero_col1, hero_col2, hero_col3 = st.columns(3)
hero_col1.metric("Mode", "Mock Data" if use_mock_data else "Salesforce Live")
hero_col2.metric("RAG", "Enabled" if st.session_state.rag_enabled else "Disabled")
hero_col3.metric("Agents", "4 Specialists")

# Initialize session state
if 'orchestrator' not in st.session_state:
    st.session_state.orchestrator = None
if 'rag_manager' not in st.session_state:
    st.session_state.rag_manager = None
if 'guardrails' not in st.session_state:
    st.session_state.guardrails = None
if 'evaluator' not in st.session_state:
    st.session_state.evaluator = None
if 'history_file' not in st.session_state:
    st.session_state.history_file = os.path.join(os.getcwd(), "session_history.json")
if 'chat_history' not in st.session_state:
    history_file = st.session_state.history_file
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                st.session_state.chat_history = json.load(f)
        except Exception:
            st.session_state.chat_history = []
    else:
        st.session_state.chat_history = []
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'rag_enabled' not in st.session_state:
    st.session_state.rag_enabled = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = "user_" + str(hash(st.session_state.get('session_id', 'default')))


def initialize_system():
    """Initialize multi-agent system with optional RAG and guardrails"""
    try:
        # Initialize OpenAI client
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            st.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            return False
        
        llm_client = OpenAI(api_key=openai_api_key)
        
        # Initialize guardrails
        guardrails_config = {
            "max_input_length": 1000,
            "min_input_length": 1,
            "rate_limit_requests_per_minute": 20,
            "rate_limit_requests_per_hour": 200,
            "block_pii": True,
            "block_profanity": True,
            "block_sql_injection": True,
            "block_prompt_injection": True,
            "enable_audit_log": True
        }
        st.session_state.guardrails = GuardrailsManager(guardrails_config)
        st.success("✅ Guardrails enabled!")

        # Prepare LangSmith callbacks if available
        callbacks = []
        try:
            from langchain.callbacks.langsmith import LangSmithTracer
            callbacks.append(LangSmithTracer())
        except Exception:
            try:
                from langchain.callbacks import LangSmithCallback
                callbacks.append(LangSmithCallback())
            except Exception:
                callbacks = []
        
        # Initialize evaluator
        st.session_state.evaluator = EvaluationManager()
        st.success("✅ Evaluation framework enabled!")
        
        # Initialize RAG manager if enabled
        rag_manager = None
        if st.session_state.rag_enabled:
            try:
                rag_manager = SalesforceRAGManager(
                    openai_api_key=openai_api_key,
                    persist_directory="./chroma_db"
                )
                st.session_state.rag_manager = rag_manager
                st.success("✅ RAG (ChromaDB) initialized!")
            except Exception as e:
                st.warning(f"RAG initialization failed: {str(e)}. Continuing without RAG.")
        
        # Initialize Salesforce agent
        sf_username = os.getenv('SALESFORCE_USERNAME') or os.getenv('SF_USERNAME')
        sf_password = os.getenv('SALESFORCE_PASSWORD') or os.getenv('SF_PASSWORD')
        sf_token = os.getenv('SALESFORCE_SECURITY_TOKEN') or os.getenv('SF_TOKEN')
        
        if use_mock_data or not all([sf_username, sf_password, sf_token]):
            if not use_mock_data:
                st.warning("Salesforce credentials not found. Using mock data mode.")
            else:
                st.info("USE_MOCK_DATA=true detected. Using mock data mode.")
            from tests.test_config import get_test_agent
            salesforce_agent = get_test_agent()
        else:
            salesforce_agent = SalesforceAgent(sf_username, sf_password, sf_token)
        
        # Initialize helper components
        lead_prioritizer = LeadPrioritizer()
        opportunity_scorer = OpportunityScorer()
        followup_generator = FollowUpGenerator()
        
        # Initialize orchestrator with RAG and optional callbacks
        st.session_state.orchestrator = OrchestratorAgent(
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            lead_prioritizer=lead_prioritizer,
            opportunity_scorer=opportunity_scorer,
            followup_generator=followup_generator,
            rag_manager=rag_manager,
            callbacks=callbacks if callbacks else None,
            skill_executor=SkillExecutor()
        )
        
        st.session_state.initialized = True
        return True
        
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        return False


async def process_message_async(message: str) -> str:
    """Process message through orchestrator asynchronously"""
    orchestrator = st.session_state.orchestrator
    response = await orchestrator.chat_async(
        message,
        {
            "user_context": UserContext(user_id=st.session_state.user_id),
            "execution_budget": ExecutionBudget(),
        },
    )
    return response


def process_message(message: str) -> str:
    """Sync wrapper for async message processing with guardrails and evaluation"""
    # Validate input with guardrails
    guardrails = st.session_state.guardrails
    user_id = st.session_state.user_id
    
    if guardrails:
        is_valid, error = guardrails.validate_input(message, user_id)
        if not is_valid:
            return f"⚠️ Input validation failed: {error}"
        
        is_allowed, error = guardrails.check_rate_limit(user_id)
        if not is_allowed:
            return f"⚠️ {error}"
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(process_message_async(message))
        
        # Get source data for evaluation
        source_data = []
        try:
            leads = st.session_state.orchestrator.salesforce_agent.get_leads()
            opps = st.session_state.orchestrator.salesforce_agent.get_opportunities()
            source_data.extend(leads)
            source_data.extend(opps)
        except:
            pass
        
        # Get RAG docs if enabled
        retrieved_docs = None
        if st.session_state.rag_enabled and st.session_state.rag_manager:
            # RAG docs would be retrieved here
            pass
        
        # Evaluate response
        if st.session_state.evaluator and source_data:
            evaluation = st.session_state.evaluator.evaluate_response(
                query=message,
                response=response,
                source_data=source_data,
                retrieved_docs=retrieved_docs
            )
            
            # Store evaluation in session state for display
            st.session_state.last_evaluation = evaluation
        
        # Validate output with guardrails
        if guardrails:
            is_valid, sanitized, error = guardrails.validate_output(response)
            return sanitized
        
        return response
    finally:
        loop.close()


def save_chat_history():
    """Persist chat history to disk so it can be restored after refresh."""
    try:
        with open(st.session_state.history_file, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not persist chat history: {e}")


# Main UI
st.title("Multi-Agent Sales Intelligence System")
st.markdown("**Orchestrated specialist agents for comprehensive sales analysis**")

# Sidebar - Agent Status
with st.sidebar:
    st.image("https://www.salesforce.com/content/dam/sfdc-docs/www/logos/logo-salesforce.svg", width=140, caption="Salesforce AI")
    st.markdown(f'<div class="mode-badge">{"TEST MODE: Mock Data" if use_mock_data else "Live Salesforce"}</div>', unsafe_allow_html=True)
    st.header("Agent Status")
    
    # RAG toggle
    st.session_state.rag_enabled = st.checkbox(
        "Enable RAG (Semantic Search)",
        value=st.session_state.rag_enabled,
        help="Use ChromaDB for semantic search and conversation memory"
    )
    
    if st.button("Initialize System", type="primary"):
        with st.spinner("Initializing multi-agent system..."):
            if initialize_system():
                st.success("✅ System initialized!")
            else:
                st.error("❌ Initialization failed")
    
    if st.session_state.initialized and st.session_state.orchestrator:
        st.markdown("---")
        
        # Guardrails status
        if st.session_state.guardrails:
            st.subheader("Guardrails Status")
            st.write("✅ Input validation enabled")
            st.write("✅ Rate limiting active")
            st.write("✅ Output sanitization enabled")
            
            # Show audit log summary
            audit_log = st.session_state.guardrails.get_audit_log()
            if audit_log:
                st.write(f"{len(audit_log)} violations logged")
                if st.button("View Violations"):
                    for entry in audit_log[-5:]:
                        st.caption(f"{entry['violation_type']} - {entry['timestamp'][:19]}")
        
        # Evaluation metrics
        if st.session_state.evaluator:
            st.subheader("Evaluation Metrics")
            report = st.session_state.evaluator.get_comprehensive_report()
            
            # Hallucination rate
            h_report = report["hallucination_report"]
            if h_report["total_evaluations"] > 0:
                rate = h_report["hallucination_rate"]
                if rate == 0:
                    st.success(f"✅ No hallucinations ({h_report['total_evaluations']} checks)")
                else:
                    st.warning(f"{rate:.1%} hallucination rate")
            
            # RAG quality
            rag_report = report["rag_quality_report"]
            metrics = rag_report.get("metrics", {})
            if metrics.get("total_evaluations", 0) > 0:
                st.write(f"RAG Quality: {rag_report['grade']}")
                st.write(f"Avg Relevance: {metrics.get('avg_relevance', 0):.2f}")
        
        st.markdown("---")
        
        # RAG stats
        if st.session_state.rag_enabled and st.session_state.rag_manager:
            st.subheader("RAG Statistics")
            try:
                stats = st.session_state.rag_manager.get_collection_stats()
                st.write(f"**Leads indexed:** {stats.get('leads', 0)}")
                st.write(f"**Opportunities indexed:** {stats.get('opportunities', 0)}")
                st.write(f"**Conversations indexed:** {stats.get('conversations', 0)}")
                
                if st.button("Clear RAG Data"):
                    st.session_state.rag_manager.clear_all()
                    st.success("RAG data cleared!")
                    st.rerun()
            except Exception as e:
                st.error(f"RAG stats error: {str(e)}")
        
        st.markdown("---")
        st.subheader("Active Agents")
        
        agent_status = st.session_state.orchestrator.get_agent_status()
        
        for agent_name, status in agent_status.items():
            with st.expander(f"{status['name']}"):
                st.write(f"**Role:** {status['role']}")
                st.write(f"**Messages:** {status['history_length']}")
                st.write(f"**Keywords:** {', '.join(status['capabilities'][:5])}...")
        
        st.markdown("---")
        
        if st.button("Clear All History"):
            st.session_state.orchestrator.clear_all_history()
            st.session_state.chat_history = []
            save_chat_history()
            st.success("History cleared!")
            st.rerun()

# Main chat interface
if st.session_state.chat_history:
    st.markdown("### Restored Chat Transcript")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

if not st.session_state.initialized:
    st.info("Click 'Initialize System' in the sidebar to start")
else:
    # Chat input
    if prompt := st.chat_input("Ask about leads, opportunities, risks, pricing, or follow-ups..."):
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        save_chat_history()
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process message
        with st.chat_message("assistant"):
            with st.spinner("Analyzing with specialist agents..."):
                try:
                    response = process_message(prompt)
                    st.markdown(response)
                    
                    # Show evaluation results if available
                    if hasattr(st.session_state, 'last_evaluation'):
                        evaluation = st.session_state.last_evaluation
                        quality = evaluation["overall_quality"]
                        confidence = evaluation["hallucination_check"]["confidence"]
                        
                        if "Excellent" in quality:
                            st.success(f"✅ Quality: {quality} | Confidence: {confidence:.0%}")
                        elif "Good" in quality:
                            st.info(f"ℹ️ Quality: {quality} | Confidence: {confidence:.0%}")
                        elif "Fair" in quality:
                            st.warning(f"⚠️ Quality: {quality} | Confidence: {confidence:.0%}")
                        else:
                            st.error(f"❌ Quality: {quality} | Confidence: {confidence:.0%}")
                        
                        # Show hallucination warning
                        if evaluation["hallucination_check"]["has_hallucination"]:
                            st.warning("⚠️ Potential hallucination detected. Please verify information.")
                        
                        # Show RAG metrics if available
                        if evaluation.get("rag_quality") and evaluation["rag_quality"].get("relevance_score"):
                            rag = evaluation["rag_quality"]
                            st.caption(f"RAG: Relevance {rag['relevance_score']:.2f} | Diversity {rag['diversity_score']:.2f}")
                    
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    save_chat_history()
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                    save_chat_history()

# Footer
st.markdown("---")

if st.session_state.rag_enabled:
    st.markdown("""
**Available Agents (RAG-Enhanced + Protected):**
- **Sales Strategy Agent**: Lead analysis with semantic search, opportunity insights, forecasting
- **Deal Risk Agent**: Risk assessment with pattern matching, deal health, churn prediction
- **Pricing Agent**: Discount analysis, pricing optimization, margin protection
- **Follow-up Agent**: Action recommendations, email drafting, task prioritization

**RAG Features:**
- Semantic search across leads and opportunities
- Conversation memory and context retrieval
- Pattern-based risk detection
- Historical analysis capabilities

**Security Features:**
- Input validation (PII, SQL injection, prompt injection)
- Rate limiting (20/min, 200/hour)
- Output sanitization and PII redaction
""")
else:
    st.markdown("""
**Available Agents (Protected):**
- **Sales Strategy Agent**: Lead analysis, opportunity insights, forecasting
- **Deal Risk Agent**: Risk assessment, deal health, churn prediction
- **Pricing Agent**: Discount analysis, pricing optimization, margin protection
- **Follow-up Agent**: Action recommendations, email drafting, task prioritization

**Security Features:**
- Input validation (PII, SQL injection, prompt injection)
- Rate limiting (20/min, 200/hour)
- Output sanitization and PII redaction
""")
