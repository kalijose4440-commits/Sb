from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.db.base import Base


def create_engine_and_sessionmaker(
    database_url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create the async engine and session factory for application use."""

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


async def init_db(engine: AsyncEngine) -> None:
    """Create tables for local/dev bootstrap (migrations recommended for production)."""

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_guild_settings_language_column)


def _ensure_guild_settings_language_column(connection) -> None:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "guild_settings" not in tables:
        return

    columns = {column["name"] for column in inspector.get_columns("guild_settings")}
    if "language" in columns:
        return

    connection.execute(
        text("ALTER TABLE guild_settings ADD COLUMN language VARCHAR(8) NOT NULL DEFAULT 'en'")
    )

