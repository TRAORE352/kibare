# app/services/enrollment.py — Enrôlement d'un agent
"""
Parcours « Enrôler un agent » (section 6.4.A du brief) :

1. L'admin remplit le formulaire (nom, prénom, matricule, ministère, etc.).
2. La Console crée le compte Keycloak SANS mot de passe (l'agent choisira le
   sien à l'activation) et avec l'action requise CONFIGURE_TOTP.
3. La Console crée le compte Matrix (pour que le compte existe AVANT la
   première connexion OIDC — voir enable_registration=false côté Synapse).
4. La Console génère un JETON D'ACTIVATION à usage unique :
     - 32 octets aléatoires ;
     - seul le HASH (SHA-256) est stocké en base ;
     - expiration 48 h ;
     - usage unique.
5. La Console affiche le lien + le QR code (à transmettre en main propre).
"""
import unicodedata
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Agent, AgentRole, AgentStatus, ActivationToken, Ministere
from app.schemas import EnrollAgentRequest
from app.config import settings
from app.auth import check_ministere_access
from fastapi import HTTPException


def _sans_accents(texte: str) -> str:
    """Retire les accents (utile pour l'e-mail : konaté -> konate)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )


def _email_agent(prenom: str, nom: str) -> str:
    """Construit l'e-mail fictif : a.konate@kibare.test (domaine .test réservé)."""
    initiale = _sans_accents(prenom)[0].lower()
    return f"{initiale}.{_sans_accents(nom).lower()}@kibare.test"


async def enroll_agent(db: AsyncSession, keycloak, synapse, data: EnrollAgentRequest, admin: Agent):
    """
    Enrôle un agent. Renvoie (agent_créé, jeton_activation_en_clair).

    Le jeton en clair n'est renvoyé QU'ICI, une seule fois, pour afficher le
    QR code. Ensuite il n'existe plus que sous forme de hash en base.
    """
    # 1. Contrôle d'accès : un admin-ministere ne peut enrôler que chez lui.
    #    Sans ce test, un admin d'un ministère pourrait créer des comptes
    #    dans un autre ministère (épreuve « Intrus »).
    if not check_ministere_access(admin, data.ministere):
        raise HTTPException(status_code=403,
                            detail="Vous ne pouvez enrôler que dans votre ministère")

    # 2. Le matricule doit être unique.
    from sqlalchemy import select
    existing = await db.execute(select(Agent).where(Agent.matricule == data.matricule))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ce matricule existe déjà")

    email = _email_agent(data.prenom, data.nom)

    # 3. Création du compte Keycloak (sans mot de passe).
    attributes = {
        "matricule": [data.matricule],
        "ministere": [data.ministere.value],
        "direction": [data.direction],
        "service": [data.service or ""],
        "fonction": [data.fonction],
    }
    keycloak_id = await keycloak.create_user(
        username=data.matricule,
        email=email,
        first_name=data.prenom,
        last_name=data.nom,
        attributes=attributes,
        realm_roles=[data.role.value],
    )

    # 4. Création du compte Matrix (identifiant @matricule:kibare.test).
    matrix_id = f"@{data.matricule}:kibare.test"
    await synapse.create_user(matrix_id, displayname=f"{data.prenom} {data.nom}")

    # 5. Enregistrement de l'agent dans la base de la Console.
    agent = Agent(
        matricule=data.matricule,
        nom=data.nom,
        prenom=data.prenom,
        email=email,
        ministere=data.ministere,
        direction=data.direction,
        service=data.service,
        fonction=data.fonction,
        role=data.role,
        status=AgentStatus.PENDING,
        keycloak_id=keycloak_id,
    )
    db.add(agent)
    await db.flush()  # pour obtenir la clé primaire sans commit

    # 6. Jeton d'activation : seul le hash est stocké.
    token_obj, token_clear = ActivationToken.create_for_agent(
        agent_matricule=data.matricule,
        ttl_hours=settings.ACTIVATION_TOKEN_TTL_HOURS,
        token_bytes=settings.ACTIVATION_TOKEN_BYTES,
    )
    db.add(token_obj)

    return agent, token_clear
