"""
Deal Risk Agent - Risk assessment, deal health, churn prediction
Specializes in identifying and mitigating sales risks
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
from .base_agent import BaseAgent


class DealRiskAgent(BaseAgent):
    """Agent specialized in deal risk assessment and mitigation"""
    
    def __init__(self, salesforce_agent, llm_client, opportunity_scorer, rag_manager=None, callbacks: Optional[List] = None):
        super().__init__(
            name="Deal Risk Agent",
            role="Risk assessment and deal health monitoring",
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            callbacks=callbacks,
            agent_key="deal_risk"
        )
        self.opportunity_scorer = opportunity_scorer
        self.rag_manager = rag_manager
    
    def get_capabilities(self) -> List[str]:
        """Keywords for routing to this agent"""
        return [
            "risk", "risks", "risky", "at-risk",
            "health", "healthy", "unhealthy",
            "churn", "churning", "lost", "losing",
            "stalled", "stale", "stuck", "blocked",
            "warning", "red flag", "concern"
        ]
    
    async def chat_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process risk assessment queries"""
        self.add_to_history("user", message)
        
        message_lower = message.lower()
        
        # Determine which analysis to perform
        tasks = []
        
        if any(word in message_lower for word in ["risk", "at-risk", "risky"]):
            tasks.append(self._identify_at_risk_deals())
        
        if any(word in message_lower for word in ["stalled", "stale", "stuck"]):
            tasks.append(self._find_stalled_deals())
        
        if any(word in message_lower for word in ["health", "healthy"]):
            tasks.append(self._assess_deal_health())
        
        # Execute analysis in parallel
        if tasks:
            results = await asyncio.gather(*tasks)
            tool_data = "\n\n".join(results)
        else:
            # Default to at-risk analysis
            tool_data = await self._identify_at_risk_deals()
        
        # Generate response using LLM
        response = await self._generate_response(message, tool_data, context)
        self.add_to_history("assistant", response)
        
        return response
    
    async def _identify_at_risk_deals(self) -> str:
        """Identify opportunities at risk with optional RAG semantic search"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Use RAG for semantic search of at-risk patterns
        if self.rag_manager:
            # Index opportunities
            await loop.run_in_executor(None, self.rag_manager.index_opportunities, opps)
            
            # Semantic search for at-risk deals
            rag_results = await loop.run_in_executor(
                None,
                self.rag_manager.semantic_search_opportunities,
                "deals at risk of being lost, stalled negotiations, pricing concerns, competitor threats",
                10
            )
            
            if rag_results:
                result = f"**At-Risk Deals (RAG-powered semantic analysis):**\n"
                for item in rag_results[:5]:
                    metadata = item['metadata']
                    result += f"- {metadata.get('name', 'Unknown')} (${metadata.get('amount', '0')}): {metadata.get('stage', 'N/A')} | {metadata.get('probability', '0')}% probability\n"
                return result
        
        # Fallback to traditional scoring
        scored_opps = await loop.run_in_executor(
            None,
            self.opportunity_scorer.score_opportunities,
            opps
        )
        
        # Filter at-risk deals (low win probability or specific stages)
        at_risk = [
            opp for opp in scored_opps
            if opp.get('win_probability', 100) < 40 or
            opp.get('StageName') in ['Negotiation/Review', 'Proposal/Price Quote']
        ]
        
        at_risk_sorted = sorted(at_risk, key=lambda x: x.get('Amount', 0) or 0, reverse=True)[:5]
        
        result = f"**At-Risk Deals ({len(at_risk)} total):**\n"
        for opp in at_risk_sorted:
            result += f"- {opp.get('Name', 'Unknown')} (${opp.get('Amount', 0):,.0f}): {opp.get('win_probability', 0)}% win probability, Stage: {opp.get('StageName', 'N/A')}\n"
        
        return result
    
    async def _find_stalled_deals(self) -> str:
        """Find deals that haven't progressed recently"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        stalled = []
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for opp in opps:
            last_modified = opp.get('LastModifiedDate', '')
            if last_modified:
                try:
                    last_mod_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                    if last_mod_dt < cutoff_date:
                        stalled.append(opp)
                except:
                    pass
        
        stalled_sorted = sorted(stalled, key=lambda x: x.get('Amount', 0) or 0, reverse=True)[:5]
        
        result = f"**Stalled Deals ({len(stalled)} total, no activity in 30+ days):**\n"
        for opp in stalled_sorted:
            result += f"- {opp.get('Name', 'Unknown')} (${opp.get('Amount', 0):,.0f}): Last modified {opp.get('LastModifiedDate', 'N/A')}\n"
        
        return result
    
    async def _assess_deal_health(self) -> str:
        """Assess overall deal health across pipeline"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Score opportunities
        scored_opps = await loop.run_in_executor(
            None,
            self.opportunity_scorer.score_opportunities,
            opps
        )
        
        # Categorize by health
        healthy = [o for o in scored_opps if o.get('win_probability', 0) >= 70]
        moderate = [o for o in scored_opps if 40 <= o.get('win_probability', 0) < 70]
        at_risk = [o for o in scored_opps if o.get('win_probability', 0) < 40]
        
        healthy_value = sum(o.get('Amount', 0) or 0 for o in healthy)
        moderate_value = sum(o.get('Amount', 0) or 0 for o in moderate)
        at_risk_value = sum(o.get('Amount', 0) or 0 for o in at_risk)
        
        result = f"**Pipeline Health Assessment:**\n"
        result += f"- Healthy Deals: {len(healthy)} (${healthy_value:,.0f})\n"
        result += f"- Moderate Risk: {len(moderate)} (${moderate_value:,.0f})\n"
        result += f"- At Risk: {len(at_risk)} (${at_risk_value:,.0f})\n"
        result += f"- Overall Health Score: {(len(healthy) / len(scored_opps) * 100):.1f}%\n"
        
        return result
    
    async def _generate_response(self, message: str, tool_data: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate natural language response using LLM"""
        system_prompt = f"""You are the {self.name}, specialized in {self.role}.

Analyze the risk data and provide actionable recommendations to mitigate risks.
Be direct, highlight critical issues, and suggest specific actions.

Risk Analysis Data:
{tool_data}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        if context and context.get("history"):
            messages.insert(1, {"role": "assistant", "content": f"Previous context: {context['history']}"})
        
        return await self._call_llm_async(messages, temperature=0.6)
