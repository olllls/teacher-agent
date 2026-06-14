import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


os.makedirs("data", exist_ok=True)

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA busy_timeout=5000"))
        from backend.models import Base  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        # Migration: add source_file column if it doesn't exist yet
        try:
            await conn.execute(text("ALTER TABLE classes ADD COLUMN source_file VARCHAR(500)"))
        except Exception:
            pass
