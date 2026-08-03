from openai import OpenAI
import os
from functools import lru_cache
import urllib3
import ssl
import certifi
from tests.test_data import TestSalesforceData

# Disable SSL warnings (for development only)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MockSalesforceAgent:
    """Mock Salesforce Agent that uses test data instead of real API calls"""
    
    def __init__(self, sf_username=None, sf_password=None, sf_token=None, limit=200):
        # Initialize test data instead of real Salesforce connection
        self.test_data = TestSalesforceData()
        
        # Initialize OpenAI client with SSL context
        import httpx
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        self._cache = {}
        self.limit = limit
        
        print("[MOCK] Using test data instead of Salesforce API")
        print(f"[MOCK] Generated {len(self.test_data.leads_data)} test leads")
        print(f"[MOCK] Generated {len(self.test_data.opportunities_data)} test opportunities")
        
    @lru_cache(maxsize=32)
    def get_leads(self, query=""):
        """Return test leads data instead of querying Salesforce"""
        leads = self.test_data.get_leads()
        
        # Apply limit
        limited_leads = leads[:self.limit] if self.limit else leads
        
        print(f"[MOCK] Returning {len(limited_leads)} test leads")
        return limited_leads
    
    @lru_cache(maxsize=32)
    def get_opportunities(self, query=""):
        """Return test opportunities data instead of querying Salesforce"""
        opportunities = self.test_data.get_opportunities()
        
        # Apply limit
        limited_opps = opportunities[:self.limit] if self.limit else opportunities
        
        print(f"[MOCK] Returning {len(limited_opps)} test opportunities")
        return limited_opps
    
    def score_lead(self, lead_data):
        """Score lead using OpenAI (same as real implementation)"""
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
        """Score opportunity using OpenAI (same as real implementation)"""
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
        """Generate follow-up actions using OpenAI (same as real implementation)"""
        prompt = f"""Generate 3 personalized follow-up actions for this {record_type}:
{record_data}
Be specific and actionable."""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def get_test_data_summary(self):
        """Get summary of test data for verification"""
        leads = self.test_data.get_leads()
        opportunities = self.test_data.get_opportunities()
        
        # Lead statistics
        lead_statuses = {}
        lead_sources = {}
        lead_ratings = {}
        
        for lead in leads:
            status = lead.get('Status', 'Unknown')
            source = lead.get('LeadSource', 'Unknown')
            rating = lead.get('Rating', 'None')
            
            lead_statuses[status] = lead_statuses.get(status, 0) + 1
            lead_sources[source] = lead_sources.get(source, 0) + 1
            lead_ratings[rating] = lead_ratings.get(rating, 0) + 1
        
        # Opportunity statistics
        opp_stages = {}
        total_pipeline = 0
        
        for opp in opportunities:
            stage = opp.get('StageName', 'Unknown')
            amount = opp.get('Amount', 0)
            
            opp_stages[stage] = opp_stages.get(stage, 0) + 1
            total_pipeline += amount
        
        summary = f"""
[TEST DATA SUMMARY]

[LEADS] ({len(leads)} total):
Status Distribution:
{chr(10).join([f"  - {status}: {count}" for status, count in lead_statuses.items()])}

Source Distribution:
{chr(10).join([f"  - {source}: {count}" for source, count in lead_sources.items()])}

Rating Distribution:
{chr(10).join([f"  - {rating}: {count}" for rating, count in lead_ratings.items()])}

[OPPORTUNITIES] ({len(opportunities)} total):
Stage Distribution:
{chr(10).join([f"  - {stage}: {count}" for stage, count in opp_stages.items()])}

Pipeline Value: ${total_pipeline:,}
Average Deal Size: ${total_pipeline/len(opportunities):,.0f}
"""
        return summary

# Test the mock agent
if __name__ == "__main__":
    print("Testing Mock Salesforce Agent...")
    
    # Create mock agent
    mock_agent = MockSalesforceAgent(limit=10)
    
    # Test leads
    print("\n=== TESTING LEADS ===")
    leads = mock_agent.get_leads()
    print(f"Retrieved {len(leads)} leads")
    
    if leads:
        print(f"Sample lead: {leads[0]['Name']} from {leads[0]['Company']}")
    
    # Test opportunities
    print("\n=== TESTING OPPORTUNITIES ===")
    opportunities = mock_agent.get_opportunities()
    print(f"Retrieved {len(opportunities)} opportunities")
    
    if opportunities:
        print(f"Sample opportunity: {opportunities[0]['Name']} - ${opportunities[0]['Amount']:,}")
    
    # Show test data summary
    print(mock_agent.get_test_data_summary())