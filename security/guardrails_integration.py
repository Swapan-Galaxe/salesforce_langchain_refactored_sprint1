"""
Guardrails Integration Example
Shows how to integrate guardrails into existing agents and applications
"""

from security.guardrails import GuardrailsManager
from typing import Optional, Dict, Any
import streamlit as st


# ==================== INTEGRATION WITH AGENTS ====================

class ProtectedAgent:
    """Example of agent with guardrails protection"""
    
    def __init__(self, base_agent, guardrails_config: Optional[Dict[str, Any]] = None):
        self.agent = base_agent
        self.guardrails = GuardrailsManager(guardrails_config)
    
    def chat(self, message: str, user_id: str = "anonymous") -> str:
        """Protected chat method with guardrails"""
        
        # 1. Validate input
        is_valid, error = self.guardrails.validate_input(message, user_id)
        if not is_valid:
            return f"⚠️ Input validation failed: {error}"
        
        # 2. Check rate limit
        is_allowed, error = self.guardrails.check_rate_limit(user_id)
        if not is_allowed:
            return f"⚠️ {error}. Please try again later."
        
        # 3. Execute agent
        try:
            response = self.agent.chat(message)
        except Exception as e:
            return f"❌ Error: {str(e)}"
        
        # 4. Validate and sanitize output
        is_valid, sanitized, error = self.guardrails.validate_output(response)
        
        return sanitized


# ==================== STREAMLIT INTEGRATION ====================

def add_guardrails_to_streamlit():
    """Add guardrails to Streamlit app"""
    
    # Initialize guardrails in session state
    if 'guardrails' not in st.session_state:
        st.session_state.guardrails = GuardrailsManager({
            "max_input_length": 1000,
            "rate_limit_requests_per_minute": 10,
            "block_pii": True
        })
    
    # Get user input
    user_input = st.chat_input("Ask me anything...")
    
    if user_input:
        guardrails = st.session_state.guardrails
        
        # Get user ID (from session or IP)
        user_id = st.session_state.get('user_id', 'anonymous')
        
        # Validate input
        is_valid, error = guardrails.validate_input(user_input, user_id)
        if not is_valid:
            st.error(f"⚠️ {error}")
            return
        
        # Check rate limit
        is_allowed, error = guardrails.check_rate_limit(user_id)
        if not is_allowed:
            st.warning(f"⚠️ {error}")
            return
        
        # Process normally
        with st.chat_message("user"):
            st.write(user_input)
        
        # Get AI response
        response = process_message(user_input)
        
        # Validate output
        is_valid, sanitized, error = guardrails.validate_output(response)
        
        with st.chat_message("assistant"):
            st.write(sanitized)


def process_message(message: str) -> str:
    """Placeholder for actual message processing"""
    return f"Response to: {message}"


# ==================== MULTI-AGENT INTEGRATION ====================

def protect_orchestrator(orchestrator_agent):
    """Add guardrails to orchestrator agent"""
    
    guardrails = GuardrailsManager()
    
    # Store original chat_async method
    original_chat = orchestrator_agent.chat_async
    
    # Create protected version
    async def protected_chat(message: str, context: Optional[Dict[str, Any]] = None, 
                            user_id: str = "anonymous"):
        """Protected async chat with guardrails"""
        
        # Validate input
        is_valid, error = guardrails.validate_input(message, user_id)
        if not is_valid:
            return f"⚠️ Input validation failed: {error}"
        
        # Check rate limit
        is_allowed, error = guardrails.check_rate_limit(user_id)
        if not is_allowed:
            return f"⚠️ {error}"
        
        # Execute original method
        response = await original_chat(message, context)
        
        # Validate output
        is_valid, sanitized, error = guardrails.validate_output(response)
        
        return sanitized
    
    # Replace method
    orchestrator_agent.chat_async = protected_chat
    
    return orchestrator_agent


# ==================== SALESFORCE AGENT PROTECTION ====================

def protect_salesforce_agent(sf_agent):
    """Add guardrails to Salesforce agent"""
    
    guardrails = GuardrailsManager()
    
    # Protect get_leads method
    original_get_leads = sf_agent.get_leads
    
    def protected_get_leads(limit: int = 50):
        """Protected get_leads with limit validation"""
        
        # Validate limit
        if limit > guardrails.config["max_records_per_query"]:
            raise ValueError(f"Limit cannot exceed {guardrails.config['max_records_per_query']}")
        
        return original_get_leads(limit)
    
    sf_agent.get_leads = protected_get_leads
    
    # Protect get_opportunities method
    original_get_opps = sf_agent.get_opportunities
    
    def protected_get_opps(limit: int = 50):
        """Protected get_opportunities with limit validation"""
        
        if limit > guardrails.config["max_records_per_query"]:
            raise ValueError(f"Limit cannot exceed {guardrails.config['max_records_per_query']}")
        
        return original_get_opps(limit)
    
    sf_agent.get_opportunities = protected_get_opps
    
    return sf_agent


# ==================== CONFIGURATION EXAMPLES ====================

# Strict configuration (production)
STRICT_CONFIG = {
    "max_input_length": 500,
    "rate_limit_requests_per_minute": 5,
    "rate_limit_requests_per_hour": 50,
    "block_pii": True,
    "block_profanity": True,
    "block_sql_injection": True,
    "block_prompt_injection": True,
    "max_records_per_query": 50,
    "enable_audit_log": True
}

# Lenient configuration (development)
LENIENT_CONFIG = {
    "max_input_length": 2000,
    "rate_limit_requests_per_minute": 50,
    "rate_limit_requests_per_hour": 500,
    "block_pii": False,
    "block_profanity": False,
    "block_sql_injection": True,
    "block_prompt_injection": True,
    "max_records_per_query": 100,
    "enable_audit_log": False
}

# Enterprise configuration
ENTERPRISE_CONFIG = {
    "max_input_length": 1000,
    "rate_limit_requests_per_minute": 20,
    "rate_limit_requests_per_hour": 200,
    "block_pii": True,
    "block_profanity": True,
    "block_sql_injection": True,
    "block_prompt_injection": True,
    "max_records_per_query": 100,
    "enable_audit_log": True,
    "log_retention_days": 90
}


# ==================== USAGE IN app_single_agent.py ====================

def integrate_with_app():
    """
    Example of integrating guardrails into app_single_agent.py
    
    Add this to app_single_agent.py:
    """
    
    # At the top of app_single_agent.py
    from security.guardrails import GuardrailsManager
    from security.guardrails_integration import STRICT_CONFIG
    
    # Initialize guardrails
    if 'guardrails' not in st.session_state:
        st.session_state.guardrails = GuardrailsManager(STRICT_CONFIG)
    
    # In the chat input section
    user_input = st.chat_input("Ask me anything...")
    
    if user_input:
        # Get user ID
        user_id = st.session_state.get('user_id', 'anonymous')
        
        # Validate with guardrails
        guardrails = st.session_state.guardrails
        
        is_valid, error = guardrails.validate_input(user_input, user_id)
        if not is_valid:
            st.error(f"⚠️ {error}")
            st.stop()
        
        is_allowed, error = guardrails.check_rate_limit(user_id)
        if not is_allowed:
            st.warning(f"⚠️ {error}")
            st.stop()
        
        # Continue with normal processing...


# ==================== USAGE IN MULTI-AGENT APP ====================

def integrate_with_multi_agent_app():
    """
    Example of integrating guardrails into app_multi_agent.py
    """
    
    from agents import OrchestratorAgent
    from security.guardrails import GuardrailsManager
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent(...)
    
    # Add guardrails protection
    guardrails = GuardrailsManager()
    
    # Wrap chat_async method
    original_chat = orchestrator.chat_async
    
    async def protected_chat(message: str, context=None):
        # Validate
        is_valid, error = guardrails.validate_input(message, "user")
        if not is_valid:
            return f"⚠️ {error}"
        
        # Check rate limit
        is_allowed, error = guardrails.check_rate_limit("user")
        if not is_allowed:
            return f"⚠️ {error}"
        
        # Execute
        response = await original_chat(message, context)
        
        # Sanitize
        _, sanitized, _ = guardrails.validate_output(response)
        return sanitized
    
    orchestrator.chat_async = protected_chat


# ==================== MONITORING DASHBOARD ====================

def create_guardrails_dashboard():
    """Create Streamlit dashboard for guardrails monitoring"""
    
    st.title("🛡️ Guardrails Monitoring Dashboard")
    
    if 'guardrails' not in st.session_state:
        st.warning("Guardrails not initialized")
        return
    
    guardrails = st.session_state.guardrails
    
    # Audit log
    st.header("📋 Audit Log")
    
    audit_log = guardrails.get_audit_log()
    
    if audit_log:
        st.write(f"Total violations: {len(audit_log)}")
        
        # Group by violation type
        violation_counts = {}
        for entry in audit_log:
            vtype = entry['violation_type']
            violation_counts[vtype] = violation_counts.get(vtype, 0) + 1
        
        st.bar_chart(violation_counts)
        
        # Recent violations
        st.subheader("Recent Violations")
        for entry in audit_log[-10:]:
            st.write(f"**{entry['violation_type']}** - {entry['timestamp']}")
            st.write(f"User: {entry['user_id']}, Severity: {entry['severity']}")
            st.write(f"Details: {entry['details'][:100]}")
            st.markdown("---")
    else:
        st.success("No violations detected")
    
    # Rate limit status
    st.header("⏱️ Rate Limit Status")
    
    if guardrails.rate_limit_store:
        for user_id, timestamps in guardrails.rate_limit_store.items():
            st.write(f"**User {user_id}**: {len(timestamps)} requests in last hour")
    else:
        st.info("No rate limit data")


if __name__ == "__main__":
    print("Guardrails Integration Examples")
    print("=" * 50)
    print("\nTo integrate guardrails:")
    print("1. Import: from security.guardrails import GuardrailsManager")
    print("2. Initialize: guardrails = GuardrailsManager(config)")
    print("3. Validate input: guardrails.validate_input(user_input, user_id)")
    print("4. Check rate limit: guardrails.check_rate_limit(user_id)")
    print("5. Validate output: guardrails.validate_output(response)")

