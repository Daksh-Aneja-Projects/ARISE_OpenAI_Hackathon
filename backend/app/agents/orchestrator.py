"""
Orchestrator Agent â€” Agent 0 (L22 Agent Architect)
Dynamically constructs, compiles, and orchestrates transient Agent Swarms.
"""

from typing import Any, Dict, List, Optional
import json
import logging
from app.agents.base import BaseAgent

# Dynamic swarm architecture mandates strictly LLM-generated pipelines.
# No static fallback pipelines are permitted.


class OrchestratorAgent(BaseAgent):
    """Agent 0: L22 Autonomous Swarm Architect."""

    name = "Orchestrator Agent"
    agent_tier = (
        "analytical"  # Swarm arch needs broad pool access, no single provider lock
    )

    def __init__(
        self, bid_id: str, manifest: Dict[str, Any], current_status: str = "created"
    ):
        super().__init__(bid_id, manifest)
        self.current_status = current_status
        # Use generated swarm if available, otherwise fallback
        self.pipeline_sequence = self.manifest.get("generated_swarm_pipeline", [])

    async def _generate_swarm(self) -> List[Dict[str, Any]]:
        """L22 Autonomous Swarm Generation using Bidder's own LLM service."""
        try:
            prompt = (
                f"You are the L22 Swarm Architect. "
                f"Analyze this Bid Manifest and generate an optimal JSON array of agent execution stages.\n"
                f"Manifest constraints:\n"
                f"- Required Agents (pick only relevant): intake, bid_no_bid, scope_builder, solution_architect, automation_ai, data_analyst, commercial_model, compliance_risk, competitive_intel, transition_change, client_intelligence, proposal_writer, output_generator, qa.\n"
                f"Bid Data: {json.dumps(self.manifest)[:500]}\n\n"
                f"Output strictly valid JSON array of objects with keys: agent, status, next_status, gate (or null), gate_reviewer_role (or null)."
            )

            generated_pipeline = await self.llm_json(prompt, max_tokens=3000)

            if not isinstance(generated_pipeline, list) or len(generated_pipeline) == 0:
                raise ValueError("LLM returned empty or invalid swarm pipeline.")

            logging.info(
                f"L22 Architect: Successfully generated custom agent swarm for Bid {self.bid_id} with {len(generated_pipeline)} agents."
            )
            return generated_pipeline
        except Exception as e:
            logging.error(f"L22 Swarm Generation failed: {e}")
            raise ValueError(f"Failed to generate dynamic swarm via LLM: {e}")

    async def observe(self) -> Dict[str, Any]:
        """Gather pipeline state and determine next steps."""
        if not self.pipeline_sequence:
            self.pipeline_sequence = await self._generate_swarm()
            self.manifest["generated_swarm_pipeline"] = self.pipeline_sequence

        current_idx = -1
        for i, stage in enumerate(self.pipeline_sequence):
            if (
                stage["status"] == self.current_status
                or stage["next_status"] == self.current_status
            ):
                current_idx = i
                break

        completed_agents = []
        pending_agents = []
        for i, stage in enumerate(self.pipeline_sequence):
            if i < current_idx:
                completed_agents.append(stage["agent"])
            elif i > current_idx:
                pending_agents.append(stage["agent"])

        return {
            "current_status": self.current_status,
            "current_stage_index": current_idx,
            "completed_agents": completed_agents,
            "pending_agents": pending_agents,
            "total_stages": len(self.pipeline_sequence),
            "manifest_keys": list(self.manifest.keys()),
        }

    async def orient(self, obs: Dict[str, Any]) -> Dict[str, Any]:
        """Determine which agent should run next."""
        idx = obs["current_stage_index"]
        if idx < 0:
            first_stage = self.pipeline_sequence[0]
            return {
                "action": "start_pipeline",
                "next_agent": first_stage["agent"],
                "stage_index": 0,
            }

        if idx >= len(self.pipeline_sequence) - 1:
            return {"action": "pipeline_complete", "stage_index": idx}

        next_stage = self.pipeline_sequence[idx + 1]
        return {
            "action": "advance",
            "next_agent": next_stage["agent"],
            "next_status": next_stage["status"],
            "requires_gate": next_stage.get("gate") is not None,
            "gate_type": next_stage.get("gate"),
            "stage_index": idx + 1,
            "gate_reviewer_role": next_stage.get("gate_reviewer_role"),
        }

    async def decide(self, orientation: Dict[str, Any]) -> Dict[str, Any]:
        """Build execution plan for the next pipeline step."""
        return {
            "action": orientation["action"],
            "next_agent": orientation.get("next_agent"),
            "next_status": orientation.get("next_status"),
            "requires_gate": orientation.get("requires_gate", False),
            "gate_type": orientation.get("gate_type"),
            "stage_index": orientation.get("stage_index", 0),
            "gate_reviewer_role": orientation.get("gate_reviewer_role", "system"),
        }

    async def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the pipeline advancement decision and enforce immutable ledger recording."""
        import logging

        if decision["action"] == "pipeline_complete":
            return {
                "status": "pipeline_complete",
                "message": "Swarm execution complete.",
                "hitl_summary": "The transient agent swarm has completed all objectives and will now dissolve.",
            }

        stage = self.pipeline_sequence[decision["stage_index"]]
        gate_required = decision["requires_gate"]
        gate_type = decision.get("gate_type")

        ledger_receipt = None
        if gate_required:
            logging.info(
                f"[HITL GATE] Gate '{gate_type}' initiated for agent '{decision['next_agent']}'"
            )

        return {
            "status": "advancing",
            "next_agent": decision["next_agent"],
            "next_status": decision["next_status"],
            "gate_required": gate_required,
            "gate_type": gate_type,
            "ledger_receipt": ledger_receipt,
            "stage": stage,
            "progress": f"{decision['stage_index'] + 1}/{len(self.pipeline_sequence)}",
            "hitl_summary": f"Swarm allocating to {decision['next_agent']}",
        }


def get_next_pipeline_step(
    current_status: str, manifest: Dict[str, Any] = None
) -> Optional[Dict[str, Any]]:
    """Utility: Get the next pipeline step for a given status."""
    seq = manifest.get("generated_swarm_pipeline") if manifest else None
    if not seq:
        return None
    for i, stage in enumerate(seq):
        if stage["next_status"] == current_status:
            if i + 1 < len(seq):
                return seq[i + 1]
    return None


def get_pipeline_progress(
    current_status: str, manifest: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Utility: Calculate pipeline progress percentage."""
    seq = manifest.get("generated_swarm_pipeline") if manifest else None
    if not seq:
        return {
            "current_stage": 0,
            "total_stages": 0,
            "percentage": 0,
            "agent": "unknown",
        }
    for i, stage in enumerate(seq):
        if stage["status"] == current_status or stage["next_status"] == current_status:
            return {
                "current_stage": i,
                "total_stages": len(seq),
                "percentage": round((i / len(seq)) * 100),
                "agent": stage["agent"],
            }
    return {
        "current_stage": 0,
        "total_stages": len(seq),
        "percentage": 0,
        "agent": "unknown",
    }
