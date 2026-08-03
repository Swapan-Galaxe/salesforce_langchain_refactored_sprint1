"""
Follow-up Agent - Action recommendations, email drafting, task prioritization
Specializes in next-best-actions and sales execution
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta
from .base_agent import BaseAgent


class FollowUpAgent(BaseAgent):
    """Agent specialized in follow-up actions and sales execution"""
    
    def __init__(self, salesforce_agent, llm_client, followup_generator, callbacks: Optional[List] = None):
        super().__init__(
            name="Follow-up Agent",
            role="Action recommendations and sales execution",
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            callbacks=callbacks,
            agent_key="followup"
        )
        self.followup_generator = followup_generator
    
    def get_capabilities(self) -> List[str]:
        """Keywords for routing to this agent"""
        return [
            "follow", "followup", "follow-up", "next steps",
            "action", "actions", "task", "tasks", "todo",
            "email", "message", "reach out", "contact",
            "schedule", "meeting", "call", "demo",
            "prioritize", "priority", "urgent"
        ]
    
    async def chat_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process follow-up and action queries"""
        self.add_to_history("user", message)
        
        message_lower = message.lower()
        
        # Determine which actions to generate
        tasks = []
        
        if any(word in message_lower for word in ["follow", "followup", "next steps", "action"]):
            tasks.append(self._generate_followup_actions())
        
        if any(word in message_lower for word in ["email", "message", "draft"]):
            tasks.append(self._draft_email(message, context))
        
        if any(word in message_lower for word in ["prioritize", "priority", "urgent"]):
            tasks.append(self._prioritize_actions())
        
        # Execute in parallel
        if tasks:
            results = await asyncio.gather(*tasks)
            tool_data = "\n\n".join(results)
        else:
            # Default to follow-up actions
            tool_data = await self._generate_followup_actions()
        
        # Generate response using LLM
        response = await self._generate_response(message, tool_data, context)
        self.add_to_history("assistant", response)
        
        return response
    
    async def _generate_followup_actions(self) -> str:
        """Generate follow-up recommendations for leads and opportunities"""
        loop = asyncio.get_event_loop()
        
        # Fetch both leads and opportunities
        leads_task = loop.run_in_executor(None, lambda: self.execute_skill("get_leads", self.salesforce_agent.get_leads))
        opps_task = loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        leads, opps = await asyncio.gather(leads_task, opps_task)
        
        # Generate follow-ups for leads
        lead_followups = []
        if leads:
            lead_followups = await loop.run_in_executor(
                None,
                self.followup_generator.generate_followups,
                leads[:10]  # Limit to top 10
            )
        
        # Generate follow-ups for opportunities
        opp_followups = []
        if opps:
            opp_followups = await loop.run_in_executor(
                None,
                self.followup_generator.generate_followups,
                opps[:10]  # Limit to top 10
            )
        
        result = ""
        
        if lead_followups:
            result += f"**Lead Follow-ups ({len(lead_followups)}):**\n"
            for item in lead_followups[:3]:
                result += f"- {item.get('Name', 'Unknown')}: {item.get('followup_action', 'No action')}\n"
            result += "\n"
        
        if opp_followups:
            result += f"**Opportunity Follow-ups ({len(opp_followups)}):**\n"
            for item in opp_followups[:3]:
                result += f"- {item.get('Name', 'Unknown')}: {item.get('followup_action', 'No action')}\n"
        
        return result if result else "No follow-up actions needed."
    
    async def _draft_email(self, message: str, context: Optional[Dict[str, Any]]) -> str:
        """Draft email based on user request"""
        # Extract recipient info from context or message
        recipient = "prospect"
        purpose = "follow-up"
        
        if context and context.get('recipient'):
            recipient = context['recipient']
        
        if "demo" in message.lower():
            purpose = "demo invitation"
        elif "proposal" in message.lower():
            purpose = "proposal follow-up"
        elif "meeting" in message.lower():
            purpose = "meeting request"
        
        email_draft = f"""**Email Draft ({purpose}):**

Subject: Following up on our conversation

Hi {recipient},

I wanted to reach out regarding our recent discussion. Based on our conversation, I believe we can help you achieve your goals.

Would you be available for a brief call this week to discuss next steps?

Looking forward to hearing from you.

Best regards
"""
        
        return email_draft
    
    async def _prioritize_actions(self) -> str:
        """Prioritize actions based on urgency and value"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Prioritize by close date and amount
        urgent_opps = []
        today = datetime.now()
        
        for opp in opps:
            close_date_str = opp.get('CloseDate', '')
            if close_date_str:
                try:
                    close_date = datetime.fromisoformat(close_date_str.replace('Z', '+00:00'))
                    days_to_close = (close_date - today).days
                    
                    if 0 <= days_to_close <= 30:  # Closing within 30 days
                        urgent_opps.append({
                            'name': opp.get('Name', 'Unknown'),
                            'amount': opp.get('Amount', 0) or 0,
                            'days': days_to_close,
                            'stage': opp.get('StageName', 'N/A')
                        })
                except:
                    pass
        
        # Sort by days to close, then by amount
        urgent_opps.sort(key=lambda x: (x['days'], -x['amount']))
        
        result = f"**Urgent Actions (Closing in 30 days):**\n"
        for opp in urgent_opps[:5]:
            result += f"- {opp['name']} (${opp['amount']:,.0f}): {opp['days']} days to close, Stage: {opp['stage']}\n"
        
        return result if urgent_opps else "No urgent actions at this time."
    
    async def _generate_response(self, message: str, tool_data: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate natural language response using LLM"""
        system_prompt = f"""You are the {self.name}, specialized in {self.role}.

Provide clear, actionable recommendations for follow-up activities.
Be specific about timing, approach, and expected outcomes.

Action Data:
{tool_data}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        if context and context.get("history"):
            messages.insert(1, {"role": "assistant", "content": f"Previous context: {context['history']}"})
        
        return await self._call_llm_async(messages, temperature=0.7)
