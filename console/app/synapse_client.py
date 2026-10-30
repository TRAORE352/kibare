# app/synapse_client.py - Client admin Synapse
"""
Client pour l'API d'administration Synapse.
Gère la désactivation d'utilisateurs, invitations aux salons, etc.
"""

import httpx
from typing import Optional, List, Dict, Any
from app.config import settings


class SynapseAdminClient:
    """
    Client asynchrone pour l'API admin Synapse.
    Utilise un token d'accès admin (macaroon ou access_token).
    """

    def __init__(self, base_url: str, admin_token: str):
        self.base_url = base_url.rstrip("/")
        self.admin_token = admin_token
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Effectue une requête vers l'API admin Synapse."""
        if not self._client:
            raise RuntimeError("Client non initialisé")
        
        url = f"{self.base_url}{path}"
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    # === Gestion des utilisateurs ===

    async def deactivate_user(self, user_id: str, erase: bool = False) -> Dict[str, Any]:
        """
        Désactive un utilisateur Matrix.
        erase=false : garde les données, supprime les tokens d'accès, fait quitter les salons.
        erase=true : supprime tout (RGPD).
        Retourne la réponse de l'API.
        """
        response = await self._request(
            "POST",
            f"/_synapse/admin/v1/deactivate/{user_id}",
            json={"erase": erase},
        )
        return response.json()

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Récupère les infos d'un utilisateur."""
        response = await self._request("GET", f"/_synapse/admin/v1/users/{user_id}")
        return response.json()

    async def list_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Liste les appareils (sessions) d'un utilisateur."""
        response = await self._request("GET", f"/_synapse/admin/v1/users/{user_id}/devices")
        return response.json().get("devices", [])

    async def delete_user_device(self, user_id: str, device_id: str) -> None:
        """Supprime un appareil spécifique (révoque sa session)."""
        await self._request("DELETE", f"/_synapse/admin/v1/users/{user_id}/devices/{device_id}")

    async def reset_user_password(self, user_id: str, new_password: str, logout_devices: bool = True) -> None:
        """Réinitialise le mot de passe (pas utilisé chez nous : OIDC only)."""
        await self._request(
            "POST",
            f"/_synapse/admin/v1/users/{user_id}/password",
            json={"new_password": new_password, "logout_devices": logout_devices},
        )

    # === Gestion des salons ===

    async def create_room(
        self,
        name: str,
        topic: str = None,
        preset: str = "private_chat",
        initial_state: List[Dict] = None,
        room_alias: str = None,
    ) -> Dict[str, Any]:
        """Crée un nouveau salon."""
        payload = {
            "name": name,
            "preset": preset,
            "initial_state": initial_state or [
                {"type": "m.room.encryption", "state_key": "", "content": {"algorithm": "m.megolm.v1.aes-sha2"}},
                {"type": "m.room.join_rules", "state_key": "", "content": {"join_rule": "invite"}},
                {"type": "m.room.history_visibility", "state_key": "", "content": {"history_visibility": "joined"}},
            ],
        }
        if topic:
            payload["topic"] = topic
        if room_alias:
            payload["room_alias_name"] = room_alias
        
        response = await self._request("POST", "/_synapse/admin/v1/rooms", json=payload)
        return response.json()

    async def invite_user_to_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """Invite un utilisateur dans un salon."""
        response = await self._request(
            "POST",
            f"/_synapse/admin/v1/rooms/{room_id}/invite",
            json={"user_id": user_id},
        )
        return response.json()

    async def kick_user_from_room(self, room_id: str, user_id: str, kicker_id: str = None) -> Dict[str, Any]:
        """Exclut un utilisateur d'un salon."""
        payload = {"user_id": user_id}
        if kicker_id:
            payload["kicker"] = kicker_id
        response = await self._request(
            "POST",
            f"/_synapse/admin/v1/rooms/{room_id}/kick",
            json=payload,
        )
        return response.json()

    async def get_room_members(self, room_id: str) -> List[Dict[str, Any]]:
        """Liste les membres d'un salon."""
        response = await self._request("GET", f"/_synapse/admin/v1/rooms/{room_id}/members")
        return response.json().get("chunk", [])

    async def get_room_state(self, room_id: str) -> List[Dict[str, Any]]:
        """Récupère l'état complet d'un salon."""
        response = await self._request("GET", f"/_synapse/admin/v1/rooms/{room_id}/state")
        return response.json()

    async def list_rooms(self, limit: int = 100, from_token: str = None) -> Dict[str, Any]:
        """Liste tous les salons."""
        params = {"limit": limit}
        if from_token:
            params["from"] = from_token
        response = await self._request("GET", "/_synapse/admin/v1/rooms", params=params)
        return response.json()

    # === Modération / Sécurité ===

    async def ban_user(self, user_id: str, reason: str = None) -> Dict[str, Any]:
        """Bannit un utilisateur du serveur."""
        payload = {"user_id": user_id}
        if reason:
            payload["reason"] = reason
        response = await self._request("POST", "/_synapse/admin/v1/users/ban", json=payload)
        return response.json()

    async def unban_user(user_id: str) -> Dict[str, Any]:
        """Débannit un utilisateur."""
        response = await self._request("POST", "/_synapse/admin/v1/users/unban", json={"user_id": user_id})
        return response.json()

    # === Médias ===

    async def quarantine_media(self, media_id: str) -> None:
        """Met un média en quarantaine."""
        await self._request("POST", f"/_synapse/admin/v1/media/quarantine/{media_id}")

    async def delete_media(self, media_id: str) -> None:
        """Supprime un média."""
        await self._request("DELETE", f"/_synapse/admin/v1/media/{media_id}")

    # === Statistiques / Santé ===

    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques du serveur."""
        response = await self._request("GET", "/_synapse/admin/v1/statistics")
        return response.json()

    async def health_check(self) -> Dict[str, Any]:
        """Health check Synapse."""
        response = await self._request("GET", "/health")
        return response.json()