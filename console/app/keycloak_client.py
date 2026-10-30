# app/keycloak_client.py - Client admin Keycloak
"""
Client pour l'API d'administration Keycloak.
Gère la création, mise à jour, désactivation des utilisateurs et rôles.
"""

import httpx
from typing import Optional, List, Dict, Any
from app.config import settings


class KeycloakAdminClient:
    """
    Client asynchrone pour l'API admin Keycloak.
    Utilise un compte de service (client kibare-console avec service account).
    """

    def __init__(
        self,
        base_url: str,
        admin_user: str,
        admin_password: str,
        realm: str,
    ):
        self.base_url = base_url.rstrip("/")
        self.admin_user = admin_user
        self.admin_password = admin_password
        self.realm = realm
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
        """Obtient un token d'accès admin via le flux password (service account)."""
        if not self._client:
            raise RuntimeError("Client non initialisé")
        
        response = await self._client.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": self.admin_user,
                "password": self.admin_password,
            },
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]

    def _headers(self) -> Dict[str, str]:
        if not self._access_token:
            raise RuntimeError("Non authentifié")
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Effectue une requête avec renouvellement automatique du token si 401."""
        if not self._client:
            raise RuntimeError("Client non initialisé")
        
        url = f"{self.base_url}/admin/realms/{self.realm}{path}"
        response = await self._client.request(method, url, headers=self._headers(), **kwargs)
        
        if response.status_code == 401:
            # Token expiré, renouveler
            await self._authenticate()
            response = await self._client.request(method, url, headers=self._headers(), **kwargs)
        
        response.raise_for_status()
        return response

    # === Gestion des utilisateurs ===

    async def create_user(
        self,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        password: str,
        required_actions: List[str] = None,
        attributes: Dict[str, List[str]] = None,
        realm_roles: List[str] = None,
    ) -> str:
        """
        Crée un utilisateur dans Keycloak.
        Retourne l'ID utilisateur Keycloak (UUID).
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
        # L'ID est dans le header Location
        location = response.headers.get("Location", "")
        user_id = location.split("/")[-1] if location else None
        
        if not user_id:
            # Fallback : rechercher l'utilisateur
            users = await self.get_users(username=username)
            user_id = users[0]["id"] if users else None
        
        # Définir le mot de passe
        if user_id:
            await self.set_password(user_id, password, temporary=False)
        
        # Assigner les rôles realm
        if realm_roles and user_id:
            await self.assign_realm_roles(user_id, realm_roles)
        
        return user_id

    async def get_users(self, username: str = None, email: str = None) -> List[Dict[str, Any]]:
        """Recherche des utilisateurs."""
        params = {}
        if username:
            params["username"] = username
        if email:
            params["email"] = email
        
        response = await self._request("GET", "/users", params=params)
        return response.json()

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Récupère un utilisateur par son ID."""
        response = await self._request("GET", f"/users/{user_id}")
        return response.json()

    async def update_user(self, user_id: str, **updates) -> None:
        """Met à jour un utilisateur."""
        await self._request("PUT", f"/users/{user_id}", json=updates)

    async def disable_user(self, user_id: str) -> None:
        """Désactive un utilisateur (enabled=false)."""
        await self.update_user(user_id, enabled=False)

    async def enable_user(self, user_id: str) -> None:
        """Réactive un utilisateur."""
        await self.update_user(user_id, enabled=True)

    async def set_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Définit le mot de passe d'un utilisateur."""
        payload = {
            "type": "password",
            "value": password,
            "temporary": temporary,
        }
        await self._request("PUT", f"/users/{user_id}/reset-password", json=payload)

    async def logout_user(self, user_id: str) -> None:
        """Ferme toutes les sessions d'un utilisateur (révocation tokens)."""
        await self._request("POST", f"/users/{user_id}/logout")

    async def assign_realm_roles(self, user_id: str, role_names: List[str]) -> None:
        """Assigne des rôles realm à un utilisateur."""
        # Récupérer les rôles
        roles = []
        for role_name in role_names:
            response = await self._request("GET", f"/roles/{role_name}")
            roles.append(response.json())
        
        if roles:
            await self._request("POST", f"/users/{user_id}/role-mappings/realm", json=roles)

    async def get_user_realm_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Récupère les rôles realm d'un utilisateur."""
        response = await self._request("GET", f"/users/{user_id}/role-mappings/realm")
        return response.json()

    async def delete_user(self, user_id: str) -> None:
        """Supprime un utilisateur (définitif)."""
        await self._request("DELETE", f"/users/{user_id}")

    # === Rôles ===

    async def get_realm_roles(self) -> List[Dict[str, Any]]:
        """Liste tous les rôles du realm."""
        response = await self._request("GET", "/roles")
        return response.json()

    # === Clients ===

    async def get_client_id(self, client_id: str) -> Optional[str]:
        """Récupère l'UUID interne d'un client par son clientId."""
        response = await self._request("GET", "/clients", params={"clientId": client_id})
        clients = response.json()
        return clients[0]["id"] if clients else None

    async def get_client_service_account_user(self, client_id: str) -> Optional[str]:
        """Récupère l'utilisateur service account d'un client."""
        client_uuid = await self.get_client_id(client_id)
        if not client_uuid:
            return None
        response = await self._request("GET", f"/clients/{client_uuid}/service-account-user")
        return response.json().get("id")