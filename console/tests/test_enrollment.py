# tests/test_enrollment.py — Enrôlement d'un agent
"""
Vérifie (sections 6.4.A et 12 du brief) :
1. l'enrôlement crée le compte Keycloak + le compte Matrix + un jeton d'activation
   dont seul le hash est stocké ;
2. un admin-ministere ne peut pas enrôler dans un autre ministère.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import Agent, AgentRole, AgentStatus, Ministere, ActivationToken
from app.schemas import EnrollAgentRequest
from app.services.enrollment import enroll_agent


def _data():
    return EnrollAgentRequest(
        matricule="demo-999", nom="TEST", prenom="Fictif",
        ministere=Ministere.MTDPCE, direction="DGTD", service="SI",
        fonction="Analyste", role=AgentRole.AGENT,
    )


async def _admin(db, role=AgentRole.SUPER_ADMIN, ministere=Ministere.MTDPCE):
    admin = Agent(
        matricule="demo-000", nom="PLATEFORME", prenom="Admin",
        email="a.p@kibare.test", ministere=ministere, direction="DGTD",
        fonction="Admin", role=role, status=AgentStatus.ACTIVE,
    )
    db.add(admin)
    await db.flush()
    return admin


async def test_enrolement_cree_comptes_et_jeton(db_session, mock_keycloak, mock_synapse):
    admin = await _admin(db_session)
    agent, token_clair = await enroll_agent(
        db_session, mock_keycloak, mock_synapse, _data(), admin)

    # Compte Keycloak + compte Matrix créés.
    assert ("create_user", "demo-999") in mock_keycloak.calls
    assert ("create_user", "@demo-999:kibare.test") in mock_synapse.calls

    # L'agent est en attente d'activation.
    assert agent.status == AgentStatus.PENDING

    # Seul le hash du jeton est stocké en base.
    hash_attendu = ActivationToken.hash_token(token_clair)
    en_base = await db_session.get(ActivationToken, hash_attendu)
    assert en_base is not None
    assert en_base.token_hash == hash_attendu


async def test_admin_ministere_ne_enrole_pas_hors_ministere(db_session, mock_keycloak, mock_synapse):
    admin = await _admin(db_session, role=AgentRole.ADMIN_MINISTERE, ministere=Ministere.SANTE)
    # L'admin est SANTE mais tente d'enrôler en MTDPCE.
    with pytest.raises(HTTPException) as exc:
        await enroll_agent(db_session, mock_keycloak, mock_synapse, _data(), admin)
    assert exc.value.status_code == 403
    assert mock_keycloak.calls == []
    assert mock_synapse.calls == []
