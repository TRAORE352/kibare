# app/services/seed.py — Peuplement des comptes de démo dans la Console
"""
Les comptes de démo (demo-000 .. demo-402) sont définis dans le realm Keycloak.
Mais la Console a sa PROPRE table `agents`, qui est la source de vérité pour les
rôles, le ministère et le statut (révocation, autorisation).

Sans ce peuplement, un admin de démo qui se connecte via OIDC n'est pas trouvé
dans la table `agents` -> boucle de redirection infinie (ERR_TOO_MANY_REDIRECTS).

On remplit donc la table au premier démarrage (uniquement si elle est vide).
"""
from sqlalchemy import select
from app.database import async_session_maker
from app.models import Agent, AgentRole, AgentStatus, Ministere


# (matricule, nom, prenom, email, ministere, direction, service, fonction, role)
DEMO_AGENTS = [
    ("demo-000", "PLATEFORME", "Admin", "admin.plateforme@kibare.test",
     "MTDPCE", "DGTD", "Exploitation", "Administrateur système", "super-admin"),
    ("demo-101", "KONATÉ", "Awa", "a.konate@kibare.test",
     "MTDPCE", "DGTD", "Sécurité des SI", "Cheffe de service", "admin-ministere"),
    ("demo-102", "SAWADOGO", "Issouf", "i.sawadogo@kibare.test",
     "MTDPCE", "DGTD", "Sécurité des SI", "Analyste sécurité", "agent"),
    ("demo-201", "OUÉDRAOGO", "Mariam", "m.ouedraogo@kibare.test",
     "SANTE", "Dir. de la veille sanitaire", "Direction", "Directrice", "admin-ministere"),
    ("demo-202", "ZONGO", "Boukary", "b.zongo@kibare.test",
     "SANTE", "Dir. de la veille sanitaire", "Direction", "Épidémiologiste", "agent"),
    ("demo-203", "TIENDRÉBÉOGO", "Karim", "k.tiendrebeogo@kibare.test",
     "SANTE", "Dir. de la veille sanitaire", "Direction", "Chargé de liaison", "agent"),
    ("demo-301", "COMPAORÉ", "Salif", "s.compaore@kibare.test",
     "SECURITE", "Dir. des opérations", "Direction", "Directeur", "admin-ministere"),
    ("demo-302", "KABORÉ", "Rasmata", "r.kabore@kibare.test",
     "SECURITE", "Dir. des opérations", "Direction", "Officière de liaison", "agent"),
    ("demo-401", "OUATTARA", "Adama", "a.ouattara@kibare.test",
     "MEF", "Dir. du budget", "Direction", "Directeur", "admin-ministere"),
    ("demo-402", "DIALLO", "Fatimata", "f.diallo@kibare.test",
     "MEF", "Dir. du budget", "Direction", "Chargée d'études", "agent"),
]


async def seed_demo_agents() -> None:
    """Insère les comptes de démo si la table agents est vide."""
    async with async_session_maker() as session:
        result = await session.execute(select(Agent).limit(1))
        if result.scalar_one_or_none() is not None:
            return  # déjà peuplée : on ne fait rien

        for (matricule, nom, prenom, email, ministere, direction,
             service, fonction, role) in DEMO_AGENTS:
            session.add(Agent(
                matricule=matricule,
                nom=nom,
                prenom=prenom,
                email=email,
                ministere=Ministere(ministere),
                direction=direction,
                service=service,
                fonction=fonction,
                role=AgentRole(role),
                # Comptes de démo déjà activés (pas de jeton d'activation).
                status=AgentStatus.ACTIVE,
            ))
        await session.commit()
