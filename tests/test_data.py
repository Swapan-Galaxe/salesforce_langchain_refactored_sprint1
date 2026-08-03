# Test Data for Salesforce AI Assistant
# This file contains sample data to test LangChain functionality without hitting Salesforce APIs

import json
from datetime import datetime, timedelta
import random

class TestSalesforceData:
    """Mock Salesforce data for testing LangChain functionality"""
    
    def __init__(self):
        self.leads_data = self._generate_test_leads()
        self.opportunities_data = self._generate_test_opportunities()
    
    def _generate_test_leads(self):
        """Generate realistic test lead data"""
        companies = [
            "Acme Corporation", "TechStart Inc", "Global Systems", "Innovation Labs",
            "MegaCorp Industries", "StartupXYZ", "Enterprise Solutions", "Digital Dynamics",
            "Future Tech", "Alpha Industries", "Beta Systems", "Gamma Corp",
            "Delta Enterprises", "Epsilon Inc", "Zeta Technologies"
        ]
        
        first_names = [
            "John", "Sarah", "Michael", "Emily", "David", "Jessica", "Robert", "Ashley",
            "James", "Amanda", "William", "Jennifer", "Richard", "Lisa", "Thomas"
        ]
        
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
            "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"
        ]
        
        statuses = [
            "Open - Not Contacted", "Working - Contacted", "Closed - Converted", 
            "Closed - Not Converted", "Nurturing", "Qualified"
        ]
        
        lead_sources = [
            "Web", "Phone Inquiry", "Partner Referral", "Purchased List", 
            "Other", "Trade Show", "Word of mouth", "Employee Referral"
        ]
        
        ratings = ["Hot", "Warm", "Cold", None]
        
        leads = []
        base_date = datetime.now()
        
        for i in range(50):  # Generate 50 test leads
            created_date = base_date - timedelta(days=random.randint(1, 180))
            modified_date = created_date + timedelta(days=random.randint(0, 30))
            
            lead = {
                "Id": f"00Q5e0000{i:06d}",
                "Name": f"{random.choice(first_names)} {random.choice(last_names)}",
                "Email": f"test{i}@{random.choice(companies).lower().replace(' ', '').replace('.', '')}.com",
                "Company": random.choice(companies),
                "Status": random.choice(statuses),
                "LeadSource": random.choice(lead_sources),
                "Rating": random.choice(ratings),
                "CreatedDate": created_date.isoformat() + "Z",
                "LastModifiedDate": modified_date.isoformat() + "Z",
                "Phone": f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
                "Title": random.choice([
                    "CEO", "CTO", "VP Sales", "Director of Marketing", "IT Manager",
                    "Operations Manager", "Business Development", "Senior Developer"
                ]),
                "Industry": random.choice([
                    "Technology", "Healthcare", "Finance", "Manufacturing", "Retail",
                    "Education", "Government", "Non-profit"
                ])
            }
            leads.append(lead)
        
        return leads
    
    def _generate_test_opportunities(self):
        """Generate realistic test opportunity data"""
        opportunity_names = [
            "United Oil Platform Integration", "TechCorp CRM Implementation", 
            "Global Systems Upgrade", "MegaCorp Digital Transformation",
            "StartupXYZ Analytics Platform", "Enterprise Cloud Migration",
            "Innovation Labs AI Solution", "Alpha Industries Automation",
            "Beta Systems Integration", "Gamma Corp Modernization",
            "Delta Digital Platform", "Epsilon Cloud Services",
            "Zeta Analytics Implementation", "Future Tech Upgrade",
            "Digital Dynamics Solution", "Acme Corp Integration",
            "Advanced Systems Deal", "Strategic Partnership",
            "Enterprise License Agreement", "Custom Development Project"
        ]
        
        stage_names = [
            "Prospecting", "Qualification", "Needs Analysis", 
            "Value Proposition", "Id. Decision Makers", "Perception Analysis",
            "Proposal/Price Quote", "Negotiation/Review", "Closed Won", "Closed Lost"
        ]
        
        opportunities = []
        base_date = datetime.now()
        
        for i in range(30):  # Generate 30 test opportunities
            created_date = base_date - timedelta(days=random.randint(1, 120))
            close_date = base_date + timedelta(days=random.randint(10, 90))
            
            # Generate realistic amounts
            amount_ranges = [
                (10000, 50000),    # Small deals
                (50000, 150000),   # Medium deals  
                (150000, 500000),  # Large deals
                (500000, 1000000)  # Enterprise deals
            ]
            
            amount_range = random.choice(amount_ranges)
            amount = random.randint(amount_range[0], amount_range[1])
            
            # Probability based on stage
            stage = random.choice(stage_names)
            if stage in ["Prospecting", "Qualification"]:
                probability = random.randint(10, 30)
            elif stage in ["Needs Analysis", "Value Proposition"]:
                probability = random.randint(30, 50)
            elif stage in ["Id. Decision Makers", "Perception Analysis"]:
                probability = random.randint(50, 70)
            elif stage in ["Proposal/Price Quote", "Negotiation/Review"]:
                probability = random.randint(70, 90)
            elif stage == "Closed Won":
                probability = 100
            else:  # Closed Lost
                probability = 0
            
            opportunity = {
                "Id": f"0065e0000{i:06d}",
                "Name": random.choice(opportunity_names),
                "Amount": amount,
                "StageName": stage,
                "Probability": probability,
                "CloseDate": close_date.strftime("%Y-%m-%d"),
                "CreatedDate": created_date.isoformat() + "Z",
                "LastModifiedDate": (created_date + timedelta(days=random.randint(1, 10))).isoformat() + "Z",
                "AccountId": f"0015e0000{i:06d}",
                "Type": random.choice([
                    "New Customer", "Existing Customer - Upgrade", 
                    "Existing Customer - Replacement", "Existing Customer - Downgrade"
                ]),
                "LeadSource": random.choice([
                    "Web", "Phone Inquiry", "Partner Referral", "Purchased List",
                    "Other", "Trade Show", "Word of mouth", "Employee Referral"
                ]),
                "Description": f"Strategic opportunity for {random.choice(opportunity_names).lower()} with significant revenue potential."
            }
            opportunities.append(opportunity)
        
        return opportunities
    
    def get_leads(self):
        """Mock Salesforce get_leads API call"""
        return self.leads_data
    
    def get_opportunities(self):
        """Mock Salesforce get_opportunities API call"""
        return self.opportunities_data
    
    def export_to_json(self):
        """Export test data to JSON files for inspection"""
        with open('test_leads.json', 'w') as f:
            json.dump(self.leads_data, f, indent=2)
        
        with open('test_opportunities.json', 'w') as f:
            json.dump(self.opportunities_data, f, indent=2)
        
        print("Test data exported to test_leads.json and test_opportunities.json")

# Sample usage and data preview
if __name__ == "__main__":
    test_data = TestSalesforceData()
    
    print("=== SAMPLE TEST LEADS ===")
    for i, lead in enumerate(test_data.leads_data[:5]):
        print(f"\nLead {i+1}:")
        print(f"  Name: {lead['Name']}")
        print(f"  Company: {lead['Company']}")
        print(f"  Status: {lead['Status']}")
        print(f"  Rating: {lead['Rating']}")
        print(f"  Email: {lead['Email']}")
    
    print("\n=== SAMPLE TEST OPPORTUNITIES ===")
    for i, opp in enumerate(test_data.opportunities_data[:5]):
        print(f"\nOpportunity {i+1}:")
        print(f"  Name: {opp['Name']}")
        print(f"  Amount: ${opp['Amount']:,}")
        print(f"  Stage: {opp['StageName']}")
        print(f"  Probability: {opp['Probability']}%")
        print(f"  Close Date: {opp['CloseDate']}")
    
    # Export to JSON files
    test_data.export_to_json()