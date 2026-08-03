# Agent Skills and Guardrails

## Runtime model

Every capability is registered in `agent_security.py` as a `SkillDefinition`.
The runtime checks the agent allowlist, risk level, user role, execution budget,
record limit, and approval before invoking the underlying function. These
checks are code-level controls and do not depend on the model following a
prompt.

## Current agent access

| Agent | Enabled read/advisory skills | Approval-gated skills |
|---|---|---|
| Orchestrator | Routing only; no Salesforce tool access | None |
| Sales Strategy | Leads, opportunities, ranking, risk advisory | Opportunity stage update |
| Deal Risk | Opportunities and risk analysis | None |
| Pricing | Opportunities and deterministic pricing advisory | Discount approval request |
| Follow-up | Leads, opportunities, draft generation | Create task, send email |

Deletion and arbitrary model-generated SOQL are disabled globally.

## Adding a new skill

1. Add a `SkillDefinition` to `SKILLS`.
2. Add the skill name to exactly the required agent allowlist.
3. Set `requires_approval=True` for writes and external effects.
4. Invoke it only through `BaseAgent.execute_skill(...)`.
5. Add authorization, approval, record-limit, and failure tests.

## Production replacements

The included approval store and request rate state are in-memory for local use.
Use Redis or a database in production. Send JSONL audit events to the company
SIEM, use per-user OAuth or a least-privilege integration identity, and retain
Salesforce CRUD/FLS/sharing enforcement as the primary authorization layer.
