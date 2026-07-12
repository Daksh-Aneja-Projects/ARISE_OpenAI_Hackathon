"""
Pipeline Orchestration API — auto-run the full agent pipeline.
Chains all agents sequentially, creates HITL gates after each stage,
and persists execution state to the database to ensure no mock data or data loss.
"""

import uuid
import asyncio
import traceback
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.auth import get_current_user
from app.database import get_db, async_session
from app.services.bid_repository import BidRepository
from app.models.bid import PipelineRun
from app.orchestration.engine import PIPELINE_STAGES, build_gate_payload

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


def _run_to_dict(run: PipelineRun) -> dict:
    return {
        "run_id": run.id,
        "bid_id": run.bid_id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "started_by": run.started_by,
        "current_stage_index": run.current_stage_index,
        "current_stage_name": run.current_stage_name,
        "total_stages": run.total_stages,
        "completed_stages": run.completed_stages,
        "failed_stage": run.failed_stage,
        "error": run.error,
        "stages": list(run.stages) if run.stages else [],
    }


async def _create_run(db: AsyncSession, bid_id: str, user_name: str) -> PipelineRun:
    """Create a new pipeline run tracker in the database."""
    run_id = str(uuid.uuid4())
    stages = []
    for s in PIPELINE_STAGES:
        stages.append(
            {
                "name": s["name"],
                "label": s["label"],
                "status": "pending",  # pending | running | completed | failed | skipped
                "started_at": None,
                "completed_at": None,
                "error": None,
                "gate_created": False,
            }
        )
    run = PipelineRun(
        id=run_id,
        bid_id=bid_id,
        status="running",
        started_by=user_name,
        current_stage_index=0,
        current_stage_name=PIPELINE_STAGES[0]["name"] if PIPELINE_STAGES else None,
        total_stages=len(PIPELINE_STAGES),
        completed_stages=0,
        stages=stages,
    )
    db.add(run)
    await db.commit()
    return run


@router.post("/{bid_id}/run")
async def start_pipeline(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start full auto-pipeline execution for a bid."""
    db_bid = await BidRepository.get_by_id(db, bid_id)
    if not db_bid:
        raise HTTPException(404, "Bid not found")

    # Check if already running
    result = await db.execute(select(PipelineRun).where(PipelineRun.bid_id == bid_id))
    existing_run = result.scalars().first()
    if existing_run:
        if existing_run.status in ("running", "waiting_on_hitl"):
            raise HTTPException(409, "Pipeline already running for this bid")
        else:
            await db.execute(delete(PipelineRun).where(PipelineRun.bid_id == bid_id))
            await db.commit()

    user_name = user.get("name", "Unknown")
    run = await _create_run(db, bid_id, user_name)

    # Telemetry
    from app.telemetry import telemetry

    telemetry.record_pipeline_start(bid_id)

    # Start async execution
    asyncio.create_task(_run_pipeline_task(bid_id, run.id, 0))

    return {
        "status": "started",
        "run_id": run.id,
        "message": f"Pipeline started — {len(PIPELINE_STAGES)} agents will execute sequentially",
    }


@router.get("/{bid_id}/status")
async def get_pipeline_status(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll pipeline progress."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.bid_id == bid_id))
    run = result.scalars().first()
    if not run:
        return {
            "status": "idle",
            "message": "No pipeline run found for this bid",
            "stages": [],
        }
    return _run_to_dict(run)


@router.post("/{bid_id}/cancel")
async def cancel_pipeline(
    bid_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a running pipeline."""
    result = await db.execute(select(PipelineRun).where(PipelineRun.bid_id == bid_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(404, "No pipeline run found")
    if run.status != "running":
        raise HTTPException(400, "Pipeline is not running")

    run.status = "cancelled"
    run.completed_at = datetime.now(timezone.utc)
    run.error = "Cancelled by user"

    stages = list(run.stages)
    idx = run.current_stage_index
    if idx < len(stages):
        if stages[idx]["status"] == "running":
            stages[idx]["status"] = "skipped"
        for j in range(idx + 1, len(stages)):
            stages[j]["status"] = "skipped"
    run.stages = stages

    await db.commit()
    return {"status": "cancelled", "message": "Pipeline cancelled"}


def resume_pipeline(bid_id: str):
    """Resume a pipeline that was waiting on a HITL gate. (Fire and forget)."""

    async def _resume():
        async with async_session() as db:
            result = await db.execute(
                select(PipelineRun).where(PipelineRun.bid_id == bid_id)
            )
            run = result.scalars().first()
            if not run or run.status != "waiting_on_hitl":
                return False

            run.status = "running"
            next_idx = run.current_stage_index + 1
            await db.commit()

            # Launch the pipeline as a background task
            asyncio.create_task(_run_pipeline_task(bid_id, run.id, next_idx))
            return True

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_resume())
        return True
    except RuntimeError:
        pass
    return False


async def _run_pipeline_task(bid_id: str, run_id: str, start_index: int = 0):
    """Execute all pipeline stages sequentially, pausing if a HITL gate is required."""
    from app.api.audit import log_event
    from app.models.hitl import HITLGate, HITLGateType, HITLGateStatus
    from app.api.bids import _execute_agent

    for idx in range(start_index, len(PIPELINE_STAGES)):
        async with async_session() as db:
            result = await db.execute(
                select(PipelineRun).where(PipelineRun.id == run_id)
            )
            run = result.scalars().first()
            if not run or run.status == "cancelled":
                return

            db_bid = await BidRepository.get_by_id(db, bid_id)
            if not db_bid:
                run.status = "failed"
                run.error = "Bid not found"
                await db.commit()
                return
            bid = BidRepository.to_dict(db_bid)

            stage_def = PIPELINE_STAGES[idx]
            agent_name = stage_def["name"]

            # Telemetry — record stage entry
            from app.telemetry import telemetry

            telemetry.record_pipeline_stage(bid_id, agent_name)

            stages = list(run.stages)
            stage = stages[idx]

            run.current_stage_index = idx
            run.current_stage_name = agent_name

            stage["status"] = "running"
            stage["started_at"] = datetime.now(timezone.utc).isoformat()
            run.stages = stages
            await db.commit()

        try:
            # Execute the agent
            result_data = await _execute_agent(agent_name, bid_id, bid)

            # Store result
            result_data["timestamp"] = datetime.now(timezone.utc).isoformat()

            # Save state in database
            async with async_session() as db:
                await BidRepository.save_agent_result(
                    db, bid_id, agent_name, result_data
                )
                # If this was strategic_assessment, also persist competitive_output separately
                if agent_name == "strategic_assessment" and bid.get(
                    "competitive_output"
                ):
                    await BidRepository.save_agent_result(
                        db, bid_id, "competitive_intel", bid["competitive_output"]
                    )
                    # Persist key bid-level fields that agents set in-memory
                    db_bid_obj = await BidRepository.get_by_id(db, bid_id)
                    if db_bid_obj:
                        if bid.get("win_probability") is not None:
                            db_bid_obj.win_probability = bid["win_probability"]
                        if bid.get("estimated_tcv") is not None:
                            db_bid_obj.estimated_tcv = bid["estimated_tcv"]
                        if bid.get("bid_recommendation") is not None:
                            db_bid_obj.bid_recommendation = bid["bid_recommendation"]
                        if bid.get("status"):
                            db_bid_obj.status = bid["status"]
                        db_bid_obj.manifest = bid.get("manifest", db_bid_obj.manifest)
                        await db.flush()
                        await db.commit()
                        # BUG-03 fix: reload bid dict so next agent sees fresh persisted state
                        bid = BidRepository.to_dict(db_bid_obj)

            # Mark stage complete and evaluate HITL
            async with async_session() as db:
                result = await db.execute(
                    select(PipelineRun).where(PipelineRun.id == run_id)
                )
                run = result.scalars().first()
                if not run:
                    return

                stages = list(run.stages)
                stage = stages[idx]
                stage["status"] = "completed"
                stage["completed_at"] = datetime.now(timezone.utc).isoformat()
                run.completed_stages = idx + 1

                # Auto-create HITL gate if this stage requires one
                if stage_def.get("gate"):
                    try:
                        agent_summary = ""
                        if result_data.get("result"):
                            r = result_data["result"]
                            if isinstance(r, dict):
                                agent_summary = r.get(
                                    "hitl_summary",
                                    r.get("executive_summary", str(r)[:500]),
                                )
                            else:
                                agent_summary = str(r)[:500]

                        gate_payload = build_gate_payload(
                            agent_name=agent_name,
                            bid_id=bid_id,
                            bid_reference=bid.get("bid_reference", ""),
                            client_name=bid.get("client_name", ""),
                            agent_summary=agent_summary,
                            agent_data=result_data.get("result"),
                        )
                        if gate_payload:
                            from datetime import timedelta

                            gate_id = str(uuid.uuid4())
                            now = datetime.now(timezone.utc)
                            sla_hours = gate_payload.get("sla_hours", 24)

                            db_gate = HITLGate(
                                id=gate_id,
                                bid_id=bid_id,
                                gate_type=HITLGateType(gate_payload["gate_type"]),
                                status=HITLGateStatus.PENDING,
                                agent_summary=gate_payload.get("agent_summary", ""),
                                agent_data=gate_payload.get("agent_data"),
                                assigned_reviewer_id=run.started_by or "System",
                                sla_hours=sla_hours,
                                sla_deadline=now + timedelta(hours=sla_hours),
                            )
                            db.add(db_gate)
                            await db.commit()
                            stage["gate_created"] = True

                    except Exception as gate_err:
                        print(
                            f"[PIPELINE] Warning: HITL gate creation failed for {agent_name}: {gate_err}"
                        )

                run.stages = stages
                await db.commit()

        except Exception as e:
            # Stage failed
            async with async_session() as db:
                result = await db.execute(
                    select(PipelineRun).where(PipelineRun.id == run_id)
                )
                run = result.scalars().first()
                if not run:
                    return

                stages = list(run.stages)
                stages[idx]["status"] = "failed"
                stages[idx]["completed_at"] = datetime.now(timezone.utc).isoformat()
                stages[idx]["error"] = str(e)

                for j in range(idx + 1, len(stages)):
                    stages[j]["status"] = "skipped"

                run.status = "failed"
                run.failed_stage = agent_name
                run.error = f"Agent '{stage_def['label']}' failed: {str(e)}"
                run.completed_at = datetime.now(timezone.utc)
                run.stages = stages
                await db.commit()

            # Store error result
            error_data = {
                "status": "failed",
                "agent": agent_name,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            async with async_session() as db:
                await BidRepository.save_agent_result(
                    db, bid_id, agent_name, error_data
                )
            return

        # Minimal yield to keep the event loop responsive between agents
        await asyncio.sleep(0.1)

    # All stages completed
    async with async_session() as db:
        result = await db.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        run = result.scalars().first()
        if run:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            await db.commit()

    # Telemetry — pipeline complete
    try:
        from app.telemetry import telemetry

        telemetry.record_pipeline_end(bid_id, "completed")
    except Exception:
        pass

    # Log pipeline completion
    try:
        log_event(
            event_type="pipeline_completed",
            event_detail=f"Full pipeline completed for bid {bid_id}",
            bid_id=bid_id,
            user_name="System",
        )
    except Exception:
        pass
