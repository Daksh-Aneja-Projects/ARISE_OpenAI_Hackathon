"""
Celery agent tasks — async agent execution for horizontal scaling.

When CELERY_BROKER_URL is set to a real Redis URL, pipeline stages can be
dispatched to a Celery worker pool instead of running inline in the FastAPI
event loop. This allows:
  - Multiple agents running in parallel (where safe)
  - Horizontal scaling (multiple worker processes/machines)
  - Retry on failure without blocking the API

Usage:
  # Dispatch a single agent task
  from app.tasks.agent_tasks import run_agent_task
  result = run_agent_task.delay(bid_id, "intake")

  # Check status
  from celery.result import AsyncResult
  r = AsyncResult(task_id)
  print(r.state, r.result)

The task re-uses the existing _execute_agent() function from bids.py,
so all agent logic, KB lookups, and manifest saves are fully preserved.
"""

import asyncio
from app.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.agent_tasks.run_agent_task",
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def run_agent_task(self, bid_id: str, agent_name: str) -> dict:
    """
    Execute a single agent for a bid and persist the result to DB.
    Retries up to 3 times on transient failures (LLM rate limits, etc.).
    Returns the agent result dict.
    """
    try:
        # Celery tasks are sync — run the async agent in a new event loop
        return asyncio.run(_run_agent_async(bid_id, agent_name))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))


async def _run_agent_async(bid_id: str, agent_name: str) -> dict:
    """Async wrapper — loads bid from DB, runs agent, saves result."""
    from app.database import async_session
    from app.services.bid_repository import BidRepository
    from app.api.bids import _execute_agent

    async with async_session() as db:
        db_bid = await BidRepository.get_by_id(db, bid_id)
        if not db_bid:
            raise ValueError(f"Bid {bid_id} not found")
        bid = BidRepository.to_dict(db_bid)

    result = await _execute_agent(agent_name, bid_id, bid)

    async with async_session() as db:
        await BidRepository.save_agent_result(db, bid_id, agent_name, result)
        await db.commit()

    return result


@celery_app.task(
    name="app.tasks.agent_tasks.run_pipeline_task",
    bind=True,
    max_retries=1,
)
def run_pipeline_task(self, bid_id: str, run_id: str, start_index: int = 0) -> dict:
    """
    Run the full ARISE pipeline sequentially via Celery.
    Delegates to the existing async pipeline task.
    """
    try:
        return asyncio.run(_run_pipeline_async(bid_id, run_id, start_index))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


async def _run_pipeline_async(bid_id: str, run_id: str, start_index: int) -> dict:
    from app.api.pipeline import _run_pipeline_task

    await _run_pipeline_task(bid_id, run_id, start_index)
    return {"status": "completed", "bid_id": bid_id, "run_id": run_id}
