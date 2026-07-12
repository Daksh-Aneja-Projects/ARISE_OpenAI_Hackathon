"""
Conflict Resolver — Detects and resolves inter-agent data conflicts.
Ensures consistency across BidManifest when multiple agents write outputs.
"""

from typing import Any, Dict, List
from datetime import datetime, timezone


def detect_conflicts(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Scan the BidManifest for inter-agent data conflicts."""
    conflicts = []

    # Check TCV consistency across scope, commercial, and bid-level
    _extract_nested(
        manifest, "scope_output", "scope_package", "effort_summary", "total_effort_days"
    )
    commercial_tcv = _extract_nested(
        manifest,
        "commercial_output",
        "commercial_package",
        "pl_summary",
        "total_contract_value",
    )
    bid_tcv = manifest.get("estimated_tcv")

    if (
        commercial_tcv
        and bid_tcv
        and abs(commercial_tcv - bid_tcv) / max(commercial_tcv, bid_tcv, 1) > 0.1
    ):
        conflicts.append(
            {
                "id": "TCV_MISMATCH",
                "severity": "High",
                "agents": ["commercial_model", "bid_level"],
                "description": f"TCV mismatch: commercial={commercial_tcv}, bid-level={bid_tcv}",
                "resolution": "Use commercial model TCV as source of truth",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Check team model consistency between scope and solution
    scope_team = _extract_nested(
        manifest, "scope_output", "scope_package", "team_model"
    )
    solution_team = _extract_nested(
        manifest, "solution_output", "solution_package", "operating_model"
    )

    if scope_team and solution_team:
        conflicts.append(
            {
                "id": "TEAM_MODEL_CHECK",
                "severity": "Low",
                "agents": ["scope_builder", "solution_architect"],
                "description": "Team model defined in both scope and solution outputs — verify consistency",
                "resolution": "Reconcile team model across both outputs",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Check risk assessments across compliance and bid/no-bid
    compliance_risk = _extract_nested(
        manifest, "compliance_output", "compliance_package", "overall_risk_score"
    )
    bid_risk = _extract_nested(manifest, "bid_score", "risk_profile", "rating")

    if compliance_risk and bid_risk:
        if (compliance_risk > 70 and bid_risk == "Low") or (
            compliance_risk < 30 and bid_risk == "High"
        ):
            conflicts.append(
                {
                    "id": "RISK_INCONSISTENCY",
                    "severity": "Medium",
                    "agents": ["compliance_risk", "bid_no_bid"],
                    "description": f"Risk assessment inconsistency: compliance_score={compliance_risk}, bid_risk={bid_risk}",
                    "resolution": "Review risk assessments and reconcile",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    # Check SLA consistency between scope and compliance
    scope_slas = _extract_nested(
        manifest, "scope_output", "scope_package", "sla_commitments"
    )
    compliance_slas = _extract_nested(
        manifest, "compliance_output", "compliance_package", "penalty_exposure"
    )
    if scope_slas and compliance_slas:
        conflicts.append(
            {
                "id": "SLA_CROSS_CHECK",
                "severity": "Medium",
                "agents": ["scope_builder", "compliance_risk"],
                "description": "SLA commitments defined in scope — verify alignment with compliance penalty exposure",
                "resolution": "Ensure scope SLA targets match compliance penalty thresholds",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # Check geography consistency between intake and transition
    intake_geo = _extract_nested(
        manifest, "intake_output", "extracted_fields", "geographies"
    )
    transition_waves = _extract_nested(
        manifest, "transition_change_output", "wave_rollout"
    )
    if intake_geo and transition_waves:
        if isinstance(intake_geo, dict):
            intake_geo = intake_geo.get("value", [])
        intake_geo_count = len(intake_geo) if isinstance(intake_geo, list) else 0
        wave_geo_count = sum(
            len(w.get("geographies", []))
            for w in transition_waves
            if isinstance(w, dict)
        )
        if (
            intake_geo_count > 0
            and wave_geo_count > 0
            and abs(intake_geo_count - wave_geo_count) > 2
        ):
            conflicts.append(
                {
                    "id": "GEO_COVERAGE_GAP",
                    "severity": "High",
                    "agents": ["intake", "transition_change"],
                    "description": f"Geography mismatch: intake identified {intake_geo_count} regions but transition wave rollout covers {wave_geo_count}",
                    "resolution": "Ensure all intake geographies are covered in the transition wave plan",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    # Check transition duration consistency between scope and transition
    scope_transition_weeks = _extract_nested(
        manifest, "scope_output", "scope_package", "transition_weeks"
    )
    transition_duration = _extract_nested(
        manifest, "transition_change_output", "transition_plan", "total_duration_weeks"
    )
    if scope_transition_weeks and transition_duration:
        if abs(scope_transition_weeks - transition_duration) > 4:
            conflicts.append(
                {
                    "id": "TRANSITION_DURATION_MISMATCH",
                    "severity": "High",
                    "agents": ["scope_builder", "transition_change"],
                    "description": f"Transition duration mismatch: scope={scope_transition_weeks}w, transition plan={transition_duration}w",
                    "resolution": "Align transition plan duration with scope builder's calculated timeline",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    # Check platform count consistency between intake and data analyst
    intake_platforms = _extract_nested(manifest, "intake_output", "platform_details")
    da_platforms = _extract_nested(
        manifest,
        "data_analyst_output",
        "data_analysis",
        "application_landscape",
        "platforms",
    )
    if intake_platforms and da_platforms:
        if isinstance(intake_platforms, list) and isinstance(da_platforms, list):
            if abs(len(intake_platforms) - len(da_platforms)) > 2:
                conflicts.append(
                    {
                        "id": "PLATFORM_COUNT_DRIFT",
                        "severity": "Medium",
                        "agents": ["intake", "data_analyst"],
                        "description": f"Platform count mismatch: intake={len(intake_platforms)}, data_analyst={len(da_platforms)}",
                        "resolution": "Use intake platform_details as source of truth",
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    }
                )

    # Check automation FTE savings vs commercial resource plan
    automation_opps = _extract_nested(
        manifest, "automation_ai_output", "prioritisation_table"
    )
    commercial_resources = _extract_nested(
        manifest, "commercial_output", "commercial_package", "resource_plan"
    )
    if automation_opps and commercial_resources and isinstance(automation_opps, list):
        total_automation_fte = sum(
            float(o.get("fte_equivalent", 0))
            for o in automation_opps
            if isinstance(o, dict) and o.get("fte_equivalent")
        )
        if total_automation_fte > 5:
            conflicts.append(
                {
                    "id": "AUTOMATION_COMMERCIAL_SYNC",
                    "severity": "Low",
                    "agents": ["automation_ai", "commercial_model"],
                    "description": f"Automation identifies {total_automation_fte:.1f} FTE savings — verify commercial model reflects YoY reduction",
                    "resolution": "Ensure commercial scenario accounts for automation-driven FTE reduction over contract life",
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return conflicts


def resolve_conflict(
    conflict: Dict[str, Any], manifest: Dict[str, Any], strategy: str = "latest_wins"
) -> Dict[str, Any]:
    """Apply a resolution strategy to a conflict."""
    resolution = {
        "conflict_id": conflict["id"],
        "strategy_applied": strategy,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "changes_made": [],
    }

    if strategy == "latest_wins":
        resolution["changes_made"].append("Latest agent output takes precedence")
    elif strategy == "escalate":
        resolution["changes_made"].append(
            "Flagged for human review — no automatic resolution"
        )
        resolution["requires_hitl"] = True
    elif strategy == "merge":
        resolution["changes_made"].append("Values merged from both sources")

    return resolution


def _extract_nested(data: Dict, *keys) -> Any:
    """Safely extract a nested value from a dictionary.

    Automatically unwraps agent output envelopes {status, agent, result: {...}}.
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            # Unwrap agent output envelope if present
            if (
                isinstance(current, dict)
                and "result" in current
                and isinstance(current.get("result"), dict)
            ):
                if "status" in current or "agent" in current:
                    current = current["result"]
        else:
            return None
    return current
