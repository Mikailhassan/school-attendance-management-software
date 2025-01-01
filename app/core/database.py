from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, declared_attr
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.config import settings
from fastapi import Depends

# Database URL from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Create async engine with optimized configuration
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,                 # SQL logging for debugging
    pool_pre_ping=True,        # Connection health check
    pool_size=20,              # Maximum number of connections in the pool
    max_overflow=10,           # Maximum number of connections that can be created beyond pool_size
    pool_timeout=30,           # Seconds to wait before timeout on connection pool checkout
    pool_recycle=1800,         # Recycle connections after 30 minutes
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,    # Don't expire objects after commit
    autocommit=False,          # Explicit transaction management
    autoflush=False            # Explicit flush management
)

# Base class for models not requiring school_id
class BaseModel:
    """Base model class with common attributes"""
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)

# Create declarative base
Base = declarative_base(cls=BaseModel)

# Base class for models requiring school relationship
class SchoolBase(Base):
    """Base class for models that belong to a school"""
    __abstract__ = True

    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey("school.id"), nullable=False)

    @declared_attr
    def school(cls):
        return relationship("School")

# FastAPI dependency for database sessions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception:
        # Rollback on error
        await session.rollback()
        raise
    finally:
        # Always close the session
        await session.close()

# Context manager for background tasks and scripts
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of request context.
    Usage: async with get_db_context() as session:
    """
    session = AsyncSessionLocal()
    try:
        yield session
        # Commit by default when used as context manager
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

# Database initialization functions
async def init_db() -> None:
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def reset_db() -> None:
    """Reset database by dropping and recreating all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()

async def close_db() -> None:
    """Close database connections"""
    await engine.dispose()

# Import all models after Base is defined
# This ensures all models are registered with the metadata
import app.models.attendance_base
import app.models.fingerprint
import app.models.parent
import app.models.school
import app.models.stream
import app.models.student
import app.models.teacher
import app.models.user
import app.models.student_attendance
import app.models.teacher_attendance
import app.models.student