# app/routers/agents.py — Tableau des agents + enrôlement
"""
Routes d'administration (réservées aux admins) :
  GET  /console/agents            -> tableau des agents (filtré par ministère)
  GET  /console/agents/enroll     -> formulaire d'enrôlement
  POST /console/agents/enroll     -> enrôlement (crée Keycloak + Matrix + jeton)
  GET  /console/agents/{matricule}-> fiche agent (appareils + bouton révoquer)
"""
from fastapi import APIRouter, Depends, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_admin
from app.models import Agent, AgentRole, AgentStatus, Ministere
from app.schemas import EnrollAgentRequest
from app.services.enrollment import enroll_agent
from app.config import settings
from app.templating import templates
from app.qr import qr_data_uri

router = APIRouter(prefix="/console", tags=["agents"])

ALL_MINISTERES = [m.value for m in Ministere]


@router.get("/agents", response_class=HTMLResponse)
async def list_agents(request: Request, db: AsyncSession = Depends(get_db),
                      admin: Agent = Depends(get_current_admin)):
    """Tableau des agents. Un admin-ministere ne voit QUE son ministère."""
    query = select(Agent)
    if admin.role == AgentRole.ADMIN_MINISTERE:
        query = query.where(Agent.ministere == admin.ministere)
    agents = (await db.execute(query.order_by(Agent.matricule))).scalars().all()
    return templates.TemplateResponse("agents.html", {
        "request": request, "agents": agents, "admin": admin,
    })


@router.get("/agents/enroll", response_class=HTMLResponse)
async def enroll_form(request: Request, admin: Agent = Depends(get_current_admin)):
    return templates.TemplateResponse("enroll.html", {
        "request": request, "admin": admin,
        "ministeres": ALL_MINISTERES,
        "roles": [r.value for r in AgentRole],
        "error": None,
    })


@router.post("/agents/enroll", response_class=HTMLResponse)
async def do_enroll(request: Request, db: AsyncSession = Depends(get_db),
                    admin: Agent = Depends(get_current_admin),
                    matricule: str = Form(...), nom: str = Form(...),
                    prenom: str = Form(...), ministere: str = Form(...),
                    direction: str = Form(...), service: str = Form(""),
                    fonction: str = Form(...), role: str = Form("agent")):
    data = EnrollAgentRequest(
        matricule=matricule, nom=nom, prenom=prenom,
        ministere=Ministere(ministere), direction=direction,
        service=service or None, fonction=fonction, role=AgentRole(role),
    )
    try:
        agent, token_clear = await enroll_agent(
            db, request.app.state.keycloak, request.app.state.synapse, data, admin)
    except HTTPException as exc:
        return templates.TemplateResponse("enroll.html", {
            "request": request, "admin": admin,
            "ministeres": ALL_MINISTERES,
            "roles": [r.value for r in AgentRole],
            "error": exc.detail,
        }, status_code=exc.status_code)

    activation_url = f"{settings.SERVER_ADDRESS}/activer/{token_clear}"
    return templates.TemplateResponse("enroll_result.html", {
        "request": request, "agent": agent,
        "activation_url": activation_url,
        "qr": qr_data_uri(activation_url),
        "ttl_hours": settings.ACTIVATION_TOKEN_TTL_HOURS,
    })


@router.get("/agents/{matricule}", response_class=HTMLResponse)
async def agent_detail(request: Request, matricule: str,
                       db: AsyncSession = Depends(get_db),
                       admin: Agent = Depends(get_current_admin)):
    """Fiche agent + liste de ses appareils (via API admin Synapse, sans contenu)."""
    result = await db.execute(select(Agent).where(Agent.matricule == matricule))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent introuvable")

    # Un admin-ministere ne peut pas consulter la fiche d'un autre ministère.
    from app.auth import check_ministere_access
    if not check_ministere_access(admin, agent.ministere):
        raise HTTPException(status_code=403, detail="Hors de votre ministère")

    devices = []
    try:
        devices = await request.app.state.synapse.list_user_devices(
            f"@{agent.matricule}:kibare.test")
    except Exception:
        devices = []  # l'API peut échouer sans jeton bot ; on affiche « inconnu »

    return templates.TemplateResponse("agent_detail.html", {
        "request": request, "agent": agent, "devices": devices, "admin": admin,
    })
