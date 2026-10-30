# app/keycloak_client.py — Client de l'API d'administration Keycloak
"""
Client asynchrone vers l'API admin Keycloak.

Utilisé par la Console pour :
  - créer un compte agent (enrôlement) SANS mot de passe ;
  - définir le mot de passe (activation par l'agent) ;
  - désactiver le compte + fermer toutes les sessions (révocation) ;
  - assigner les rôles de realm.

Authentification : le compte bootstrap « admin » (realm master) via le client
« admin-cli » (flux password). Le mot de passe admin est lu depuis un fichier
secret, jamais en clair dans le code.
"""
import httpx
from typing import Optional, List, Dict, Any
from app.config import settings


class KeycloakAdminClient:
    def __init__(self, base_url: str = None, admin_user: str = None,
                 admin_password: str = None, realm: str = None):
        self.base_url = (base_url or settings.KEYCLOAK_INTERNAL_URL).rstrip("/")
        self.admin_user = admin_user or settings.KEYCLOAK_ADMIN_USER
        self._admin_password = (admin_password if admin_password is not None
                                else settings.keycloak_admin_password)
        self.realm = realm or settings.KEYCLOAK_REALM
        self._client: Optional[httpx.AsyncClient] = None
        self._access_token: Optional[str] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        await self._authenticate()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _authenticate(self):
        """Obtient un jeton admin via le flux password (client admin-cli)."""
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        response = await self._client.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": self.admin_user,
                "password": self._admin_password,
            },
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        url = f"{self.base_url}/admin/realms/{self.realm}{path}"
        response = await self._client.request(method, url, headers=self._headers(), **kwargs)
        if response.status_code == 401:
            # Jeton expiré : on se ré-authentifie et on réessaie une fois.
            await self._authenticate()
            response = await self._client.request(method, url, headers=self._headers(), **kwargs)
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # Utilisateurs
    # ------------------------------------------------------------------

    async def create_user(self, username: str, email: str, first_name: str,
                          last_name: str, attributes: Dict[str, List[str]] = None,
                          realm_roles: List[str] = None,
                          required_actions: List[str] = None) -> str:
        """
        Crée un utilisateur Keycloak SANS mot de passe.
        Le mot de passe sera défini par l'agent lui-même au moment de l'activation
        (set_password), ce qui garantit que personne d'autre ne le connaît.
        Renvoie l'identifiant Keycloak (UUID).
        """
        payload = {
            "username": username,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
            "requiredActions": required_actions or ["CONFIGURE_TOTP"],
            "attributes": attributes or {},
        }
        response = await self._request("POST", "/users", json=payload)
        # L'UUID est renvoyé dans l'en-tête Location : .../users/<uuid>
        location = response.headers.get("Location", "")
        user_id = location.rstrip("/").split("/")[-1] if location else None
        if not user_id:
            found = await self.get_user_by_username(username)
            user_id = found["id"] if found else None
        if realm_roles and user_id:
            await self.assign_realm_roles(user_id, realm_roles)
        return user_id

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        response = await self._request("GET", "/users", params={"username": username})
        users = response.json()
        return users[0] if users else None

    async def set_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Définit le mot de passe de l'utilisateur (appelé à l'activation)."""
        await self._request(
            "PUT", f"/users/{user_id}/reset-password",
            json={"type": "password", "value": password, "temporary": temporary},
        )

    async def disable_user(self, user_id: str) -> None:
        """Désactive le compte (enabled=false) — 1re étape de la révocation."""
        await self._request("PUT", f"/users/{user_id}", json={"enabled": False})

    async def logout_user(self, user_id: str) -> None:
        """Ferme toutes les sessions actives de l'utilisateur (tokens invalidés)."""
        await self._request("POST", f"/users/{user_id}/logout")

    async def assign_realm_roles(self, user_id: str, role_names: List[str]) -> None:
        """Assigne des rôles de realm à un utilisateur."""
        roles = []
        for name in role_names:
            r = await self._request("GET", f"/roles/{name}")
            roles.append(r.json())
        if roles:
            await self._request("POST", f"/users/{user_id}/role-mappings/realm", json=roles)

    async def delete_user(self, user_id: str) -> None:
        """Supprime définitivement l'utilisateur (non utilisé dans le MVP)."""
        await self._request("DELETE", f"/users/{user_id}")
