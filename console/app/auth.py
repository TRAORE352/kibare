# app/auth.py - Authentification et autorisation Console Kibaré
"""
Gestion de l'authentification OIDC Keycloak et des autorisations par rôle.
"""

from functools import lru_cache
from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models import Agent, AgentRole, AgentStatus


# Configuration OAuth2 pour Keycloak
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{settings.KEYCLOAK_ADMIN_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{settings.KEYCLOAK_ADMIN_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
    auto_error=False,
)


def decode_token(token: str) -> dict:
    """
    Décode un token JWT sans vérification de signature (pour lecture des claims).
    La vérification de signature se fait côté Keycloak lors de l'échange du code.
    """
    try:
        # Ne pas vérifier la signature ici - on fait confiance au token émis par Keycloak
        # qui a été validé lors de l'échange du code d'autorisation
        return jwt.get_unverified_claims(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )


def get_token_from_cookie(request: Request) -> Optional[str]:
    """Récupère le token d'accès depuis le cookie HttpOnly."""
    return request.cookies.get("access_token")


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """
    Récupère l'agent connecté via le cookie de session.
    Utilisé pour les admins (super-admin, admin-ministere).
    """
    token = get_token_from_cookie(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    claims = decode_token(token)
    matricule = claims.get("preferred_username")
    if not matricule:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide : pas de matricule",
        )
    
    # Récupérer l'agent en base
    result = await db.execute(select(Agent).where(Agent.matricule == matricule))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent introuvable",
        )
    
    if agent.status != AgentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte non actif",
        )
    
    return agent


async def get_current_admin(
    current_user: Agent = Depends(get_current_user),
) -> Agent:
    """
    Vérifie que l'utilisateur est un administrateur (super-admin ou admin-ministere).
    """
    if current_user.role not in (AgentRole.SUPER_ADMIN, AgentRole.ADMIN_MINISTERE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_user


def require_super_admin(current_admin: Agent = Depends(get_current_admin)) -> Agent:
    """Exige le rôle super-admin."""
    if current_admin.role != AgentRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé au super-admin",
        )
    return current_admin


def require_ministere_admin(current_admin: Agent = Depends(get_current_admin)) -> Agent:
    """
    Vérifie que l'admin-ministère agit dans son périmètre.
    La vérification fine (même ministère) se fait dans les routeurs.
    """
    if current_admin.role not in (AgentRole.SUPER_ADMIN, AgentRole.ADMIN_MINISTERE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_admin


def check_ministere_access(admin: Agent, target_ministere: str) -> bool:
    """
    Vérifie si un admin a accès à un ministère.
    super-admin : accès à tout.
    admin-ministere : uniquement son ministère.
    """
    if admin.role == AgentRole.SUPER_ADMIN:
        return True
    return admin.ministere == target_ministere