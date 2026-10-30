#!/usr/bin/env python3
"""
scripts/demo_seed.py — Peuplement de l'environnement de démo

Crée, via l'API admin de Synapse :
  1. le compte technique @kibare-bot:kibare.test (admin) — il gère les salons
     mais n'a aucune session de chiffrement (il ne peut pas lire les messages) ;
  2. les comptes Matrix des agents de démo (demo-000 .. demo-402) ;
  3. les salons chiffrés (join_rule=invite) et y ajoute les membres.

Le jeton du bot est affiché en clair SUR UNE SEULE LIGNE à la fin, pour être
sauvegardé dans secrets/synapse_admin_token.txt par demo_seed.sh.

Variables d'environnement :
  SYNAPSE_URL                      (défaut http://synapse:8008)
  REGISTRATION_SHARED_SECRET       (ou REGISTRATION_SHARED_SECRET_FILE)
  SYNAPSE_ADMIN_TOKEN              (jeton existant, si le bot est déjà créé)
"""
import hashlib
import hmac
import json
import os
import sys
import secrets as pysecrets

import httpx

SYNAPSE_URL = os.getenv("SYNAPSE_URL", "http://synapse:8008").rstrip("/")
SERVER_NAME = "kibare.test"

# Comptes de démo (matricule -> nom complet). Tous fictifs.
DEMO_USERS = {
    "demo-000": "Admin PLATEFORME",
    "demo-101": "Awa KONATÉ",
    "demo-102": "Issouf SAWADOGO",
    "demo-201": "Mariam OUÉDRAOGO",
    "demo-202": "Boukary ZONGO",
    "demo-203": "Karim TIENDRÉBÉOGO",
    "demo-301": "Salif COMPAORÉ",
    "demo-302": "Rasmata KABORÉ",
    "demo-401": "Adama OUATTARA",
    "demo-402": "Fatimata DIALLO",
}

# Salons de démo (clé -> (nom, membres)).
ROOMS = {
    "mtdpce": ("MTDPCE — Canal officiel", ["demo-000", "demo-101", "demo-102"]),
    "sante": ("Santé — Canal officiel", ["demo-201", "demo-202", "demo-203"]),
    "securite": ("Sécurité — Canal officiel", ["demo-301", "demo-302"]),
    "mef": ("MEF — Canal officiel", ["demo-401", "demo-402"]),
    "crise": ("Cellule de crise sanitaire",
              ["demo-101", "demo-102", "demo-201", "demo-202",
               "demo-203", "demo-301", "demo-302"]),
}


def _shared_secret() -> str:
    if os.getenv("REGISTRATION_SHARED_SECRET"):
        return os.getenv("REGISTRATION_SHARED_SECRET").strip()
    p = os.getenv("REGISTRATION_SHARED_SECRET_FILE",
                  "/run/secrets/registration_shared_secret")
    if os.path.exists(p):
        return open(p).read().strip()
    return ""


def register_bot(client: httpx.Client) -> str:
    """Crée le bot via l'API d'enregistrement (HMAC-SHA1 + secret partagé).
    Renvoie le jeton d'accès. Si le bot existe déjà, renvoie None."""
    secret = _shared_secret()
    if not secret:
        print("ERREUR: secret partagé introuvable", file=sys.stderr)
        sys.exit(1)

    user = "kibare-bot"
    password = os.getenv("BOT_PASSWORD") or pysecrets.token_urlsafe(24)

    r = client.get(f"{SYNAPSE_URL}/_synapse/admin/v1/register")
    r.raise_for_status()
    nonce = r.json()["nonce"]

    # Construction HMAC identique à register_new_matrix_user (Synapse).
    mac = hmac.new(secret.encode("utf8"), digestmod=hashlib.sha1)
    mac.update(nonce.encode("utf8"))
    mac.update(b"\x00")
    mac.update(user.encode("utf8"))
    mac.update(b"\x00")
    mac.update(password.encode("utf8"))
    mac.update(b"\x00")
    mac.update(b"admin")

    data = {
        "nonce": nonce, "username": user, "password": password,
        "admin": True, "mac": mac.hexdigest(),
    }
    r = client.post(f"{SYNAPSE_URL}/_synapse/admin/v1/register", json=data)
    if r.status_code == 400 and r.json().get("errcode") == "M_USER_IN_USE":
        return None
    r.raise_for_status()
    return r.json()["access_token"]


def create_users(client: httpx.Client, headers: dict):
    """Crée les comptes Matrix des agents de démo (sans mot de passe : OIDC)."""
    for matricule, nom in DEMO_USERS.items():
        user_id = f"@{matricule}:{SERVER_NAME}"
        client.put(f"{SYNAPSE_URL}/_synapse/admin/v2/users/{user_id}",
                   headers=headers, json={"displayname": nom, "admin": False})


def create_rooms(client: httpx.Client, headers: dict):
    """Crée les salons chiffrés (invite) et ajoute les membres."""
    for key, (name, members) in ROOMS.items():
        payload = {
            "name": name,
            "preset": "private_chat",
            "initial_state": [
                {"type": "m.room.encryption", "state_key": "",
                 "content": {"algorithm": "m.megolm.v1.aes-sha2"}},
                {"type": "m.room.join_rules", "state_key": "",
                 "content": {"join_rule": "invite"}},
                {"type": "m.room.history_visibility", "state_key": "",
                 "content": {"history_visibility": "joined"}},
            ],
        }
        # Création via l'API CLIENT Matrix (l'API admin n'a pas d'endpoint
        # de création de salon). Le bot en est le créateur.
        r = client.post(f"{SYNAPSE_URL}/_matrix/client/v3/createRoom",
                        headers=headers, json=payload)
        r.raise_for_status()
        room_id = r.json()["room_id"]
        print(f"Salon '{name}' -> {room_id}")

        for matricule in members:
            user_id = f"@{matricule}:{SERVER_NAME}"
            client.post(f"{SYNAPSE_URL}/_synapse/admin/v1/join/{room_id}",
                        headers=headers, json={"user_id": user_id})


def main():
    client = httpx.Client(timeout=60.0)
    token = os.getenv("SYNAPSE_ADMIN_TOKEN", "").strip()

    if not token:
        token = register_bot(client)

    if not token:
        print("ERREUR: impossible d'obtenir un jeton admin (bot déjà créé sans "
              "jeton ?). Relancez avec SYNAPSE_ADMIN_TOKEN défini.", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}
    create_users(client, headers)
    create_rooms(client, headers)

    # Le jeton est affiché en dernière ligne, pour capture par demo_seed.sh.
    print(f"BOT_TOKEN={token}")


if __name__ == "__main__":
    main()
