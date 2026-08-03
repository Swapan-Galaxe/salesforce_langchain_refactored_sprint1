"""
Guardrails System - Security, Validation, and Safety Controls
Protects against malicious inputs, rate limits, and ensures safe outputs
"""

import re
import time
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib


class GuardrailsManager:
    """Comprehensive guardrails for AI system security and safety"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        default_config = self._default_config()
        if config:
            # Merge provided config into defaults so partial configs do not break guardrails
            default_config.update(config)
        self.config = default_config
        
        # Rate limiting storage
        self.rate_limit_store: Dict[str, List[float]] = {}
        
        # Blocked patterns cache
        self.blocked_cache: Dict[str, bool] = {}
        
        # Audit log
        self.audit_log: List[Dict[str, Any]] = []
        # Persistent audit log file (optional)
        self.audit_log_file = self.config.get("audit_log_file", "audit_log.json")
        # Load existing audit log if present
        try:
            if os.path.exists(self.audit_log_file):
                with open(self.audit_log_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, list):
                        self.audit_log = existing
        except Exception:
            # If loading fails, keep an empty in-memory log
            self.audit_log = []
    
    def _default_config(self) -> Dict[str, Any]:
        """Default guardrails configuration"""
        return {
            # Input validation
            "max_input_length": 2000,
            "min_input_length": 1,
            "allowed_languages": ["en"],
            
            # Rate limiting
            "rate_limit_requests_per_minute": 20,
            "rate_limit_requests_per_hour": 200,
            "rate_limit_window_seconds": 60,
            
            # Content filtering
            "block_pii": True,
            "pii_mode": "block",
            "block_profanity": True,
            "block_sql_injection": True,
            "block_prompt_injection": True,
            
            # Output validation
            "max_output_length": 10000,
            "sanitize_output": True,
            
            # Security
            "enable_audit_log": True,
            "log_retention_days": 30,
            
            # Salesforce specific
            "max_records_per_query": 100,
            "allowed_soql_operations": ["SELECT"],
            "block_delete_operations": True
        }
    
    # ==================== INPUT VALIDATION ====================
    
    def validate_input(self, user_input: str, user_id: str = "anonymous") -> Tuple[bool, str]:
        """
        Validate user input against all guardrails
        
        Returns:
            (is_valid, error_message)
        """
        # Length check
        if len(user_input) < self.config["min_input_length"]:
            return False, "Input too short"
        
        if len(user_input) > self.config["max_input_length"]:
            return False, f"Input too long (max {self.config['max_input_length']} characters)"
        
        # Empty/whitespace check
        if not user_input.strip():
            return False, "Input cannot be empty"
        
        # PII handling: block only when explicitly configured. Business contact
        # data is common in CRM, so production defaults to masking downstream.
        if self.config.get("block_pii", False):
            has_pii, pii_type = self._detect_pii(user_input)
            if has_pii:
                self._log_violation(user_id, "PII_DETECTED", pii_type)
                return False, f"Input contains sensitive information ({pii_type}). Please remove it."
        
        # SQL injection detection
        if self.config["block_sql_injection"]:
            if self._detect_sql_injection(user_input):
                self._log_violation(user_id, "SQL_INJECTION", user_input[:100])
                return False, "Input contains potentially malicious SQL patterns"
        
        # Prompt injection detection
        if self.config["block_prompt_injection"]:
            if self._detect_prompt_injection(user_input):
                self._log_violation(user_id, "PROMPT_INJECTION", user_input[:100])
                return False, "Input contains prompt manipulation attempts"
        
        # Profanity check
        if self.config["block_profanity"]:
            if self._detect_profanity(user_input):
                self._log_violation(user_id, "PROFANITY", "blocked")
                return False, "Input contains inappropriate language"
        
        return True, ""
    
    def _detect_pii(self, text: str) -> Tuple[bool, str]:
        """Detect personally identifiable information"""
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.search(email_pattern, text):
            return True, "email address"
        
        # Phone number patterns (US)
        phone_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b',  # (123) 456-7890
        ]
        for pattern in phone_patterns:
            if re.search(pattern, text):
                return True, "phone number"
        
        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        if re.search(ssn_pattern, text):
            return True, "social security number"
        
        # Credit card pattern (basic)
        cc_pattern = r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'
        if re.search(cc_pattern, text):
            return True, "credit card number"
        
        return False, ""
    
    def _detect_sql_injection(self, text: str) -> bool:
        """Detect SQL injection attempts"""
        sql_keywords = [
            r'\bDROP\s+TABLE\b',
            r'\bDELETE\s+FROM\b',
            r'\bUPDATE\s+.*\s+SET\b',
            r'\bINSERT\s+INTO\b',
            r'\bEXEC\s*\(',
            r'\bUNION\s+SELECT\b',
            r';\s*DROP\b',
            r'--\s*$',
            r'/\*.*\*/',
            r'\bOR\s+1\s*=\s*1\b',
            r'\bAND\s+1\s*=\s*1\b'
        ]
        
        text_upper = text.upper()
        for pattern in sql_keywords:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_prompt_injection(self, text: str) -> bool:
        """Detect prompt injection/jailbreak attempts"""
        injection_patterns = [
            r'ignore\s+(previous|above|all)\s+instructions',
            r'disregard\s+(previous|above|all)',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now',
            r'new\s+instructions',
            r'system\s*:\s*',
            r'<\|im_start\|>',
            r'<\|im_end\|>',
            r'\[INST\]',
            r'\[/INST\]',
            r'roleplay\s+as',
            r'pretend\s+(you|to)\s+are',
            r'act\s+as\s+if',
            r'override\s+your',
            r'bypass\s+your'
        ]
        
        text_lower = text.lower()
        for pattern in injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_profanity(self, text: str) -> bool:
        """Detect profanity and inappropriate language"""
        # Basic profanity list (add more as needed)
        profanity_list = [
            'fuck', 'shit', 'damn', 'bitch', 'asshole',
            'bastard', 'crap', 'piss', 'dick', 'cock'
        ]
        
        text_lower = text.lower()
        for word in profanity_list:
            if re.search(r'\b' + word + r'\b', text_lower):
                return True
        
        return False
    
    # ==================== RATE LIMITING ====================
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user has exceeded rate limits
        
        Returns:
            (is_allowed, error_message)
        """
        current_time = time.time()
        
        # Initialize user's request history
        if user_id not in self.rate_limit_store:
            self.rate_limit_store[user_id] = []
        
        # Clean old requests (older than 1 hour)
        self.rate_limit_store[user_id] = [
            ts for ts in self.rate_limit_store[user_id]
            if current_time - ts < 3600
        ]
        
        # Check per-minute limit
        recent_requests = [
            ts for ts in self.rate_limit_store[user_id]
            if current_time - ts < 60
        ]
        
        if len(recent_requests) >= self.config["rate_limit_requests_per_minute"]:
            return False, f"Rate limit exceeded: {self.config['rate_limit_requests_per_minute']} requests per minute"
        
        # Check per-hour limit
        if len(self.rate_limit_store[user_id]) >= self.config["rate_limit_requests_per_hour"]:
            return False, f"Rate limit exceeded: {self.config['rate_limit_requests_per_hour']} requests per hour"
        
        # Add current request
        self.rate_limit_store[user_id].append(current_time)
        
        return True, ""
    
    # ==================== OUTPUT VALIDATION ====================
    
    def validate_output(self, output: str) -> Tuple[bool, str, str]:
        """
        Validate and sanitize AI output
        
        Returns:
            (is_valid, sanitized_output, error_message)
        """
        # Length check
        max_output = self.config.get("max_output_length", 10000)
        if len(output) > max_output:
            output = output[:max_output] + "... [truncated]"
        
        # Sanitize if enabled
        if self.config.get("sanitize_output", True):
            output = self._sanitize_output(output)
        
        # Check for leaked PII in output
        has_pii, pii_type = self._detect_pii(output)
        if has_pii:
            # Redact PII
            output = self._redact_pii(output)
            # Flag for human review and log the event
            self._log_violation("system", "PII_IN_OUTPUT", pii_type)
            self.flag_for_human_review(output, reason=f"PII redacted: {pii_type}")
        
        return True, output, ""

    def flag_for_human_review(self, output: str, reason: str = "manual_review") -> None:
        """Flag an output for human review by adding an audit entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "HUMAN_REVIEW",
            "reason": reason,
            "content_snippet": output[:1000]
        }
        self.audit_log.append(entry)
        # persist audit log
        try:
            with open(self.audit_log_file, "w", encoding="utf-8") as f:
                json.dump(self.audit_log, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _sanitize_output(self, text: str) -> str:
        """Sanitize output text"""
        # Remove potential HTML/script tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove potential SQL commands in output
        text = re.sub(r'\bDROP\s+TABLE\b', '[REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'\bDELETE\s+FROM\b', '[REDACTED]', text, flags=re.IGNORECASE)
        
        return text
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text"""
        # Redact emails
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL REDACTED]',
            text
        )
        
        # Redact phone numbers
        text = re.sub(
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            '[PHONE REDACTED]',
            text
        )
        
        # Redact SSN
        text = re.sub(
            r'\b\d{3}-\d{2}-\d{4}\b',
            '[SSN REDACTED]',
            text
        )
        
        # Redact API keys and bearer/session tokens
        text = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', '[SECRET REDACTED]', text)
        text = re.sub(r'Bearer\s+[A-Za-z0-9._-]+', 'Bearer [SECRET REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'00D[A-Za-z0-9]{12,15}![A-Za-z0-9._-]+', '[SALESFORCE SESSION REDACTED]', text)

        # Redact credit cards
        text = re.sub(
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            '[CARD REDACTED]',
            text
        )
        
        return text
    
    # ==================== SALESFORCE SPECIFIC ====================
    
    def validate_soql_query(self, query: str) -> Tuple[bool, str]:
        """Validate SOQL query for safety"""
        query_upper = query.upper()
        
        # Only allow SELECT operations
        if not query_upper.strip().startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Block DELETE operations
        if self.config["block_delete_operations"]:
            if 'DELETE' in query_upper:
                return False, "DELETE operations are not allowed"
        
        # Block UPDATE operations
        if 'UPDATE' in query_upper:
            return False, "UPDATE operations are not allowed"
        
        # Check for LIMIT clause
        if 'LIMIT' not in query_upper:
            return False, "LIMIT clause is required"
        
        # Extract LIMIT value
        limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > self.config["max_records_per_query"]:
                return False, f"LIMIT cannot exceed {self.config['max_records_per_query']}"
        
        return True, ""
    
    # ==================== AUDIT LOGGING ====================
    
    def _log_violation(self, user_id: str, violation_type: str, details: str):
        """Log security violation"""
        if not self.config["enable_audit_log"]:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "violation_type": violation_type,
            "details": details,
            "severity": self._get_severity(violation_type)
        }
        
        self.audit_log.append(log_entry)
        
        # persist audit log
        try:
            with open(self.audit_log_file, "w", encoding="utf-8") as f:
                json.dump(self.audit_log, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Clean old logs
        self._clean_audit_log()
    
    def _get_severity(self, violation_type: str) -> str:
        """Get severity level for violation type"""
        high_severity = ["SQL_INJECTION", "PROMPT_INJECTION", "PII_DETECTED"]
        medium_severity = ["PROFANITY", "RATE_LIMIT"]
        
        if violation_type in high_severity:
            return "HIGH"
        elif violation_type in medium_severity:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _clean_audit_log(self):
        """Remove old audit log entries"""
        retention_days = self.config["log_retention_days"]
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        self.audit_log = [
            entry for entry in self.audit_log
            if datetime.fromisoformat(entry["timestamp"]) > cutoff_date
        ]
    
    def get_audit_log(self, user_id: Optional[str] = None, 
                     violation_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve audit log entries"""
        filtered_log = self.audit_log
        
        if user_id:
            filtered_log = [e for e in filtered_log if e.get("user_id") == user_id]
        
        if violation_type:
            filtered_log = [e for e in filtered_log if e.get("violation_type") == violation_type]
        
        return filtered_log
    
    # ==================== DECORATOR ====================
    
    def protect(self, user_id_param: str = "user_id"):
        """
        Decorator to protect functions with guardrails
        
        Usage:
            @guardrails.protect(user_id_param="user_id")
            def chat(user_input: str, user_id: str):
                ...
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user_id
                user_id = kwargs.get(user_id_param, "anonymous")
                
                # Extract user_input (assume first string arg)
                user_input = None
                for arg in args:
                    if isinstance(arg, str):
                        user_input = arg
                        break
                
                if not user_input:
                    user_input = kwargs.get("message", kwargs.get("query", ""))
                
                # Validate input
                is_valid, error_msg = self.validate_input(user_input, user_id)
                if not is_valid:
                    raise ValueError(f"Input validation failed: {error_msg}")
                
                # Check rate limit
                is_allowed, error_msg = self.check_rate_limit(user_id)
                if not is_allowed:
                    raise ValueError(f"Rate limit exceeded: {error_msg}")
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Validate output
                if isinstance(result, str):
                    is_valid, sanitized, error_msg = self.validate_output(result)
                    return sanitized
                
                return result
            
            return wrapper
        return decorator


# ==================== USAGE EXAMPLES ====================

def example_usage():
    """Example usage of guardrails"""
    
    # Initialize guardrails
    guardrails = GuardrailsManager()
    
    # Example 1: Validate input
    user_input = "Show me top leads"
    is_valid, error = guardrails.validate_input(user_input, user_id="user123")
    if not is_valid:
        print(f"Input rejected: {error}")
    
    # Example 2: Check rate limit
    is_allowed, error = guardrails.check_rate_limit(user_id="user123")
    if not is_allowed:
        print(f"Rate limit exceeded: {error}")
    
    # Example 3: Validate output
    output = "Here are the top leads: john@example.com, 555-1234"
    is_valid, sanitized, error = guardrails.validate_output(output)
    print(f"Sanitized output: {sanitized}")
    
    # Example 4: Validate SOQL
    query = "SELECT Id, Name FROM Lead LIMIT 50"
    is_valid, error = guardrails.validate_soql_query(query)
    if not is_valid:
        print(f"Query rejected: {error}")
    
    # Example 5: Use decorator
    @guardrails.protect(user_id_param="user_id")
    def chat(message: str, user_id: str):
        return f"Response to: {message}"
    
    try:
        response = chat("Show me leads", user_id="user123")
        print(response)
    except ValueError as e:
        print(f"Guardrail violation: {e}")


if __name__ == "__main__":
    example_usage()
