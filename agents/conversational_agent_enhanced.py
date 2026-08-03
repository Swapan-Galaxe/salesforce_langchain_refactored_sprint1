from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from services.salesforce_agent import SalesforceAgent
from skills.prioritization_simple import LeadPrioritizer, OpportunityScorer, FollowUpGenerator
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime, timedelta
import os
import json
from functools import lru_cache
import time
import ssl
import httpx

# Disable SSL verification for development
os.environ["PYTHONHTTPSVERIFY"] = "0"
ssl._create_default_https_context = ssl._create_unverified_context
# LangSmith / tracing configuration (use env vars to enable in prod)
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "salesforce-agent")

# Structured output models
class LeadAnalysis(BaseModel):
    """Structured lead analysis output"""
    name: str = Field(description="Lead name")
    score: int = Field(description="Priority score 0-100", ge=0, le=100)
    urgency: Literal["low", "medium", "high", "critical"] = Field(description="Urgency level")
    next_action: str = Field(description="Recommended next action")
    should_alert_manager: bool = Field(description="Whether to alert sales manager")

class OpportunityAnalysis(BaseModel):
    """Structured opportunity analysis output"""
    name: str = Field(description="Opportunity name")
    amount: float = Field(description="Deal amount")
    score: int = Field(description="Conversion score 0-100", ge=0, le=100)
    risk_level: Literal["low", "medium", "high"] = Field(description="Risk level")
    days_stale: int = Field(description="Days since last activity")
    recommended_discount: float = Field(description="Suggested discount percentage", ge=0, le=100)

class ConversationalSalesAgentEnhanced:
    def __init__(self, sf_username=None, sf_password=None, sf_token=None, cache_ttl=300, sf_agent=None):
        # Allow injecting a pre-configured Salesforce agent (useful for tests/mock mode)
        if sf_agent is not None:
            self.sf_agent = sf_agent
        else:
            self.sf_agent = SalesforceAgent(sf_username, sf_password, sf_token, limit=50)
        self.prioritizer = LeadPrioritizer()
        self.scorer = OpportunityScorer()
        self.followup_gen = FollowUpGenerator()
        
        # Configure LangChain to use custom HTTP client
        import openai
        openai_http_client = httpx.Client(verify=False)

        # Optionally enable LangSmith tracer/callbacks when installed and configured
        callbacks = []
        try:
            # LangChain newer callback
            from langchain.callbacks.langsmith import LangSmithTracer
            callbacks.append(LangSmithTracer())
        except Exception:
            try:
                from langchain.callbacks import LangSmithCallback
                callbacks.append(LangSmithCallback())
            except Exception:
                # LangSmith not available or failed to initialize; continue without callbacks
                callbacks = []
        
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            http_client=openai_http_client,
            callbacks=callbacks if callbacks else None,
        )
        
        # Cache for Salesforce data (TTL in seconds, default 5 minutes)
        self.cache_ttl = cache_ttl
        self._leads_cache = None
        self._leads_cache_time = 0
        self._opps_cache = None
        self._opps_cache_time = 0
        self._scored_leads_cache = None
        self._scored_opps_cache = None
        
        # Memory for conversation context
        self.memory = MemorySaver()
        
        # Create agent with tools and memory
        self.agent = self._create_agent()
        
        # Thread ID for conversation continuity
        self.thread_id = "default"
    
    def _get_leads_cached(self):
        """Get leads with caching to avoid Salesforce API limits"""
        current_time = time.time()
        if self._leads_cache is None or (current_time - self._leads_cache_time) > self.cache_ttl:
            self._leads_cache = self.sf_agent.get_leads()
            self._leads_cache_time = current_time
            self._scored_leads_cache = None  # Invalidate scored cache
        return self._leads_cache
    
    def _get_opportunities_cached(self):
        """Get opportunities with caching to avoid Salesforce API limits"""
        current_time = time.time()
        if self._opps_cache is None or (current_time - self._opps_cache_time) > self.cache_ttl:
            self._opps_cache = self.sf_agent.get_opportunities()
            self._opps_cache_time = current_time
            self._scored_opps_cache = None  # Invalidate scored cache
        return self._opps_cache
    
    def _get_scored_leads_cached(self):
        """Get scored leads with caching"""
        if self._scored_leads_cache is None:
            leads = self._get_leads_cached()
            self._scored_leads_cache = self.prioritizer.prioritize_leads(leads)
        return self._scored_leads_cache
    
    def _get_scored_opportunities_cached(self):
        """Get scored opportunities with caching"""
        if self._scored_opps_cache is None:
            opps = self._get_opportunities_cached()
            self._scored_opps_cache = self.scorer.score_opportunities(opps)
        return self._scored_opps_cache
    
    def refresh_cache(self):
        """Manually refresh Salesforce data cache"""
        self._leads_cache = None
        self._opps_cache = None
        self._scored_leads_cache = None
        self._scored_opps_cache = None
    
    def _create_agent(self):
        # Original 8 tools
        @tool
        def get_top_leads(n: int = 5) -> str:
            """Get top N prioritized leads with their scores. Use this when user asks about best leads or top leads."""
            scored = self._get_scored_leads_cached()[:n]
            
            result = f"Top {n} Leads:\n"
            for i, lead in enumerate(scored, 1):
                result += f"{i}. {lead['Name']} ({lead['Company']}) - Score: {lead['priority_score']}\n"
            return result
        
        @tool
        def get_top_opportunities(n: int = 5) -> str:
            """Get top N opportunities with conversion scores. Use this when user asks about best opportunities or deals."""
            scored = self._get_scored_opportunities_cached()[:n]
            
            result = f"Top {n} Opportunities:\n"
            for i, opp in enumerate(scored, 1):
                result += f"{i}. {opp['Name']} - ${opp['Amount']:,.0f} - Score: {opp['conversion_score']}\n"
            return result
        
        @tool
        def search_lead_by_name(name: str) -> str:
            """Search for a specific lead by name and get their details and score."""
            scored = self._get_scored_leads_cached()
            
            for lead in scored:
                if name.lower() in lead['Name'].lower():
                    return json.dumps({
                        "Name": lead['Name'],
                        "Company": lead['Company'],
                        "Email": lead.get('Email', 'N/A'),
                        "Status": lead.get('Status', 'N/A'),
                        "Score": lead['priority_score']
                    }, indent=2)
            return f"Lead '{name}' not found"
        
        @tool
        def generate_followup_for_lead(lead_name: str) -> str:
            """Generate personalized follow-up actions for a specific lead by name."""
            scored = self._get_scored_leads_cached()
            
            for lead in scored:
                if lead_name.lower() in lead['Name'].lower():
                    return self.followup_gen.generate_actions(lead, "lead")
            return f"Lead '{lead_name}' not found"
        
        @tool
        def compare_leads(lead1_name: str, lead2_name: str) -> str:
            """Compare two leads and explain which one is better and why."""
            scored = self._get_scored_leads_cached()
            
            found_leads = []
            for lead in scored:
                if lead1_name.lower() in lead['Name'].lower() or lead2_name.lower() in lead['Name'].lower():
                    found_leads.append(lead)
            
            if len(found_leads) < 2:
                return "Could not find both leads for comparison"
            
            comparison = f"Comparison:\n"
            comparison += f"1. {found_leads[0]['Name']} - Score: {found_leads[0]['priority_score']}\n"
            comparison += f"2. {found_leads[1]['Name']} - Score: {found_leads[1]['priority_score']}\n"
            return comparison
        
        @tool
        def get_pipeline_summary() -> str:
            """Get quick pipeline summary with key metrics."""
            leads = self._get_leads_cached()
            opps = self._get_opportunities_cached()
            scored_leads = self._get_scored_leads_cached()
            scored_opps = self._get_scored_opportunities_cached()
            
            total_value = sum(o['Amount'] for o in scored_opps if o['Amount'])
            avg_lead_score = sum(l['priority_score'] for l in scored_leads) / len(scored_leads)
            avg_opp_score = sum(o['conversion_score'] for o in scored_opps) / len(scored_opps)
            
            return f"""📊 Quick Pipeline Summary:
- Total Leads: {len(leads)} (Avg Score: {avg_lead_score:.1f})
- Total Opportunities: {len(opps)}
- Pipeline Value: ${total_value:,.0f}
- Avg Opportunity Score: {avg_opp_score:.1f}"""
        
        @tool
        def get_opportunity_summary(opportunity_name: str) -> str:
            """Get comprehensive summary and analysis for a specific opportunity by name."""
            scored = self._get_scored_opportunities_cached()
            
            for opp in scored:
                if opportunity_name.lower() in opp['Name'].lower():
                    summary = f"""📊 COMPREHENSIVE OPPORTUNITY ANALYSIS

🏢 Opportunity: {opp['Name']}
💰 Amount: ${opp['Amount']:,.0f}
📈 Stage: {opp.get('StageName', 'N/A')}
📅 Close Date: {opp.get('CloseDate', 'N/A')}
🎯 AI Conversion Score: {opp['conversion_score']}/100
📊 Probability: {opp.get('Probability', 'N/A')}%

💡 INSIGHTS:
- Score Ranking: #{scored.index(opp) + 1} out of {len(scored)} opportunities
- Risk Level: {'Low' if opp['conversion_score'] >= 75 else 'Medium' if opp['conversion_score'] >= 50 else 'High'}
- Deal Size: {'Large' if opp['Amount'] > 200000 else 'Medium' if opp['Amount'] > 100000 else 'Small'}

📝 RECOMMENDED ACTIONS:
{self.followup_gen.generate_actions(opp, 'opportunity')}
"""
                    return summary
            return f"Opportunity '{opportunity_name}' not found"
        
        @tool
        def get_all_opportunities_summary() -> str:
            """Get summary of all opportunities with key metrics and insights."""
            scored = self._get_scored_opportunities_cached()
            
            total_value = sum(o['Amount'] for o in scored if o['Amount'])
            avg_score = sum(o['conversion_score'] for o in scored) / len(scored)
            high_value = [o for o in scored if o['Amount'] > 200000]
            hot_deals = [o for o in scored if o['conversion_score'] >= 80]
            
            stages = {}
            for opp in scored:
                stage = opp.get('StageName', 'Unknown')
                stages[stage] = stages.get(stage, 0) + 1
            
            summary = f"""📊 COMPLETE OPPORTUNITY PIPELINE SUMMARY

💰 FINANCIAL OVERVIEW:
- Total Pipeline Value: ${total_value:,.0f}
- Number of Opportunities: {len(scored)}
- Average Deal Size: ${total_value/len(scored):,.0f}
- High-Value Deals (>$200K): {len(high_value)}

🎯 CONVERSION ANALYSIS:
- Average AI Score: {avg_score:.1f}/100
- Hot Deals (Score ≥80): {len(hot_deals)}
- Deals Needing Attention (Score <50): {len([o for o in scored if o['conversion_score'] < 50])}

📈 STAGE BREAKDOWN:
{chr(10).join([f'- {stage}: {count} deals' for stage, count in stages.items()])}

🏆 TOP 5 OPPORTUNITIES:
{chr(10).join([f'{i+1}. {o["Name"]} - ${o["Amount"]:,.0f} (Score: {o["conversion_score"]})' for i, o in enumerate(scored[:5])])}

⚠️ PRIORITY ACTIONS:
- Focus on {len(hot_deals)} hot deals with high conversion probability
- Review {len([o for o in scored if o['conversion_score'] < 50])} underperforming opportunities
- Total potential revenue at risk: ${sum(o['Amount'] for o in scored if o['conversion_score'] < 50):,.0f}
"""
            return summary
        
        # NEW TOOLS - Using existing Salesforce data
        
        @tool
        def identify_stale_leads(days: int = 30) -> str:
            """Find leads that haven't been contacted or updated in specified days. Default 30 days."""
            scored = self._get_scored_leads_cached()
            
            stale = []
            for lead in scored:
                # Check LastModifiedDate or LastActivityDate
                last_modified = lead.get('LastModifiedDate', '')
                if last_modified:
                    try:
                        last_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                        days_old = (datetime.now(last_date.tzinfo) - last_date).days
                        if days_old >= days:
                            stale.append({
                                'name': lead['Name'],
                                'company': lead['Company'],
                                'score': lead['priority_score'],
                                'days_old': days_old
                            })
                    except:
                        pass
            
            if not stale:
                return f"No stale leads found (inactive for {days}+ days)"
            
            result = f"🚨 STALE LEADS (Inactive {days}+ days):\n\n"
            for i, lead in enumerate(sorted(stale, key=lambda x: x['score'], reverse=True)[:10], 1):
                result += f"{i}. {lead['name']} ({lead['company']}) - Score: {lead['score']} - {lead['days_old']} days old\n"
            return result
        
        @tool
        def find_high_value_at_risk() -> str:
            """Find high-value opportunities (>$100K) with low conversion scores (<60). These need immediate attention."""
            scored = self._get_scored_opportunities_cached()
            
            at_risk = [o for o in scored if o['Amount'] > 100000 and o['conversion_score'] < 60]
            
            if not at_risk:
                return "✅ No high-value deals at risk found!"
            
            total_at_risk = sum(o['Amount'] for o in at_risk)
            result = f"⚠️ HIGH-VALUE DEALS AT RISK:\n\n"
            result += f"💰 Total Value at Risk: ${total_at_risk:,.0f}\n"
            result += f"📊 Number of Deals: {len(at_risk)}\n\n"
            
            for i, opp in enumerate(sorted(at_risk, key=lambda x: x['Amount'], reverse=True)[:5], 1):
                result += f"{i}. {opp['Name']} - ${opp['Amount']:,.0f} - Score: {opp['conversion_score']}\n"
                result += f"   Stage: {opp.get('StageName', 'N/A')} | Close: {opp.get('CloseDate', 'N/A')}\n\n"
            
            return result
        
        @tool
        def analyze_deal_velocity() -> str:
            """Analyze how fast deals are moving through pipeline. Shows average time in each stage."""
            opps = self._get_opportunities_cached()
            
            stage_times = {}
            for opp in opps:
                stage = opp.get('StageName', 'Unknown')
                created = opp.get('CreatedDate', '')
                
                if created:
                    try:
                        created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        days_in_stage = (datetime.now(created_date.tzinfo) - created_date).days
                        
                        if stage not in stage_times:
                            stage_times[stage] = []
                        stage_times[stage].append(days_in_stage)
                    except:
                        pass
            
            result = "📈 DEAL VELOCITY ANALYSIS:\n\n"
            for stage, times in sorted(stage_times.items()):
                avg_days = sum(times) / len(times)
                result += f"• {stage}: {avg_days:.1f} days average ({len(times)} deals)\n"
            
            return result
        
        @tool
        def suggest_discount_strategy(opportunity_name: str) -> str:
            """Suggest optimal discount strategy for a specific opportunity based on score, stage, and amount."""
            scored = self._get_scored_opportunities_cached()
            
            for opp in scored:
                if opportunity_name.lower() in opp['Name'].lower():
                    score = opp['conversion_score']
                    amount = opp['Amount']
                    stage = opp.get('StageName', '')
                    
                    # Smart discount logic
                    if score >= 80:
                        discount = 0
                        strategy = "No discount needed - deal is hot!"
                    elif score >= 60:
                        discount = 5
                        strategy = "Small discount to close faster"
                    elif score >= 40:
                        discount = 10
                        strategy = "Moderate discount to overcome objections"
                    else:
                        discount = 15
                        strategy = "Aggressive discount to save deal"
                    
                    # Adjust for deal size
                    if amount > 500000:
                        discount = max(0, discount - 3)
                        strategy += " (reduced for large deal)"
                    
                    result = f"""💰 DISCOUNT STRATEGY: {opp['Name']}

📊 Current Score: {score}/100
💵 Deal Amount: ${amount:,.0f}
📈 Stage: {stage}

🎯 RECOMMENDATION:
• Suggested Discount: {discount}%
• Strategy: {strategy}
• New Amount: ${amount * (1 - discount/100):,.0f}
• Revenue Impact: -${amount * discount/100:,.0f}

💡 RATIONALE:
{'High conversion probability - maintain pricing power' if score >= 80 else 
 'Good momentum - small incentive to accelerate' if score >= 60 else
 'Deal needs help - discount justified to close' if score >= 40 else
 'Deal at risk - aggressive action needed'}
"""
                    return result
            
            return f"Opportunity '{opportunity_name}' not found"
        
        @tool
        def compare_opportunities(opp1_name: str, opp2_name: str) -> str:
            """Compare two opportunities side-by-side with detailed analysis."""
            scored = self._get_scored_opportunities_cached()
            
            found = []
            for opp in scored:
                if opp1_name.lower() in opp['Name'].lower() or opp2_name.lower() in opp['Name'].lower():
                    found.append(opp)
                    if len(found) == 2:
                        break
            
            if len(found) < 2:
                return "Could not find both opportunities for comparison"
            
            result = f"""⚖️ OPPORTUNITY COMPARISON:

📊 OPPORTUNITY 1: {found[0]['Name']}
• Amount: ${found[0]['Amount']:,.0f}
• Score: {found[0]['conversion_score']}/100
• Stage: {found[0].get('StageName', 'N/A')}
• Close Date: {found[0].get('CloseDate', 'N/A')}

📊 OPPORTUNITY 2: {found[1]['Name']}
• Amount: ${found[1]['Amount']:,.0f}
• Score: {found[1]['conversion_score']}/100
• Stage: {found[1].get('StageName', 'N/A')}
• Close Date: {found[1].get('CloseDate', 'N/A')}

🎯 RECOMMENDATION:
"""
            if found[0]['conversion_score'] > found[1]['conversion_score']:
                result += f"Focus on {found[0]['Name']} - Higher conversion probability ({found[0]['conversion_score']} vs {found[1]['conversion_score']})"
            else:
                result += f"Focus on {found[1]['Name']} - Higher conversion probability ({found[1]['conversion_score']} vs {found[0]['conversion_score']})"
            
            return result
        
        @tool
        def get_critical_actions_today() -> str:
            """Get list of critical actions needed today based on AI analysis."""
            scored_leads = self._get_scored_leads_cached()
            scored_opps = self._get_scored_opportunities_cached()
            
            critical_leads = [l for l in scored_leads if l['priority_score'] >= 85][:3]
            at_risk_opps = [o for o in scored_opps if o['Amount'] > 100000 and o['conversion_score'] < 60][:3]
            hot_deals = [o for o in scored_opps if o['conversion_score'] >= 85][:3]
            
            result = f"""🚨 CRITICAL ACTIONS FOR TODAY:

🔥 HOT LEADS TO CONTACT (Score ≥85):
"""
            for i, lead in enumerate(critical_leads, 1):
                result += f"{i}. {lead['Name']} ({lead['Company']}) - Score: {lead['priority_score']}\n"
            
            result += f"\n⚠️ AT-RISK DEALS TO SAVE (High value, low score):\n"
            for i, opp in enumerate(at_risk_opps, 1):
                result += f"{i}. {opp['Name']} - ${opp['Amount']:,.0f} - Score: {opp['conversion_score']}\n"
            
            result += f"\n🎯 HOT DEALS TO CLOSE (Score ≥85):\n"
            for i, opp in enumerate(hot_deals, 1):
                result += f"{i}. {opp['Name']} - ${opp['Amount']:,.0f} - Score: {opp['conversion_score']}\n"
            
            return result
        
        tools = [
            # Original 8 tools
            get_top_leads,
            get_top_opportunities,
            search_lead_by_name,
            generate_followup_for_lead,
            compare_leads,
            get_pipeline_summary,
            get_opportunity_summary,
            get_all_opportunities_summary,
            # New 7 tools
            identify_stale_leads,
            find_high_value_at_risk,
            analyze_deal_velocity,
            suggest_discount_strategy,
            compare_opportunities,
            get_critical_actions_today
        ]
        
        # Create agent with memory
        return create_react_agent(self.llm, tools, checkpointer=self.memory)
    
    def chat(self, message: str):
        """Send a message to the conversational agent with memory"""
        config = {"configurable": {"thread_id": self.thread_id}}
        response = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config
        )
        return response["messages"][-1].content
    
    def stream_chat(self, message: str):
        """Stream response from agent for better UX"""
        config = {"configurable": {"thread_id": self.thread_id}}
        for chunk in self.agent.stream(
            {"messages": [{"role": "user", "content": message}]},
            config=config
        ):
            if "messages" in chunk and chunk["messages"]:
                yield chunk["messages"][-1].content
    
    def reset_conversation(self):
        """Reset conversation memory"""
        self.thread_id = f"thread_{datetime.now().timestamp()}"
