"""
Health endpoints - system readiness, DB, Celery worker, and LLM pool status.

GET /api/health         - overall system health (always fast, no LLM calls)
GET /api/health/celery  - Celery worker connectivity + queue depth
GET /api/health/llm     - LLM provider pool status (tier sequences, slot stats)
GET /api/health/rag     - RAG backend stats (backend type, chunk counts)
"""

from fastapi import APIRouter
from datetime import datetime, timezone
import time

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
async def health_check():
    """Overall system health - always fast, no blocking calls."""
    from app.config import settings
    from app.services.llm import llm_service
    from app.knowledge.rag import rag_pipeline

    status_data = llm_service.get_config_status()

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "ai_engine_pool": {
            "total_slots": status_data.get("pool_size", 0),
            "available_slots": status_data.get("pool_size", 0),
            "engine_count": 1 if status_data.get("configured") else 0,
        },
        "rag": {
            "backend": rag_pipeline.stats().get("backend", "unknown"),
            "chunk_count": rag_pipeline.stats().get("total_chunks", 0),
        },
    }


@router.get("/celery")
async def celery_health():
    """
    Celery worker health check.
    Pings the worker pool and returns:
      - alive: True if at least one worker responded
      - workers: list of worker hostnames
      - queue_depth: number of tasks in arise_agents queue (if Redis)
      - broker_url: sanitized broker URL (password redacted)
    """
    from app.celery_app import celery_app
    from app.config import settings
    import re

    broker_display = re.sub(r":([^@/]+)@", ":***@", settings.CELERY_BROKER_URL)

    try:
        inspector = celery_app.control.inspect(timeout=1.0)
        ping_result = inspector.ping() or {}

        workers = list(ping_result.keys())
        alive = len(workers) > 0

        queue_depth = None
        if "redis://" in settings.CELERY_BROKER_URL:
            try:
                import redis

                r = redis.from_url(settings.CELERY_BROKER_URL)
                queue_depth = r.llen("arise_agents")
            except Exception:
                pass

        return {
            "status": "ok" if alive else "degraded",
            "alive": alive,
            "worker_count": len(workers),
            "workers": workers,
            "queue_depth": queue_depth,
            "broker": broker_display,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return {
            "status": "error",
            "alive": False,
            "error": str(e),
            "broker": broker_display,
            "note": "If using memory:// broker, workers run in-process",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/llm")
async def llm_health():
    """LLM engine pool health - sanitized, no model/provider names exposed."""
    from app.services.llm import llm_service

    status_data = llm_service.get_config_status()

    slot_stats = (
        [
            {
                "slot": "Engine 1",
                "calls": status_data.get("total_calls", 0),
                "errors": 0,
                "available": True,
                "cooldown_remaining_s": 0,
            }
        ]
        if status_data.get("configured")
        else []
    )

    tier_info = {
        "critical": {
            "description": "Maximum reasoning quality",
            "engine_count": 1,
        },
        "analytical": {
            "description": "Balanced analysis + speed",
            "engine_count": 1,
        },
        "volume": {
            "description": "High throughput",
            "engine_count": 1,
        },
        "lightweight": {
            "description": "Ultra-fast responses",
            "engine_count": 1,
        },
    }

    return {
        "status": "ok" if status_data.get("configured") else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pool_size": status_data.get("pool_size", 0),
        "available_slots": status_data.get("pool_size", 0),
        "cooled_down_slots": 0,
        "total_tokens_used": status_data.get("total_tokens_used", 0),
        "total_calls": status_data.get("total_calls", 0),
        "tiers": tier_info,
        "slot_stats": slot_stats,
    }


@router.get("/rag")
async def rag_health():
    """RAG backend stats - backend type, chunk counts by collection."""
    from app.knowledge.rag import rag_pipeline

    stats = rag_pipeline.stats()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **stats,
    }
