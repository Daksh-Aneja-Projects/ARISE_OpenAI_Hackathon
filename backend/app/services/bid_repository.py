import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.bid import Bid, BidStatus


class BidRepository:
    """Repository for managing Bid entities in the database."""

    @staticmethod
    async def get_all(
        db: AsyncSession, status: Optional[str] = None, search: Optional[str] = None
    ) -> List[Bid]:
        query = select(Bid).order_by(Bid.created_at.desc())
        if status:
            query = query.where(Bid.status == status)
        result = await db.execute(query)
        bids = result.scalars().all()

        # Apply search filter in-memory for now (since it searches JSON deeply)
        if search:
            q = search.lower()
            filtered = []
            for b in bids:
                if (
                    q in b.client_name.lower()
                    or q in b.bid_reference.lower()
                    or (b.client_industry and q in b.client_industry.lower())
                ):
                    filtered.append(b)
            return filtered
        return list(bids)

    @staticmethod
    async def get_by_id(db: AsyncSession, bid_id: str) -> Optional[Bid]:
        result = await db.execute(select(Bid).where(Bid.id == bid_id))
        return result.scalars().first()

    @staticmethod
    async def create(
        db: AsyncSession, bid_data: Dict[str, Any], user_id: str = None
    ) -> Bid:
        # Generate a bid reference
        result = await db.execute(select(Bid).order_by(Bid.created_at.desc()).limit(1))
        last_bid = result.scalars().first()
        next_num = 1
        if last_bid and last_bid.bid_reference.startswith("BID-"):
            try:
                next_num = int(last_bid.bid_reference.split("-")[-1]) + 1
            except ValueError:
                pass

        ref = f"BID-2026-{next_num:04d}"

        bid = Bid(
            bid_reference=ref,
            client_name=bid_data.get("client_name"),
            client_industry=bid_data.get("client_industry"),
            client_geography=json.dumps(bid_data.get("client_geography", [])),
            contract_type=bid_data.get("contract_type"),
            products=json.dumps(bid_data.get("products", [])),
            created_by=user_id,
            manifest=bid_data,  # Store the raw request as manifest
            status=BidStatus.CREATED,
        )
        db.add(bid)
        await db.flush()
        return bid

    @staticmethod
    async def update_status(
        db: AsyncSession, bid_id: str, status: str
    ) -> Optional[Bid]:
        bid = await BidRepository.get_by_id(db, bid_id)
        if bid:
            bid.status = status
            bid.updated_at = datetime.now(timezone.utc)
            await db.flush()
        return bid

    AGENT_TO_COLUMN = {
        "intake": "intake_output",
        "data_analyst": "data_analyst_output",
        "client_intelligence": "client_intel_output",
        "bid_no_bid": "bid_no_bid_output",
        "strategic_assessment": "bid_no_bid_output",
        "scope_builder": "scope_output",
        "solution_architect": "solution_output",
        "solution_scope": "scope_output",
        "automation_ai": "automation_ai_output",
        "competitive_intel": "competitive_output",
        "commercial_model": "commercial_output",
        "compliance_risk": "compliance_output",
        "proposal_writer": "proposal_output",
        "proposal_generator": "proposal_output",
        "output_generator": "output_generator_output",
        "discovery": "discovery_output",
        "qa": "qa_output",
        "feedback_learning": "feedback_output",
        "transition_change": "transition_change_output",
    }

    @staticmethod
    async def save_agent_result(
        db: AsyncSession, bid_id: str, agent_name: str, result: dict
    ) -> Optional[Bid]:
        bid = await BidRepository.get_by_id(db, bid_id)
        if not bid:
            return None

        # Map every agent to its dedicated DB column
        col = BidRepository.AGENT_TO_COLUMN.get(agent_name)
        if col and hasattr(bid, col):
            setattr(bid, col, result)

        # Update manifest
        manifest = dict(bid.manifest)
        manifest[f"{agent_name}_output"] = result
        bid.manifest = manifest
        bid.updated_at = datetime.now(timezone.utc)

        await db.flush()
        return bid

    @staticmethod
    def to_dict(bid: Bid) -> dict:
        """Convert SQLAlchemy model to the dictionary format expected by the frontend."""
        # Compute current_agent from status
        STATUS_TO_AGENT = {
            "created": "intake",
            "intake_processing": "intake",
            "intake_review": "bid_no_bid",
            "bid_no_bid": "bid_no_bid",
            "scope_building": "scope_builder",
            "scope_review": "automation_ai",
            "solution_design": "automation_ai",
            "solution_review": "competitive_intel",
            "strategy_alignment": "commercial_model",
            "commercial_modeling": "commercial_model",
            "commercial_approval": "compliance_risk",
            "compliance_review": "compliance_risk",
            "legal_sign_off": "proposal_writer",
            "output_generation": "output_generator",
            "qa_review": "qa",
            "final_review": "output_generator",
        }
        current_agent = STATUS_TO_AGENT.get(bid.status, "intake")

        d = {
            "id": bid.id,
            "bid_reference": bid.bid_reference,
            "client_name": bid.client_name,
            "client_industry": bid.client_industry,
            "status": bid.status,
            "created_at": bid.created_at.isoformat() if bid.created_at else None,
            "updated_at": bid.updated_at.isoformat() if bid.updated_at else None,
            "manifest": bid.manifest or {},
            "org_unit_id": (bid.manifest or {}).get("org_unit_id")
            or (bid.manifest or {}).get("org_unit", {}).get("id"),
            "org_unit_label": (bid.manifest or {}).get("org_unit_label")
            or (bid.manifest or {}).get("org_unit", {}).get("label"),
            "intake_output": bid.intake_output,
            "data_analyst_output": bid.data_analyst_output,
            "client_intel_output": bid.client_intel_output,
            "bid_no_bid_output": bid.bid_no_bid_output,
            "scope_output": bid.scope_output,
            "solution_output": bid.solution_output,
            "automation_ai_output": bid.automation_ai_output,
            "competitive_output": bid.competitive_output,
            "commercial_output": bid.commercial_output,
            "compliance_output": bid.compliance_output,
            "proposal_output": bid.proposal_output,
            "output_generator_output": bid.output_generator_output,
            "discovery_output": bid.discovery_output,
            "qa_output": bid.qa_output,
            "feedback_output": bid.feedback_output,
            "transition_change_output": bid.transition_change_output,
            "estimated_tcv": bid.estimated_tcv,
            "win_probability": bid.win_probability,
            "deadline_risk": bid.deadline_risk or "low",
            "bid_recommendation": bid.bid_recommendation,
            "strategic_value": bid.strategic_value,
            "current_agent": current_agent,
        }

        # Parse JSON fields
        try:
            d["client_geography"] = (
                json.loads(bid.client_geography) if bid.client_geography else []
            )
        except (ValueError, TypeError):
            d["client_geography"] = []

        try:
            d["products"] = json.loads(bid.products) if bid.products else []
        except (ValueError, TypeError):
            d["products"] = []

        # Merge manifest root keys (contract_type, org_unit_id, etc.)
        for k, v in (bid.manifest or {}).items():
            if k not in d and k != "id":
                d[k] = v

        return d
