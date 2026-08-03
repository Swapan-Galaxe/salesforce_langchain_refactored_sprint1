# Test Configuration for Salesforce AI Assistant
# Use this to switch between mock data and real Salesforce API calls

import os
from services.salesforce_agent import SalesforceAgent
from tests.mock_salesforce_agent import MockSalesforceAgent

class TestConfig:
    """Configuration class to manage test vs production modes"""
    
    def __init__(self):
        # Check if we should use mock data
        self.use_mock_data = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
        
        # Salesforce credentials (only needed for real API calls)
        self.sf_username = os.getenv("SF_USERNAME")
        self.sf_password = os.getenv("SF_PASSWORD") 
        self.sf_token = os.getenv("SF_TOKEN")
        
    def get_salesforce_agent(self, limit=200):
        """Get appropriate Salesforce agent based on configuration"""
        
        if self.use_mock_data:
            print("[MOCK] Using mock data - No Salesforce API calls will be made")
            return MockSalesforceAgent(
                sf_username=self.sf_username,
                sf_password=self.sf_password,
                sf_token=self.sf_token,
                limit=limit
            )
        else:
            print("[LIVE] Using real Salesforce API")
            return SalesforceAgent(
                sf_username=self.sf_username,
                sf_password=self.sf_password,
                sf_token=self.sf_token,
                limit=limit
            )
    
    def print_config(self):
        """Print current configuration"""
        print("=" * 50)
        print("SALESFORCE AI ASSISTANT - TEST CONFIGURATION")
        print("=" * 50)
        print(f"Mode: {'[MOCK DATA]' if self.use_mock_data else '[REAL SALESFORCE API]'}")
        print(f"SF Username: {'***' if self.sf_username else 'Not Set'}")
        print(f"SF Password: {'***' if self.sf_password else 'Not Set'}")
        print(f"SF Token: {'***' if self.sf_token else 'Not Set'}")
        print("=" * 50)
        
        if self.use_mock_data:
            print("[OK] Mock mode enabled - safe to test without API limits")
            print("[INFO] To use real Salesforce: Set USE_MOCK_DATA=false in .env")
        else:
            print("[WARNING] Real API mode - will consume Salesforce API calls")
            print("[INFO] To use mock data: Set USE_MOCK_DATA=true in .env")
        print()

# Convenience function for easy import
def get_test_agent(limit=200):
    """Get configured Salesforce agent (mock or real based on environment)"""
    config = TestConfig()
    config.print_config()
    return config.get_salesforce_agent(limit)

# Test the configuration
if __name__ == "__main__":
    print("Testing configuration...")
    
    # Test with mock data
    os.environ["USE_MOCK_DATA"] = "true"
    config = TestConfig()
    config.print_config()
    
    agent = config.get_salesforce_agent(limit=5)
    leads = agent.get_leads()
    opportunities = agent.get_opportunities()
    
    print(f"✅ Successfully retrieved {len(leads)} leads and {len(opportunities)} opportunities")
    
    if hasattr(agent, 'get_test_data_summary'):
        print(agent.get_test_data_summary())