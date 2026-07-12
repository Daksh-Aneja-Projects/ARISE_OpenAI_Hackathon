"""
Authentication service — JWT auth with DB verification.
Uses bcrypt directly (passlib has known incompatibility with bcrypt >= 4.1).
"""

import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.config import settings

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user_id: str, email: str, role: str, name: str) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "name": name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict:
    """
    FastAPI dependency to extract the current user from JWT.
    Returns a dict with user info.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return decode_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """Dependency factory to enforce role-based access."""

    async def role_checker(user: Dict = Depends(get_current_user)) -> Dict:
        if user["role"] not in allowed_roles and user["role"] != "admin":
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user['role']}' not authorized. Required: {allowed_roles}",
            )
        return user

    return role_checker
