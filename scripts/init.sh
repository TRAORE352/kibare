#!/usr/bin/env bash
# =====================================================================
# scripts/init.sh — initialisation UNIQUE de la plateforme Kibaré
#
# Génère :
#   1. les secrets de démo (secrets/ — jamais versionnés) ;
#   2. la CA locale « Kibaré CA (DÉMO) » et le certificat serveur signé ;
#   3. synapse/homeserver.yaml   (depuis homeserver.yaml.template) ;
#   4. keycloak/realm-kibare.json (depuis realm-kibare.json.template) ;
#   5. le fichier .env (adresse du serveur, lu par docker compose).
#
# À lancer UNE SEULE FOIS avant `docker compose up -d`.
# Sans Internet : tout est généré localement avec openssl.
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="$REPO_ROOT/secrets"
CADDY_DIR="$REPO_ROOT/caddy"
SYNAPSE_DIR="$REPO_ROOT/synapse"
KEYCLOAK_DIR="$REPO_ROOT/keycloak"

log_info() { echo "[INFO] $*"; }
log_ok()   { echo "[OK]   $*"; }
log_warn() { echo "[WARN] $*"; }
log_err()  { echo "[ERR]  $*" >&2; }

# ---------------------------------------------------------------------
# Adresse IP du serveur sur le réseau local.
#
# C'est LA valeur la plus critique de toute l'installation : elle est écrite
# dans le certificat du serveur, dans public_baseurl de Synapse et dans les
# adresses de redirection de Keycloak. Une valeur erronée ne provoque aucune
# erreur au démarrage : les services tournent, mais le téléphone reçoit une
# adresse injoignable et l'écran de connexion reste BLANC, sans message.
#
# Une version précédente de ce script utilisait une adresse d'exemple par
# défaut (192.168.10.10). Qui oubliait de définir la variable obtenait une
# plateforme silencieusement inutilisable. On détecte donc l'adresse, on
# l'affiche, et on exige une confirmation.
# ---------------------------------------------------------------------
detecter_adresse() {
    # Adresse de l'interface qui porte la route par défaut : celle par
    # laquelle les téléphones du réseau local joindront ce PC.
    ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K[0-9.]+' && return 0
    hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^127\.' | head -1 && return 0
    return 1
}

if [ -n "${KIBARE_SERVER_ADDRESS:-}" ]; then
    log_info "Adresse fournie par la variable KIBARE_SERVER_ADDRESS."
else
    KIBARE_SERVER_ADDRESS="$(detecter_adresse || true)"
    if [ -z "$KIBARE_SERVER_ADDRESS" ]; then
        log_err "Impossible de détecter l'adresse IP de ce PC sur le réseau local."
        log_err "Relancez en l'indiquant vous-même :"
        log_err "    KIBARE_SERVER_ADDRESS=192.168.1.42 ./scripts/init.sh"
        exit 1
    fi
    log_info "Adresse détectée automatiquement : ${KIBARE_SERVER_ADDRESS}"
fi

# Contrôle de forme : une IPv4 et rien d'autre.
if ! echo "$KIBARE_SERVER_ADDRESS" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
    log_err "« ${KIBARE_SERVER_ADDRESS} » n'est pas une adresse IPv4 valide."
    exit 1
fi

echo
echo "  ┌──────────────────────────────────────────────────────────┐"
printf "  │  Adresse du serveur Kibaré : %-27s │\n" "$KIBARE_SERVER_ADDRESS"
echo "  └──────────────────────────────────────────────────────────┘"
echo
echo "  Cette adresse sera inscrite dans le certificat du serveur et dans"
echo "  toute la configuration. Les téléphones devront l'utiliser telle"
echo "  quelle. Si elle est fausse, l'écran de connexion restera blanc."
echo
if [ -t 0 ] && [ "${KIBARE_CONFIRMATION_AUTO:-0}" != "1" ]; then
    printf "  Est-elle correcte ? [o/N] "
    read -r reponse
    case "$reponse" in
        o|O|oui|OUI|y|Y|yes) ;;
        *)
            log_err "Initialisation annulée. Relancez avec la bonne adresse :"
            log_err "    KIBARE_SERVER_ADDRESS=<votre-ip> ./scripts/init.sh"
            exit 1
            ;;
    esac
fi

log_info "=== Initialisation de Kibaré ==="
log_info "Adresse du serveur : ${KIBARE_SERVER_ADDRESS}"

mkdir -p "$SECRETS_DIR" "$CADDY_DIR"

# ---------------------------------------------------------------------
# 1. Secrets de démo (hex : aucun caractère spécial, sûr pour sed)
# ---------------------------------------------------------------------
log_info "Génération des secrets de démo..."
gen_secret() { openssl rand -hex 32; }

SECRET_NAMES=(
  postgres_password
  keycloak_db_password
  keycloak_admin_password
  console_db_password
  oidc_client_secret
  console_client_secret
  synapse_admin_token
  registration_shared_secret
)
for name in "${SECRET_NAMES[@]}"; do
  if [[ ! -s "$SECRETS_DIR/$name.txt" ]]; then
    gen_secret > "$SECRETS_DIR/$name.txt"
    log_ok "secret '$name' généré"
  else
    log_warn "secret '$name' déjà présent, conservé"
  fi
done

# ---------------------------------------------------------------------
# 2. Autorité de certification locale « Kibaré CA (DÉMO) »
# ---------------------------------------------------------------------
CA_KEY="$CADDY_DIR/kibare-ca.key"
CA_CRT="$CADDY_DIR/kibare-ca.crt"

if [[ ! -f "$CA_KEY" || ! -f "$CA_CRT" ]]; then
  log_info "Génération de la CA locale 'Kibaré CA (DÉMO)'..."
  openssl genrsa -out "$CA_KEY" 4096 2>/dev/null
  openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days 3650 \
    -out "$CA_CRT" \
    -subj "/CN=Kibaré CA (DÉMO)/O=Kibaré/OU=Hackathon 226" 2>/dev/null
  log_ok "CA locale générée"
else
  log_warn "CA locale déjà présente, conservée"
fi

# ---------------------------------------------------------------------
# 3. Certificat serveur signé par la CA locale (SAN : IP + DNS locaux)
# ---------------------------------------------------------------------
SERVER_KEY="$CADDY_DIR/kibare-server.key"
SERVER_CRT="$CADDY_DIR/kibare-server.crt"
SERVER_CONF="$CADDY_DIR/server.cnf"

cat > "$SERVER_CONF" <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = ${KIBARE_SERVER_ADDRESS}

[v3_req]
# digitalSignature : requis pour le handshake TLS moderne (ECDHE/DHE)
# keyEncipherment : pour l'échange de clé RSA (compatibilité)
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
IP.1 = ${KIBARE_SERVER_ADDRESS}
DNS.1 = kibare.test
DNS.2 = kibare.lan
DNS.3 = localhost
EOF

if [[ ! -f "$SERVER_KEY" || ! -f "$SERVER_CRT" ]]; then
  log_info "Génération du certificat serveur pour ${KIBARE_SERVER_ADDRESS}..."
  openssl genrsa -out "$SERVER_KEY" 4096 2>/dev/null
  openssl req -new -key "$SERVER_KEY" -out "$CADDY_DIR/kibare-server.csr" \
    -config "$SERVER_CONF" 2>/dev/null
  openssl x509 -req -in "$CADDY_DIR/kibare-server.csr" \
    -CA "$CA_CRT" -CAkey "$CA_KEY" -CAcreateserial \
    -out "$SERVER_CRT" -days 825 -sha256 \
    -extensions v3_req -extfile "$SERVER_CONF" 2>/dev/null
  rm -f "$CADDY_DIR/kibare-server.csr"
  log_ok "certificat serveur généré"
else
  log_warn "certificat serveur déjà présent, conservé"
fi
rm -f "$SERVER_CONF"

# ---------------------------------------------------------------------
# 4. homeserver.yaml depuis le modèle (injection des secrets)
# ---------------------------------------------------------------------
log_info "Génération de synapse/homeserver.yaml..."
sed \
  -e "s|__POSTGRES_PASSWORD__|$(cat "$SECRETS_DIR/postgres_password.txt")|" \
  -e "s|__REGISTRATION_SHARED_SECRET__|$(cat "$SECRETS_DIR/registration_shared_secret.txt")|" \
  -e "s|__KIBARE_ADDRESS__|${KIBARE_SERVER_ADDRESS}|g" \
  "$SYNAPSE_DIR/homeserver.yaml.template" > "$SYNAPSE_DIR/homeserver.yaml"
log_ok "homeserver.yaml généré"

# ---------------------------------------------------------------------
# 5. realm-kibare.json depuis le modèle (injection adresse + secrets)
# ---------------------------------------------------------------------
log_info "Génération de keycloak/realm-kibare.json..."
sed \
  -e "s|__KIBARE_ADDRESS__|${KIBARE_SERVER_ADDRESS}|g" \
  -e "s|__SYNAPSE_OIDC_SECRET__|$(cat "$SECRETS_DIR/oidc_client_secret.txt")|" \
  -e "s|__CONSOLE_OIDC_SECRET__|$(cat "$SECRETS_DIR/console_client_secret.txt")|" \
  "$KEYCLOAK_DIR/realm-kibare.json.template" > "$KEYCLOAK_DIR/realm-kibare.json"
log_ok "realm-kibare.json généré"

# ---------------------------------------------------------------------
# 6. .env (lu automatiquement par docker compose)
# ---------------------------------------------------------------------
cat > "$REPO_ROOT/.env" <<EOF
# Généré par scripts/init.sh — ne pas versionner
KIBARE_SERVER_ADDRESS=${KIBARE_SERVER_ADDRESS}
# Mots de passe Keycloak (lus par docker compose via \${VAR})
KEYCLOAK_ADMIN_PASSWORD=$(cat "$SECRETS_DIR/keycloak_admin_password.txt")
KEYCLOAK_DB_PASSWORD=$(cat "$SECRETS_DIR/keycloak_db_password.txt")
EOF

chmod 600 "$REPO_ROOT/.env"
chmod 600 "$SECRETS_DIR"/*.txt

echo
log_ok "=== Initialisation terminée ==="
echo
echo "Étapes suivantes :"
echo "  1. docker compose up -d"
echo "  2. Attendre que les services soient sains (docker compose ps)"
echo "  3. Peupler la démo : ./scripts/demo_seed.sh"
echo "  4. Vérifier : ./scripts/verif_serveur_ne_lit_rien.sh"
