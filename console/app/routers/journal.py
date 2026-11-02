# app/routers/journal.py — Journal des révocations
"""
GET /console/journal : liste des révocations (qui a révoqué qui, quand, motif).
Ne contient AUCUN contenu de message (règle éliminatoire).
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import get_current_admin
from app.models import Agent, RevocationLog
from app.templating import templates

router = APIRouter(prefix="/console", tags=["journal"])


@router.get("/journal", response_class=HTMLResponse)
async def journal(request: Request, db: AsyncSession = Depends(get_db),
                  admin: Agent = Depends(get_current_admin)):
    logs = (await db.execute(
        select(RevocationLog).order_by(RevocationLog.date_revocation.desc()).limit(200)
    )).scalars().all()
    return templates.TemplateResponse("journal.html", {
        "request": request, "logs": logs, "admin": admin, "page": "journal",
    })
