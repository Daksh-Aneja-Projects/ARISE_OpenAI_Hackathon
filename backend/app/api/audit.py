"""
Audit Trail API — immutable event logging via database.
Every agent action, HITL decision, and system event is recorded permanently.
Uses the AuditLog SQLAlchemy model for persistent, append-only storage.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import get_current_user
from app.database import get_db, async_session
from app.models.audit import AuditLog


router = APIRouter(prefix="/api/audit", tags=["Audit"])


def log_event(
    event_type: str,
    event_detail: str,
    bid_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    gate_type: Optional[str] = None,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    extra_data: Optional[dict] = None,
):
    """
    Synchronous helper to log an audit event from anywhere in the codebase.
    Creates the DB record via a fire-and-forget async task.
    """
    import asyncio

    entry = AuditLog(
        id=str(uuid.uuid4()),
        event_type=event_type,
        event_detail=event_detail,
        bid_id=bid_id,
        agent_name=agent_name,
        gate_type=gate_type,
        user_id=user_id,
        user_name=user_name,
        extra_data=extra_data or {},
    )

    async def _persist():
        try:
            async with async_session() as db:
                db.add(entry)
                await db.commit()
        except Exception as e:
            print(f"[Audit] Failed to persist log: {e}")

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist())
    except RuntimeError:
        # No event loop — skip (happens during shutdown)
        pass

    # Return dict representation for callers that need it
    return {
        "id": entry.id,
        "event_type": event_type,
        "event_detail": event_detail,
        "bid_id": bid_id,
        "agent_name": agent_name,
        "gate_type": gate_type,
        "user_id": user_id,
        "user_name": user_name,
        "extra_data": extra_data or {},
        "timestamp": entry.timestamp.isoformat()
        if entry.timestamp
        else datetime.now(timezone.utc).isoformat(),
    }


def _row_to_dict(row: AuditLog) -> dict:
    return {
        "id": row.id,
        "event_type": row.event_type,
        "event_detail": row.event_detail,
        "bid_id": row.bid_id,
        "agent_name": row.agent_name,
        "gate_type": row.gate_type,
        "user_id": row.user_id,
        "user_name": row.user_name,
        "extra_data": row.extra_data or {},
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }


@router.get("/")
async def list_audit_logs(
    bid_id: Optional[str] = None,
    event_type: Optional[str] = None,
    agent_name: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query audit logs with optional filters from the database."""
    query = select(AuditLog)

    if bid_id:
        query = query.where(AuditLog.bid_id == bid_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if agent_name:
        query = query.where(AuditLog.agent_name == agent_name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results sorted newest first
    query = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [_row_to_dict(r) for r in rows],
    }


@router.get("/{bid_id}")
async def get_bid_audit_trail(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete audit trail for a specific bid."""
    query = (
        select(AuditLog).where(AuditLog.bid_id == bid_id).order_by(AuditLog.timestamp)
    )
    result = await db.execute(query)
    rows = result.scalars().all()
    return {
        "bid_id": bid_id,
        "total_events": len(rows),
        "trail": [_row_to_dict(r) for r in rows],
    }


@router.get("/types/summary")
async def get_event_type_summary(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get summary counts by event type."""
    query = select(AuditLog.event_type, func.count(AuditLog.id)).group_by(
        AuditLog.event_type
    )
    result = await db.execute(query)
    counts = {row[0]: row[1] for row in result.all()}

    total_query = select(func.count(AuditLog.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    return {
        "total_events": total,
        "by_type": counts,
    }
