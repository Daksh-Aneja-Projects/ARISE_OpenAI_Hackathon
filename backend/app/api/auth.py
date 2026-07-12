"""
Authentication API routes.
JWT-based login with DB-backed users.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.services.auth import verify_password, create_token, get_current_user
from app.models.user import User
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    avatar: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """DB-backed login."""

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        name=user.full_name,
    )

    return LoginResponse(
        token=token,
        user={
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "role": user.role,
            "avatar": user.avatar_url or "U",
        },
    )


@router.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get current user profile from DB."""
    result = await db.execute(select(User).where(User.id == current_user.get("sub")))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "name": user.full_name,
        "role": user.role,
        "avatar": user.avatar_url or "U",
    }


@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    """List all available users from DB (for reviewer assignment)."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            name=u.full_name,
            role=u.role,
            avatar=u.avatar_url or "U",
        )
        for u in users
    ]
