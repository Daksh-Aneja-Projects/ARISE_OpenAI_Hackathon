"""
HITL Gate Manager.
Enforces mandatory human review gates, manages SLA timers,
and handles escalation routing when gates expire.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional


# Gate reviewer role mapping
GATE_REVIEWER_ROLES = {
    "bid_initiation": "bid_manager",
    "intake_review": "bid_manager",
    "bid_no_bid": "practice_director",
    "scope_review": "solutioning_lead",
    "solution_review": "solution_director",
    "strategy_alignment": "practice_director",
    "commercial_approval": "commercial_director",
    "legal_compliance": "legal_counsel",
    "clarification_submission": "bid_manager",
    "final_review": "practice_director",
}

# Escalation targets when SLA expires
ESCALATION_TARGETS = {
    "bid_manager": "practice_director",
    "solutioning_lead": "solution_director",
    "solution_director": "practice_director",
    "practice_director": "evp",
    "commercial_director": "practice_director",
    "legal_counsel": "practice_director",
    "evp": "evp",  # Top of chain
}

# SLA hours per gate type
GATE_SLA_HOURS = {
    "bid_initiation": 4,
    "intake_review": 8,
    "bid_no_bid": 24,
    "scope_review": 24,
    "solution_review": 24,
    "strategy_alignment": 8,
    "commercial_approval": 24,
    "legal_compliance": 48,
    "clarification_submission": 4,
    "final_review": 8,
}


def get_reviewer_role(gate_type: str) -> str:
    """Get the required reviewer role for a gate type."""
    return GATE_REVIEWER_ROLES.get(gate_type, "bid_manager")


def get_sla_hours(gate_type: str) -> int:
    """Get SLA deadline hours for a gate type."""
    return GATE_SLA_HOURS.get(gate_type, 24)


def calculate_sla_deadline(
    gate_type: str, created_at: Optional[datetime] = None
) -> datetime:
    """Calculate the SLA deadline for a gate."""
    base = created_at or datetime.now(timezone.utc)
    hours = get_sla_hours(gate_type)
    return base + timedelta(hours=hours)


def check_sla_status(sla_deadline: datetime) -> Dict[str, Any]:
    """Check current SLA status for a gate."""
    now = datetime.now(timezone.utc)
    if isinstance(sla_deadline, str):
        sla_deadline = datetime.fromisoformat(sla_deadline)
    remaining = (sla_deadline - now).total_seconds() / 3600
    return {
        "remaining_hours": round(max(0, remaining), 1),
        "is_expired": remaining <= 0,
        "is_urgent": 0 < remaining <= 2,
        "is_warning": 2 < remaining <= 8,
        "status": "expired"
        if remaining <= 0
        else "urgent"
        if remaining <= 2
        else "warning"
        if remaining <= 8
        else "safe",
    }


def get_escalation_target(current_reviewer_role: str) -> str:
    """Get the escalation target for a given reviewer role."""
    return ESCALATION_TARGETS.get(current_reviewer_role, "practice_director")


def validate_decision(decision: str, comments: str) -> Dict[str, Any]:
    """Validate a HITL gate decision."""
    valid_decisions = [
        "approved",
        "approved_with_comments",
        "request_changes",
        "rejected",
        "escalated",
    ]
    errors = []
    if decision not in valid_decisions:
        errors.append(
            f"Invalid decision: {decision}. Must be one of: {valid_decisions}"
        )
    if not comments or not comments.strip():
        errors.append("Comments are mandatory for all HITL decisions")
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def build_gate_record(
    gate_type: str,
    bid_id: str,
    bid_reference: str,
    client_name: str,
    agent_summary: str,
    agent_data: Optional[Dict] = None,
    assigned_reviewer: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete gate record for creation."""
    now = datetime.now(timezone.utc)
    sla_hours = get_sla_hours(gate_type)
    return {
        "bid_id": bid_id,
        "bid_reference": bid_reference,
        "client_name": client_name,
        "gate_type": gate_type,
        "status": "pending",
        "agent_summary": agent_summary,
        "agent_data": agent_data,
        "assigned_reviewer": assigned_reviewer,
        "reviewer_role": get_reviewer_role(gate_type),
        "sla_hours": sla_hours,
        "sla_deadline": (now + timedelta(hours=sla_hours)).isoformat(),
        "is_escalated": False,
        "created_at": now.isoformat(),
    }
