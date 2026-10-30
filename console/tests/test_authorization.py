# tests/test_authorization.py — Règles d'autorisation par rôle
"""
Vérifie (section 7.3 du brief) :
- un agent n'a pas accès à la Console ;
- un admin-ministere est limité à SON ministère ;
- un super-admin a accès à tout.
"""
from app.auth import is_admin, is_super_admin, check_ministere_access
from app.models import Agent, AgentRole, AgentStatus, Ministere


def _agent(role, ministere=Ministere.MTDPCE):
    return Agent(
        matricule="demo-x", nom="N", prenom="P", email="x@kibare.test",
        ministere=ministere, direction="D", fonction="F",
        role=role, status=AgentStatus.ACTIVE,
    )


def test_agent_nest_pas_admin():
    agent = _agent(AgentRole.AGENT)
    assert is_admin(agent) is False
    assert is_super_admin(agent) is False


def test_admin_ministere_est_admin_mais_pas_super():
    admin = _agent(AgentRole.ADMIN_MINISTERE)
    assert is_admin(admin) is True
    assert is_super_admin(admin) is False


def test_super_admin_est_admin_et_super():
    admin = _agent(AgentRole.SUPER_ADMIN)
    assert is_admin(admin) is True
    assert is_super_admin(admin) is True


def test_admin_ministere_limite_a_son_ministere():
    admin = _agent(AgentRole.ADMIN_MINISTERE, Ministere.MTDPCE)
    # Dans son ministère : autorisé.
    assert check_ministere_access(admin, Ministere.MTDPCE) is True
    # Dans un autre ministère : REFUSÉ (c'est l'épreuve « Intrus »).
    assert check_ministere_access(admin, Ministere.SANTE) is False


def test_super_admin_accede_a_tous_les_ministeres():
    admin = _agent(AgentRole.SUPER_ADMIN, Ministere.MTDPCE)
    assert check_ministere_access(admin, Ministere.SANTE) is True
    assert check_ministere_access(admin, Ministere.SECURITE) is True
