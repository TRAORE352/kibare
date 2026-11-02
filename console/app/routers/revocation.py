# app/routers/revocation.py — Révocation d'un agent
"""
POST /console/agents/{matricule}/revoke

Le formulaire exige la confirmation en tapant le matricule (section 7.2) pour
éviter une révocation accidentelle (action irréversible pour l'agent).
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_admin
from app.models import Agent
from app.services.revocation import revoke_agent
from app.templating import templates

router = APIRouter(prefix="/console", tags=["revocation"])


@router.post("/agents/{matricule}/revoke", response_class=HTMLResponse)
async def do_revoke(request: Request, matricule: str,
                    confirmation: str = Form(...),
                    motif: str = Form(""),
                    db: AsyncSession = Depends(get_db),
                    admin: Agent = Depends(get_current_admin)):
    # Confirmation : il faut retaper exactement le matricule.
    if confirmation.strip().lower() != matricule.strip().lower():
        return templates.TemplateResponse("agent_detail.html", {
            "request": request, "agent": await _get_agent(db, matricule),
            "devices": [], "admin": admin, "page": "agents",
            "error": "La confirmation ne correspond pas au matricule.",
        }, status_code=400)

    await revoke_agent(db, request.app.state.keycloak,
                       request.app.state.synapse, matricule, admin, motif or None)
    return RedirectResponse(url="/console/agents", status_code=303)


async def _get_agent(db, matricule):
    from sqlalchemy import select
    r = await db.execute(select(Agent).where(Agent.matricule == matricule))
    return r.scalar_one_or_none()
