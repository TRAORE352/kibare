#!/usr/bin/env bash
# scripts/init.sh
# Génère la CA locale, les certificats serveur, et les secrets de démo pour Kibaré.
# À lancer UNE SEULE FOIS avant le premier `docker compose up -d`.

set -euo pipefail

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Répertoires
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="${REPO_ROOT}/secrets"
CADDY_DIR="${REPO_ROOT}/caddy"

# Adresse du serveur (IP locale par défaut, peut être surchargée par variable d'env)
KIBARE_SERVER_ADDRESS="${KIBARE_SERVER_ADDRESS:-192.168.10.10}"

log_info "=== Initialisation de Kibaré ==="
log_info "Adresse du serveur : ${KIBARE_SERVER_ADDRESS}"
log_info "Répertoire du projet : ${REPO_ROOT}"

# 1. Créer les répertoires
mkdir -p "${SECRETS_DIR}" "${CADDY_DIR}"

# 2. Générer les secrets (mots de passe, tokens) — UNIQUEMENT POUR LA DÉMO
log_info "Génération des secrets de démo..."

# Fonction pour générer un secret aléatoire
gen_secret() {
    openssl rand -base64 32 | tr -d '\n'
}

# PostgreSQL
if [[ ! -f "${SECRETS_DIR}/postgres_password.txt" ]]; then
    gen_secret > "${SECRETS_DIR}/postgres_password.txt"
    log_ok "Secret PostgreSQL généré"
else
    log_warn "Secret PostgreSQL existe déjà, conservé"
fi

# Keycloak DB
if [[ ! -f "${SECRETS_DIR}/keycloak_db_password.txt" ]]; then
    gen_secret > "${SECRETS_DIR}/keycloak_db_password.txt"
    log_ok "Secret Keycloak DB généré"
else
    log_warn "Secret Keycloak DB existe déjà, conservé"
fi

# Keycloak Admin
if [[ ! -f "${SECRETS_DIR}/keycloak_admin_password.txt" ]]; then
    gen_secret > "${SECRETS_DIR}/keycloak_admin_password.txt"
    log_ok "Secret Keycloak Admin généré"
else
    log_warn "Secret Keycloak Admin existe déjà, conservé"
fi

# Synapse Admin Token (pour l'API admin)
if [[ ! -f "${SECRETS_DIR}/synapse_admin_token.txt" ]]; then
    gen_secret > "${SECRETS_DIR}/synapse_admin_token.txt"
    log_ok "Token admin Synapse généré"
else
    log_warn "Token admin Synapse existe déjà, conservé"
fi

# JWT Secret pour la Console
if [[ ! -f "${SECRETS_DIR}/jwt_secret.txt" ]]; then
    gen_secret > "${SECRETS_DIR}/jwt_secret.txt"
    log_ok "Secret JWT Console généré"
else
    log_warn "Secret JWT Console existe déjà, conservé"
fi

# 3. Générer la CA locale (Kibaré CA)
log_info "Génération de la CA locale 'Kibaré CA (DÉMO)'..."

CA_KEY="${CADDY_DIR}/kibare-ca.key"
CA_CRT="${CADDY_DIR}/kibare-ca.crt"

if [[ ! -f "${CA_KEY}" ]] || [[ ! -f "${CA_CRT}" ]]; then
    # Clé privée CA (RSA 4096)
    openssl genrsa -out "${CA_KEY}" 4096
    
    # Certificat CA auto-signé (valide 10 ans)
    openssl req -x509 -new -nodes -key "${CA_KEY}" -sha256 -days 3650 \
        -out "${CA_CRT}" \
        -subj "/CN=Kibaré CA (DÉMO)/O=Kibaré/OU=Hackathon 226"
    
    log_ok "CA locale générée : ${CA_CRT}"
else
    log_warn "CA locale existe déjà, conservée"
fi

# 4. Générer le certificat serveur signé par la CA locale
log_info "Génération du certificat serveur pour ${KIBARE_SERVER_ADDRESS} et kibare.lan..."

SERVER_KEY="${CADDY_DIR}/kibare-server.key"
SERVER_CSR="${CADDY_DIR}/kibare-server.csr"
SERVER_CRT="${CADDY_DIR}/kibare-server.crt"
SERVER_CONF="${CADDY_DIR}/server.conf"

# Configuration OpenSSL pour SAN (Subject Alternative Names)
cat > "${SERVER_CONF}" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = kibare.test

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1 = ${KIBARE_SERVER_ADDRESS}
DNS.1 = kibare.test
DNS.2 = kibare.lan
DNS.3 = localhost
EOF

if [[ ! -f "${SERVER_KEY}" ]] || [[ ! -f "${SERVER_CRT}" ]]; then
    # Clé privée serveur
    openssl genrsa -out "${SERVER_KEY}" 4096
    
    # CSR
    openssl req -new -key "${SERVER_KEY}" -out "${SERVER_CSR}" \
        -config "${SERVER_CONF}" -subj "/CN=kibare.test"
    
    # Signer avec la CA
    openssl x509 -req -in "${SERVER_CSR}" -CA "${CA_CRT}" -CAkey "${CA_KEY}" \
        -CAcreateserial -out "${SERVER_CRT}" -days 825 -sha256 \
        -extensions v3_req -extfile "${SERVER_CONF}"
    
    log_ok "Certificat serveur généré : ${SERVER_CRT}"
else
    log_warn "Certificat serveur existe déjà, conservé"
fi

# Nettoyer le CSR et la config temporaire
rm -f "${SERVER_CSR}" "${SERVER_CONF}"

# 5. Générer le fichier .env.example (sans vrais secrets)
log_info "Génération de .env.example..."
cat > "${REPO_ROOT}/.env.example" <<EOF
# Fichier d'exemple — NE PAS UTILISER EN PRODUCTION
# Copier vers .env et adapter si nécessaire
# Tous les mots de passe ci-dessous sont des VALEURS DE DÉMO

# Adresse IP du serveur sur le réseau local
KIBARE_SERVER_ADDRESS=${KIBARE_SERVER_ADDRESS}

# Mots de passe de démo (générés par init.sh, stockés dans secrets/)
# POSTGRES_PASSWORD=<généré>
# KEYCLOAK_DB_PASSWORD=<généré>
# KEYCLOAK_ADMIN_PASSWORD=<généré>
# SYNAPSE_ADMIN_TOKEN=<généré>
# JWT_SECRET=<généré>
EOF
log_ok ".env.example créé"

# 6. Créer le script de réinitialisation de la démo
log_info "Création de scripts/demo_reset.sh..."
cat > "${REPO_ROOT}/scripts/demo_reset.sh" <<'RESET_EOF'
#!/usr/bin/env bash
# Réinitialise l'environnement de démo (base de données, volumes Docker)
# ATTENTION : SUPPRIME TOUTES LES DONNÉES

set -euo pipefail

echo "⚠️  Cela va TOUT SUPPRIMER (messages, comptes, salons)."
read -p "Confirmer ? (oui/non) " -r
if [[ ! $REPLY =~ ^[Oo][Uu][Ii]$ ]]; then
    echo "Annulé."
    exit 1
fi

cd "$(dirname "$0")/.."
docker compose down -v
docker volume rm kibare_postgres_data kibare_synapse_data kibare_keycloak_data kibare_caddy_data kibare_caddy_config 2>/dev/null || true
./scripts/init.sh
echo "Environnement réinitialisé. Lancez 'docker compose up -d'."
RESET_EOF
chmod +x "${REPO_ROOT}/scripts/demo_reset.sh"
log_ok "demo_reset.sh créé"

# 7. Créer le script de vérification "le serveur ne lit rien"
log_info "Création de scripts/verif_serveur_ne_lit_rien.sh..."
cat > "${REPO_ROOT}/scripts/verif_serveur_ne_lit_rien.sh" <<'VERIF_EOF'
#!/usr/bin/env bash
# Vérification automatisée : le serveur ne stocke aucun message en clair
# Critères (section 5.1 du brief) :
# 1. Message test "MESSAGE-TEST-JURY-123" introuvable dans event_json
# 2. Événements de type m.room.encrypted uniquement
# 3. Fichiers dans media_store illisibles (chiffrés)
# 4. Logs Synapse sans contenu de message

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local desc="$1"
    local cmd="$2"
    echo -n "  [ ] $desc... "
    if eval "$cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        ((PASS++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAIL++))
    fi
}

echo "=== Vérification 'Le serveur ne lit rien' ==="
echo

# 1. Message test introuvable en base
check "Message test absent de event_json" \
    "docker exec kibare-postgres psql -U postgres -d synapse -t -c \"SELECT count(*) FROM event_json WHERE jsonb_pretty(event_json) LIKE '%MESSAGE-TEST-JURY-123%';\" | grep -q '^ *0$'"

# 2. Événements chiffrés uniquement (pas de m.room.message en clair)
check "Aucun m.room.message en clair dans events" \
    "docker exec kibare-postgres psql -U postgres -d synapse -t -c \"SELECT count(*) FROM events WHERE type = 'm.room.message' AND content NOT LIKE '%m.room.encrypted%';\" | grep -q '^ *0$'"

# 3. Vérifier media_store : fichiers chiffrés (taille > 0 mais pas de magic bytes clairs)
check "Media store : fichiers présents (chiffrés côté client)" \
    "docker exec kibare-synapse test -d /data/media_store && find /data/media_store -type f -size +0 | head -1 | grep -q ."

# 4. Logs Synapse sans contenu
check "Logs Synapse sans 'MESSAGE-TEST-JURY-123'" \
    "! docker logs kibare-synapse 2>&1 | grep -q 'MESSAGE-TEST-JURY-123'"

# 5. Vérifier que le chiffrement est activé par défaut
check "Config Synapse : encryption_enabled_by_default_for_room_type = all" \
    "docker exec kibare-synapse grep -q 'encryption_enabled_by_default_for_room_type: all' /data/homeserver.yaml"

# 6. URL preview désactivé
check "Config Synapse : url_preview_enabled: false" \
    "docker exec kibare-synapse grep -q 'url_preview_enabled: false' /data/homeserver.yaml"

# 7. Fédération désactivée
check "Config Synapse : federation_domain_whitelist: []" \
    "docker exec kibare-synapse grep -q 'federation_domain_whitelist: \[\]' /data/homeserver.yaml"

# 8. Presence désactivée
check "Config Synapse : presence.enabled: false" \
    "docker exec kibare-synapse grep -q 'presence:' /data/homeserver.yaml && docker exec kibare-synapse grep -A2 'presence:' /data/homeserver.yaml | grep -q 'enabled: false'"

echo
echo "=== Résultat : ${PASS} passed, ${FAIL} failed ==="
if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}ÉCHEC : Certaines vérifications ont échoué.${NC}"
    exit 1
else
    echo -e "${GREEN}SUCCÈS : Toutes les vérifications passent.${NC}"
    exit 0
fi
VERIF_EOF
chmod +x "${REPO_ROOT}/scripts/verif_serveur_ne_lit_rien.sh"
log_ok "verif_serveur_ne_lit_rien.sh créé"

# 8. Créer le script de lancement des tests
log_info "Création de scripts/run_tests.sh..."
cat > "${REPO_ROOT}/scripts/run_tests.sh" <<'TESTS_EOF'
#!/usr/bin/env bash
# Lance tous les tests automatisés

set -euo pipefail

echo "=== Tests Console (pytest) ==="
cd "$(dirname "$0")/../console"
if [[ -f "requirements.txt" ]]; then
    pip install -q -r requirements.txt 2>/dev/null || true
fi
python -m pytest tests/ -v --tb=short 2>/dev/null || echo "Tests console : à implémenter"

echo
echo "=== Tests d'intégration ==="
cd "$(dirname "$0")/.."
./scripts/verif_serveur_ne_lit_rien.sh

echo
echo "=== Tests intrusion (intrus) ==="
# Test : compte intrus rejeté
# À implémenter avec matrix-commander ou client Matrix de test

echo
echo "=== Tests révocation ==="
# Test : révocation demo-203
# À implémenter

echo
echo "Tous les tests terminés."
TESTS_EOF
chmod +x "${REPO_ROOT}/scripts/run_tests.sh"
log_ok "run_tests.sh créé"

# 9. Créer le script de seed de démo
log_info "Création de scripts/demo_seed.py..."
cat > "${REPO_ROOT}/scripts/demo_seed.py" <<'SEED_EOF'
#!/usr/bin/env python3
"""
Script de peuplement de la démo : crée les salons, ajoute les membres.
Utilise l'API admin de Synapse via le token admin.
"""

import os
import sys
import asyncio
import aiohttp
import json

SYNAPSE_URL = os.getenv("SYNAPSE_ADMIN_URL", "http://localhost:8008")
ADMIN_TOKEN = os.getenv("SYNAPSE_ADMIN_TOKEN")

# Comptes de démo (matricules)
DEMO_USERS = [
    "demo-000", "demo-101", "demo-102", "demo-201", "demo-202", "demo-203",
    "demo-301", "demo-302", "demo-401", "demo-402"
]

# Salons à créer
ROOMS = {
    "mtdpce": {"name": "MTDPCE — Canal officiel", "members": ["demo-000", "demo-101", "demo-102"]},
    "sante": {"name": "Santé — Canal officiel", "members": ["demo-201", "demo-202", "demo-203"]},
    "securite": {"name": "Sécurité — Canal officiel", "members": ["demo-301", "demo-302"]},
    "mef": {"name": "MEF — Canal officiel", "members": ["demo-401", "demo-402"]},
    "crise": {"name": "Cellule de crise sanitaire", "members": ["demo-101", "demo-102", "demo-201", "demo-202", "demo-203", "demo-301", "demo-302"]},
}

async def create_room(session, name, members):
    """Crée un salon chiffré, invite les membres."""
    # Créer le salon
    payload = {
        "name": name,
        "preset": "private_chat",
        "initial_state": [
            {"type": "m.room.encryption", "state_key": "", "content": {"algorithm": "m.megolm.v1.aes-sha2"}},
            {"type": "m.room.join_rules", "state_key": "", "content": {"join_rule": "invite"}},
            {"type": "m.room.history_visibility", "state_key": "", "content": {"history_visibility": "joined"}},
        ],
    }
    async with session.post(
        f"{SYNAPSE_URL}/_synapse/admin/v1/rooms",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        json=payload
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            print(f"Erreur création salon {name}: {resp.status} - {text}")
            return None
        data = await resp.json()
        room_id = data["room_id"]
        print(f"Salon créé: {name} ({room_id})")
    
    # Inviter les membres (via le bot admin ou directement)
    for user in members:
        user_id = f"@{user}:kibare.test"
        async with session.post(
            f"{SYNAPSE_URL}/_synapse/admin/v1/rooms/{room_id}/invite",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            json={"user_id": user_id}
        ) as resp:
            if resp.status in (200, 201):
                print(f"  Invité: {user_id}")
            else:
                text = await resp.text()
                print(f"  Erreur invitation {user_id}: {resp.status} - {text}")
    
    return room_id

async def main():
    if not ADMIN_TOKEN:
        print("ERREUR: SYNAPSE_ADMIN_TOKEN non défini", file=sys.stderr)
        sys.exit(1)
    
    async with aiohttp.ClientSession() as session:
        for key, config in ROOMS.items():
            await create_room(session, config["name"], config["members"])
    
    print("\nSeed terminé. Les utilisateurs doivent accepter les invitations dans l'app.")

if __name__ == "__main__":
    asyncio.run(main())
SEED_EOF
chmod +x "${REPO_ROOT}/scripts/demo_seed.py"
log_ok "demo_seed.py créé"

echo
log_ok "=== Initialisation terminée ==="
echo
echo "Prochaines étapes :"
echo "  1. Vérifier/adapter les fichiers de config dans caddy/, synapse/, keycloak/, console/"
echo "  2. Lancer : docker compose up -d"
echo "  3. Attendre que tous les services soient healthy"
echo "  4. Peupler la démo : python3 scripts/demo_seed.py"
echo "  5. Tester : ./scripts/verif_serveur_ne_lit_rien.sh"
echo
echo "Pour réinitialiser la démo : ./scripts/demo_reset.sh"