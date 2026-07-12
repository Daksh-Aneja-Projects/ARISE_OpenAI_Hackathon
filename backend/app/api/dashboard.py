"""
Executive Dashboard API — analytics, trends, and pipeline health metrics.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from app.services.auth import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.bid_repository import BidRepository

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/executive")
async def get_executive_dashboard(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Executive-level dashboard with pipeline health, trends, and KPIs."""
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]
    active = [
        b
        for b in bids
        if b["status"] not in ("submitted", "won", "lost", "abandoned", "no_bid")
    ]
    won = [b for b in bids if b["status"] == "won"]
    lost = [b for b in bids if b["status"] == "lost"]
    total_completed = len(won) + len(lost)

    # Pipeline by stage
    stage_counts = {}
    stage_tcv = {}
    for b in bids:
        s = b.get("status", "created")
        stage_counts[s] = stage_counts.get(s, 0) + 1
        stage_tcv[s] = stage_tcv.get(s, 0) + (b.get("estimated_tcv") or 0)

    # Win rate
    win_rate = (len(won) / total_completed * 100) if total_completed > 0 else 0

    # TCV analysis
    total_pipeline_tcv = sum(b.get("estimated_tcv") or 0 for b in active)
    won_tcv = sum(b.get("estimated_tcv") or 0 for b in won)
    lost_tcv = sum(b.get("estimated_tcv") or 0 for b in lost)

    # Risk distribution
    risk_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for b in active:
        risk = b.get("deadline_risk", "low")
        risk_dist[risk] = risk_dist.get(risk, 0) + 1

    # Industry breakdown
    industry_map = {}
    for b in bids:
        ind = b.get("client_industry") or "Unknown"
        if ind not in industry_map:
            industry_map[ind] = {"count": 0, "tcv": 0, "won": 0, "lost": 0}
        industry_map[ind]["count"] += 1
        industry_map[ind]["tcv"] += b.get("estimated_tcv") or 0
        if b["status"] == "won":
            industry_map[ind]["won"] += 1
        elif b["status"] == "lost":
            industry_map[ind]["lost"] += 1

    # Contract type breakdown
    type_map = {}
    for b in bids:
        ct = b.get("contract_type") or "unknown"
        if ct not in type_map:
            type_map[ct] = {"count": 0, "tcv": 0}
        type_map[ct]["count"] += 1
        type_map[ct]["tcv"] += b.get("estimated_tcv") or 0

    return {
        "summary": {
            "total_bids": len(bids),
            "active_bids": len(active),
            "won": len(won),
            "lost": len(lost),
            "win_rate": round(win_rate, 1),
            "total_pipeline_tcv": total_pipeline_tcv,
            "won_tcv": won_tcv,
            "lost_tcv": lost_tcv,
        },
        "pipeline_by_stage": [
            {"stage": k, "count": v, "tcv": stage_tcv.get(k, 0)}
            for k, v in stage_counts.items()
        ],
        "risk_distribution": risk_dist,
        "industry_breakdown": [{"industry": k, **v} for k, v in industry_map.items()],
        "contract_type_breakdown": [{"type": k, **v} for k, v in type_map.items()],
        "avg_win_probability": round(
            sum(b.get("win_probability") or 0 for b in active) / len(active), 2
        )
        if active
        else 0,
    }


@router.get("/timeline")
async def get_timeline(
    bid_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get timeline of bid activities and milestones."""
    events = []
    db_bids = await BidRepository.get_all(db)
    bids = [BidRepository.to_dict(b) for b in db_bids]
    if bid_id:
        bids = [b for b in bids if b["id"] == bid_id]

    for b in bids:
        events.append(
            {
                "bid_id": b["id"],
                "bid_reference": b["bid_reference"],
                "client_name": b["client_name"],
                "event": "Bid Created",
                "timestamp": b.get("created_at"),
                "status": b["status"],
            }
        )

    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return events[:50]
