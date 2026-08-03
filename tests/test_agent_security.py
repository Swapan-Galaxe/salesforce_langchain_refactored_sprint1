"""Unit tests for enforceable agent skill guardrails."""

import os
import tempfile
import pytest

from security import (
    ApprovalRequiredError,
    ApprovalStore,
    ExecutionBudget,
    ExecutionBudgetExceeded,
    SecurityAuditLogger,
    SkillAuthorizationError,
    SkillExecutor,
    UserContext,
)


def make_executor():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    return SkillExecutor(audit_logger=SecurityAuditLogger(tmp.name)), tmp.name


def test_agent_allowlist_blocks_cross_agent_skill():
    executor, path = make_executor()
    try:
        with pytest.raises(SkillAuthorizationError):
            executor.execute(
                agent_key="pricing",
                skill_name="get_leads",
                function=lambda: [],
                user_context=UserContext(user_id="u1"),
            )
    finally:
        os.unlink(path)


def test_write_skill_requires_matching_one_time_approval():
    approvals = ApprovalStore()
    executor, path = make_executor()
    executor.approvals = approvals
    args = {"record_id": "006000000000001", "stage": "Negotiation/Review"}
    try:
        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                agent_key="sales_strategy",
                skill_name="update_opportunity_stage",
                function=lambda **kwargs: kwargs,
                user_context=UserContext(user_id="u1"),
                arguments=args,
            )

        approvals.approve("a1", "u1", "update_opportunity_stage", args)
        result = executor.execute(
            agent_key="sales_strategy",
            skill_name="update_opportunity_stage",
            function=lambda **kwargs: kwargs,
            user_context=UserContext(user_id="u1"),
            approval_id="a1",
            arguments=args,
        )
        assert result == args

        with pytest.raises(ApprovalRequiredError):
            executor.execute(
                agent_key="sales_strategy",
                skill_name="update_opportunity_stage",
                function=lambda **kwargs: kwargs,
                user_context=UserContext(user_id="u1"),
                approval_id="a1",
                arguments=args,
            )
    finally:
        os.unlink(path)


def test_record_budget_is_enforced():
    executor, path = make_executor()
    try:
        with pytest.raises(ExecutionBudgetExceeded):
            executor.execute(
                agent_key="sales_strategy",
                skill_name="get_leads",
                function=lambda: [{"Id": str(i)} for i in range(3)],
                user_context=UserContext(user_id="u1"),
                budget=ExecutionBudget(max_records=2),
            )
    finally:
        os.unlink(path)


def test_prohibited_skill_is_never_executable():
    executor, path = make_executor()
    try:
        with pytest.raises(SkillAuthorizationError):
            executor.execute(
                agent_key="sales_strategy",
                skill_name="delete_salesforce_record",
                function=lambda: True,
                user_context=UserContext(user_id="u1"),
            )
    finally:
        os.unlink(path)
