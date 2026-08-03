"""
Pricing Agent - Discount analysis, pricing optimization, margin protection
Specializes in pricing strategy and profitability optimization
"""

from typing import Dict, Any, List, Optional
import asyncio
from .base_agent import BaseAgent


class PricingAgent(BaseAgent):
    """Agent specialized in pricing strategy and discount management"""
    
    def __init__(self, salesforce_agent, llm_client, callbacks: Optional[List] = None):
        super().__init__(
            name="Pricing Agent",
            role="Pricing optimization and margin protection",
            salesforce_agent=salesforce_agent,
            llm_client=llm_client,
            callbacks=callbacks,
            agent_key="pricing"
        )
    
    def get_capabilities(self) -> List[str]:
        """Keywords for routing to this agent"""
        return [
            "price", "pricing", "discount", "discounts",
            "margin", "margins", "profitability", "profit",
            "cost", "costs", "revenue", "value",
            "negotiation", "negotiate"
        ]
    
    async def chat_async(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process pricing queries"""
        self.add_to_history("user", message)
        
        message_lower = message.lower()
        
        # Determine which analysis to perform
        tasks = []
        
        if any(word in message_lower for word in ["discount", "discounts"]):
            tasks.append(self._analyze_discounts())
        
        if any(word in message_lower for word in ["margin", "profitability", "profit"]):
            tasks.append(self._analyze_margins())
        
        if any(word in message_lower for word in ["price", "pricing", "optimize"]):
            tasks.append(self._pricing_recommendations())
        
        # Execute analysis in parallel
        if tasks:
            results = await asyncio.gather(*tasks)
            tool_data = "\n\n".join(results)
        else:
            # Default to discount analysis
            tool_data = await self._analyze_discounts()
        
        # Generate response using LLM
        response = await self._generate_response(message, tool_data, context)
        self.add_to_history("assistant", response)
        
        return response
    
    async def _analyze_discounts(self) -> str:
        """Analyze discount patterns across opportunities"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Calculate discount metrics (assuming Discount__c field exists)
        discounted_deals = []
        total_discount_amount = 0
        
        for opp in opps:
            discount = opp.get('Discount__c', 0) or 0
            if discount > 0:
                discounted_deals.append({
                    'name': opp.get('Name', 'Unknown'),
                    'amount': opp.get('Amount', 0) or 0,
                    'discount': discount,
                    'stage': opp.get('StageName', 'N/A')
                })
                total_discount_amount += (opp.get('Amount', 0) or 0) * (discount / 100)
        
        # Sort by discount percentage
        discounted_deals.sort(key=lambda x: x['discount'], reverse=True)
        top_discounts = discounted_deals[:5]
        
        avg_discount = sum(d['discount'] for d in discounted_deals) / len(discounted_deals) if discounted_deals else 0
        
        result = f"**Discount Analysis:**\n"
        result += f"- Deals with Discounts: {len(discounted_deals)}/{len(opps)}\n"
        result += f"- Average Discount: {avg_discount:.1f}%\n"
        result += f"- Total Discount Impact: ${total_discount_amount:,.0f}\n\n"
        
        if top_discounts:
            result += f"**Top Discounted Deals:**\n"
            for deal in top_discounts:
                result += f"- {deal['name']} (${deal['amount']:,.0f}): {deal['discount']}% discount\n"
        
        return result
    
    async def _analyze_margins(self) -> str:
        """Analyze profit margins across opportunities"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Calculate margin metrics (assuming Cost__c and Margin__c fields)
        margin_data = []
        
        for opp in opps:
            amount = opp.get('Amount', 0) or 0
            cost = opp.get('Cost__c', 0) or 0
            
            if amount > 0:
                margin_pct = ((amount - cost) / amount) * 100 if cost else 50  # Default 50% if no cost
                margin_data.append({
                    'name': opp.get('Name', 'Unknown'),
                    'amount': amount,
                    'margin': margin_pct,
                    'profit': amount - cost
                })
        
        # Sort by margin percentage
        margin_data.sort(key=lambda x: x['margin'])
        low_margin = margin_data[:5]
        
        avg_margin = sum(d['margin'] for d in margin_data) / len(margin_data) if margin_data else 0
        total_profit = sum(d['profit'] for d in margin_data)
        
        result = f"**Margin Analysis:**\n"
        result += f"- Average Margin: {avg_margin:.1f}%\n"
        result += f"- Total Projected Profit: ${total_profit:,.0f}\n\n"
        
        if low_margin:
            result += f"**Low Margin Deals (Attention Needed):**\n"
            for deal in low_margin:
                result += f"- {deal['name']} (${deal['amount']:,.0f}): {deal['margin']:.1f}% margin\n"
        
        return result
    
    async def _pricing_recommendations(self) -> str:
        """Generate pricing optimization recommendations"""
        loop = asyncio.get_event_loop()
        opps = await loop.run_in_executor(None, lambda: self.execute_skill("get_opportunities", self.salesforce_agent.get_opportunities))
        
        if not opps:
            return "No opportunities found."
        
        # Analyze pricing patterns by stage
        stage_pricing = {}
        for opp in opps:
            stage = opp.get('StageName', 'Unknown')
            amount = opp.get('Amount', 0) or 0
            
            if stage not in stage_pricing:
                stage_pricing[stage] = []
            stage_pricing[stage].append(amount)
        
        result = f"**Pricing Insights by Stage:**\n"
        for stage, amounts in stage_pricing.items():
            avg_amount = sum(amounts) / len(amounts)
            result += f"- {stage}: Avg ${avg_amount:,.0f} ({len(amounts)} deals)\n"
        
        return result
    
    async def _generate_response(self, message: str, tool_data: str, context: Optional[Dict[str, Any]]) -> str:
        """Generate natural language response using LLM"""
        system_prompt = f"""You are the {self.name}, specialized in {self.role}.

Analyze the pricing data and provide recommendations to optimize pricing and protect margins.
Focus on profitability, competitive positioning, and sustainable discounting practices.

Pricing Analysis Data:
{tool_data}
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ]
        
        if context and context.get("history"):
            messages.insert(1, {"role": "assistant", "content": f"Previous context: {context['history']}"})
        
        return await self._call_llm_async(messages, temperature=0.6)
