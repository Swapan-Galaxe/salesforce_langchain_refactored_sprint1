from openai import OpenAI
from simple_salesforce import Salesforce
import os
from functools import lru_cache
import urllib3
import ssl
import certifi
from datetime import date, datetime
from typing import Any, Dict, List, Optional

# Disable SSL warnings (for development only)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def calculate_deal_risk(opportunity: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    """Calculate an explainable 0-100 risk score from Salesforce fields.

    This deliberately remains deterministic: the LLM may explain the result,
    but it must not invent the underlying score or evidence.
    """
    today = today or date.today()
    score = 0
    reasons: List[str] = []

    def number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    probability = number(opportunity.get("Probability"))
    amount = number(opportunity.get("Amount"))
    stage = str(opportunity.get("StageName") or "")

    if probability < 30:
        score += 30
        reasons.append("Low win probability")
    elif probability < 50:
        score += 15
        reasons.append("Moderate win probability")

    if stage in {"Prospecting", "Qualification"}:
        score += 15
        reasons.append("Early-stage opportunity")

    close_date = opportunity.get("CloseDate")
    if close_date:
        try:
            close = datetime.strptime(str(close_date)[:10], "%Y-%m-%d").date()
            days_to_close = (close - today).days
            if days_to_close < 0:
                score += 30
                reasons.append("Close date has passed")
            elif days_to_close <= 14 and probability < 60:
                score += 20
                reasons.append("Close date is near with low probability")
        except (TypeError, ValueError):
            reasons.append("Close date is invalid")

    if amount >= 100000:
        score += 10
        reasons.append("High-value opportunity")

    score = min(score, 100)
    level = "Critical" if score >= 70 else "At Risk" if score >= 40 else "Healthy"
    return {
        "risk_score": score,
        "risk_level": level,
        "risk_reasons": reasons or ["No material risk indicators detected"],
    }


def recommend_next_action(opportunity: Dict[str, Any], risk: Optional[Dict[str, Any]] = None) -> str:
    """Return a reviewable next action grounded in the risk reasons."""
    risk = risk or calculate_deal_risk(opportunity)
    reasons = risk["risk_reasons"]

    if "Close date has passed" in reasons:
        return "Review the close date and schedule a deal-recovery meeting."
    if "Low win probability" in reasons:
        return "Contact the decision-maker and confirm objections and buying timeline."
    if "Close date is near with low probability" in reasons:
        return "Validate the close plan and identify missing approval or procurement steps."
    if "High-value opportunity" in reasons:
        return "Arrange an executive sponsorship or stakeholder review."
    if "Moderate win probability" in reasons:
        return "Schedule the next customer touchpoint and confirm the mutual action plan."
    return "Schedule the next customer touchpoint."


def build_deal_risk_dashboard(opportunities: Any, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Normalize opportunities for the Phase 1 dashboard."""
    if not isinstance(opportunities, list):
        return []

    rows = []
    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue
        risk = calculate_deal_risk(opportunity, today=today)
        rows.append({
            **opportunity,
            **risk,
            "next_action": recommend_next_action(opportunity, risk),
            "risk_value": (opportunity.get("Amount") or 0) if risk["risk_score"] >= 40 else 0,
        })
    return sorted(rows, key=lambda row: (row["risk_score"], row.get("Amount") or 0), reverse=True)

class SalesforceAgent:
    def __init__(self, sf_username, sf_password, sf_token, limit=200):
        # Disable SSL verification for Salesforce connection
        import requests
        session = requests.Session()
        session.verify = False
        self.sf = Salesforce(
            username=sf_username, 
            password=sf_password, 
            security_token=sf_token,
            session=session
        )
        
        # Initialize OpenAI client with SSL context
        import httpx
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        self._cache = {}
        self.limit = limit
        
    @lru_cache(maxsize=32)
    def get_leads(self, query=""):
        soql = f"SELECT Id, Name, Email, Company, Status, LeadSource, Rating FROM Lead WHERE IsConverted = false LIMIT {self.limit}"
        try:
            return self.sf.query(soql)['records']
        except Exception as e:
            return f"Error fetching leads: {str(e)}"
    
    @lru_cache(maxsize=32)
    def get_opportunities(self, query=""):
        soql = f"SELECT Id, Name, Amount, StageName, Probability, CloseDate, AccountId FROM Opportunity WHERE IsClosed = false LIMIT {self.limit}"
        try:
            return self.sf.query(soql)['records']
        except Exception as e:
            return f"Error fetching opportunities: {str(e)}"
    
    def score_lead(self, lead_data):
        if str(lead_data) in self._cache:
            return self._cache[str(lead_data)]
        
        prompt = f"""Score this lead from 0-100 based on conversion likelihood:
Lead: {lead_data}
Return only the numeric score and brief reason."""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = response.choices[0].message.content
        self._cache[str(lead_data)] = result
        return result
    
    def score_opportunity(self, opp_data):
        if str(opp_data) in self._cache:
            return self._cache[str(opp_data)]
        
        prompt = f"""Score this opportunity from 0-100 based on likelihood to close:
Opportunity: {opp_data}
Return only the numeric score and brief reason."""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result = response.choices[0].message.content
        self._cache[str(opp_data)] = result
        return result
    
    def generate_followup(self, record_data, record_type):
        prompt = f"""Generate 3 personalized follow-up actions for this {record_type}:
{record_data}
Be specific and actionable."""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
