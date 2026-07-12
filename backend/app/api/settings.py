"""
Settings API — BYOK (Bring Your Own Key) + LLM config management.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.auth import get_current_user
from app.services.llm import llm_service

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class BYOKRequest(BaseModel):
    openai_api_key: Optional[str] = None


@router.get("/llm-status")
async def get_llm_status(user: dict = Depends(get_current_user)):
    """Get current LLM provider configuration status."""
    status = llm_service.get_config_status()
    # Mask actual keys for security — just show if configured
    return status


@router.post("/byok")
async def set_byok_keys(req: BYOKRequest, user: dict = Depends(get_current_user)):
    """BYOK — Set user-provided API keys to override environment defaults."""
    llm_service.set_override_keys(openai_key=req.openai_api_key or "")
    s = llm_service.get_config_status()
    return {
        "status": "success",
        "message": "API keys applied. AI engine pool rebuilt.",
        "pool_size": s.get("pool_size", 1),
        "total_calls": s.get("total_calls", 0),
        "total_tokens_used": s.get("total_tokens_used", 0),
    }


@router.post("/byok/clear")
async def clear_byok_keys(user: dict = Depends(get_current_user)):
    """Revert to environment API keys."""
    llm_service.clear_override_keys()
    s = llm_service.get_config_status()
    return {
        "status": "success",
        "message": "Reverted to server environment keys.",
        "pool_size": s.get("pool_size", 1),
        "total_calls": s.get("total_calls", 0),
        "total_tokens_used": s.get("total_tokens_used", 0),
    }


@router.post("/byok/test")
async def test_llm_connection(user: dict = Depends(get_current_user)):
    """Quick test to verify the current LLM configuration works."""
    try:
        result = await llm_service.generate(
            prompt="Say 'Connection successful' in exactly 3 words.",
            system_prompt="You are a test bot. Reply concisely.",
            max_tokens=20,
        )
        s = llm_service.get_config_status()
        return {
            "status": "success",
            "response": result.strip(),
            "pool_size": s["pool_size"],
            "available_slots": s["pool_size"] - s["cooled_down_slots"],
            "total_calls": s["total_calls"],
            "total_tokens_used": s["total_tokens_used"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
