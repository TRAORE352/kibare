#!/bin/bash
# =====================================================================
# scripts/init-postgres.sh — exécuté au PREMIER démarrage du conteneur
# PostgreSQL (monté dans /docker-entrypoint-initdb.d/).
#
# Crée :
#   - la base « synapse »  (locale C, exigée par Synapse) ;
#   - l'utilisateur + la base « keycloak » ;
#   - l'utilisateur « console » + la base « kibare_console ».
#
# Les mots de passe sont lus depuis les secrets Docker (jamais en dur).
# =====================================================================
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Base Synapse : locale C obligatoire (Synapse refuse une locale non-C)
    CREATE DATABASE synapse
        ENCODING 'UTF8'
        LC_COLLATE 'C'
        LC_CTYPE 'C'
        TEMPLATE template0;

    -- Base + utilisateur Keycloak
    CREATE USER keycloak WITH PASSWORD '$(cat /run/secrets/keycloak_db_password)';
    CREATE DATABASE keycloak OWNER keycloak;

    -- Base + utilisateur Console
    CREATE USER console WITH PASSWORD '$(cat /run/secrets/console_db_password)';
    CREATE DATABASE kibare_console OWNER console;
EOSQL

echo "[init-postgres] Bases synapse, keycloak et kibare_console créées."
