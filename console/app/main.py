# app/main.py — Point d'entrée de la Console Kibaré (FastAPI)
"""
Application web d'administration de la messagerie souveraine Kibaré.

Connexion des admins : Keycloak (OIDC, flux « code ») — échange de code et
récupération du profil faits manuellement via httpx, puis session via un cookie
signé (app/session.py). Accès réservé aux rôles super-admin et admin-ministere.
"""
from contextlib import asynccontextmanager
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db
from app.services.seed import seed_demo_agents
from app.session import sign_matricule
from app.keycloak_client import KeycloakAdminClient
from app.synapse_client import SynapseAdminClient
from app.models import Agent, AgentRole, AgentStatus
from app.routers import health, agents, activation, revocation, directory, journal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Au démarrage : crée les tables et initialise les clients admin."""
    await init_db()
    # Peuple la table agents avec les comptes de démo (sinon boucle de redirection).
    await seed_demo_agents()
    app.state.keycloak = KeycloakAdminClient()
    app.state.synapse = SynapseAdminClient()
    await app.state.keycloak.__aenter__()
    await app.state.synapse.__aenter__()
    yield
    await app.state.keycloak.__aexit__(None, None, None)
    await app.state.synapse.__aexit__(None, None, None)


app = FastAPI(title="Console Kibaré", version="1.0.0", lifespan=lifespan)

app.mount("/console/static", StaticFiles(directory="app/static"), name="static")

app.include_router(health.router)
app.include_router(activation.router)   # /activer/{token} (public)
app.include_router(agents.router)
app.include_router(revocation.router)
app.include_router(directory.router)
app.include_router(journal.router)


@app.get("/console/")
async def console_root():
    """Racine de la console : redirige vers la connexion OIDC (Keycloak)."""
    return RedirectResponse(url="/console/login")


@app.get("/console/login")
async def login():
    """Redirige le navigateur vers l'écran de connexion Keycloak (flux code)."""
    redirect_uri = quote(f"{settings.SERVER_ADDRESS}/console/callback", safe="")
    auth_url = (
        f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/auth"
        f"?response_type=code&client_id=kibare-console"
        f"&redirect_uri={redirect_uri}&scope=openid+profile+email"
    )
    return RedirectResponse(url=auth_url)


@app.get("/console/callback")
async def oidc_callback(code: str = None, db: AsyncSession = Depends(get_db)):
    """
    Retour de Keycloak : échange le code d'autorisation contre des jetons,
    récupère le matricule (preferred_username) via userinfo, vérifie le rôle,
    puis ouvre la session (cookie signé).
    """
    if not code:
        return RedirectResponse(url="/console/login")

    redirect_uri = f"{settings.SERVER_ADDRESS}/console/callback"
    token_url = (f"{settings.KEYCLOAK_INTERNAL_URL}/realms/"
                 f"{settings.KEYCLOAK_REALM}/protocol/openid-connect/token")
    userinfo_url = (f"{settings.KEYCLOAK_INTERNAL_URL}/realms/"
                    f"{settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Échange du code (client confidentiel : client_id + client_secret).
            r = await client.post(token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "kibare-console",
                "client_secret": settings.keycloak_console_client_secret,
                "redirect_uri": redirect_uri,
            })
            r.raise_for_status()
            tokens = r.json()

            # Récupère le profil utilisateur (Keycloak valide le jeton lui-même).
            u = await client.get(userinfo_url, headers={
                "Authorization": f"Bearer {tokens['access_token']}",
            })
            u.raise_for_status()
            userinfo = u.json()
    except Exception as exc:
        # Journalise l'erreur pour diagnostic (jamais de secret ni de contenu).
        import traceback
        print("OIDC CALLBACK ERROR:", repr(exc))
        traceback.print_exc()
        return RedirectResponse(url="/console/login")

    matricule = userinfo.get("preferred_username")
    if not matricule:
        return RedirectResponse(url="/console/login")

    # L'utilisateur doit être un agent ACTIF avec un rôle d'administration.
    result = await db.execute(select(Agent).where(Agent.matricule == matricule))
    agent = result.scalar_one_or_none()
    if (not agent or agent.status != AgentStatus.ACTIVE
            or agent.role not in (AgentRole.SUPER_ADMIN, AgentRole.ADMIN_MINISTERE)):
        return RedirectResponse(url="/console/login")

    # Ouvre la session : cookie signé contenant le matricule.
    response = RedirectResponse(url="/console/agents", status_code=303)
    response.set_cookie(
        "kibare_user", sign_matricule(matricule),
        httponly=True, secure=True, samesite="none", max_age=1800, path="/",
    )
    return response


@app.get("/console/logout")
async def logout():
    """Déconnecte : supprime le cookie local, puis redirige vers Keycloak."""
    response = RedirectResponse(url=(
        f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/logout"
    ))
    response.delete_cookie("kibare_user", path="/")
    return response
