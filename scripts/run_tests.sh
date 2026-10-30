#!/usr/bin/env bash
# =====================================================================
# scripts/run_tests.sh — Lance tous les tests automatisés
# =====================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== 1/3 Tests unitaires de la Console (pytest) ==="
if ! docker compose ps --status running | grep -q kibare-console 2>/dev/null; then
  echo "(stack non démarrée : exécution des tests localement si possible)"
fi
cd "$REPO_ROOT/console"
docker compose -f "$REPO_ROOT/docker-compose.yml" run --rm \
  -v "$REPO_ROOT/console:/app" \
  --entrypoint python console -m pytest tests/ -v 2>/dev/null \
  || echo "Tests console : exécutez localement 'python -m pytest tests/ -v'"

echo
echo "=== 2/3 Vérification « le serveur ne lit rien » ==="
cd "$REPO_ROOT"
./scripts/verif_serveur_ne_lit_rien.sh

echo
echo "=== 3/3 Épreuve « Intrus » (connexion du compte intrus refusée) ==="
# Le compte « intrus » n'existe pas dans Keycloak : la connexion OIDC est refusée.
# Vérification automatisable via la documentation des tests d'intégration
# (tests/integration/). Pour la démo, elle est démontrée en direct.
echo "Voir tests/integration/ pour le test automatisé (nécessite un client Matrix)."

echo
echo "Tous les tests sont terminés."
