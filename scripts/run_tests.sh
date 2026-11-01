#!/usr/bin/env bash
# =====================================================================
# scripts/run_tests.sh — Lance tous les tests automatisés (section 12)
#
#   1. Tests unitaires de la Console (pytest)
#   2. Épreuves du jury automatisées (intrus / serveur ne lit rien /
#      révocation), contre une instance Synapse de test
#   3. Vérification « le serveur ne lit rien » sur la plateforme Docker,
#      si elle est démarrée
# =====================================================================
set -uo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ECHECS=0

titre() { echo; echo "=== $* ==="; }

# ---------------------------------------------------------------------
titre "1/3 Tests unitaires de la Console (pytest)"
cd "$RACINE/console"
if python3 -c "import pytest, sqlalchemy" 2>/dev/null; then
  if ! python3 -m pytest tests/ -q; then
    ECHECS=$((ECHECS + 1))
  fi
else
  echo "Dépendances absentes. Installez-les avec :"
  echo "    pip install -r console/requirements.txt pytest"
  ECHECS=$((ECHECS + 1))
fi

# ---------------------------------------------------------------------
titre "2/3 Épreuves du jury (intrus / serveur ne lit rien / révocation)"
cd "$RACINE"
if python3 -c "import nio, olm, synapse" 2>/dev/null; then
  # Instance de test jetable : la production est OIDC-seulement, donc
  # inaccessible à un client automatisé (voir tests/integration/README.md).
  python3 tests/integration/instance_test.py || ECHECS=$((ECHECS + 1))
  python3 tests/integration/test_epreuves_jury.py || ECHECS=$((ECHECS + 1))
else
  echo "Dépendances absentes. Installez-les avec :"
  echo "    apt-get install -y libolm-dev"
  echo "    pip install matrix-synapse 'matrix-nio[e2e]' aiohttp"
  echo "(ignoré)"
fi

# ---------------------------------------------------------------------
titre "3/3 « Le serveur ne lit rien » sur la plateforme Docker"
if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' 2>/dev/null | grep -q kibare-synapse; then
  ./scripts/verif_serveur_ne_lit_rien.sh || ECHECS=$((ECHECS + 1))
else
  echo "Plateforme Docker non démarrée (lancez 'docker compose up -d')."
  echo "L'épreuve équivalente a déjà été exécutée à l'étape 2."
fi

# ---------------------------------------------------------------------
echo
if [[ $ECHECS -eq 0 ]]; then
  echo "Tous les tests sont passés."
  exit 0
fi
echo "ÉCHEC : $ECHECS série(s) de tests en erreur."
exit 1
