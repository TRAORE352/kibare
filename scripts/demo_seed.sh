#!/usr/bin/env bash
# =====================================================================
# scripts/demo_seed.sh — Peuple l'environnement de démo (salons + membres)
#
# Exécute scripts/demo_seed.py À L'INTÉRIEUR du réseau Docker (via un
# conteneur jetable basé sur l'image de la Console, qui peut joindre
# synapse:8008). Le jeton du bot est sauvegardé dans secrets/.
#
# Prérequis : `docker compose up -d` et des services sains.
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f secrets/registration_shared_secret.txt ]]; then
  echo "ERREUR : lancez d'abord ./scripts/init.sh" >&2
  exit 1
fi

# Récupère un jeton bot existant (si déjà créé lors d'un précédent seed).
EXISTING_TOKEN=""
if [[ -s secrets/synapse_admin_token.txt ]]; then
  EXISTING_TOKEN="$(cat secrets/synapse_admin_token.txt)"
fi

OUTPUT="$(
  docker compose run --rm \
    -e SYNAPSE_URL=http://synapse:8008 \
    -e REGISTRATION_SHARED_SECRET="$(cat secrets/registration_shared_secret.txt)" \
    -e SYNAPSE_ADMIN_TOKEN="${EXISTING_TOKEN}" \
    -v "$REPO_ROOT/scripts/demo_seed.py:/demo_seed.py:ro" \
    --entrypoint python console /demo_seed.py
)"

echo "$OUTPUT"

# Capture du jeton bot (dernière ligne « BOT_TOKEN=... ») s'il vient d'être créé.
if echo "$OUTPUT" | grep -q '^BOT_TOKEN='; then
  echo "$OUTPUT" | grep '^BOT_TOKEN=' | cut -d= -f2- > secrets/synapse_admin_token.txt
  chmod 600 secrets/synapse_admin_token.txt
  echo "[OK] jeton bot sauvegardé dans secrets/synapse_admin_token.txt"
fi

echo
echo "Seed terminé. Les salons et membres de démo sont en place."
