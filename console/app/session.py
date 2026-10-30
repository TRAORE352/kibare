# app/session.py — Cookie de session signé (simple et robuste)
"""
La session de la Console est un simple cookie signé (itsdangerous) contenant le
matricule de l'admin connecté. On n'utilise PAS la session Starlette (qui posait
des problèmes de persistance du cookie dans le flux OIDC via Keycloak).

Pourquoi un cookie signé ?
  - le matricule est signé avec le secret de la Console : on ne peut pas le
    falsifier sans connaître le secret ;
  - c'est simple, sans état côté serveur, et ça fonctionne derrière Caddy.
"""
from itsdangerous import URLSafeSerializer
from app.config import settings

_serializer = URLSafeSerializer(settings.session_secret)

COOKIE_NAME = "kibare_user"


def sign_matricule(matricule: str) -> str:
    """Signe le matricule et renvoie le jeton à mettre dans le cookie."""
    return _serializer.dumps({"m": matricule})


def read_matricule(token: str):
    """Lit et vérifie le matricule depuis le jeton signé (None si invalide)."""
    if not token:
        return None
    try:
        data = _serializer.loads(token)
        return data.get("m")
    except Exception:
        return None
