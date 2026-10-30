# app/routers/health.py — Sonde de santé
"""
GET /health : utilisé par le healthcheck Docker. Ne révèle aucune information
sensible (un simple « ok »).
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
