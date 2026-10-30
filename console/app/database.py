# app/database.py — Base de données async (SQLAlchemy 2.0 + asyncpg)
"""
La Console Kibaré utilise une base PostgreSQL dédiée `kibare_console`.
L'URL de connexion est construite par settings.database_url (mot de passe
lu depuis un fichier secret).
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


engine = _make_engine()

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)


async def init_db():
    """Crée les tables si elles n'existent pas (au démarrage)."""
    # Import des modèles pour qu'ils s'enregistrent dans Base.metadata
    from app import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dépendance FastAPI : fournit une session, commit en fin de requête."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
