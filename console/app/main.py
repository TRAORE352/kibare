# app/main.py - Point d'entrée FastAPI
"""
Console Kibaré - Application d'administration pour la messagerie souveraine.
Gère l'enrôlement, l'activation, la révocation et l'annuaire des agents.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2AuthorizationCodeBearer
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import settings
from app.database import init_db, get_db
from app.models import ActivationToken, Agent, RevocationLog
from app.keycloak_client import KeycloakAdminClient
from app.synapse_client import SynapseAdminClient
from app.auth import get_current_admin, require_super_admin, require_ministere_admin
from app.routers import agents, activation, revocation, directory, journal, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage
    await init_db()
    # Initialiser les clients admin
    app.state.keycloak = KeycloakAdminClient(
        base_url=settings.KEYCLOAK_ADMIN_URL,
        admin_user=settings.KEYCLOAK_ADMIN_USER,
        admin_password=settings.KEYCLOAK_ADMIN_PASSWORD,
        realm=settings.KEYCLOAK_REALM,
    )
    app.state.synapse = SynapseAdminClient(
        base_url=settings.SYNAPSE_ADMIN_URL,
        admin_token=settings.SYNAPSE_ADMIN_TOKEN,
    )
    await app.state.keycloak.__aenter__()
    await app.state.synapse.__aenter__()
    yield
    # Arrêt
    await app.state.keycloak.__aexit__(None, None, None)
    await app.state.synapse.__aexit__(None, None, None)


app = FastAPI(
    title="Console Kibaré",
    description="Administration de la messagerie souveraine Kibaré",
    version="1.0.0",
    lifespan=lifespan,
)

# Templates Jinja2
templates = Jinja2Templates(directory="app/templates")

# Fichiers statiques (CSS, JS, polices)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Inclure les routeurs
app.include_router(health.router)
app.include_router(agents.router)
app.include_router(activation.router)
app.include_router(revocation.router)
app.include_router(directory.router)
app.include_router(journal.router)


# Page d'accueil - redirection selon le rôle
@app.get("/", response_class=HTMLResponse)
async def root(request: Request, current_admin=Depends(get_current_admin)):
    return RedirectResponse(url="/console/agents")


# Page de connexion (OIDC Keycloak)
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # Rediriger vers Keycloak pour l'authentification
    auth_url = (
        f"{settings.KEYCLOAK_ADMIN_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/auth"
        f"?client_id=kibare-console"
        f"&redirect_uri={settings.SERVER_ADDRESS}/console/callback"
        f"&response_type=code"
        f"&scope=openid+profile+roles+email"
    )
    return RedirectResponse(url=auth_url)


# Callback OIDC
@app.get("/callback")
async def oidc_callback(request: Request, code: str, db: AsyncSession = Depends(get_db)):
    # Échanger le code contre des tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            f"{settings.KEYCLOAK_ADMIN_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "kibare-console",
                "client_secret": settings.KEYCLOAK_CONSOLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.SERVER_ADDRESS}/console/callback",
            },
        )
        tokens = token_response.json()
    
    # Décoder le token ID pour récupérer les rôles
    from app.auth import decode_token
    id_token = decode_token(tokens["id_token"])
    
    # Vérifier que l'utilisateur a un rôle admin
    realm_roles = id_token.get("realm_roles", [])
    if "super-admin" not in realm_roles and "admin-ministere" not in realm_roles:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    
    # Créer la session (simplifié : stocker dans un cookie sécurisé)
    response = RedirectResponse(url="/console/agents")
    response.set_cookie(
        "access_token",
        tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800,  # 30 min
    )
    response.set_cookie(
        "refresh_token",
        tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=2592000,  # 30 jours
    )
    response.set_cookie(
        "user_roles",
        ",".join(realm_roles),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800,
    )
    response.set_cookie(
        "user_ministere",
        id_token.get("ministere", ""),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=1800,
    )
    return response


# Déconnexion
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("user_roles")
    response.delete_cookie("user_ministere")
    # Déconnexion Keycloak
    logout_url = (
        f"{settings.KEYCLOAK_ADMIN_URL}/realms/{settings.KEYCLOAK_REALM}"
        f"/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={settings.SERVER_ADDRESS}/console/"
    )
    return RedirectResponse(url=logout_url)