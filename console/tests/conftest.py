# tests/conftest.py — Fixtures partagées pour les tests de la Console
"""
Base de données SQLite en mémoire (fichier temporaire) pour tester la logique
métier sans PostgreSQL. Clients Keycloak/Synapse simulés qui enregistrent les
appels reçus (pour vérifier qu'une révocation appelle bien LES DEUX services).
"""
import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base
import app.models  # noqa: F401  (enregistre les modèles dans Base.metadata)


@pytest.fixture
async def db_session():
    """Une session SQLite asynchrone isolée par test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()
    os.unlink(path)


class MockKeycloak:
    """Simule le client Keycloak : enregistre les appels, renvoie des IDs fictifs."""
    def __init__(self):
        self.calls = []

    async def create_user(self, username, email, first_name, last_name,
                          attributes=None, realm_roles=None, required_actions=None):
        self.calls.append(("create_user", username))
        return f"kc-{username}"

    async def set_password(self, user_id, password, temporary=False):
        self.calls.append(("set_password", user_id))

    async def disable_user(self, user_id):
        self.calls.append(("disable_user", user_id))

    async def logout_user(self, user_id):
        self.calls.append(("logout_user", user_id))

    async def assign_realm_roles(self, user_id, role_names):
        self.calls.append(("assign_realm_roles", user_id, tuple(role_names)))


class MockSynapse:
    """Simule le client Synapse : enregistre les appels."""
    def __init__(self):
        self.calls = []

    async def create_user(self, user_id, displayname=None, admin=False):
        self.calls.append(("create_user", user_id))
        return {}

    async def deactivate_user(self, user_id, erase=False):
        self.calls.append(("deactivate_user", user_id, erase))
        return {"id_server_unbind_result": "success"}

    async def list_user_devices(self, user_id):
        return []


@pytest.fixture
def mock_keycloak():
    return MockKeycloak()


@pytest.fixture
def mock_synapse():
    return MockSynapse()
