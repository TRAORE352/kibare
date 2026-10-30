# app/schemas.py — Schémas de requête/réponse (Pydantic)
"""
Validation des données reçues par la Console. Pydantic garantit que les champs
sont du bon type avant d'atteindre la logique métier.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models import AgentRole, Ministere


class EnrollAgentRequest(BaseModel):
    """Formulaire « Enrôler un agent » (section 7.2 du brief)."""
    matricule: str = Field(..., min_length=3, max_length=50,
                           description="Matricule (identifiant de connexion)")
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    ministere: Ministere
    direction: str = Field(..., min_length=1, max_length=200)
    service: Optional[str] = Field(None, max_length=200)
    fonction: str = Field(..., min_length=1, max_length=200)
    role: AgentRole = AgentRole.AGENT

    @field_validator("matricule")
    @classmethod
    def matricule_en_minuscules(cls, v: str) -> str:
        """Le matricule est toujours stocké en minuscules (identifiant Matrix)."""
        return v.strip().lower()


class ActivateRequest(BaseModel):
    """Requête d'activation : le jeton à usage unique + le mot de passe choisi."""
    token: str = Field(..., description="Jeton d'activation à usage unique")
    password: str = Field(..., min_length=12, max_length=128,
                          description="Mot de passe choisi par l'agent (12 caractères min.)")


class RevokeRequest(BaseModel):
    """Requête de révocation : le matricule de l'agent à révoquer + motif."""
    matricule: str = Field(..., min_length=3, max_length=50)
    motif: Optional[str] = Field(None, max_length=500)


class EnrollResponse(BaseModel):
    """Réponse d'enrôlement : le lien d'activation à usage unique."""
    matricule: str
    activation_url: str
    expires_in_hours: int
