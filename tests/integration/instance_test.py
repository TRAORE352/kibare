#!/usr/bin/env python3
# =====================================================================
# tests/integration/instance_test.py — Instance Synapse de TEST
#
# Pourquoi ce fichier
# -------------------
# En production, Kibaré se connecte UNIQUEMENT via Keycloak (OIDC) :
# `password_config.enabled: false`. C'est voulu (section 5.3 du brief) :
# sans cela, un mot de passe Synapse permettrait de contourner l'enrôlement
# et l'OTP.
#
# Mais les clients Matrix de test (matrix-nio) se connectent par mot de
# passe : ils ne savent pas dérouler un flux OIDC qui demande un navigateur.
#
# Ce script fabrique donc une instance de test SÉPARÉE, qui reprend la
# configuration de production à UNE exception près : la connexion par mot de
# passe y est autorisée, pour que deux clients de test puissent se connecter.
#
# Ce qui reste STRICTEMENT identique à la production :
#   - chiffrement de bout en bout imposé pour tous les salons ;
#   - aperçus de liens coupés, fédération coupée, statistiques coupées ;
#   - inscription libre désactivée.
#
# La configuration de production, elle, n'est jamais modifiée.
# =====================================================================

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER = "/tmp/kibare-synapse-test"
PORT = 8009
URL = f"http://localhost:{PORT}"
SERVER_NAME = "kibare.test"

# Secret de TEST uniquement : cette instance est jetable, elle ne contient
# aucune donnée réelle et n'est jamais exposée sur le réseau.
SECRET_INSCRIPTION = "secret-de-test-jetable-kibare"

CONFIG = f"""
server_name: "{SERVER_NAME}"
pid_file: {DOSSIER}/homeserver.pid
public_baseurl: {URL}/

listeners:
  - port: {PORT}
    tls: false
    type: http
    x_forwarded: true
    bind_addresses: ['127.0.0.1']
    resources:
      - names: [client]
        compress: false

database:
  name: sqlite3
  args:
    database: {DOSSIER}/homeserver.db

log_config: "{DOSSIER}/log.config"
media_store_path: {DOSSIER}/media_store
signing_key_path: "{DOSSIER}/signing.key"

# --- Identique à la production ---------------------------------------
enable_registration: false
registration_shared_secret: "{SECRET_INSCRIPTION}"
encryption_enabled_by_default_for_room_type: all
url_preview_enabled: false
federation_domain_whitelist: []
report_stats: false
trusted_key_servers: []
presence:
  enabled: false

# --- SEULE différence avec la production -----------------------------
# Connexion par mot de passe autorisée, pour que les clients de test
# puissent se connecter sans navigateur. En production cette valeur est
# `false` et la connexion passe obligatoirement par Keycloak + OTP.
password_config:
  enabled: true

# Limites de débit relevées POUR LE TEST UNIQUEMENT.
# Sans cela, le test se bloque lui-même : il enchaîne plusieurs connexions
# en quelques secondes, déclenche la protection anti-force-brute de Synapse,
# reçoit un HTTP 429 (« trop de requêtes ») et interprète à tort ce refus
# comme un échec du produit. La protection reste ACTIVE en production :
# c'est une exigence du brief (section 5.3).
rc_login:
  address:
    per_second: 1000
    burst_count: 1000
  account:
    per_second: 1000
    burst_count: 1000
  failed_attempts:
    per_second: 1000
    burst_count: 1000
"""

LOG_CONFIG = f"""
version: 1
formatters:
  precise:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  file:
    class: logging.FileHandler
    formatter: precise
    filename: {DOSSIER}/homeserver.log
loggers:
  synapse:
    level: INFO
root:
  level: INFO
  handlers: [file]
disable_existing_loggers: false
"""


def liberer_port():
    """
    Tue tout Synapse de test qui occuperait encore le port.

    Sans cela, un serveur lancé précédemment continue de répondre sur le
    port : le nouveau processus ne démarre pas, mais le script croit que
    tout va bien puisque « quelque chose » répond. Les tests interrogent
    alors l'ANCIENNE instance, dont le fichier de base a été supprimé —
    la base lue sur le disque est vide, et les vérifications « aucun
    message en clair » passent au vert sans rien prouver.
    """
    subprocess.run(
        ["pkill", "-f", f"synapse.app.homeserver.*{os.path.basename(DOSSIER)}"],
        capture_output=True,
    )
    # On attend que le port soit réellement libéré.
    import socket
    for _ in range(20):
        prise = socket.socket()
        try:
            prise.bind(("127.0.0.1", PORT))
            prise.close()
            return
        except OSError:
            time.sleep(0.5)
        finally:
            prise.close()
    print(f"Le port {PORT} reste occupé : arrêtez le processus manuellement.")
    sys.exit(1)


def preparer():
    """Crée un dossier d'instance propre et y écrit la configuration."""
    liberer_port()
    if os.path.exists(DOSSIER):
        shutil.rmtree(DOSSIER)
    os.makedirs(f"{DOSSIER}/media_store", exist_ok=True)

    with open(f"{DOSSIER}/homeserver.yaml", "w", encoding="utf-8") as f:
        f.write(CONFIG)
    with open(f"{DOSSIER}/log.config", "w", encoding="utf-8") as f:
        f.write(LOG_CONFIG)

    # Génère la clé de signature du serveur (Synapse le fait lui-même).
    subprocess.run(
        [sys.executable, "-m", "synapse.app.homeserver",
         "--config-path", f"{DOSSIER}/homeserver.yaml",
         "--generate-keys"],
        check=True, capture_output=True,
    )
    print(f"Instance de test préparée dans {DOSSIER}")


def demarrer():
    """Démarre Synapse en arrière-plan et attend qu'il réponde."""
    journal = open(f"{DOSSIER}/demarrage.log", "w", encoding="utf-8")
    processus = subprocess.Popen(
        [sys.executable, "-m", "synapse.app.homeserver",
         "--config-path", f"{DOSSIER}/homeserver.yaml"],
        stdout=journal, stderr=subprocess.STDOUT,
    )

    # On attend que le serveur réponde VRAIMENT, au lieu d'un sleep fixe :
    # une attente fixe réussit sur une machine rapide et échoue ailleurs.
    for _ in range(60):
        if processus.poll() is not None:
            print("Synapse s'est arrêté au démarrage. Journal :")
            print(open(f"{DOSSIER}/demarrage.log", encoding="utf-8").read()[-2000:])
            sys.exit(1)
        try:
            with urllib.request.urlopen(f"{URL}/_matrix/client/versions", timeout=2):
                print(f"Synapse de test démarré sur {URL} (PID {processus.pid})")
                return processus
        except (urllib.error.URLError, OSError):
            time.sleep(1)

    processus.kill()
    print("Synapse n'a pas répondu dans le délai imparti.")
    sys.exit(1)


if __name__ == "__main__":
    preparer()
    p = demarrer()
    print(f"PID={p.pid}")
    with open(f"{DOSSIER}/pid", "w", encoding="utf-8") as f:
        f.write(str(p.pid))
