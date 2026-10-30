# app/main.py — Point d'entrée de la Console Kibaré (FastAPI)
"""
Application web d'administration de la messagerie souveraine Kibaré.

Connexion des admins : Keycloak (OIDC) via la bibliothèque Authlib.
Accès réservé aux rôles super-admin et admin-ministere (voir app/auth.py).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import init_db, get_db
from app.services.seed import seed_demo_agents
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

# Session signée (cookie HttpOnly) pour la connexion OIDC.
# https_only=False : la Console est DERRIÈRE Caddy qui termine le TLS ;
# le cookie est tout de même HttpOnly + SameSite (par défaut de SessionMiddleware).
app.add_middleware(
    SessionMiddleware, secret_key=settings.session_secret,
    https_only=False, max_age=1800,
)

# ----------------------------------------------------------------------
# Client OIDC (Authlib) pour Keycloak
# ----------------------------------------------------------------------
oauth = OAuth()
oauth.register(
    name="keycloak",
    client_id="kibare-console",
    client_secret=settings.keycloak_console_client_secret,
    # URL publique pour la redirection du NAVIGATEUR :
    authorize_url=f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth",
    # URL interne pour l'échange de code et le userinfo (côté serveur) :
    access_token_url=f"{settings.KEYCLOAK_INTERNAL_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
    userinfo_endpoint=f"{settings.KEYCLOAK_INTERNAL_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/userinfo",
    client_kwargs={"scope": "openid profile email"},
)

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
async def login(request: Request):
    """Redirige vers Keycloak pour l'authentification OIDC."""
    redirect_uri = f"{settings.SERVER_ADDRESS}/console/callback"
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@app.get("/console/callback")
async def oidc_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retour de Keycloak : échange le code contre des jetons, récupère le
    matricule (preferred_username) via userinfo, puis ouvre la session.
    """
    redirect_uri = f"{settings.SERVER_ADDRESS}/console/callback"
    try:
        token = await oauth.keycloak.authorize_access_token(request, redirect_uri=redirect_uri)
        userinfo = await oauth.keycloak.userinfo(token=token)
    except Exception:
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

    request.session["matricule"] = matricule
    return RedirectResponse(url="/console/agents")


@app.get("/console/logout")
async def logout(request: Request):
    """Déconnecte : vide la session locale, puis redirige vers Keycloak."""
    request.session.clear()
    logout_url = (
        f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/logout"
    )
    return RedirectResponse(url=logout_url)
