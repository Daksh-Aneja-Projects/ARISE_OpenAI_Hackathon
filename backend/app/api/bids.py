"""
Bid management API routes — real data, real LLM.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from app.services.auth import get_current_user, require_role
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.services.bid_repository import BidRepository
from app.models.bid import Bid, BidStatus, BidDocument

router = APIRouter(prefix="/api/bids", tags=["Bids"])


@router.delete("/clear-all")
async def clear_all_bids(
    user: dict = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)
):
    """Clear ALL data — bids, agent results, KB documents, HITL gates, generated docs, audit logs."""
    import os
    import shutil
    from app.models.hitl import HITLDecision, HITLGate
    from app.models.audit import AuditLog
    from app.models.knowledge import KBDocument, KBEmbedding
    from app.models.bid import GeneratedDocument, PipelineRun

    # Count bids before clearing
    result = await db.execute(select(Bid))
    bids = result.scalars().all()
    count = len(bids)

    # Delete ALL DB rows in FK-safe order (children first)
    await db.execute(delete(PipelineRun))
    await db.execute(delete(KBEmbedding))
    await db.execute(delete(KBDocument))
    await db.execute(delete(HITLDecision))
    await db.execute(delete(HITLGate))
    await db.execute(delete(BidDocument))
    await db.execute(delete(GeneratedDocument))
    await db.execute(delete(AuditLog))
    await db.execute(delete(Bid))
    await db.commit()

    # Clear RAG embeddings cache only if already loaded to avoid blocking on model init
    import sys

    if "app.knowledge.rag" in sys.modules:
        try:
            rag_pipeline = sys.modules["app.knowledge.rag"].rag_pipeline
            for attr in ("documents", "embeddings", "collections"):
                if hasattr(rag_pipeline, attr):
                    getattr(rag_pipeline, attr).clear()
        except Exception:
            pass

    # Clear pipeline run state
    try:
        from app.api.pipeline import pipeline_runs

        pipeline_runs.clear()
    except Exception:
        pass

    # Clear knowledge_base upload/output files from disk
    kb_dir = os.path.join("..", "knowledge_base")
    for sub in ["uploads", "outputs", "bid_data"]:
        sub_dir = os.path.join(kb_dir, sub)
        if os.path.exists(sub_dir):
            try:
                shutil.rmtree(sub_dir)
                os.makedirs(sub_dir, exist_ok=True)
            except Exception:
                pass

    return {
        "status": "success",
        "cleared_bids": count,
        "message": "All data reset successfully",
    }


class CreateBidRequest(BaseModel):
    client_name: str
    client_industry: Optional[str] = None
    client_geography: Optional[List[str]] = None
    contract_type: Optional[str] = None
    products: Optional[List[str]] = None
    submission_deadline: Optional[str] = None
    notes: Optional[str] = None
    # === Org Structure Linkage ===
    org_unit_id: Optional[str] = None  # Links bid to org node
    org_unit_label: Optional[str] = None  # Human-readable org unit label
    # === Optional Strategic Inputs (bible for all agents) ===
    known_competitors: Optional[List[str]] = None  # e.g. ["Infosys", "Accenture"]
    incumbent_vendor: Optional[str] = None  # Current vendor if any
    rate_onshore_usd: Optional[float] = None  # $/hr onshore
    rate_offshore_usd: Optional[float] = None  # $/hr offshore
    rate_nearshore_usd: Optional[float] = None  # $/hr nearshore
    deal_size_estimate: Optional[str] = None  # small/mid/large/enterprise
    past_relationship: Optional[str] = None  # new/existing/renewal
    additional_context: Optional[str] = None  # Free text — user knowledge


@router.get("/")
async def list_bids(
    status: Optional[str] = None,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    contract_type: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_bids = await BidRepository.get_all(db, status, search)
    results = [BidRepository.to_dict(b) for b in db_bids]
    if status:
        results = [b for b in results if b["status"] == status]
    if search:
        q = search.lower()
        results = [
            b
            for b in results
            if q in b.get("client_name", "").lower()
            or q in b.get("bid_reference", "").lower()
            or q in (b.get("client_industry") or "").lower()
        ]
    if industry:
        results = [
            b
            for b in results
            if (b.get("client_industry") or "").lower() == industry.lower()
        ]
    if contract_type:
        results = [
            b
            for b in results
            if (b.get("contract_type") or "").lower() == contract_type.lower()
        ]
    # Sort
    reverse = sort_order == "desc"
    if sort_by == "client_name":
        results.sort(key=lambda b: b.get("client_name", "").lower(), reverse=reverse)
    elif sort_by == "deadline":
        results.sort(
            key=lambda b: b.get("submission_deadline") or "9999", reverse=reverse
        )
    elif sort_by == "win_probability":
        results.sort(key=lambda b: b.get("win_probability") or 0, reverse=reverse)
    elif sort_by == "tcv":
        results.sort(key=lambda b: b.get("estimated_tcv") or 0, reverse=reverse)
    else:
        results.sort(key=lambda b: b.get("created_at", ""), reverse=reverse)
    return results


@router.get("/stats")
async def get_bid_stats(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]
    active = [
        b
        for b in bids
        if b["status"] not in ("submitted", "won", "lost", "abandoned", "no_bid")
    ]
    total_tcv = sum(b.get("estimated_tcv") or 0 for b in active)

    # Normalize win_probability to 0-1 range (agents may return 0-1 or 0-100)
    def _norm_wp(v):
        if v is None:
            return 0
        return v / 100 if v > 1 else v

    avg_wp = (
        (sum(_norm_wp(b.get("win_probability")) for b in active) / len(active))
        if active
        else 0
    )
    from sqlalchemy import select
    from app.models.hitl import HITLGate, HITLGateStatus

    try:
        query = select(HITLGate).where(HITLGate.status == HITLGateStatus.PENDING)
        result = await db.execute(query)
        pending = len(result.scalars().all())
    except Exception:
        pending = 0
    critical = len(
        [b for b in active if b.get("deadline_risk") in ("high", "critical")]
    )
    return {
        "active_bids": len(active),
        "total_pipeline_tcv": total_tcv,
        "avg_win_probability": round(avg_wp, 2),
        "pending_hitl_gates": pending,
        "at_risk_bids": critical,
        "bids_won": len([b for b in bids if b["status"] == "won"]),
        "bids_lost": len([b for b in bids if b["status"] == "lost"]),
        "avg_cycle_days": 0,
    }


@router.get("/{bid_id}")
async def get_bid(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    return BidRepository.to_dict(db_bid)


@router.post("/")
async def create_bid(
    req: CreateBidRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Build user_context (the "bible") from optional inputs
    user_context = {}
    if req.known_competitors:
        user_context["known_competitors"] = req.known_competitors
    if req.incumbent_vendor:
        user_context["incumbent_vendor"] = req.incumbent_vendor
    if req.rate_onshore_usd is not None:
        user_context["rate_onshore_usd"] = req.rate_onshore_usd
    if req.rate_offshore_usd is not None:
        user_context["rate_offshore_usd"] = req.rate_offshore_usd
    if req.rate_nearshore_usd is not None:
        user_context["rate_nearshore_usd"] = req.rate_nearshore_usd
    if req.deal_size_estimate:
        user_context["deal_size_estimate"] = req.deal_size_estimate
    if req.past_relationship:
        user_context["past_relationship"] = req.past_relationship
    if req.additional_context:
        user_context["additional_context"] = req.additional_context

    bid_data = {
        "client_name": req.client_name,
        "client_industry": req.client_industry,
        "contract_type": req.contract_type,
        "products": req.products or [],
        "submission_deadline": req.submission_deadline,
        "org_unit_id": req.org_unit_id,
        "org_unit_label": req.org_unit_label,
        "user_context": user_context,
        "client_geography": req.client_geography or [],
    }

    db_bid = await BidRepository.create(db, bid_data, user.get("id"))
    return BidRepository.to_dict(db_bid)


@router.delete("/{bid_id}")
async def delete_bid(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific bid and all its associated data."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")

    from sqlalchemy import delete
    from app.models.hitl import HITLDecision, HITLGate
    from app.models.audit import AuditLog
    from app.models.bid import GeneratedDocument, PipelineRun, BidDocument, Bid

    # Delete child records in FK-safe order
    await db.execute(delete(PipelineRun).where(PipelineRun.bid_id == bid_id))
    await db.execute(delete(HITLDecision).where(HITLDecision.bid_id == bid_id))
    await db.execute(delete(HITLGate).where(HITLGate.bid_id == bid_id))
    await db.execute(delete(BidDocument).where(BidDocument.bid_id == bid_id))
    await db.execute(
        delete(GeneratedDocument).where(GeneratedDocument.bid_id == bid_id)
    )
    await db.execute(delete(AuditLog).where(AuditLog.bid_id == bid_id))
    await db.execute(delete(Bid).where(Bid.id == bid_id))

    await db.commit()
    return {"status": "success", "message": f"Bid {bid_id} deleted"}


@router.post("/{bid_id}/clone")
async def clone_bid(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clone a bid as a starting template."""
    source_db = await BidRepository.get_by_id(db, bid_id)
    if not source_db:
        raise HTTPException(404, "Source bid not found")
    source = BidRepository.to_dict(source_db)
    bid_data = {
        "client_name": f"{source['client_name']} (Copy)",
        "client_industry": source.get("client_industry"),
        "contract_type": source.get("contract_type"),
        "products": source.get("products", []),
        "submission_deadline": source.get("submission_deadline"),
        "org_unit_id": source.get("org_unit_id"),
        "org_unit_label": source.get("org_unit_label"),
        "user_context": source.get("user_context", {}),
        "client_geography": source.get("client_geography", []),
    }
    db_cloned = await BidRepository.create(db, bid_data, user.get("id"))
    return BidRepository.to_dict(db_cloned)


@router.patch("/{bid_id}/status")
async def update_bid_status(
    bid_id: str,
    status: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_bid = await BidRepository.update_status(db, bid_id, status)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    return {"status": "updated", "new_status": status}


class UpdateBidRequest(BaseModel):
    """Fields that can be edited on an existing bid."""

    client_name: Optional[str] = None
    client_industry: Optional[str] = None
    client_geography: Optional[List[str]] = None
    contract_type: Optional[str] = None
    products: Optional[List[str]] = None
    submission_deadline: Optional[str] = None
    org_unit_id: Optional[str] = None
    org_unit_label: Optional[str] = None
    known_competitors: Optional[List[str]] = None
    incumbent_vendor: Optional[str] = None
    rate_onshore_usd: Optional[float] = None
    rate_offshore_usd: Optional[float] = None
    rate_nearshore_usd: Optional[float] = None
    deal_size_estimate: Optional[str] = None
    past_relationship: Optional[str] = None
    additional_context: Optional[str] = None
    estimated_tcv: Optional[float] = None
    win_probability: Optional[float] = None
    status: Optional[str] = None


@router.patch("/{bid_id}")
async def update_bid(
    bid_id: str,
    req: UpdateBidRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update bid details — org unit, client info, strategic inputs, etc."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)

    now = datetime.now(timezone.utc).isoformat()

    # Updatable top-level fields
    field_map = {
        "client_name": req.client_name,
        "client_industry": req.client_industry,
        "contract_type": req.contract_type,
        "products": req.products,
        "submission_deadline": req.submission_deadline,
        "org_unit_id": req.org_unit_id,
        "org_unit_label": req.org_unit_label,
        "estimated_tcv": req.estimated_tcv,
        "win_probability": req.win_probability,
        "status": req.status,
    }

    for key, val in field_map.items():
        if val is not None:
            bid[key] = val

    db_field_map = dict(field_map)
    if db_field_map.get("products") is not None:
        db_field_map["products"] = json.dumps(db_field_map["products"])
    if db_field_map.get("client_geography") is not None:
        db_field_map["client_geography"] = json.dumps(db_field_map["client_geography"])

    # Update manifest client/rfp/org sections
    manifest = bid.get("manifest", {})
    if req.client_name is not None:
        manifest.setdefault("client", {})["name"] = req.client_name
    if req.client_industry is not None:
        manifest.setdefault("client", {})["industry"] = req.client_industry
    if req.client_geography is not None:
        manifest.setdefault("client", {})["geography"] = req.client_geography
    if req.contract_type is not None:
        manifest.setdefault("rfp", {})["contract_type"] = req.contract_type
    if req.products is not None:
        manifest.setdefault("rfp", {})["products"] = req.products
    if req.submission_deadline is not None:
        manifest.setdefault("rfp", {})["submission_deadline"] = req.submission_deadline
    if req.org_unit_id is not None or req.org_unit_label is not None:
        new_id = (
            req.org_unit_id if req.org_unit_id is not None else bid.get("org_unit_id")
        )
        new_label = (
            req.org_unit_label
            if req.org_unit_label is not None
            else bid.get("org_unit_label")
        )
        manifest["org_unit"] = {"id": new_id, "label": new_label}
        manifest["org_unit_id"] = new_id
        manifest["org_unit_label"] = new_label

    # Update user_context (strategic inputs)
    user_context = bid.get("user_context", {})
    strategic_map = {
        "known_competitors": req.known_competitors,
        "incumbent_vendor": req.incumbent_vendor,
        "rate_onshore_usd": req.rate_onshore_usd,
        "rate_offshore_usd": req.rate_offshore_usd,
        "rate_nearshore_usd": req.rate_nearshore_usd,
        "deal_size_estimate": req.deal_size_estimate,
        "past_relationship": req.past_relationship,
        "additional_context": req.additional_context,
    }
    for key, val in strategic_map.items():
        if val is not None:
            user_context[key] = val
    bid["user_context"] = user_context
    manifest["user_context"] = user_context

    bid["manifest"] = manifest

    # Save back to DB
    manifest_data = bid["manifest"]
    db_bid.manifest = manifest_data
    db_bid.updated_at = datetime.fromisoformat(now)
    # Also update DB top-level fields
    for key, val in db_field_map.items():
        if val is not None and hasattr(db_bid, key):
            setattr(db_bid, key, val)

    await db.flush()
    await db.commit()

    # Audit log
    try:
        from app.api.audit import log_event

        log_event(
            event_type="bid_updated",
            event_detail=f"Bid {bid.get('bid_reference', bid_id)} details updated",
            bid_id=bid_id,
            user_name=user.get("name"),
        )
    except Exception:
        pass

    return bid


@router.post("/{bid_id}/documents")
async def upload_bid_documents(
    bid_id: str,
    files: List[UploadFile] = File(...),
    document_type: str = Form("rfp"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more RFP documents to a bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)
    import os

    save_dir = os.path.join("../knowledge_base", "rfps")
    os.makedirs(save_dir, exist_ok=True)
    uploaded = []
    for file in files:
        content = await file.read()
        doc_id = str(uuid.uuid4())
        path = os.path.join(save_dir, f"{doc_id}_{file.filename}")
        with open(path, "wb") as f:
            f.write(content)
        # Save to DB BidDocument
        db_doc = BidDocument(
            id=doc_id,
            bid_id=bid_id,
            filename=file.filename,
            file_path=path,
            file_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(content),
            uploaded_by=user.get("id"),
            document_type=document_type,
        )
        db.add(db_doc)

        doc = {
            "id": doc_id,
            "filename": file.filename,
            "file_path": path,
            "file_type": file.content_type,
            "file_size": len(content),
            "document_type": document_type,
            "uploaded_by": user.get("name", "Unknown"),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        manifest = dict(db_bid.manifest)
        if "documents" not in manifest:
            manifest["documents"] = []
        manifest["documents"].append(doc)
        db_bid.manifest = manifest

        bid.setdefault("documents", []).append(doc)
        uploaded.append(doc)

        # ── Auto-embed into RAG for agent access ──
        try:
            from app.knowledge.upload import extract_text
            from app.knowledge.embeddings import embedding_service
            from app.knowledge.rag import rag_pipeline

            extracted = extract_text(path, file.filename)
            if extracted and len(extracted) > 50:
                chunks = embedding_service.chunk_text(
                    extracted, chunk_size=400, overlap=50
                )
                for i, chunk in enumerate(chunks):
                    embedding = embedding_service.embed(chunk)
                    rag_pipeline.add_embedding(
                        doc_id=f"bid_{bid_id}_{doc_id}_chunk_{i}",
                        chunk_text=chunk,
                        embedding=embedding,
                        metadata={
                            "collection": "rfps",
                            "filename": file.filename,
                            "bid_id": bid_id,
                            "product": ", ".join(
                                bid.get("rfp", {}).get("products", [])
                            ),
                            "industry": bid.get("client", {}).get("industry", ""),
                        },
                    )
                doc["rag_indexed"] = True
                doc["rag_chunks"] = min(len(chunks), 50)
        except Exception:
            doc["rag_indexed"] = False

    if db_bid.status == BidStatus.CREATED and db_bid.manifest.get("documents"):
        db_bid.status = BidStatus.INTAKE_PROCESSING
        manifest = dict(db_bid.manifest)
        manifest["current_agent"] = "Intake Agent"
        db_bid.manifest = manifest

    await db.commit()
    return uploaded


# ── Agent Outputs ──────────────────────────────────────────────


@router.get("/{bid_id}/agent-outputs")
async def get_all_agent_outputs(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all agent outputs for a bid — the full result from each run."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        return {}
    bid = BidRepository.to_dict(db_bid)

    outputs = {}
    # Agent name → DB column name mapping (ALL 15 agents — keys MUST match frontend agent names)
    AGENT_COLUMN_MAP = {
        "intake": "intake_output",
        "data_analyst": "data_analyst_output",
        "client_intelligence": "client_intel_output",
        "strategic_assessment": "bid_no_bid_output",  # merged: bid_no_bid + competitive_intel
        "solution_scope": "scope_output",  # merged: scope_builder + solution_architect
        "automation_ai": "automation_ai_output",
        "transition_change": "transition_change_output",
        "commercial_model": "commercial_output",
        "compliance_risk": "compliance_output",
        "proposal_generator": "proposal_output",  # merged: proposal_writer + output_generator
        "discovery": "discovery_output",
        "feedback_learning": "feedback_output",
    }
    for agent_key, col_key in AGENT_COLUMN_MAP.items():
        val = bid.get(col_key)
        if val:
            # DB column already stores the full envelope {status, agent, result, logs}
            # from save_agent_result — return it directly, do NOT double-wrap
            outputs[agent_key] = val

    return outputs


@router.get("/{bid_id}/agent-output/{agent_name}")
async def get_agent_output(
    bid_id: str,
    agent_name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the full output of a specific agent run."""
    outputs = await get_all_agent_outputs(bid_id, user, db)
    if agent_name not in outputs:
        return {
            "status": "pending",
            "agent": agent_name,
            "message": "Agent has not produced output yet.",
        }
    return outputs[agent_name]


# ── Discovery Answers (Client Response Loop) ──────────────────

# Maps discovery question categories → agents that need re-running
CATEGORY_TO_AGENTS = {
    "Scope": [
        "solution_scope",
        "automation_ai",
        "transition_change",
        "commercial_model",
    ],
    "Technical": ["solution_scope", "automation_ai", "transition_change"],
    "Commercial": ["commercial_model"],
    "Governance": ["compliance_risk", "transition_change"],
    "Transition": ["transition_change", "commercial_model"],
    "Integration": [
        "solution_scope",
        "automation_ai",
        "transition_change",
        "commercial_model",
    ],
    "Compliance": ["compliance_risk"],
    "SLA": ["compliance_risk", "commercial_model"],
}


@router.post("/{bid_id}/discovery-answers")
async def save_discovery_answers(
    bid_id: str,
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Save client answers to discovery questions and determine which agents should be re-run.
    Body: { "answers": [{ "question": "...", "category": "Scope", "answer": "..." }] }
    """
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")

    answers = body.get("answers", [])
    if not answers:
        raise HTTPException(400, "No answers provided")

    # Persist answers into manifest
    bid = BidRepository.to_dict(db_bid)
    manifest = bid.get("manifest", {}) or {}
    manifest["discovery_answers"] = answers

    # Also inject answers into rfp_text context so all agents see them
    answers_text = "\n\n=== CLIENT DISCOVERY ANSWERS ===\n"
    for a in answers:
        if a.get("answer") and a["answer"].strip():
            answers_text += f"\nQ ({a.get('category', 'General')}): {a.get('question', '')}\nA: {a['answer']}\n"

    # Append to existing rfp_text so ALL agents see answers on re-run
    existing_text = manifest.get("rfp_text", "")
    enriched_text = existing_text + answers_text
    manifest["rfp_text"] = enriched_text  # Agents read THIS key
    manifest["rfp_text_with_answers"] = enriched_text  # Backward compat

    # Update manifest in DB
    db_bid.manifest = manifest
    await db.commit()

    # Compute which agents are affected
    affected_agents = set()
    answered_categories = set()
    for a in answers:
        if a.get("answer") and a["answer"].strip():
            cat = a.get("category", "")
            answered_categories.add(cat)
            for agent in CATEGORY_TO_AGENTS.get(cat, []):
                affected_agents.add(agent)

    # Always include proposal_generator and discovery itself when any answers are saved
    if affected_agents:
        affected_agents.add("proposal_generator")

    # Build agent labels for UI display
    AGENT_LABELS = {
        "solution_scope": "Solution Design & Scoping",
        "automation_ai": "AI & Automation Advisory",
        "transition_change": "Transition & Change Management",
        "commercial_model": "Commercial & Pricing",
        "compliance_risk": "Risk & Compliance",
        "proposal_generator": "Proposal Generator",
    }

    return {
        "saved": len([a for a in answers if a.get("answer", "").strip()]),
        "total_submitted": len(answers),
        "answered_categories": list(answered_categories),
        "affected_agents": [
            {"key": a, "label": AGENT_LABELS.get(a, a)} for a in sorted(affected_agents)
        ],
        "message": f"Saved {len([a for a in answers if a.get('answer', '').strip()])} answers. {len(affected_agents)} agents should be re-run for updated outputs.",
    }


@router.get("/{bid_id}/discovery-answers")
async def get_discovery_answers(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get saved client answers for discovery questions."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)
    manifest = bid.get("manifest", {}) or {}
    return {"answers": manifest.get("discovery_answers", [])}


# ── Agent Execution ────────────────────────────────────────────


@router.post("/{bid_id}/run-agent/{agent_name}")
async def run_agent(
    bid_id: str,
    agent_name: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger an agent run on a bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")
    bid = BidRepository.to_dict(db_bid)

    try:
        result = await _execute_agent(agent_name, bid_id, bid)
    except Exception as e:
        error_result = {
            "status": "failed",
            "agent": agent_name,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await BidRepository.save_agent_result(db, bid_id, agent_name, error_result)
        raise HTTPException(500, f"Agent '{agent_name}' failed: {str(e)}")

    # Store the full result
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    await BidRepository.save_agent_result(db, bid_id, agent_name, result)

    # Update manifest and key DB fields from agent execution
    db_bid.manifest = bid.get("manifest", db_bid.manifest)
    # Persist status, win_probability, estimated_tcv, etc. that agents set
    if bid.get("status") and hasattr(BidStatus, bid["status"].upper()):
        db_bid.status = bid["status"]
    if bid.get("win_probability") is not None:
        db_bid.win_probability = bid["win_probability"]
    if bid.get("estimated_tcv") is not None:
        db_bid.estimated_tcv = bid["estimated_tcv"]
    if bid.get("bid_recommendation") is not None:
        db_bid.bid_recommendation = bid["bid_recommendation"]
    await db.flush()

    # ── Stale output detection ──
    _mark_downstream_stale(bid_id, agent_name)

    # ── Audit log ──
    try:
        from app.api.audit import log_event

        log_event(
            event_type="agent_completed",
            event_detail=f"Agent '{agent_name}' completed for bid {bid.get('bid_reference', bid_id)}",
            bid_id=bid_id,
            agent_name=agent_name,
            user_name=user.get("name"),
        )
    except Exception:
        pass

    # ── Auto-create HITL gate for review ──
    try:
        from app.models.hitl import HITLGate

        agent_result = result.get("result", {})
        hitl_summary = ""
        if isinstance(agent_result, dict):
            hitl_summary = agent_result.get(
                "hitl_summary", agent_result.get("narrative", "")
            )
            if hitl_summary:
                hitl_summary = hitl_summary[:500]

        # Map agents to valid HITLGateType enum values
        AGENT_GATE_TYPE = {
            "intake": "intake_review",
            "data_analyst": "intake_review",
            "client_intelligence": "intake_review",
            "strategic_assessment": "bid_no_bid",
            "bid_no_bid": "bid_no_bid",
            "solution_scope": "scope_review",
            "scope_builder": "scope_review",
            "solution_architect": "solution_review",
            "automation_ai": "solution_review",
            "transition_change": "scope_review",
            "commercial_model": "commercial_approval",
            "compliance_risk": "legal_compliance",
            "proposal_generator": "final_review",
            "proposal_writer": "final_review",
            "discovery": "clarification_submission",
            "feedback_learning": "final_review",
        }
        gate_type = AGENT_GATE_TYPE.get(agent_name, "final_review")

        gate = HITLGate(
            bid_id=bid_id,
            gate_type=gate_type,
            status="pending",
            agent_summary=hitl_summary
            or f"Agent '{agent_name}' completed. Review required.",
            agent_data={"agent": agent_name, "timestamp": result.get("timestamp")},
        )
        db.add(gate)
        await db.flush()
    except Exception as gate_err:
        print(f"[HITL] Gate creation warning: {gate_err}")

    return result


# Strategic pipeline order — 12-agent pipeline
AGENT_PIPELINE_ORDER = [
    "intake",  # 1. Parse RFP docs → extract fields, build index
    "data_analyst",  # 2. Comprehensive data extraction from RFP
    "client_intelligence",  # 3. Web-research the client
    "strategic_assessment",  # 4. Go/No-Go + competitive landscape (merged)
    "solution_scope",  # 5. Architecture + WBS + effort estimation (merged)
    "automation_ai",  # 6. AI/automation opportunities
    "transition_change",  # 7. Transition planning, KT, change management
    "commercial_model",  # 8. Pricing & P&L
    "compliance_risk",  # 9. Legal/risk assessment
    "proposal_generator",  # 10. Full proposal writing + doc assembly (merged)
    "discovery",  # 11. Gap analysis, clarification questions
    "feedback_learning",  # 12. Capture learnings for future bids
]


def _mark_downstream_stale(bid_id: str, agent_name: str):
    """When an upstream agent re-runs, mark all downstream outputs as stale."""
    # Without in-memory dict, downstream staleness should be tracked in Bid.manifest if needed.
    pass


async def _execute_agent(agent_name: str, bid_id: str, bid: dict) -> dict:
    """Execute an agent and update bid state."""
    import time as _time
    from app.telemetry import telemetry

    _t0 = _time.monotonic()

    try:
        result = await __execute_agent_inner(agent_name, bid_id, bid)
        _dur = (_time.monotonic() - _t0) * 1000
        telemetry.record_agent_call(
            agent_name, bid_id=bid_id, duration_ms=_dur, success=True
        )
        return result
    except Exception as _exc:
        _dur = (_time.monotonic() - _t0) * 1000
        telemetry.record_agent_call(
            agent_name, bid_id=bid_id, duration_ms=_dur, success=False
        )
        telemetry.record_error(agent_name, str(_exc))
        raise


async def __execute_agent_inner(agent_name: str, bid_id: str, bid: dict) -> dict:
    """Internal — actual agent dispatch. Wrapped by _execute_agent for telemetry."""

    if agent_name == "intake":
        from app.agents.intake import IntakeAgent

        doc_texts = []
        all_image_infos = []
        for doc in bid.get("documents", []):
            try:
                from app.knowledge.upload import (
                    extract_text_from_file,
                    extract_all_images,
                )

                text = extract_text_from_file(doc["file_path"])
                if text:
                    doc_texts.append(text)
                # Extract images/diagrams from the document
                images = extract_all_images(doc["file_path"])
                if images:
                    all_image_infos.extend(images)
                    print(
                        f"[Vision] Extracted {len(images)} images from {doc.get('filename', 'unknown')}"
                    )
            except Exception:
                try:
                    with open(doc["file_path"], "r", encoding="utf-8") as f:
                        doc_texts.append(f.read())
                except Exception:
                    pass
        agent = IntakeAgent(bid_id, bid["manifest"], doc_texts)
        result = await agent.run()
        bid["intake_output"] = result.get("result")
        bid["manifest"]["intake_output"] = result.get("result")

        # CRITICAL: Store the raw RFP text so every subsequent agent can use it
        rfp_text = "\n\n".join(doc_texts)

        # ── Vision Analysis: Describe extracted images/diagrams ──
        # This ensures agents can reason about architecture diagrams, org charts,
        # data flows, and comparison tables that are embedded as images in RFPs.
        if all_image_infos:
            try:
                from app.services.vision import vision_service

                if vision_service.is_available:
                    print(
                        f"[Vision] Analysing {len(all_image_infos)} diagrams/charts from RFP..."
                    )
                    descriptions = await vision_service.describe_images_batch(
                        all_image_infos,
                        context=rfp_text[
                            :3000
                        ],  # Give vision model surrounding text context
                        max_concurrent=3,
                    )
                    vision_text = vision_service.format_image_descriptions_for_prompt(
                        descriptions
                    )
                    if vision_text:
                        rfp_text += vision_text
                        # Store image metadata in manifest for traceability
                        bid["manifest"]["rfp_images"] = [
                            {
                                "filename": d["filename"],
                                "page": d.get("page", 0),
                                "description_preview": d["description"][:200],
                            }
                            for d in descriptions
                        ]
                        print(
                            f"[Vision] Added {len(descriptions)} image descriptions to RFP context"
                        )
                else:
                    # No vision API key — add placeholders so agents know images exist
                    placeholder = "\n\n=== RFP VISUAL CONTENT (not analysed) ===\n"
                    placeholder += f"This RFP contains {len(all_image_infos)} embedded images/diagrams "
                    placeholder += "that could not be analysed (no Gemini API key configured for vision). "
                    placeholder += "These may contain architecture diagrams, org charts, data flows, "
                    placeholder += "or comparison tables. Request manual review.\n"
                    rfp_text += placeholder
            except Exception as vision_err:
                print(f"[Vision] Analysis failed (non-blocking): {vision_err}")

        bid["manifest"]["rfp_text"] = rfp_text  # Full text + image descriptions

        # Store document paths in manifest for data_analyst agent
        bid["manifest"]["documents"] = bid.get("documents", [])

        # Store the RFP section index for targeted agent access
        rfp_index = result.get("result", {}).get("rfp_index")
        if rfp_index:
            bid["manifest"]["rfp_index"] = rfp_index

        # Propagate extracted fields into the manifest rfp section
        extracted = result.get("result", {}).get("extracted_fields", {})
        if extracted:
            products = extracted.get("products", {}).get("value", [])
            contract_type = extracted.get("contract_type", {}).get("value", "")
            client_name = extracted.get("client_name", {}).get("value", "")
            if products:
                bid["manifest"].setdefault("rfp", {})["products"] = products
                bid["products"] = products
            if contract_type:
                bid["manifest"].setdefault("rfp", {})["contract_type"] = contract_type
                bid["contract_type"] = contract_type
            if client_name and client_name != "Unknown":
                bid["manifest"].setdefault("client", {})["name"] = client_name

        bid["status"] = "intake_review"
        bid["current_agent"] = "Awaiting Intake Review"
        return result

    elif agent_name == "bid_no_bid":
        from app.agents.bid_no_bid import BidNoBidAgent

        agent = BidNoBidAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["manifest"]["bid_score"] = result.get("result", {}).get("score_card", {})
        bid["win_probability"] = (
            result.get("result", {}).get("score_card", {}).get("win_probability")
        )
        bid["bid_recommendation"] = (
            result.get("result", {}).get("score_card", {}).get("recommendation")
        )
        bid["status"] = "bid_no_bid"
        bid["current_agent"] = "Awaiting Bid/No-Bid Decision"
        return result

    # ── MERGED: Strategic Assessment = Bid/No-Bid + Competitive Intel ──
    elif agent_name == "strategic_assessment":
        from app.agents.bid_no_bid import BidNoBidAgent
        from app.agents.competitive_intel import CompetitiveIntelAgent

        # Run both sub-agents
        bid_agent = BidNoBidAgent(bid_id, bid["manifest"])
        bid_result = await bid_agent.run()
        bid_data = bid_result.get("result", {})

        comp_agent = CompetitiveIntelAgent(bid_id, bid["manifest"])
        comp_result = await comp_agent.run()
        comp_data = comp_result.get("result", {})

        # Combine results
        combined = {**bid_data, **comp_data}

        def safe_str(val):
            if isinstance(val, dict):
                return str(val)
            if isinstance(val, list):
                return str(val)
            return str(val) if val else ""

        combined["narrative"] = (
            safe_str(bid_data.get("narrative"))
            + "\n\n"
            + safe_str(comp_data.get("narrative"))
        ).strip()
        combined["hitl_summary"] = (
            safe_str(bid_data.get("hitl_summary"))
            + " | "
            + safe_str(comp_data.get("hitl_summary"))
        )

        result = {
            "status": "success",
            "agent": "strategic_assessment",
            "result": combined,
        }

        # Persist to manifest
        bid["manifest"]["bid_score"] = bid_data.get("score_card", {})
        bid["win_probability"] = bid_data.get("score_card", {}).get("win_probability")
        bid["bid_recommendation"] = bid_data.get("score_card", {}).get("recommendation")
        bid["manifest"]["competitive_output"] = comp_data
        bid["bid_no_bid_output"] = result
        bid["competitive_output"] = {
            "status": "success",
            "agent": "competitive_intel",
            "result": comp_data,
        }
        bid["status"] = "strategy_alignment"
        bid["current_agent"] = "Strategic Assessment Complete"
        return result

    # ── MERGED: Solution Design & Scoping = Scope Builder + Solution Architect ──
    elif agent_name == "solution_scope":
        from app.agents.scope_builder import ScopeBuilderAgent
        from app.agents.solution_architect import SolutionArchitectAgent

        # Run solution architect first (architecture drives scope)
        sol_agent = SolutionArchitectAgent(bid_id, bid["manifest"])
        sol_result = await sol_agent.run()
        sol_data = sol_result.get("result", {})

        # Feed architecture into manifest for scope builder
        bid["manifest"]["solution_output"] = sol_data

        # Run scope builder with architecture context
        scope_agent = ScopeBuilderAgent(bid_id, bid["manifest"])
        scope_result = await scope_agent.run()
        scope_data = scope_result.get("result", {})

        # Combine results
        combined = {**sol_data, **scope_data}

        def safe_str(val):
            if isinstance(val, dict):
                return str(val)
            if isinstance(val, list):
                return str(val)
            return str(val) if val else ""

        combined["narrative"] = (
            safe_str(sol_data.get("narrative"))
            + "\n\n"
            + safe_str(scope_data.get("narrative"))
        ).strip()
        combined["hitl_summary"] = (
            safe_str(scope_data.get("hitl_summary"))
            + " | Architecture: "
            + safe_str(sol_data.get("hitl_summary"))
        )

        result = {"status": "success", "agent": "solution_scope", "result": combined}

        bid["scope_output"] = result
        bid["solution_output"] = {
            "status": "success",
            "agent": "solution_architect",
            "result": sol_data,
        }
        bid["manifest"]["scope_output"] = scope_data
        bid["manifest"]["solution_output"] = sol_data
        bid["status"] = "solution_review"
        bid["current_agent"] = "Solution & Scope Complete"
        return result

    # ── MERGED: Proposal Generator = Proposal Writer + Output Generator + QA validation ──
    elif agent_name == "proposal_generator":
        from app.agents.proposal_writer import ProposalWriterAgent
        from app.agents.output_generator import OutputGeneratorAgent

        # Run proposal writer first
        pw_agent = ProposalWriterAgent(bid_id, bid["manifest"])
        pw_result = await pw_agent.run()
        pw_data = pw_result.get("result", {})

        # Feed proposal into manifest for output generator
        bid["manifest"]["proposal_output"] = pw_data

        # Run output generator with proposal context
        og_agent = OutputGeneratorAgent(bid_id, bid["manifest"])
        og_result = await og_agent.run()
        og_data = og_result.get("result", {})

        # Combine results
        combined = {**pw_data, **og_data}

        def safe_str(val):
            if isinstance(val, dict):
                import json

                try:
                    return json.dumps(val, indent=2)
                except (TypeError, ValueError):
                    return str(val)
            if isinstance(val, list):
                import json

                try:
                    return json.dumps(val, indent=2)
                except (TypeError, ValueError):
                    return str(val)
            return str(val) if val else ""

        combined["narrative"] = (
            safe_str(pw_data.get("narrative"))
            + "\n\n"
            + safe_str(og_data.get("narrative"))
        ).strip()
        combined["hitl_summary"] = (
            safe_str(pw_data.get("hitl_summary"))
            + " | "
            + safe_str(og_data.get("hitl_summary"))
        )

        result = {
            "status": "success",
            "agent": "proposal_generator",
            "result": combined,
        }

        bid["proposal_output"] = result
        bid["output_generator_output"] = {
            "status": "success",
            "agent": "output_generator",
            "result": og_data,
        }
        bid["manifest"]["proposal_output"] = pw_data
        bid["manifest"]["output_generator_output"] = og_data
        bid["status"] = "final_review"
        bid["current_agent"] = "Proposal Generation Complete"
        return result

    elif agent_name == "scope_builder":
        from app.agents.scope_builder import ScopeBuilderAgent

        agent = ScopeBuilderAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["scope_output"] = result.get("result")
        bid["manifest"]["scope_output"] = result.get("result")
        bid["status"] = "scope_review"
        bid["current_agent"] = "Awaiting Scope Review"
        return result

    elif agent_name == "solution_architect":
        from app.agents.solution_architect import SolutionArchitectAgent

        agent = SolutionArchitectAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["solution_output"] = result.get("result")
        bid["manifest"]["solution_output"] = result.get("result")
        bid["status"] = "solution_review"
        bid["current_agent"] = "Awaiting Solution Review"
        return result

    elif agent_name == "competitive_intel":
        from app.agents.competitive_intel import CompetitiveIntelAgent

        agent = CompetitiveIntelAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["competitive_output"] = result.get("result")
        bid["manifest"]["competitive_output"] = result.get("result")
        bid["status"] = "strategy_alignment"
        bid["current_agent"] = "Awaiting Strategy Alignment"
        return result

    elif agent_name == "transition_change":
        from app.agents.transition_change import TransitionChangeAgent

        agent = TransitionChangeAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["transition_change_output"] = result.get("result")
        bid["manifest"]["transition_change_output"] = result.get("result")
        # Feed transition duration into manifest for commercial agent
        tp = result.get("result", {}).get("transition_plan", {})
        if tp.get("total_duration_weeks"):
            bid["manifest"].setdefault(
                "transition_duration_weeks", tp["total_duration_weeks"]
            )
        bid["status"] = "transition_review"
        bid["current_agent"] = "Awaiting Transition Review"
        return result

    elif agent_name == "commercial_model":
        from app.agents.commercial_model import CommercialModelAgent

        agent = CommercialModelAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["commercial_output"] = result.get("result")
        bid["manifest"]["commercial_output"] = result.get("result")
        # Extract real calculated TCV from P&L
        pl = result.get("result", {}).get("pl_model", {})
        if pl:
            bid["estimated_tcv"] = pl.get("revenue", {}).get("total_contract_value")
        bid["status"] = "commercial_approval"
        bid["current_agent"] = "Awaiting Commercial Approval"
        return result

    elif agent_name == "compliance_risk":
        from app.agents.compliance_risk import ComplianceRiskAgent

        agent = ComplianceRiskAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["compliance_output"] = result.get("result")
        bid["manifest"]["compliance_output"] = result.get("result")
        bid["status"] = "legal_sign_off"
        bid["current_agent"] = "Awaiting Legal Sign-off"
        return result

    elif agent_name == "output_generator":
        from app.agents.output_generator import OutputGeneratorAgent

        agent = OutputGeneratorAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["output_generator_output"] = result.get("result")
        bid["manifest"]["output_generator_output"] = result.get("result")
        bid["status"] = "qa_review"
        bid["current_agent"] = "Output Generation Complete"
        return result

    elif agent_name == "qa":
        from app.agents.qa_agent import QAAgent

        agent = QAAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["qa_output"] = result.get("result")
        bid["manifest"]["qa_output"] = result.get("result")
        bid["status"] = "final_review"
        bid["current_agent"] = "Awaiting Final Review"
        return result

    elif agent_name == "automation_ai":
        from app.agents.automation_ai import AutomationAIAgent

        agent = AutomationAIAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["automation_ai_output"] = result.get("result")
        bid["manifest"]["automation_ai_output"] = result.get("result")
        bid["status"] = "solution_review"
        bid["current_agent"] = "Intelligent Solutioning Complete"
        return result

    elif agent_name == "client_intelligence":
        from app.agents.client_intelligence import ClientIntelligenceAgent

        agent = ClientIntelligenceAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["client_intel_output"] = result.get("result")
        bid["manifest"]["client_intel_output"] = result.get("result")
        bid["status"] = "client_intel_review"
        bid["current_agent"] = "Client Intelligence Complete"
        return result

    elif agent_name == "proposal_writer":
        from app.agents.proposal_writer import ProposalWriterAgent

        agent = ProposalWriterAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["proposal_output"] = result.get("result")
        bid["manifest"]["proposal_output"] = result.get("result")
        bid["status"] = "proposal_review"
        bid["current_agent"] = "Proposal Draft Complete"
        return result

    elif agent_name == "discovery":
        from app.agents.discovery import DiscoveryAgent

        agent = DiscoveryAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["discovery_output"] = result.get("result")
        bid["manifest"]["discovery_output"] = result.get("result")
        bid["status"] = "qa_review"
        bid["current_agent"] = "Discovery Analysis Complete"
        return result

    elif agent_name == "data_analyst":
        from app.agents.data_analyst import DataAnalystAgent

        doc_texts = []
        for doc in bid.get("documents", []):
            try:
                from app.knowledge.upload import extract_text_from_file

                text = extract_text_from_file(doc["file_path"])
                if text:
                    doc_texts.append(text)
            except Exception:
                pass
        agent = DataAnalystAgent(bid_id, bid["manifest"], doc_texts)
        result = await agent.run()
        bid["data_analyst_output"] = result.get("result")
        bid["manifest"]["data_analysis"] = result.get("result", {}).get(
            "data_analysis", {}
        )
        bid["manifest"]["data_analyst_output"] = result.get("result")
        bid["current_agent"] = "Data Intelligence Complete"
        return result

    elif agent_name == "feedback_learning":
        from app.agents.feedback_learning import FeedbackLearningAgent

        agent = FeedbackLearningAgent(bid_id, bid["manifest"])
        result = await agent.run()
        bid["feedback_output"] = result.get("result")
        bid["manifest"]["feedback_output"] = result.get("result")
        bid["current_agent"] = "Learning & Feedback Complete"
        return result

    else:
        raise HTTPException(400, f"Unknown agent: {agent_name}")
