# app/routers/directory.py — Annuaire des agents actifs
"""
GET /console/annuaire : agents actifs, groupés par ministère et fonction.
Un admin-ministere ne voit que son ministère.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_admin
from app.models import Agent, AgentRole, AgentStatus
from app.templating import templates

router = APIRouter(prefix="/console", tags=["annuaire"])


@router.get("/annuaire", response_class=HTMLResponse)
async def directory(request: Request, db: AsyncSession = Depends(get_db),
                    admin: Agent = Depends(get_current_admin)):
    query = select(Agent).where(Agent.status == AgentStatus.ACTIVE)
    if admin.role == AgentRole.ADMIN_MINISTERE:
        query = query.where(Agent.ministere == admin.ministere)
    agents = (await db.execute(query.order_by(Agent.ministere, Agent.fonction))).scalars().all()

    # Groupement par ministère pour l'affichage.
    by_ministere = {}
    for a in agents:
        by_ministere.setdefault(a.ministere.value, []).append(a)

    return templates.TemplateResponse("directory.html", {
        "request": request, "by_ministere": by_ministere, "admin": admin,
    })
