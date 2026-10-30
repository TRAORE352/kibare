# app/services/revocation.py — Révocation immédiate d'un agent
"""
Parcours de révocation (section 5.4 du brief), exécuté DANS CET ORDRE :

1. Keycloak : désactive le compte (enabled=false) et ferme toutes ses sessions
   (les jetons d'accès sont immédiatement invalidés).
2. Synapse : désactive le compte via l'API admin (supprime les jetons d'accès
   sur TOUS les appareils et fait quitter tous les salons).
3. Journal : enregistre QUI a révoqué QUI et QUAND (sans contenu de message).

Effet côté chiffrement (fourni par Matrix, aucun code de l'équipe) :
  quand un membre quitte un salon, les clients restants créent une nouvelle
  session Megolm ; l'agent révoqué ne reçoit plus les clés et ne peut plus lire
  les nouveaux messages.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import Agent, AgentStatus, RevocationLog, utcnow
from app.auth import check_ministere_access


async def revoke_agent(db: AsyncSession, keycloak, synapse,
                       agent_matricule: str, admin: Agent, motif: str = None) -> RevocationLog:
    """Révoque un agent : Keycloak + Synapse, puis journalise l'action."""

    # 1. Récupération de l'agent cible.
    result = await db.execute(select(Agent).where(Agent.matricule == agent_matricule))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent introuvable")

    # 2. Contrôle d'accès : un admin-ministere ne peut révoquer que chez lui.
    if not check_ministere_access(admin, agent.ministere):
        raise HTTPException(status_code=403,
                            detail="Vous ne pouvez révoquer que dans votre ministère")

    # 3. Révocation — on suit l'ordre du brief et on trace chaque étape.
    log = RevocationLog(agent_matricule=agent.matricule,
                        revoque_par=admin.matricule, motif=motif)

    # 3a. Keycloak : désactiver le compte PUIS fermer les sessions.
    if agent.keycloak_id:
        await keycloak.disable_user(agent.keycloak_id)
        log.keycloak_disabled = True
        await keycloak.logout_user(agent.keycloak_id)
        log.keycloak_sessions_closed = True

    # 3b. Synapse : désactiver le compte (erase=false, on garde l'historique).
    matrix_id = f"@{agent.matricule}:kibare.test"
    await synapse.deactivate_user(matrix_id, erase=False)
    log.synapse_deactivated = True

    # 3c. Mise à jour locale : l'agent est révoqué immédiatement.
    agent.status = AgentStatus.REVOKED
    agent.date_revocation = utcnow()
    agent.revoque_par = admin.matricule
    agent.motif_revocation = motif

    db.add(log)
    return log
