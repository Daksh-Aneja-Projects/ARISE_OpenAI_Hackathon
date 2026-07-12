"""
Pipeline Orchestration Engine.
Manages agent execution sequencing and state transitions.
"""

from typing import Any, Dict, Optional


# Strategic agent execution order — new 11-agent pipeline
PIPELINE_STAGES = [
    {"name": "intake", "label": "RFP Intake"},
    {"name": "data_analyst", "label": "Data Intelligence"},
    {"name": "client_intelligence", "label": "Client Intelligence"},
    {"name": "strategic_assessment", "label": "Strategic Assessment"},
    {"name": "solution_scope", "label": "Solution Design & Scoping"},
    {"name": "automation_ai", "label": "AI & Automation Advisory"},
    {"name": "transition_change", "label": "Transition & Change Management"},
    {"name": "commercial_model", "label": "Commercial & Pricing"},
    {"name": "compliance_risk", "label": "Risk & Compliance"},
    {"name": "proposal_generator", "label": "Proposal Generator"},
    {"name": "discovery", "label": "Discovery & Clarifications"},
    {"name": "feedback_learning", "label": "Learning & Feedback"},
]

# Status mapping: agent name → bid statuses
STATUS_MAP = {
    "intake": {"processing": "intake_processing", "review": "intake_review"},
    "data_analyst": {"processing": "data_analysis", "review": "data_analysis"},
    "client_intelligence": {
        "processing": "client_intel",
        "review": "client_intel_review",
    },
    "strategic_assessment": {
        "processing": "bid_no_bid",
        "review": "strategy_alignment",
    },
    "solution_scope": {"processing": "scope_building", "review": "solution_review"},
    "automation_ai": {"processing": "solution_design", "review": "solution_review"},
    "transition_change": {
        "processing": "transition_planning",
        "review": "transition_review",
    },
    "commercial_model": {
        "processing": "commercial_modeling",
        "review": "commercial_approval",
    },
    "compliance_risk": {"processing": "compliance_review", "review": "legal_sign_off"},
    "proposal_generator": {"processing": "proposal_writing", "review": "final_review"},
    "discovery": {"processing": "discovery", "review": "discovery"},
    "feedback_learning": {"processing": "feedback", "review": "feedback"},
}


def get_stage_index(agent_name: str) -> int:
    """Get the index of a stage by agent name."""
    for i, stage in enumerate(PIPELINE_STAGES):
        if stage["name"] == agent_name:
            return i
    return -1


def get_next_stage(current_agent: str) -> Optional[Dict[str, Any]]:
    """Get the next pipeline stage after the current agent."""
    idx = get_stage_index(current_agent)
    if idx >= 0 and idx < len(PIPELINE_STAGES) - 1:
        return PIPELINE_STAGES[idx + 1]
    return None


def get_pipeline_status(current_agent: str) -> Dict[str, Any]:
    """Get full pipeline status with progress info."""
    idx = get_stage_index(current_agent)
    total = len(PIPELINE_STAGES)
    return {
        "current_stage": idx,
        "total_stages": total,
        "progress_pct": round((max(0, idx) / total) * 100) if total > 0 else 0,
        "stages": [
            {
                "name": s["name"],
                "label": s["label"],
                "status": "completed"
                if i < idx
                else "active"
                if i == idx
                else "pending",
            }
            for i, s in enumerate(PIPELINE_STAGES)
        ],
    }


def get_agent_status_key(agent_name: str, phase: str = "processing") -> str:
    """Get the bid status string for a given agent and phase."""
    return STATUS_MAP.get(agent_name, {}).get(phase, "created")


def is_pipeline_complete(current_agent: str) -> bool:
    """Check if the pipeline has completed all stages."""
    idx = get_stage_index(current_agent)
    return idx >= len(PIPELINE_STAGES) - 1


# Mapping: agent name → HITL gate type and SLA hours
GATE_TYPE_MAP = {
    "intake": {"gate_type": "intake_review", "sla_hours": 8},
    "data_analyst": {"gate_type": "intake_review", "sla_hours": 8},
    "strategic_assessment": {"gate_type": "bid_decision", "sla_hours": 24},
    "solution_scope": {"gate_type": "scope_review", "sla_hours": 24},
    "automation_ai": {"gate_type": "solution_review", "sla_hours": 24},
    "commercial_model": {"gate_type": "commercial_review", "sla_hours": 24},
    "compliance_risk": {"gate_type": "legal_compliance", "sla_hours": 48},
    "proposal_generator": {"gate_type": "output_review", "sla_hours": 8},
}


def build_gate_payload(
    agent_name: str,
    bid_id: str,
    bid_reference: str,
    client_name: str,
    agent_summary: str,
    agent_data: dict = None,
) -> dict:
    """Build a HITL gate payload for the pipeline to create after an agent completes.
    Returns None if the agent doesn't require a gate."""
    gate_info = GATE_TYPE_MAP.get(agent_name)
    if not gate_info:
        return None
    return {
        "bid_id": bid_id,
        "bid_reference": bid_reference,
        "client_name": client_name,
        "gate_type": gate_info["gate_type"],
        "sla_hours": gate_info["sla_hours"],
        "agent_summary": agent_summary,
        "agent_data": agent_data,
    }
