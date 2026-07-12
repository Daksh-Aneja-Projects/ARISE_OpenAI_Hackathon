"""
Rate Card API — Configure and manage rate cards for commercial calculations.
"""

from fastapi import APIRouter, Depends
from app.services.auth import get_current_user
from app.services.commercial_calculator import (
    get_rate_card,
    set_rate_card,
    set_active_rate_card,
    DEFAULT_RATE_CARD,
)

router = APIRouter(prefix="/api/ratecard", tags=["Rate Card"])


@router.get("/")
async def get_current_rate_card(user: dict = Depends(get_current_user)):
    """Get the active rate card."""
    return get_rate_card()


@router.get("/default")
async def get_default_rate_card(user: dict = Depends(get_current_user)):
    """Get the default rate card."""
    return DEFAULT_RATE_CARD


@router.post("/")
async def update_rate_card(
    card: dict, name: str = "custom", user: dict = Depends(get_current_user)
):
    """Upload a custom rate card. Format: {onshore: {role: rate}, offshore: {role: rate}}"""
    set_rate_card(name, card)
    set_active_rate_card(name)
    return {"status": "updated", "active": name}


@router.post("/activate/{name}")
async def activate_rate_card(name: str, user: dict = Depends(get_current_user)):
    """Activate a named rate card."""
    set_active_rate_card(name)
    return {"status": "activated", "active": name}
