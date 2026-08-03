"""
Sales Strategy Agent - Lead analysis, opportunity insights, forecasting
Specializes in strategic sales intelligence and pipeline optimization
"""

from typing import Dict, Any, List, Optional
import asyncio
from .base_agent import BaseAgent


class SalesStrategyAgent(BaseAgent):
    """Agent specialized in sales strategy, lead analysis, and forecasting"""
    
    def __init__(self, salesforce_agent, llm_client, lead_prioritizer, opportunity_scorer, rag_manager=None, callbacks: Optional[List] = None):
        super().__init__(
            name="Sales Strategy Agent",
            role="Strategic sales intelligence and pipeline optimization",
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            callbacks=callbacks,
            agent_key="sales_strategy"
        )
        self.lead_prioritizer = lead_prioritizer
        self.opportunity_scorer = opportunity_scorer
        self.rag_manager = rag_manager
    
    def get_capabilities(self) -> List[str]:
        """Keywords for routing to this agent"""
        return [
            "lead", "leads", "prospect", "prospects", "pipeline",
            "opportunity", "opportunities", "deal", "deals",
            "forecast", "forecasting", "revenue", "quota",
            "strategy", "strategic", "prioritize", "priority"
        ]
    
    async def chat_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process sales strategy queries"""
        self.add_to_history("user", message)
        
        message_lower = message.lower()
        
        # Determine which tools to use
        tasks = []
        
        if any(word in message_lower for word in ["lead", "prospect"]):
            tasks.append(self._analyze_leads())
        
        if any(word in message_lower for word in ["opportunity", "deal", "pipeline"]):
            tasks.append(self._analyze_opportunities())
        
        if any(word in message_lower for word in ["forecast", "revenue", "quota"]):
            tasks.append(self._generate_forecast())
        
        # Execute tools in parallel
        if tasks:
            results = await asyncio.gather(*tasks)
            tool_data = "\n\n".join(results)
        else:
            tool_data = "No specific data requested."
        
        # Generate response using LLM
        response = await self._generate_response(message, tool_data, context)
        self.add_to_history("assistant", response)
        
        return response
    
    async def _analyze_leads(self) -> str:
        """Fetch and analyze leads with optional RAG semantic search"""
        loop = asyncio.get_event_loop()
        
        # Use RAG if available for semantic search
        if self.rag_manager:
            # Get recent context from conversation history
            leads = await loop.run_in_executor(None, lambda: self.execute_skill("get_leads", self.salesforce_agent.get_leads))
            
            if leads:
                # Index leads for semantic search
                await loop.run_in_executor(None, self.rag_manager.index_leads, leads)
            
            # Semantic search for high-priority leads
            rag_results = await loop.run_in_executor(
                None,
                self.rag_manager.semantic_search_leads,
                "high priority leads with recent activity and strong engagement",
                10
            )
            
            if rag_results:
                result = f"**Semantically Relevant Leads (RAG-powered):**\n"
                for item in rag_results[:5]:
                    metadata = item['metadata']
                    result += f"- {metadata.get('name', 'Unknown')} ({metadata.get('company', 'N/A')}): {metadata.get('status', 'N/A')} | Rating: {metadata.get('rating', 'N/A')}\n"
                return result
        
        # Fallback to traditional approach
        leads = await loop.run_in_executor(None, lambda: self.execute_skill("get_leads", self.salesforce_agent.get_leads))
        
        if not leads:
            return "No leads found."
        
        # Score leads
        scored_leads = await loop.run_in_executor(
            None,
            self.lead_prioritizer.prioritize_leads,
            leads
        )
        
        top_leads = sorted(scored_leads, key=lambda x: x.get('priority_score', 0), reverse=True)[:5]
        
        result = f"**Top {len(top_leads)} Leads:**\n"
        for lead in top_leads:
            result += f"- {lead.get('Name', 'Unknown')} ({lead.get('Company', 'N/A')}): Score {lead.get('priority_score', 0)}/100\n"
        
        return result
    
    async def _analyze_opportunities(self) -> str:
        """Fetch and analyze opportunities with optional RAG semantic search"""
        loop = asyncio.get_event_loop()
        
        # Use RAG if available
        if self.rag_manager:
            opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
            
            if opps:
                # Index opportunities
                await loop.run_in_executor(None, self.rag_manager.index_opportunities, opps)
            
            # Semantic search for high-value opportunities
            rag_results = await loop.run_in_executor(
                None,
                self.rag_manager.semantic_search_opportunities,
                "high value opportunities close to closing with strong probability",
                10
            )
            
            if rag_results:
                result = f"**Semantically Relevant Opportunities (RAG-powered):**\n"
                for item in rag_results[:5]:
                    metadata = item['metadata']
                    result += f"- {metadata.get('name', 'Unknown')} (${metadata.get('amount', '0')}): {metadata.get('stage', 'N/A')} | {metadata.get('probability', '0')}% probability\n"
                return result
        
        # Fallback to traditional approach
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Score opportunities
        scored_opps = await loop.run_in_executor(
            None,
            self.opportunity_scorer.score_opportunities,
            opps
        )
        
        top_opps = sorted(scored_opps, key=lambda x: x.get('win_probability', 0), reverse=True)[:5]
        
        result = f"**Top {len(top_opps)} Opportunities:**\n"
        for opp in top_opps:
            result += f"- {opp.get('Name', 'Unknown')} (${opp.get('Amount', 0):,.0f}): {opp.get('win_probability', 0)}% win probability\n"
        
        return result
    
    async def _generate_forecast(self) -> str:
        """Generate revenue forecast"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities for forecasting."
        
        total_pipeline = sum(opp.get('Amount', 0) or 0 for opp in opps)
        weighted_pipeline = sum(
            (opp.get('Amount', 0) or 0) * (opp.get('Probability', 0) or 0) / 100
            for opp in opps
        )
        
        result = f"**Revenue Forecast:**\n"
        result += f"- Total Pipeline: ${total_pipeline:,.0f}\n"
        result += f"- Weighted Pipeline: ${weighted_pipeline:,.0f}\n"
        result += f"- Number of Opportunities: {len(opps)}\n"
        
        return result
    
    async def _generate_response(self, message: str, tool_data: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate natural language response using LLM"""
        system_prompt = f"""You are the {self.name}, specialized in {self.role}.

Analyze the data provided and answer the user's question with strategic insights.
Be concise, actionable, and focus on business impact.

Data from tools:
{tool_data}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        if context and context.get("history"):
            messages.insert(1, {"role": "assistant", "content": f"Previous context: {context['history']}"})
        
        return await self._call_llm_async(messages, temperature=0.7)
