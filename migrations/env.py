import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool
from alembic import context
from app.models import Base  # Ensure this path is correct

# Alembic Config object, provides access to the .ini file in use.
config = context.config

# Set up Python logging based on the configuration file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object for 'autogenerate' support.
target_metadata = Base.metadata

# Offline migration mode, where only the SQL statements are generated without a live database connection
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# Online migration mode where an asynchronous connection to the database is established
def do_run_migrations(connection: Connection) -> None:
    """Synchronous helper to configure and run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

# Async migration runner that uses sync mode to ensure compatibility with Alembic
async def run_async_migrations() -> None:
    """In this scenario we create an Engine and associate a connection with the context."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=NullPool,  # Disable connection pooling in async migrations
    )

    # Open a connection to the database
    async with connectable.connect() as connection:
        # Use run_sync to execute the migrations synchronously
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine after migrations are complete
    await connectable.dispose()

# Wrapper to ensure asyncio runs properly for online migrations
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

# Determine whether to run migrations in online or offline mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
