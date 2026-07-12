"""
Celery Worker — async task processing for agent execution.
Agents run as background tasks via Celery to avoid blocking the API.
"""
import os
import asyncio
from celery import Celery

# Celery configuration
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "bidder",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 min max per agent
    task_soft_time_limit=540,  # Soft limit at 9 min
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


def run_async(coro):
    """Helper to run async functions in Celery (sync) tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="run_agent", bind=True, max_retries=2)
def run_agent_task(self, agent_name: str, bid_id: str, manifest: dict, extra_data: dict = None):
    """Execute an agent as a Celery background task."""
    from app.agents import (
        IntakeAgent, BidNoBidAgent, ScopeBuilderAgent,
        SolutionArchitectAgent, CompetitiveIntelAgent,
        CommercialModelAgent, ComplianceRiskAgent,
        OutputGeneratorAgent, QAAgent, DiscoveryAgent,
        FeedbackLearningAgent,
    )

    AGENT_MAP = {
        "intake": IntakeAgent,
        "bid_no_bid": BidNoBidAgent,
        "scope_builder": ScopeBuilderAgent,
        "solution_architect": SolutionArchitectAgent,
        "competitive_intel": CompetitiveIntelAgent,
        "commercial_model": CommercialModelAgent,
        "compliance_risk": ComplianceRiskAgent,
        "output_generator": OutputGeneratorAgent,
        "qa": QAAgent,
        "discovery": DiscoveryAgent,
        "feedback_learning": FeedbackLearningAgent,
    }

    agent_class = AGENT_MAP.get(agent_name)
    if not agent_class:
        return {"status": "error", "message": f"Unknown agent: {agent_name}"}

    try:
        if agent_name == "intake":
            doc_texts = extra_data.get("document_texts", []) if extra_data else []
            agent = agent_class(bid_id, manifest, doc_texts)
        else:
            agent = agent_class(bid_id, manifest)

        result = run_async(agent.run())
        return result
    except Exception as e:
        self.retry(exc=e, countdown=30)


@celery_app.task(name="generate_documents")
def generate_documents_task(bid_id: str, bid_data: dict, output_types: list = None):
    """Generate bid documents as a background task."""
    from app.document_gen import generate_sow, generate_proposal_deck, generate_commercial_model

    types = output_types or ["sow", "proposal", "commercial"]
    results = {}

    output_dir = os.path.join("../knowledge_base", "outputs", bid_id)
    os.makedirs(output_dir, exist_ok=True)

    if "sow" in types:
        results["sow"] = generate_sow(bid_data, output_dir)
    if "proposal" in types:
        results["proposal"] = generate_proposal_deck(bid_data, output_dir)
    if "commercial" in types:
        results["commercial"] = generate_commercial_model(bid_data, output_dir)

    return results
