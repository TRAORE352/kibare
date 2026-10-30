# app/routers/activation.py — Activation publique par lien à usage unique
"""
Routes PUBLIQUES (sans connexion) :

  GET  /activer/{token}   -> page sobre : explication, choix du mot de passe,
                             téléchargement de la CA et de l'APK.
  POST /activer/{token}   -> consomme le jeton, enregistre le mot de passe.

Ces routes sont accessibles par l'AGENT (pas par l'admin). Le jeton fait foi :
il est à usage unique et expire après 48 h.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.database import get_db
from app.config import settings
from app.templating import templates
from app.services.activation import activate_agent

router = APIRouter()


@router.get("/activer/{token}", response_class=HTMLResponse)
async def activation_page(request: Request, token: str):
    """Affiche la page d'activation (choix du mot de passe)."""
    return templates.TemplateResponse("activate.html", {
        "request": request,
        "token": token,
        "server_address": settings.SERVER_ADDRESS,
        "error": None,
    })


@router.post("/activer/{token}", response_class=HTMLResponse)
async def do_activate(request: Request, token: str,
                      password: str = Form(...),
                      db: AsyncSession = Depends(get_db)):
    """
    Consomme le jeton et enregistre le mot de passe dans Keycloak.
    En cas d'échec (jeton déjà utilisé / expiré), on réaffiche la page avec
    le message prévu par le brief : « Ce lien a déjà été utilisé ou a expiré. »
    """
    keycloak = request.app.state.keycloak
    try:
        agent = await activate_agent(db, keycloak, token, password)
    except HTTPException as exc:
        return templates.TemplateResponse("activate.html", {
            "request": request,
            "token": token,
            "server_address": settings.SERVER_ADDRESS,
            "error": exc.detail,
        }, status_code=400)

    return templates.TemplateResponse("activated.html", {
        "request": request,
        "agent": agent,
        "server_address": settings.SERVER_ADDRESS,
    })
