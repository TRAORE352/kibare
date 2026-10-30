# app/config.py - Configuration de la Console Kibaré
"""
Configuration centralisée via variables d'environnement.
Tous les secrets sont lus depuis des fichiers (Docker secrets).
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Base de données Console
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://console:console@postgres/kibare_console",
        description="URL de connexion PostgreSQL async",
    )

    # Keycloak
    KEYCLOAK_ADMIN_URL: str = Field(
        default="http://keycloak:8080",
        description="URL admin Keycloak (interne Docker)",
    )
    KEYCLOAK_ADMIN_USER: str = Field(default="admin", description="Utilisateur admin Keycloak")
    KEYCLOAK_ADMIN_PASSWORD: str = Field(
        default="",
        description="Mot de passe admin Keycloak (lu depuis secret)",
    )
    KEYCLOAK_ADMIN_PASSWORD_FILE: str = Field(
        default="/run/secrets/keycloak_admin_password",
        description="Chemin vers le fichier secret",
    )
    KEYCLOAK_REALM: str = Field(default="kibare", description="Realm Keycloak")
    KEYCLOAK_CONSOLE_CLIENT_SECRET: str = Field(
        default="",
        description="Secret client kibare-console (lu depuis secret ou env)",
    )

    # Synapse
    SYNAPSE_ADMIN_URL: str = Field(
        default="http://synapse:8008",
        description="URL admin Synapse (interne Docker)",
    )
    SYNAPSE_ADMIN_TOKEN: str = Field(
        default="",
        description="Token admin Synapse (lu depuis secret)",
    )
    SYNAPSE_ADMIN_TOKEN_FILE: str = Field(
        default="/run/secrets/synapse_admin_token",
        description="Chemin vers le fichier secret",
    )

    # JWT pour sessions Console
    JWT_SECRET: str = Field(default="", description="Secret JWT (lu depuis secret)")
    JWT_SECRET_FILE: str = Field(default="/run/secrets/jwt_secret", description="Chemin vers le fichier secret")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # Serveur
    SERVER_ADDRESS: str = Field(
        default="https://192.168.10.10",
        description="Adresse publique du serveur (avec https://)",
    )
    KIBARE_SERVER_ADDRESS: str = Field(
        default="192.168.10.10",
        description="Adresse IP du serveur (sans protocole)",
    )

    # Activation
    ACTIVATION_TOKEN_TTL_HOURS: int = Field(
        default=48,
        description="Durée de validité du jeton d'activation (heures)",
    )
    ACTIVATION_TOKEN_BYTES: int = Field(
        default=32,
        description="Longueur du jeton aléatoire (octets)",
    )

    # Synapse Bot (pour gestion salons)
    SYNAPSE_BOT_USER: str = Field(
        default="@kibare-bot:kibare.test",
        description="Utilisateur bot pour invitations automatiques",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Charger les secrets depuis les fichiers
        self._load_secrets()

    def _load_secrets(self):
        """Charge les secrets depuis les fichiers Docker secrets."""
        secret_files = {
            "KEYCLOAK_ADMIN_PASSWORD": self.KEYCLOAK_ADMIN_PASSWORD_FILE,
            "SYNAPSE_ADMIN_TOKEN": self.SYNAPSE_ADMIN_TOKEN_FILE,
            "JWT_SECRET": self.JWT_SECRET_FILE,
        }
        for attr, path in secret_files.items():
            if Path(path).exists():
                value = Path(path).read_text().strip()
                setattr(self, attr, value)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()