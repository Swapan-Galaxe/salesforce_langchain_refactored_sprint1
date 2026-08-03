# Multi-Agent System

Async orchestrated architecture with specialized agents for Salesforce sales intelligence.

## Architecture

```
OrchestratorAgent (Router & Coordinator)
    |
    ├── SalesStrategyAgent (Lead analysis, forecasting)
    ├── DealRiskAgent (Risk assessment, deal health)
    ├── PricingAgent (Discount analysis, margins)
    └── FollowUpAgent (Actions, emails, tasks)
```

## Files

- **base_agent.py**: Abstract base class with async interface
- **orchestrator_agent.py**: Query routing and multi-agent coordination
- **sales_strategy_agent.py**: Lead/opportunity analysis and forecasting
- **deal_risk_agent.py**: Risk assessment and deal health monitoring
- **pricing_agent.py**: Pricing optimization and margin protection
- **followup_agent.py**: Action recommendations and email drafting

## Key Features

- **Async Execution**: Parallel agent processing using asyncio
- **Intelligent Routing**: Keyword-based query routing to specialists
- **Multi-Agent Collaboration**: Coordinated responses from multiple agents
- **Conversation Memory**: Per-agent history tracking
- **Modular Design**: Easy to add new specialist agents

## Usage

```python
from agents import OrchestratorAgent

# Initialize orchestrator with dependencies
orchestrator = OrchestratorAgent(
    salesforce_agent=sf_agent,
    llm_client=openai_client,
    lead_prioritizer=lead_prioritizer,
    opportunity_scorer=opp_scorer,
    followup_generator=followup_gen
)

# Process query asynchronously
response = await orchestrator.chat_async("Show at-risk deals")
```

## Routing Examples

- "top leads" → Sales Strategy Agent
- "at-risk deals" → Deal Risk Agent  
- "discount analysis" → Pricing Agent
- "follow-up actions" → Follow-up Agent
- "pipeline risks" → Sales Strategy + Deal Risk (parallel)

## Adding New Agents

1. Create new agent class inheriting from BaseAgent
2. Implement `chat_async()` and `get_capabilities()` methods
3. Add agent to OrchestratorAgent initialization
4. Update routing logic if needed

## Testing

```bash
python tests/test_multi_agent.py
```

## Documentation

See `documentation/MULTI_AGENT_SYSTEM.md` for complete architecture details.
