# app/services/activation.py — Activation par lien à usage unique
"""
Parcours d'activation (section 6.4.A du brief) :

1. L'agent ouvre le lien https://<serveur>/activer/<jeton> sur son téléphone.
2. Il choisit son mot de passe (12 caractères minimum).
3. La Console vérifie le jeton (usage unique + expiration), le CONSOMME, puis
   enregistre le mot de passe dans Keycloak.
4. Le compte passe à l'état ACTIF.

Pourquoi consommer le jeton AVANT de définir le mot de passe ?
  Pour qu'un jeton rejoué ne puisse pas ré-écrire le mot de passe : le jeton
  est marqué « utilisé » en base avant toute action sensible.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Agent, AgentStatus, ActivationToken, utcnow


async def activate_agent(db: AsyncSession, keycloak, token_str: str, password: str) -> Agent:
    """Active un agent avec son jeton à usage unique + son mot de passe."""
    token_hash = ActivationToken.hash_token(token_str)

    result = await db.execute(
        select(ActivationToken).where(ActivationToken.token_hash == token_hash)
    )
    token_obj = result.scalar_one_or_none()

    # Vérification du jeton : existence, non-usage, non-expiration.
    # `verify` compare le hash à temps constant (pas d'attaque par timing).
    if token_obj is None or not token_obj.verify(token_str):
        raise HTTPException(status_code=400,
                            detail="Ce lien a déjà été utilisé ou a expiré. "
                                   "Contactez votre administrateur.")

    # Consommation AVANT l'action sensible (définition du mot de passe).
    token_obj.consume()

    # Récupération de l'agent lié au jeton.
    agent_result = await db.execute(
        select(Agent).where(Agent.matricule == token_obj.agent_matricule)
    )
    agent = agent_result.scalar_one()

    if agent.keycloak_id:
        # Le mot de passe est enregistré DANS KEYCLOAK (jamais dans la base
        # de la Console). La Console ne stocke donc aucun mot de passe.
        await keycloak.set_password(agent.keycloak_id, password, temporary=False)

    # Passage à l'état actif.
    agent.status = AgentStatus.ACTIVE
    agent.date_activation = utcnow()

    return agent
