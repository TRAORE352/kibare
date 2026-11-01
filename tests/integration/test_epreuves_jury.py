#!/usr/bin/env python3
# =====================================================================
# tests/integration/test_epreuves_jury.py
#
# Automatise les trois épreuves du jury (section 12 et 17 du brief) :
#
#   1. « Intrus »              : le compte non enrôlé est refusé.
#   2. « Le serveur ne lit rien » : un message réellement chiffré est
#                                introuvable en clair dans la base.
#   3. « Révocation »          : après révocation, le jeton d'accès de
#                                l'agent ne fonctionne plus.
#
# Ces tests tournent contre l'instance de TEST (tests/integration/
# instance_test.py), pas contre la production : voir l'explication dans
# ce fichier (la production est OIDC-seulement, donc inaccessible à un
# client automatisé sans navigateur).
#
# Le chiffrement, lui, est le VRAI chiffrement Matrix (Olm/Megolm) fourni
# par la bibliothèque matrix-nio. Aucune ligne de cryptographie n'est
# écrite par l'équipe (règle éliminatoire, section 2 du brief).
# =====================================================================

import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import sys

import aiohttp
from nio import AsyncClient, AsyncClientConfig, LoginResponse, RoomCreateResponse

DOSSIER = "/tmp/kibare-synapse-test"
URL = "http://localhost:8009"
SERVEUR = "kibare.test"
SECRET_INSCRIPTION = "secret-de-test-jetable-kibare"

# Le message que le jury recherche dans la base de données.
MESSAGE_TEST = "MESSAGE-TEST-JURY-123"

# Comptes fictifs (section 9 du brief). Aucune personne réelle.
AGENTS = {
    "demo-202": "MotDePasseDemo202!",   # Boukary ZONGO, agent Santé
    "demo-203": "MotDePasseDemo203!",   # Karim TIENDRÉBÉOGO, à révoquer
}

vert = "\033[0;32m"
rouge = "\033[0;31m"
neutre = "\033[0m"

resultats = []


def verifier(description, condition):
    """Enregistre et affiche le résultat d'une vérification."""
    etat = f"{vert}PASS{neutre}" if condition else f"{rouge}FAIL{neutre}"
    print(f"  [{etat}] {description}")
    resultats.append((description, bool(condition)))
    return condition


async def creer_compte(session, identifiant, mot_de_passe):
    """
    Crée un compte sur l'instance de TEST via l'API d'enregistrement
    partagée (la même que l'outil officiel register_new_matrix_user).

    Note importante : `enable_registration` est à `false`. Cette API exige
    une signature HMAC-SHA1 avec le secret du serveur — ce n'est donc PAS
    de l'inscription libre. C'est exactement ce que fait la Console Kibaré
    pour créer le compte technique du bot.
    """
    async with session.get(f"{URL}/_synapse/admin/v1/register") as r:
        nonce = (await r.json())["nonce"]

    # La signature prouve qu'on détient le secret du serveur.
    message = b"\x00".join([
        nonce.encode(), identifiant.encode(), mot_de_passe.encode(), b"notadmin",
    ])
    signature = hmac.new(
        SECRET_INSCRIPTION.encode(), message, hashlib.sha1
    ).hexdigest()

    corps = {
        "nonce": nonce,
        "username": identifiant,
        "password": mot_de_passe,
        "admin": False,
        "mac": signature,
    }
    async with session.post(f"{URL}/_synapse/admin/v1/register", json=corps) as r:
        return r.status == 200


# =====================================================================
# ÉPREUVE 1 — « Intrus »
# =====================================================================
async def epreuve_intrus(session):
    """
    Le compte « intrus » n'a jamais été enrôlé. Il ne doit pouvoir ni se
    connecter, ni s'inscrire tout seul.

    Sans cette protection, n'importe qui sur le réseau de l'État pourrait
    se créer un compte et rejoindre la messagerie de l'administration.
    """
    print("\n=== ÉPREUVE 1 : « Intrus » ===")

    # 1. Tentative de connexion avec un compte qui n'existe pas.
    corps = {
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": "intrus"},
        "password": "peu-importe",
    }
    async with session.post(f"{URL}/_matrix/client/v3/login", json=corps) as r:
        statut = r.status
        reponse = await r.json()

    verifier(
        f"Connexion de « intrus » refusée (HTTP {statut}, {reponse.get('errcode')})",
        statut == 403 and reponse.get("errcode") == "M_FORBIDDEN",
    )

    # 2. Tentative d'inscription libre : l'API doit la refuser.
    async with session.post(
        f"{URL}/_matrix/client/v3/register",
        json={"username": "intrus", "password": "peu-importe", "auth": {"type": "m.login.dummy"}},
    ) as r:
        statut = r.status
        reponse = await r.json()

    verifier(
        f"Inscription libre refusée (HTTP {statut}, {reponse.get('errcode')})",
        statut == 403 and reponse.get("errcode") == "M_FORBIDDEN",
    )


# =====================================================================
# ÉPREUVE 2 — « Le serveur ne lit rien »
# =====================================================================
async def epreuve_serveur_ne_lit_rien(session):
    """
    Deux agents échangent un message RÉELLEMENT chiffré de bout en bout.
    On vérifie ensuite que le serveur n'en a aucune trace en clair.

    C'est la règle éliminatoire n°2 du brief : un seul message lisible
    côté serveur et l'équipe est éliminée.
    """
    print("\n=== ÉPREUVE 2 : « Le serveur ne lit rien » ===")

    for identifiant, mot_de_passe in AGENTS.items():
        await creer_compte(session, identifiant, mot_de_passe)

    # Deux clients distincts, chacun avec son propre magasin de clés :
    # c'est ce qui rend le chiffrement réel (deux appareils différents).
    clients = {}
    for identifiant, mot_de_passe in AGENTS.items():
        magasin = f"{DOSSIER}/nio-{identifiant}"
        os.makedirs(magasin, exist_ok=True)
        client = AsyncClient(
            URL, f"@{identifiant}:{SERVEUR}", store_path=magasin,
            config=AsyncClientConfig(encryption_enabled=True, store_sync_tokens=True),
        )
        reponse = await client.login(mot_de_passe)
        if not isinstance(reponse, LoginResponse):
            print(f"  Connexion impossible pour {identifiant} : {reponse}")
            return
        client.load_store()
        clients[identifiant] = client

    envoyeur = clients["demo-202"]
    invite = clients["demo-203"]

    # Création d'un salon chiffré, sur invitation uniquement.
    creation = await envoyeur.room_create(
        name="Cellule de crise sanitaire (test)",
        initial_state=[{
            "type": "m.room.encryption",
            "state_key": "",
            "content": {"algorithm": "m.megolm.v1.aes-sha2"},
        }],
    )
    if not isinstance(creation, RoomCreateResponse):
        print(f"  Création du salon impossible : {creation}")
        return
    salon = creation.room_id

    await envoyeur.room_invite(salon, f"@demo-203:{SERVEUR}")
    await invite.join(salon)

    # Les deux clients se synchronisent pour échanger leurs clés.
    await envoyeur.sync(timeout=3000, full_state=True)
    await invite.sync(timeout=3000, full_state=True)

    # Étape indispensable n°1 : chaque client PUBLIE ses clés d'appareil
    # sur le serveur. Sans cela, le serveur ne connaît aucun appareil, donc
    # l'envoyeur ne trouve personne à qui remettre la clé de session et le
    # destinataire ne peut rien déchiffrer
    # (« no session found with session id … »).
    for client in clients.values():
        if client.should_upload_keys:
            await client.keys_upload()

    # Étape indispensable n°2 : l'envoyeur doit CONNAÎTRE les appareils du
    # destinataire avant de chiffrer. La clé de session Megolm est envoyée
    # à chaque appareil connu au moment de l'envoi ; un appareil découvert
    # trop tard ne reçoit jamais la clé.
    # (matrix-nio refuse l'appel s'il n'a rien à demander : d'où le test.)
    if envoyeur.should_query_keys:
        await envoyeur.keys_query()
    if invite.should_query_keys:
        await invite.keys_query()

    appareils_vus = list(envoyeur.device_store.active_user_devices(f"@demo-203:{SERVEUR}"))
    verifier(
        f"L'envoyeur voit l'appareil du destinataire ({len(appareils_vus)})",
        len(appareils_vus) > 0,
    )

    # On fait confiance aux appareils de l'autre (en production, c'est la
    # vérification entre appareils ; ici on l'automatise pour le test).
    for client in clients.values():
        for utilisateur in client.device_store.users:
            for appareil in client.device_store.active_user_devices(utilisateur):
                client.verify_device(appareil)

    # Partage explicite de la clé de session du salon avec les appareils
    # vérifiés ci-dessus. Si le salon n'était PAS chiffré, matrix-nio refuse
    # ici : on le signale au lieu de laisser le test planter, pour que les
    # vérifications en base ci-dessous s'exécutent quand même et montrent
    # le message en clair.
    salon_chiffre = envoyeur.rooms[salon].encrypted
    verifier("Salon créé avec chiffrement Megolm activé", salon_chiffre)

    if salon_chiffre and envoyeur.olm.should_share_group_session(salon):
        await envoyeur.share_group_session(salon, ignore_unverified_devices=True)
    await invite.sync(timeout=3000)

    # On installe un « écouteur » sur le client destinataire : matrix-nio
    # l'appelle à chaque message DÉCHIFFRÉ avec succès. C'est la preuve
    # que le chiffrement fonctionne dans les deux sens (si le message
    # n'était pas déchiffrable, l'écouteur ne serait jamais appelé).
    messages_recus = []

    async def a_la_reception(salon_recu, evenement):
        messages_recus.append(getattr(evenement, "body", None))

    from nio import RoomMessageText
    invite.add_event_callback(a_la_reception, RoomMessageText)

    # Envoi du message test — chiffré par matrix-nio (Olm/Megolm).
    envoi = await envoyeur.room_send(
        salon, "m.room.message",
        {"msgtype": "m.text", "body": MESSAGE_TEST},
        ignore_unverified_devices=True,
    )
    verifier("Message test envoyé", hasattr(envoi, "event_id"))

    # Plusieurs synchronisations : la première sert souvent à récupérer la
    # clé de session Megolm, le message n'est déchiffré qu'ensuite.
    for _ in range(5):
        await invite.sync(timeout=3000)
        if MESSAGE_TEST in messages_recus:
            break
        await asyncio.sleep(1)

    verifier("Le destinataire déchiffre bien le message",
             MESSAGE_TEST in messages_recus)

    for client in clients.values():
        await client.close()

    # --- Vérification côté SERVEUR : la base de données ---------------
    base = sqlite3.connect(f"{DOSSIER}/homeserver.db")
    curseur = base.cursor()

    # Garde-fou indispensable : si la base est vide, TOUTES les recherches
    # « le message est introuvable » réussissent sans rien prouver. Cela
    # arrive quand un ancien serveur répond encore sur le port et que la
    # base lue sur le disque n'est pas celle qu'il utilise.
    curseur.execute("SELECT count(*) FROM events")
    total_evenements = curseur.fetchone()[0]
    if not verifier(
        f"La base contient bien les événements du test ({total_evenements})",
        total_evenements > 0,
    ):
        print("    → base vide : les vérifications suivantes ne prouveraient rien.")
        base.close()
        return

    curseur.execute(
        "SELECT count(*) FROM event_json WHERE json LIKE ?", (f"%{MESSAGE_TEST}%",)
    )
    occurrences = curseur.fetchone()[0]
    verifier(
        f"Message test INTROUVABLE dans event_json ({occurrences} occurrence(s))",
        occurrences == 0,
    )

    curseur.execute(
        "SELECT count(*) FROM events WHERE type='m.room.message' AND room_id=?", (salon,)
    )
    en_clair = curseur.fetchone()[0]
    verifier(
        f"Aucun événement m.room.message en clair ({en_clair})",
        en_clair == 0,
    )

    curseur.execute(
        "SELECT count(*) FROM events WHERE type='m.room.encrypted' AND room_id=?", (salon,)
    )
    chiffres = curseur.fetchone()[0]
    verifier(
        f"Les messages sont stockés comme m.room.encrypted ({chiffres})",
        chiffres > 0,
    )
    base.close()

    # --- Vérification dans les JOURNAUX -------------------------------
    trouve_dans_logs = False
    for nom in ("homeserver.log", "demarrage.log"):
        chemin = f"{DOSSIER}/{nom}"
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8", errors="ignore") as f:
                if MESSAGE_TEST in f.read():
                    trouve_dans_logs = True
    verifier("Message test absent des journaux Synapse", not trouve_dans_logs)

    return salon


# =====================================================================
# ÉPREUVE 3 — « Révocation »
# =====================================================================
async def epreuve_revocation(session):
    """
    Après révocation, l'agent perd l'accès immédiatement.

    On reproduit ce que fait la Console Kibaré : appel de l'API admin de
    Synapse pour désactiver le compte. Tous les jetons d'accès de TOUS
    les appareils sont alors supprimés.
    """
    print("\n=== ÉPREUVE 3 : « Révocation » ===")

    # Il faut un compte administrateur pour appeler l'API admin.
    await creer_compte_admin(session, "demo-000", "MotDePasseAdmin000!")

    async with session.post(f"{URL}/_matrix/client/v3/login", json={
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": "demo-000"},
        "password": "MotDePasseAdmin000!",
    }) as r:
        jeton_admin = (await r.json())["access_token"]

    # Connexion de l'agent qui va être révoqué.
    async with session.post(f"{URL}/_matrix/client/v3/login", json={
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": "demo-203"},
        "password": AGENTS["demo-203"],
    }) as r:
        jeton_agent = (await r.json())["access_token"]

    entetes_agent = {"Authorization": f"Bearer {jeton_agent}"}

    # Avant révocation : le jeton fonctionne.
    async with session.get(f"{URL}/_matrix/client/v3/account/whoami",
                           headers=entetes_agent) as r:
        avant = r.status
    verifier(f"Avant révocation : le jeton de demo-203 fonctionne (HTTP {avant})",
             avant == 200)

    # Révocation — exactement l'appel que fait la Console.
    async with session.post(
        f"{URL}/_synapse/admin/v1/deactivate/@demo-203:{SERVEUR}",
        headers={"Authorization": f"Bearer {jeton_admin}"},
        json={"erase": False},
    ) as r:
        statut_revocation = r.status
        corps = await r.json()
    verifier(
        f"Révocation acceptée par Synapse (HTTP {statut_revocation}, "
        f"{corps.get('id_server_unbind_result')})",
        statut_revocation == 200,
    )

    # Après révocation : le même jeton doit être rejeté.
    async with session.get(f"{URL}/_matrix/client/v3/account/whoami",
                           headers=entetes_agent) as r:
        apres = r.status
        reponse = await r.json()
    verifier(
        f"Après révocation : jeton rejeté avec {reponse.get('errcode')} (HTTP {apres})",
        apres == 401 and reponse.get("errcode") == "M_UNKNOWN_TOKEN",
    )

    # C'est précisément M_UNKNOWN_TOKEN sans « soft_logout » qui déclenche
    # l'effacement des données sur le téléphone (section 6.4 du brief).
    verifier(
        "Erreur sans « soft_logout » → l'app effacera ses données",
        reponse.get("soft_logout") is not True,
    )

    # Et il ne doit plus pouvoir se reconnecter du tout.
    async with session.post(f"{URL}/_matrix/client/v3/login", json={
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": "demo-203"},
        "password": AGENTS["demo-203"],
    }) as r:
        reconnexion = r.status
    verifier(f"Reconnexion de demo-203 impossible (HTTP {reconnexion})",
             reconnexion == 403)


async def creer_compte_admin(session, identifiant, mot_de_passe):
    """Crée un compte administrateur de test (API d'enregistrement signée)."""
    async with session.get(f"{URL}/_synapse/admin/v1/register") as r:
        nonce = (await r.json())["nonce"]
    message = b"\x00".join([
        nonce.encode(), identifiant.encode(), mot_de_passe.encode(), b"admin",
    ])
    signature = hmac.new(SECRET_INSCRIPTION.encode(), message, hashlib.sha1).hexdigest()
    async with session.post(f"{URL}/_synapse/admin/v1/register", json={
        "nonce": nonce, "username": identifiant, "password": mot_de_passe,
        "admin": True, "mac": signature,
    }) as r:
        return r.status == 200


async def principal():
    print("=" * 62)
    print("ÉPREUVES DU JURY — Kibaré (tests automatisés)")
    print("=" * 62)

    async with aiohttp.ClientSession() as session:
        await epreuve_intrus(session)
        await epreuve_serveur_ne_lit_rien(session)
        await epreuve_revocation(session)

    print("\n" + "=" * 62)
    reussis = sum(1 for _, ok in resultats if ok)
    total = len(resultats)
    print(f"RÉSULTAT : {reussis}/{total} vérifications réussies")
    for description, ok in resultats:
        if not ok:
            print(f"  ÉCHEC : {description}")
    print("=" * 62)
    return 0 if reussis == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))
