"""
Orchestrator Agent - Routes queries and coordinates specialist agents
Implements intelligent routing and multi-agent collaboration
"""

from typing import Dict, Any, List, Optional, Tuple
import asyncio
from .base_agent import BaseAgent
from .sales_strategy_agent import SalesStrategyAgent
from .deal_risk_agent import DealRiskAgent
from .pricing_agent import PricingAgent
from .followup_agent import FollowUpAgent
from security import ExecutionBudget, SkillExecutor, UserContext


class OrchestratorAgent(BaseAgent):
    """Orchestrator that routes queries to appropriate specialist agents"""
    
    def __init__(self, salesforce_agent, llm_client, lead_prioritizer, opportunity_scorer, followup_generator, rag_manager=None, callbacks: Optional[List] = None, skill_executor: Optional[SkillExecutor] = None):
        super().__init__(
            name="Orchestrator Agent",
            role="Query routing and multi-agent coordination",
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            callbacks=callbacks,
            agent_key="orchestrator",
            skill_executor=skill_executor
        )
        self.rag_manager = rag_manager
        shared_executor = skill_executor or self.skill_executor
        
        # Initialize specialist agents
        self.sales_strategy = SalesStrategyAgent(
            salesforce_agent, llm_client, lead_prioritizer, opportunity_scorer, rag_manager, callbacks=callbacks
        )
        self.deal_risk = DealRiskAgent(
            salesforce_agent, llm_client, opportunity_scorer, rag_manager, callbacks=callbacks
        )
        self.pricing = PricingAgent(
            salesforce_agent, llm_client, callbacks=callbacks
        )
        self.followup = FollowUpAgent(
            salesforce_agent, llm_client, followup_generator, callbacks=callbacks
        )
        
        self.agents = {
            'sales_strategy': self.sales_strategy,
            'deal_risk': self.deal_risk,
            'pricing': self.pricing,
            'followup': self.followup
        }
        for specialist in self.agents.values():
            specialist.skill_executor = shared_executor
    
    def get_capabilities(self) -> List[str]:
        """Orchestrator handles all queries"""
        return ["all"]
    
    async def chat_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Route query to appropriate agent(s) and coordinate response"""
        self.add_to_history("user", message)
        context = context or {}
        user_context = context.get("user_context")
        if isinstance(user_context, dict):
            user_context = UserContext(**user_context)
        user_context = user_context or UserContext(user_id=context.get("user_id", "anonymous"))
        budget = context.get("execution_budget") or ExecutionBudget()
        self.set_request_context(user_context, budget)

        # Determine which agents should handle this query
        selected_agents = self._route_query(message)
        
        if not selected_agents:
            # Fallback to general response
            response = await self._general_response(message)
        elif len(selected_agents) == 1:
            # Single agent handles query
            agent = selected_agents[0]
            budget.consume_agent_hop()
            agent.set_request_context(user_context, budget)
            response = await agent.chat_async(message, context)
        else:
            # Multiple agents collaborate
            response = await self._multi_agent_collaboration(selected_agents, message, context)
        
        self.add_to_history("assistant", response)
        return response
    
    def _route_query(self, message: str) -> List[BaseAgent]:
        """Route query to appropriate specialist agent(s) using keyword matching"""
        message_lower = message.lower()
        selected_agents = []
        
        # Check each agent's capabilities
        for agent in self.agents.values():
            capabilities = agent.get_capabilities()
            if any(keyword in message_lower for keyword in capabilities):
                selected_agents.append(agent)
        
        return selected_agents
    
    async def _multi_agent_collaboration(
        self, 
        agents: List[BaseAgent], 
        message: str, 
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Coordinate multiple agents to answer query"""
        
        # Execute agents in parallel with one shared request budget
        for agent in agents:
            self.execution_budget.consume_agent_hop()
            agent.set_request_context(self.user_context, self.execution_budget)
        tasks = [agent.chat_async(message, context) for agent in agents]
        responses = await asyncio.gather(*tasks)
        
        # Index conversation in RAG if available
        if self.rag_manager:
            combined_response = "\n\n".join(responses)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.rag_manager.index_conversation,
                message,
                combined_response,
                {"agents": ", ".join(a.name for a in agents)}
            )
        
        # Synthesize responses
        agent_outputs = []
        for agent, response in zip(agents, responses):
            agent_outputs.append(f"**{agent.name}:**\n{response}")
        
        combined_output = "\n\n".join(agent_outputs)
        
        # Generate unified response
        synthesis_prompt = f"""Multiple specialist agents have analyzed the query: "{message}"

Agent Responses:
{combined_output}

Synthesize these insights into a cohesive, actionable response. Highlight key findings and recommendations.
"""
        
        messages = [
            {"role": "system", "content": "You are an orchestrator synthesizing insights from multiple specialist agents."},
            {"role": "user", "content": synthesis_prompt}
        ]
        
        synthesized_response = await self._call_llm_async(messages, temperature=0.7)
        
        return f"{synthesized_response}\n\n---\n*Insights from: {', '.join(a.name for a in agents)}*"
    
    async def _general_response(self, message: str) -> str:
        """Handle general queries that don't match specific agents"""
        messages = [
            {
                "role": "system",
                "content": "You are a helpful sales intelligence assistant. Answer general questions about sales, CRM, and business strategy."
            },
            {"role": "user", "content": message}
        ]
        
        return await self._call_llm_async(messages, temperature=0.7)
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all specialist agents"""
        return {
            agent_name: {
                "name": agent.name,
                "role": agent.role,
                "capabilities": agent.get_capabilities(),
                "history_length": len(agent.conversation_history)
            }
            for agent_name, agent in self.agents.items()
        }
    
    def clear_all_history(self):
        """Clear conversation history for all agents"""
        self.clear_history()
        for agent in self.agents.values():
            agent.clear_history()
