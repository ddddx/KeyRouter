from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase
from config import DATABASE_URL

# Convert sqlite:/// to sqlite+aiosqlite:/// for async support
ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_schema_columns)


def _ensure_schema_columns(sync_conn):
    """Lightweight SQLite-friendly migrations for existing deployments."""
    inspector = inspect(sync_conn)
    tables = inspector.get_table_names()
    if "keys" in tables:
        key_columns = {col["name"] for col in inspector.get_columns("keys")}
        if "cooldown_until" not in key_columns:
            sync_conn.execute(text("ALTER TABLE keys ADD COLUMN cooldown_until DATETIME"))
    if "request_logs" in tables:
        log_columns = {col["name"] for col in inspector.get_columns("request_logs")}
        if "error_code" not in log_columns:
            sync_conn.execute(text("ALTER TABLE request_logs ADD COLUMN error_code VARCHAR(100)"))


async def get_session() -> AsyncSession:
    """FastAPI Depends-compatible async generator."""
    async with async_session() as session:
        yield session


def get_session_ctx():
    """Manual async context manager for use outside FastAPI Depends."""
    @staticmethod
    async def _ctx():
        async with async_session() as session:
            yield session
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def ctx():
        async with async_session() as session:
            yield session
    return ctx()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    """Async context manager for manual session creation (outside Depends)."""
    async with async_session() as session:
        yield session
