from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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