# app/database.py - Configuration base de données async
"""
Base de données PostgreSQL async pour la Console Kibaré.
Utilise SQLAlchemy 2.0 + asyncpg.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Moteur async
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base pour les modèles
class Base(DeclarativeBase):
    pass


async def init_db():
    """Initialise la base de données (crée les tables si absentes)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncSession:
    """Dépendance FastAPI pour obtenir une session DB."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()