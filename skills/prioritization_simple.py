from openai import OpenAI
import json
import os
import httpx
import ssl

# Disable SSL verification
ssl._create_default_https_context = ssl._create_unverified_context

class LeadPrioritizer:
    def __init__(self):
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        
    def prioritize_leads(self, leads):
        scored_leads = []
        for lead in leads:
            score = self._calculate_score(lead)
            scored_leads.append({**lead, 'priority_score': score})
        return sorted(scored_leads, key=lambda x: x['priority_score'], reverse=True)
    
    def _calculate_score(self, lead):
        prompt = f"""Analyze this lead and return ONLY a number 0-100:
{json.dumps(lead)}
Consider: Rating, Status, LeadSource, Company size indicators.
Score only:"""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        try:
            return int(''.join(filter(str.isdigit, response.choices[0].message.content[:3])))
        except:
            return 50

class OpportunityScorer:
    def __init__(self):
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        
    def score_opportunities(self, opportunities):
        scored_opps = []
        for opp in opportunities:
            score = self._calculate_score(opp)
            scored_opps.append({**opp, 'conversion_score': score})
        return sorted(scored_opps, key=lambda x: x['conversion_score'], reverse=True)
    
    def _calculate_score(self, opp):
        prompt = f"""Score this opportunity 0-100 for close likelihood:
{json.dumps(opp)}
Consider: Amount, StageName, Probability, CloseDate proximity.
Score only:"""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        try:
            return int(''.join(filter(str.isdigit, response.choices[0].message.content[:3])))
        except:
            return 50

class FollowUpGenerator:
    def __init__(self):
        http_client = httpx.Client(verify=False)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=http_client
        )
        
    def generate_actions(self, record, record_type="lead"):
        prompt = f"""Generate 3 specific follow-up actions for this {record_type}:
{json.dumps(record)}

Format as numbered list with actionable steps."""
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    def generate_followups(self, records):
        """Generate follow-up actions for a batch of records."""
        followups = []
        for record in records:
            followup_text = self.generate_actions(record, record_type=record.get('Type', 'record') if isinstance(record, dict) else 'record')
            followups.append({
                'Name': record.get('Name', 'Unknown') if isinstance(record, dict) else str(record),
                'followup_action': followup_text
            })
        return followups
