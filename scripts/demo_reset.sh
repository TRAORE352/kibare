#!/usr/bin/env bash
# =====================================================================
# scripts/demo_reset.sh — Réinitialise l'environnement de démo
# SUPPRIME toutes les données (volumes Docker) puis régénère les secrets.
# =====================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "⚠️  Cela va TOUT supprimer (messages, comptes, salons, données)."
read -r -p "Confirmer en tapant 'oui' : " answer
if [[ "$answer" != "oui" ]]; then
  echo "Annulé."
  exit 1
fi

docker compose down -v
rm -f secrets/*.txt
rm -f caddy/*.crt caddy/*.key caddy/*.srl
./scripts/init.sh

echo "Environnement réinitialisé. Lancez : docker compose up -d"
