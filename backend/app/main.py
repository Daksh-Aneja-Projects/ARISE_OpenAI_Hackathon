"""
FastAPI main application.
Agentic Bid Management & Pre-Sales Automation Platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import (
    auth,
    bids,
    knowledge,
    documents,
    dashboard,
    generate,
    ratecard,
    audit,
    hitl,
    pipeline,
    org,
    ws,
    health,
)
from app.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    print(f"[START] {settings.APP_NAME} starting...")
    print(f"[ENV] Environment: {settings.APP_ENV}")
    print(f"[LLM] Model: {settings.LLM_MODEL}")
    # Initialize database tables on startup
    try:
        await init_db()
        print("[DB] Database tables initialized successfully")
    except Exception as e:
        print(f"[DB] Database init skipped (using in-memory stores): {e}")
    yield
    # Cleanup database connections
    try:
        await close_db()
    except Exception:
        pass
    print("[STOP] Shutting down...")


app = FastAPI(
    title="ARISE — Autonomous RFP Intelligence and Sales Engine",
    description="Multi-agent AI system for autonomous pre-sales and RFP response generation.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Audit Interceptor
from app.middleware import AuditMiddleware

app.add_middleware(AuditMiddleware)

# Pipeline rate limiter (10 POST calls/min per user)
from app.api.rate_limiter import PipelineRateLimiter

app.add_middleware(PipelineRateLimiter, max_calls=10, window_seconds=60)

# Register API routers
app.include_router(auth.router)
app.include_router(bids.router)
app.include_router(knowledge.router)
app.include_router(documents.router)
app.include_router(dashboard.router)
app.include_router(generate.router)
app.include_router(ratecard.router)
app.include_router(audit.router)
app.include_router(hitl.router)
app.include_router(pipeline.router)
app.include_router(org.router)
app.include_router(ws.router)  # WebSocket streaming

from app.api import settings as settings_api

app.include_router(settings_api.router)
app.include_router(
    health.router
)  # /api/health, /api/health/celery, /api/health/llm, /api/health/rag


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "agents": [
            "Orchestrator",
            "Intake",
            "Data Analyst",
            "Client Intelligence",
            "Bid/No-Bid",
            "Discovery & Qualification",
            "Scope Builder",
            "Solution Architect",
            "Automation & AI",
            "Competitive Intel",
            "Transition & Change",
            "Commercial Model",
            "Compliance & Risk",
            "Proposal Writer",
            "QA",
            "Output Generator",
            "Feedback & Learning",
        ],
    }
