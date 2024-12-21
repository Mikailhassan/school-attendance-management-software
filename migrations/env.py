from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context
from typing import Optional, Any, Dict

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models
from app.models.base import Base
from app.models import (
    School,
    Class,
    Stream,
    TeacherAttendance,
    StudentAttendance,
    Fingerprint,
    AttendanceBase,
    User,
    RevokedToken,
    Parent,
    Session,
    Student
)

target_metadata = Base.metadata



def get_config_section(section: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Retrieve configuration section with a default fallback.
    """
    try:
        return {key: config.get_section(section)[key] for key in config.get_section(section)}
    except Exception:
        return default or {}

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Any) -> None:
    """
    Helper function to run migrations in the correct context
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    
    # Configure the async engine
    engine = create_async_engine(
        url,
        poolclass=pool.NullPool,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    async with engine.begin() as connection:
        await connection.run_sync(do_run_migrations)

# Entry point for migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())