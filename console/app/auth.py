# app/auth.py — Authentification et autorisation de la Console Kibaré
"""
Deux notions distinctes :

1. AUTHENTIFICATION : « qui êtes-vous ? »
   L'admin se connecte via Keycloak (OIDC). La Console reçoit le matricule
   (preferred_username) et le stocke dans une session signée (cookie HttpOnly).

2. AUTORISATION : « avez-vous le droit ? »
   - `agent`            : AUCUN accès à la Console (sauf la page « téléphone perdu »).
   - `admin-ministere`  : gère UNIQUEMENT les agents de son ministère.
   - `super-admin`      : tout.

La source de vérité du rôle et du ministère est la BASE de la Console (table
agents), pas le jeton Keycloak : ainsi, une révocation ou un changement de rôle
est pris en compte immédiatement, sans attendre l'expiration d'un jeton.
"""
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.session import read_matricule
from app.models import Agent, AgentRole, AgentStatus, Ministere


def is_admin(agent: Agent) -> bool:
    """Vrai si l'agent a un rôle d'administration (super-admin ou admin-ministere)."""
    return agent.role in (AgentRole.SUPER_ADMIN, AgentRole.ADMIN_MINISTERE)


def is_super_admin(agent: Agent) -> bool:
    """Vrai si l'agent est super-admin."""
    return agent.role == AgentRole.SUPER_ADMIN


def check_ministere_access(admin: Agent, target_ministere) -> bool:
    """
    Vérifie qu'un admin peut agir sur un ministère donné.

    - super-admin      : accès à tous les ministères.
    - admin-ministere  : accès UNIQUEMENT à son propre ministère.

    SANS cette fonction, un admin d'un ministère pourrait enrôler ou révoquer
    des agents d'un autre ministère — c'est exactement l'épreuve « Intrus ».
    """
    if admin.role == AgentRole.SUPER_ADMIN:
        return True
    return admin.ministere == target_ministere


async def get_current_agent(request: Request, db: AsyncSession = Depends(get_db)) -> Agent:
    """
    Récupère l'agent connecté depuis le cookie signé, et vérifie qu'il est actif.
    """
    token = request.cookies.get("kibare_user")
    matricule = read_matricule(token) if token else None
    if not matricule:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Non authentifié")

    result = await db.execute(select(Agent).where(Agent.matricule == matricule))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Agent inconnu")

    # Un compte révoqué ne doit plus rien pouvoir faire, même avec une session.
    if agent.status != AgentStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès révoqué")
    return agent


async def get_current_admin(agent: Agent = Depends(get_current_agent)) -> Agent:
    """Exige un rôle d'administration (super-admin ou admin-ministere)."""
    if not is_admin(agent):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Accès réservé aux administrateurs")
    return agent


def require_super_admin(agent: Agent = Depends(get_current_admin)) -> Agent:
    """Exige le rôle super-admin (pour gérer les admins ministère)."""
    if not is_super_admin(agent):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Accès réservé au super-admin")
    return agent
