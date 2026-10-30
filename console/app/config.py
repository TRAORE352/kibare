# app/config.py — Configuration centralisée de la Console Kibaré
"""
Tous les secrets sont lus depuis des FICHIERS (montés en secrets Docker),
jamais depuis des variables d'environnement exposées. Les valeurs par défaut
correspondent à l'exécution dans docker-compose.

Pourquoi des fichiers plutôt que des variables d'environnement ?
  Les variables d'environnement sont visibles via `docker inspect` et les logs.
  Un fichier secret monté en lecture seule est plus difficile à faire fuiter.
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def _read_secret(path: str) -> str:
    """Lit un secret depuis un fichier et renvoie son contenu (sans l'afficher)."""
    p = Path(path)
    if p.exists():
        return p.read_text().strip()
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True)

    # ------------------------------------------------------------------
    # Base de données (la Console a sa propre base `kibare_console`)
    # ------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://console@postgres/kibare_console"
    DATABASE_PASSWORD_FILE: str = "/run/secrets/console_db_password"

    # ------------------------------------------------------------------
    # Keycloak
    # ------------------------------------------------------------------
    KEYCLOAK_REALM: str = "kibare"
    # URL interne : utilisée côté serveur (API admin, échange de code, userinfo).
    # Le préfixe /auth est OBLIGATOIRE (KC_HTTP_RELATIVE_PATH=/auth côté Keycloak).
    KEYCLOAK_INTERNAL_URL: str = "http://keycloak:8080/auth"
    # URL publique : utilisée par le NAVIGATEUR de l'admin (redirection de login)
    KEYCLOAK_PUBLIC_URL: str = "https://192.168.10.10/auth"
    KEYCLOAK_ADMIN_USER: str = "admin"
    KEYCLOAK_ADMIN_PASSWORD_FILE: str = "/run/secrets/keycloak_admin_password"
    KEYCLOAK_CONSOLE_CLIENT_SECRET_FILE: str = "/run/secrets/console_client_secret"

    # ------------------------------------------------------------------
    # Synapse (API d'administration)
    # ------------------------------------------------------------------
    SYNAPSE_ADMIN_URL: str = "http://synapse:8008"
    SYNAPSE_ADMIN_TOKEN_FILE: str = "/run/secrets/synapse_admin_token"

    # ------------------------------------------------------------------
    # Adresse publique du serveur (avec https://)
    # ------------------------------------------------------------------
    SERVER_ADDRESS: str = "https://192.168.10.10"

    # ------------------------------------------------------------------
    # Jeton d'activation (usage unique, section 6.4 du brief)
    # ------------------------------------------------------------------
    ACTIVATION_TOKEN_TTL_HOURS: int = 48
    ACTIVATION_TOKEN_BYTES: int = 32

    # ------------------------------------------------------------------
    # Propriétés : lecture des secrets depuis les fichiers
    # ------------------------------------------------------------------

    @property
    def keycloak_admin_password(self) -> str:
        return _read_secret(self.KEYCLOAK_ADMIN_PASSWORD_FILE)

    @property
    def keycloak_console_client_secret(self) -> str:
        return _read_secret(self.KEYCLOAK_CONSOLE_CLIENT_SECRET_FILE)

    @property
    def synapse_admin_token(self) -> str:
        # Lecture paresseuse : le jeton du bot est écrit par demo_seed.sh
        # APRÈS le démarrage ; on le relit à chaque appel.
        return _read_secret(self.SYNAPSE_ADMIN_TOKEN_FILE)

    @property
    def database_url(self) -> str:
        """Reconstruit l'URL de connexion avec le mot de passe lu depuis le fichier."""
        pw = _read_secret(self.DATABASE_PASSWORD_FILE)
        return self.DATABASE_URL.replace("console@", f"console:{pw}@")

    @property
    def session_secret(self) -> str:
        """Secret de signature des sessions (cookies)."""
        # Réutilise le secret client console (déjà monté) comme clé de session.
        return self.keycloak_console_client_secret


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
