# Agent security layer

This package is the runtime policy boundary for the Salesforce agents.

- `runtime.py` defines the skill registry, per-agent allowlists, execution budgets, one-time approvals, audit logging, and the secure skill executor.
- Agents must call Salesforce through `BaseAgent.execute_skill(...)` rather than invoking new write operations directly.
- Read skills are bounded by record limits.
- Write and external-action skills require a one-time approval bound to the authenticated user and exact arguments.
- Record deletion and arbitrary model-generated SOQL are disabled.

The root-level `agent_security.py` remains only as a compatibility import for older code.
