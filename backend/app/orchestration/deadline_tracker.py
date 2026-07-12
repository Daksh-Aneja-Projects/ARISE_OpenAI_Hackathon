"""
Deadline Tracker — Monitors submission deadlines and calculates risk levels.
Triggers escalations when deadlines approach critical thresholds.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Risk thresholds in days
RISK_THRESHOLDS = {
    "critical": 3,  # < 3 days
    "high": 7,  # < 7 days
    "medium": 14,  # < 14 days
    "low": 999,  # > 14 days
}

# Minimum time estimates per stage (days)
STAGE_DURATION_ESTIMATES = {
    "intake_processing": 0.5,
    "intake_review": 1,
    "bid_no_bid": 1,
    "scope_building": 2,
    "scope_review": 1,
    "solution_design": 3,
    "solution_review": 1,
    "strategy_alignment": 0.5,
    "commercial_modeling": 2,
    "commercial_approval": 1,
    "compliance_review": 2,
    "transition_planning": 1.5,
    "transition_review": 0.5,
    "legal_sign_off": 2,
    "output_generation": 3,
    "qa_review": 1,
    "final_review": 1,
}


def calculate_deadline_risk(
    submission_deadline: Optional[str], current_status: str = "created"
) -> Dict[str, Any]:
    """Calculate deadline risk level and remaining time analysis."""
    if not submission_deadline:
        return {
            "risk": "low",
            "days_remaining": None,
            "is_feasible": True,
            "message": "No deadline set",
        }

    try:
        if isinstance(submission_deadline, str):
            deadline = datetime.fromisoformat(
                submission_deadline.replace("Z", "+00:00")
            )
        else:
            deadline = submission_deadline
    except (ValueError, TypeError):
        return {
            "risk": "low",
            "days_remaining": None,
            "is_feasible": True,
            "message": "Invalid deadline format",
        }

    now = datetime.now(timezone.utc)
    remaining = (deadline - now).total_seconds() / 86400
    days = round(remaining, 1)

    # Determine risk level
    risk = "low"
    for level, threshold in sorted(RISK_THRESHOLDS.items(), key=lambda x: x[1]):
        if days < threshold:
            risk = level
            break

    # Estimate remaining work
    remaining_effort = estimate_remaining_effort(current_status)
    is_feasible = days >= remaining_effort

    return {
        "risk": risk,
        "days_remaining": max(0, days),
        "remaining_effort_days": remaining_effort,
        "is_feasible": is_feasible,
        "deadline": deadline.isoformat(),
        "message": _build_message(risk, days, is_feasible, remaining_effort),
    }


def estimate_remaining_effort(current_status: str) -> float:
    """Estimate remaining effort in days from the current status to submission."""
    stages = list(STAGE_DURATION_ESTIMATES.keys())
    try:
        current_idx = stages.index(current_status)
    except ValueError:
        return sum(STAGE_DURATION_ESTIMATES.values())

    remaining = sum(STAGE_DURATION_ESTIMATES[s] for s in stages[current_idx:])
    return round(remaining, 1)


def get_deadline_alerts(bids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate alerts for all bids approaching deadlines."""
    alerts = []
    for bid in bids:
        deadline = bid.get("submission_deadline")
        if not deadline:
            continue
        risk = calculate_deadline_risk(deadline, bid.get("status", "created"))
        if risk["risk"] in ("critical", "high"):
            alerts.append(
                {
                    "bid_id": bid.get("id"),
                    "bid_reference": bid.get("bid_reference"),
                    "client_name": bid.get("client_name"),
                    "risk": risk["risk"],
                    "days_remaining": risk["days_remaining"],
                    "is_feasible": risk["is_feasible"],
                    "message": risk["message"],
                }
            )
    return sorted(alerts, key=lambda a: a.get("days_remaining", 999))


def _build_message(risk: str, days: float, is_feasible: bool, effort: float) -> str:
    """Build a human-readable deadline message."""
    if days <= 0:
        return "⚠️ DEADLINE PASSED — immediate escalation required"
    if not is_feasible:
        return f"🔴 {days:.0f} days remaining but {effort:.0f} days of work left — accelerate or descope"
    if risk == "critical":
        return f"🔴 CRITICAL: Only {days:.0f} days remaining — prioritize all resources"
    if risk == "high":
        return f"🟠 HIGH RISK: {days:.0f} days remaining — monitor closely"
    if risk == "medium":
        return f"🟡 {days:.0f} days remaining — on track but watch for delays"
    return f"🟢 {days:.0f} days remaining — comfortable timeline"
