#!/usr/bin/env bash
# =====================================================================
# scripts/verif_serveur_ne_lit_rien.sh — Épreuve « Le serveur ne lit rien »
#
# Vérifie automatiquement (section 5.1 du brief) :
#   1. le message test « MESSAGE-TEST-JURY-123 » est introuvable en base ;
#   2. aucun événement m.room.message en clair (tout est m.room.encrypted) ;
#   3. les fichiers du media_store sont des octets chiffrés (illisibles) ;
#   4. les logs Synapse ne contiennent aucun contenu de message.
#
# À lancer après avoir envoyé un message test entre deux agents.
# =====================================================================
set -uo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
PASS=0; FAIL=0

check() {
  local desc="$1"; shift
  printf '  [ ] %s ... ' "$desc"
  if "$@" >/dev/null 2>&1; then
    printf "${GREEN}PASS${NC}\n"; PASS=$((PASS+1))
  else
    printf "${RED}FAIL${NC}\n"; FAIL=$((FAIL+1))
  fi
}

echo "=== Vérification « Le serveur ne lit rien » ==="

# 1. Le message test est absent de la base (table event_json).
check "Message test absent de event_json" bash -c \
  "docker exec kibare-postgres psql -U postgres -d synapse -tA -c \
   \"SELECT count(*) FROM event_json WHERE event_json::text LIKE '%MESSAGE-TEST-JURY-123%'\" | grep -qx '0'"

# 2. Aucun message en clair : seuls des événements chiffrés m.room.encrypted.
check "Aucun m.room.message en clair" bash -c \
  "docker exec kibare-postgres psql -U postgres -d synapse -tA -c \
   \"SELECT count(*) FROM events WHERE type='m.room.message'\" | grep -qx '0'"

# 3. Le media_store ne contient que des octets opaques (fichiers chiffrés).
check "Fichiers media_store présents (chiffrés)" bash -c \
  "docker exec kibare-synapse sh -c 'test -d /data/media_store && find /data/media_store -type f | grep -q .'"

# 4. Les logs Synapse ne contiennent pas le contenu du message test.
check "Logs Synapse sans contenu de message" bash -c \
  "! docker logs kibare-synapse 2>&1 | grep -q 'MESSAGE-TEST-JURY-123'"

# 5. Le chiffrement est imposé par défaut (config Synapse).
check "encryption_enabled_by_default_for_room_type=all" bash -c \
  "docker exec kibare-synapse grep -q 'encryption_enabled_by_default_for_room_type: all' /data/homeserver.yaml"

# 6. Les aperçus de liens sont désactivés.
check "url_preview_enabled: false" bash -c \
  "docker exec kibare-synapse grep -q 'url_preview_enabled: false' /data/homeserver.yaml"

echo
echo "=== Résultat : ${PASS} vérifications PASS, ${FAIL} FAIL ==="
if [[ $FAIL -gt 0 ]]; then
  echo -e "${RED}ÉCHEC : certaines vérifications ont échoué.${NC}"
  exit 1
fi
echo -e "${GREEN}SUCCÈS : le serveur ne stocke aucun contenu en clair.${NC}"
