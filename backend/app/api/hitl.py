"""
HITL Gate API — real data only, no seeds.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from app.services.auth import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bid_repository import BidRepository
from app.models.hitl import (
    HITLGate,
    HITLGateStatus,
    HITLGateType,
    HITLDecisionType,
    HITLDecision,
)
from app.models.bid import Bid

router = APIRouter(prefix="/api/hitl", tags=["HITL Gates"])


class GateDecisionRequest(BaseModel):
    decision: str
    comments: str


class CreateGateRequest(BaseModel):
    bid_id: str
    gate_type: str
    agent_summary: str
    agent_data: Optional[dict] = None
    assigned_reviewer: Optional[str] = None
    client_name: Optional[str] = None
    bid_reference: Optional[str] = None


SLA_MAP = {
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


def _enum_val(v):
    """Safely extract .value from enum or return string as-is."""
    return v.value if hasattr(v, "value") else v


def gate_to_dict(gate: HITLGate, bid: Bid = None) -> dict:
    return {
        "id": gate.id,
        "bid_id": gate.bid_id,
        "gate_type": _enum_val(gate.gate_type),
        "status": _enum_val(gate.status),
        "assigned_reviewer": gate.assigned_reviewer_id,
        "agent_summary": gate.agent_summary,
        "agent_data": gate.agent_data,
        "sla_hours": gate.sla_hours,
        "sla_deadline": gate.sla_deadline.isoformat() if gate.sla_deadline else None,
        "is_escalated": gate.is_escalated,
        "decision": _enum_val(gate.decision) if gate.decision else None,
        "decided_by": gate.decided_by,
        "decided_at": gate.decided_at.isoformat() if gate.decided_at else None,
        "comments": gate.comments,
        "created_at": gate.created_at.isoformat() if gate.created_at else None,
        "bid_reference": bid.bid_reference if bid else "",
        "client_name": bid.client_name if bid else "",
    }


@router.get("/")
async def list_gates(
    status: Optional[str] = None,
    bid_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(HITLGate, Bid).join(Bid, HITLGate.bid_id == Bid.id)
    if status:
        query = query.where(HITLGate.status == HITLGateStatus(status).value)
    if bid_id:
        query = query.where(HITLGate.bid_id == bid_id)

    result = await db.execute(query)
    gates_bids = result.all()

    results = [gate_to_dict(g, b) for g, b in gates_bids]
    now = datetime.now(timezone.utc)
    for g in results:
        if g["sla_deadline"]:
            dl = datetime.fromisoformat(g["sla_deadline"])
            g["sla_remaining_hours"] = round(
                max(0, (dl - now).total_seconds() / 3600), 1
            )
    return results


@router.get("/pending")
async def get_pending(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    query = (
        select(HITLGate, Bid)
        .join(Bid, HITLGate.bid_id == Bid.id)
        .where(HITLGate.status == HITLGateStatus.PENDING.value)
    )
    result = await db.execute(query)
    gates_bids = result.all()

    results = [gate_to_dict(g, b) for g, b in gates_bids]
    now = datetime.now(timezone.utc)
    for g in results:
        if g["sla_deadline"]:
            dl = datetime.fromisoformat(g["sla_deadline"])
            g["sla_remaining_hours"] = round(
                max(0, (dl - now).total_seconds() / 3600), 1
            )
    return results


@router.post("/{gate_id}/decide")
async def decide(
    gate_id: str,
    req: GateDecisionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_gate = await db.get(HITLGate, gate_id)
    if not db_gate:
        raise HTTPException(404, "Gate not found")
    if db_gate.status != HITLGateStatus.PENDING:
        raise HTTPException(400, "Already resolved")
    if not req.comments.strip():
        raise HTTPException(400, "Comments required for all HITL decisions")

    db_gate.decision = HITLDecisionType(req.decision)
    db_gate.decided_by = user.get("id", user.get("name"))
    db_gate.decided_at = datetime.now(timezone.utc)
    db_gate.comments = req.comments
    db_gate.status = HITLGateStatus.COMPLETED
    db_gate.is_locked = True

    db_decision = HITLDecision(
        gate_id=gate_id,
        bid_id=db_gate.bid_id,
        gate_type=db_gate.gate_type,
        reviewer_id=user.get("id", "Unknown"),
        reviewer_name=user.get("name", "Unknown"),
        decision=HITLDecisionType(req.decision),
        comments=req.comments,
    )
    db.add(db_decision)
    await db.flush()

    # Propagate decision to the bid record (informational — does NOT block pipeline)
    try:
        db_bid = await BidRepository.get_by_id(db, db_gate.bid_id)
        if db_bid:
            # 1. Update manifest summary
            manifest = dict(db_bid.manifest)
            if "hitl_decisions" not in manifest:
                manifest["hitl_decisions"] = []
            manifest["hitl_decisions"].append(
                {
                    "gate_id": gate_id,
                    "gate_type": _enum_val(db_gate.gate_type),
                    "decision": req.decision,
                    "decided_by": user.get("name"),
                    "decided_at": db_gate.decided_at.isoformat(),
                    "comments": req.comments,
                }
            )
            db_bid.manifest = manifest

            # 2. Embed feedback live into the specific agent's output
            from app.orchestration.engine import GATE_TYPE_MAP

            target_agent = None
            for agent_name, info in GATE_TYPE_MAP.items():
                if info["gate_type"] == _enum_val(db_gate.gate_type):
                    target_agent = agent_name
                    break

            if target_agent:
                # Find the column from bid_repository
                col_name = BidRepository.AGENT_TO_COLUMN.get(target_agent)
                if col_name:
                    current_output = getattr(db_bid, col_name)
                    if current_output:
                        updated_output = dict(current_output)
                        updated_output["human_feedback"] = {
                            "decision": req.decision,
                            "comments": req.comments,
                            "reviewer": user.get("name"),
                            "timestamp": db_gate.decided_at.isoformat(),
                        }
                        setattr(db_bid, col_name, updated_output)

            db_bid.updated_at = datetime.now(timezone.utc)
            await db.flush()

    except Exception as e:
        print(f"[HITL] Error propagating decision: {e}")

    # Audit log
    try:
        from app.api.audit import log_event

        log_event(
            event_type="hitl_decision",
            event_detail=f"HITL gate '{_enum_val(db_gate.gate_type)}' decided as '{req.decision}' for bid {db_gate.bid_id}",
            bid_id=db_gate.bid_id,
            user_name=user.get("name"),
        )
    except Exception:
        pass

    await db.commit()
    return {
        "status": "recorded",
        "decision": req.decision,
        "gate_type": _enum_val(db_gate.gate_type),
    }


@router.post("/")
async def create_gate(
    req: CreateGateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gate_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    sla = SLA_MAP.get(req.gate_type, 24)
    db_gate = HITLGate(
        id=gate_id,
        bid_id=req.bid_id,
        gate_type=HITLGateType(req.gate_type),
        status=HITLGateStatus.PENDING,
        agent_summary=req.agent_summary,
        agent_data=req.agent_data,
        assigned_reviewer_id=req.assigned_reviewer or user.get("id", user.get("name")),
        sla_hours=sla,
        sla_deadline=now + timedelta(hours=sla),
    )
    db.add(db_gate)
    await db.commit()

    db_bid = await BidRepository.get_by_id(db, req.bid_id)
    return gate_to_dict(db_gate, db_bid)
