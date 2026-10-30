# app/synapse_client.py — Client de l'API d'administration Synapse
"""
Client asynchrone vers l'API admin Synapse (/_synapse/admin/v1/...).
Utilisé par la Console pour : désactiver un compte (révocation), lister les
appareils, gérer les salons.

Le jeton admin est relu depuis son fichier secret à CHAQUE requête : ainsi,
quand scripts/demo_seed.sh crée le compte technique @kibare-bot et écrit son
jeton, la Console le récupère sans redémarrage.
"""
import httpx
from typing import Optional, List, Dict, Any
from app.config import settings


class SynapseAdminClient:
    def __init__(self, base_url: str = None):
        self.base_url = (base_url or settings.SYNAPSE_ADMIN_URL).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    def _headers(self) -> Dict[str, str]:
        # Lecture paresseuse du jeton admin (écrit par demo_seed.sh)
        return {
            "Authorization": f"Bearer {settings.synapse_admin_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if not self._client:
            self._client = httpx.AsyncClient(timeout=30.0)
        url = f"{self.base_url}{path}"
        response = await self._client.request(method, url, headers=self._headers(), **kwargs)
        response.raise_for_status()
        return response

    # ------------------------------------------------------------------
    # Utilisateurs
    # ------------------------------------------------------------------

    async def deactivate_user(self, user_id: str, erase: bool = False) -> Dict[str, Any]:
        """
        Désactive un compte Matrix (révocation).

        `erase=False` (notre cas) : supprime les jetons d'accès sur TOUS les
        appareils et fait quitter tous les salons à l'utilisateur, mais garde
        l'historique. `erase=True` supprimerait tout (non utilisé ici).
        """
        response = await self._request(
            "POST", f"/_synapse/admin/v1/deactivate/{user_id}", json={"erase": erase},
        )
        return response.json()

    async def list_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Liste les appareils (sessions) d'un utilisateur — sans contenu de message."""
        response = await self._request("GET", f"/_synapse/admin/v1/users/{user_id}/devices")
        return response.json().get("devices", [])

    async def create_user(self, user_id: str, displayname: str = None, admin: bool = False) -> None:
        """
        Crée un compte Matrix (appelé à l'enrôlement, pour que le compte existe
        AVANT la première connexion OIDC — voir enable_registration=false).
        """
        payload = {"displayname": displayname, "admin": admin}
        if displayname is None:
            payload.pop("displayname")
        await self._request("PUT", f"/_synapse/admin/v2/users/{user_id}", json=payload)

    # ------------------------------------------------------------------
    # Salons
    # ------------------------------------------------------------------

    async def create_room(self, name: str, topic: str = None,
                          preset: str = "private_chat",
                          initial_state: List[Dict] = None,
                          room_alias: str = None) -> Dict[str, Any]:
        """Crée un salon chiffré (join_rule=invite) et renvoie {room_id: ...}."""
        payload = {
            "name": name,
            "preset": preset,
            "initial_state": initial_state or [
                {"type": "m.room.encryption", "state_key": "",
                 "content": {"algorithm": "m.megolm.v1.aes-sha2"}},
                {"type": "m.room.join_rules", "state_key": "",
                 "content": {"join_rule": "invite"}},
                {"type": "m.room.history_visibility", "state_key": "",
                 "content": {"history_visibility": "joined"}},
            ],
        }
        if topic:
            payload["topic"] = topic
        if room_alias:
            payload["room_alias_name"] = room_alias
        response = await self._request("POST", "/_synapse/admin/v1/rooms", json=payload)
        return response.json()

    async def invite_user_to_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """Invite un utilisateur dans un salon (via le bot)."""
        response = await self._request(
            "POST", f"/_synapse/admin/v1/rooms/{room_id}/invite", json={"user_id": user_id},
        )
        return response.json()

    async def join_user_to_room(self, room_id: str, user_id: str) -> Dict[str, Any]:
        """Fait rejoindre un salon à un utilisateur (sans invitation préalable)."""
        response = await self._request(
            "POST", f"/_synapse/admin/v1/join/{room_id}", json={"user_id": user_id},
        )
        return response.json()

    async def health_check(self) -> Dict[str, Any]:
        response = await self._request("GET", "/health")
        return response.json()
