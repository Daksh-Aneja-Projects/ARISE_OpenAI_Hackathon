"""
Database connection and session management.
Uses SQLAlchemy async with aiosqlite for SQLite.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from app.config import settings
import json


# Create async engine — use StaticPool for SQLite (single-file DB)
_is_sqlite = settings.DATABASE_URL.startswith("sqlite")
_engine_kwargs = {
    "echo": settings.APP_ENV == "development",
    "json_serializer": lambda obj: json.dumps(obj, default=str),
}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency for database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and seed default users."""
    # Step 1: Create all tables and run migrations using a raw connection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate: add new columns to existing tables (SQLite create_all won't alter existing tables)
        migrations = [
            # Agent output columns that may be missing on older DBs
            "ALTER TABLE bids ADD COLUMN transition_change_output JSON",
            "ALTER TABLE bids ADD COLUMN discovery_output JSON",
            "ALTER TABLE bids ADD COLUMN feedback_output JSON",
            "ALTER TABLE bids ADD COLUMN client_intel_output JSON",
            "ALTER TABLE bids ADD COLUMN data_analyst_output JSON",
            "ALTER TABLE bids ADD COLUMN automation_ai_output JSON",
            "ALTER TABLE bids ADD COLUMN output_generator_output JSON",
            "ALTER TABLE bids ADD COLUMN qa_output JSON",
            # Generated document paths
            "ALTER TABLE bids ADD COLUMN output_word_path VARCHAR(500)",
            "ALTER TABLE bids ADD COLUMN output_ppt_path VARCHAR(500)",
            "ALTER TABLE bids ADD COLUMN output_excel_path VARCHAR(500)",
            # Scoring columns
            "ALTER TABLE bids ADD COLUMN strategic_value VARCHAR(50)",
            "ALTER TABLE bids ADD COLUMN bid_recommendation VARCHAR(50)",
        ]
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists

    # Step 2: Seed default demo users using a proper ORM session
    async with async_session() as session:
        from sqlalchemy.future import select
        from app.models.user import User

        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            from app.services.auth import hash_password
            import uuid
            from datetime import datetime, timezone

            demo_users = [
                User(
                    id=str(uuid.uuid4()),
                    email="bid.manager@arise.dev",
                    full_name="Demo Bid Manager",
                    role="bid_manager",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    password_hash=hash_password("demo123"),
                ),
                User(
                    id=str(uuid.uuid4()),
                    email="sol.lead@arise.dev",
                    full_name="Demo Solution Lead",
                    role="solutioning_lead",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    password_hash=hash_password("demo123"),
                ),
                User(
                    id=str(uuid.uuid4()),
                    email="admin@arise.dev",
                    full_name="System Admin",
                    role="admin",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    password_hash=hash_password("demo123"),
                ),
            ]
            session.add_all(demo_users)
            await session.commit()
            print("[DB] Default demo users seeded (bid.manager@arise.dev / demo123)")


async def close_db():
    """Cleanup database connections."""
    await engine.dispose()
