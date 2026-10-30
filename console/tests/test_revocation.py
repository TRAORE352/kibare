# tests/test_revocation.py — Révocation immédiate
"""
Vérifie (sections 5.4 et 12 du brief) :
1. la révocation appelle Keycloak (désactivation + fermeture des sessions)
   ET Synapse (désactivation du compte) ;
2. un admin-ministere ne peut pas révoquer dans un autre ministère ;
3. le journal ne contient jamais de contenu de message.
"""
import pytest
from fastapi import HTTPException

from app.models import Agent, AgentRole, AgentStatus, Ministere, RevocationLog
from app.services.revocation import revoke_agent


async def _creer_agents(db):
    agent = Agent(
        matricule="demo-203", nom="TIENDRÉBÉOGO", prenom="Karim",
        email="k.t@kibare.test", ministere=Ministere.SANTE,
        direction="Dir.", fonction="Chargé de liaison",
        role=AgentRole.AGENT, status=AgentStatus.ACTIVE, keycloak_id="kc-203",
    )
    admin = Agent(
        matricule="demo-201", nom="OUÉDRAOGO", prenom="Mariam",
        email="m.o@kibare.test", ministere=Ministere.SANTE,
        direction="Dir.", fonction="Directrice",
        role=AgentRole.ADMIN_MINISTERE, status=AgentStatus.ACTIVE,
    )
    db.add(agent)
    db.add(admin)
    await db.flush()
    return agent, admin


async def test_revocation_appelle_keycloak_et_synapse(db_session, mock_keycloak, mock_synapse):
    agent, admin = await _creer_agents(db_session)

    await revoke_agent(db_session, mock_keycloak, mock_synapse,
                       "demo-203", admin, "Départ de l'agent")

    # Keycloak : désactivation PUIS fermeture des sessions (dans cet ordre).
    assert ("disable_user", "kc-203") in mock_keycloak.calls
    assert ("logout_user", "kc-203") in mock_keycloak.calls
    assert mock_keycloak.calls.index(("disable_user", "kc-203")) < \
           mock_keycloak.calls.index(("logout_user", "kc-203"))

    # Synapse : désactivation du compte Matrix.
    assert ("deactivate_user", "@demo-203:kibare.test", False) in mock_synapse.calls

    # L'agent est révoqué localement.
    assert agent.status == AgentStatus.REVOKED
    assert agent.date_revocation is not None


async def test_admin_ministere_ne_revoque_pas_hors_ministere(db_session, mock_keycloak, mock_synapse):
    agent, admin = await _creer_agents(db_session)
    # L'admin est SANTE, on tente de révoquer... en changeant son ministère.
    admin.ministere = Ministere.MTDPCE

    with pytest.raises(HTTPException) as exc:
        await revoke_agent(db_session, mock_keycloak, mock_synapse,
                           "demo-203", admin, None)
    assert exc.value.status_code == 403
    # Aucun appel aux services ne doit avoir eu lieu.
    assert mock_keycloak.calls == []
    assert mock_synapse.calls == []


def test_journal_sans_contenu_de_message():
    """Le journal de révocation ne comporte aucun champ pouvant contenir un message."""
    colonnes = {c.name for c in RevocationLog.__table__.columns}
    for nom in colonnes:
        assert "message" not in nom and "content" not in nom and "body" not in nom
    # Les champs attendus sont bien là.
    assert {"agent_matricule", "revoque_par", "motif", "date_revocation"} <= colonnes
